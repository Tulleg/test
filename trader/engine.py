from __future__ import annotations

import select
import sys
import time
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from trader.bingx_common import bingx_swap_private, load_bingx_keys_from_env
from trader.bingx_exchange import BingXExecution
from trader.bingx_feed import BingXDataFeed
from trader.config import Settings
from trader.datafeed import MockDataFeed
from trader.exchange import PaperExchange
from trader.logging_utils import TradeLogger
from trader.models import Candle, Signal, Trade
from trader.risk import RiskCheck, validate_signal
from trader.strategy import HybridStrategy


class TradingEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.strategy = HybridStrategy(symbol=settings.symbol, min_rr=settings.min_rr)
        self.logger = TradeLogger(settings.logs_dir)
        self.candles: list[Candle] = []
        self.open_trade: Trade | None = None
        self.realized_pnl_today = 0.0
        self.wins = 0
        self.losses = 0
        self.rejections = 0
        self.total_trades = 0
        self.gross_profit = 0.0
        self.gross_loss = 0.0
        self.peak_equity = settings.account_equity
        self.max_drawdown = 0.0
        # Zählt Ablehnungen aufgeschlüsselt nach Grund
        self.rejection_counts: dict[str, int] = defaultdict(int)
        self.bingx_exec: BingXExecution | None = None
        self._exchange: Any = None
        self._last_candle: Candle | None = None

        if settings.execution == "live":
            key, secret = settings.bingx_api_key, settings.bingx_api_secret
            if not key or not secret:
                key, secret = load_bingx_keys_from_env()
            ex = bingx_swap_private(key, secret)
            self.bingx_exec = BingXExecution(ex, settings.ccxt_symbol, settings.symbol, settings.max_spread_bps)
            self._exchange = self.bingx_exec
            self.datafeed = BingXDataFeed(settings.ccxt_symbol, settings.timeframe_minutes)
            self.candles = self.datafeed.warmup(200)
            self.settings.account_equity = self.bingx_exec.fetch_equity_usdt()
        else:
            self.datafeed = MockDataFeed()
            self._exchange = PaperExchange()

    def _refresh_equity_live(self) -> None:
        if self.settings.execution == "live" and self.bingx_exec:
            try:
                self.settings.account_equity = self.bingx_exec.fetch_equity_usdt()
            except Exception as exc:
                self.logger.log_event({"decision": "equity_fetch_error", "error": str(exc)})

    def _manual_confirm(self, signal: Signal, risk: RiskCheck) -> bool:
        print("WARNING: Neues Signal erkannt (manual bestaetigen).")
        print(
            f"Signal {signal.setup_name} {signal.direction.upper()} "
            f"entry={signal.entry:.2f} stop={signal.stop:.2f} target={signal.target:.2f} "
            f"CRV={risk.rr:.2f} size={risk.position_size:.4f} risk={risk.risk_percent:.2f}% "
            f"reason={signal.reason}"
        )
        print(f"Bitte eingeben: confirm oder reject (timeout {self.settings.manual_timeout_sec}s): ", end="", flush=True)
        ready, _, _ = select.select([sys.stdin], [], [], self.settings.manual_timeout_sec)
        if not ready:
            print("timeout -> rejected")
            return False
        answer = sys.stdin.readline().strip().lower()
        return answer == "confirm"

    def _session_end(self) -> bool:
        now = datetime.now(UTC)
        return now.hour >= self.settings.session_end_hour_utc

    def _risk_guard(self) -> bool:
        return self.realized_pnl_today <= -(self.settings.account_equity * self.settings.daily_loss_limit_pct)

    def _pnl_at_exit(self, trade: Trade, exit_price: float) -> float:
        if trade.direction == "long":
            return (exit_price - trade.entry_price) * trade.position_size
        return (trade.entry_price - exit_price) * trade.position_size

    def _mark_to_market(self, candle: Candle) -> None:
        if not self.open_trade:
            return
        t = self.open_trade
        if t.direction == "long":
            hit_sl = candle.low <= t.stop_price
            hit_tp = candle.high >= t.take_profit_price
            if hit_sl or hit_tp:
                exit_price = t.stop_price if hit_sl else t.take_profit_price
                pnl = self._pnl_at_exit(t, exit_price)
                self._close_trade(t, pnl, "stop_loss" if hit_sl else "take_profit")
        else:
            hit_sl = candle.high >= t.stop_price
            hit_tp = candle.low <= t.take_profit_price
            if hit_sl or hit_tp:
                exit_price = t.stop_price if hit_sl else t.take_profit_price
                pnl = self._pnl_at_exit(t, exit_price)
                self._close_trade(t, pnl, "stop_loss" if hit_sl else "take_profit")

    def _sync_live_position(self) -> None:
        if self.settings.execution != "live" or not self.bingx_exec or not self.open_trade:
            return
        if self.bingx_exec.has_open_position():
            return
        exit_px = self.bingx_exec.fetch_exit_price_approx()
        if exit_px <= 0:
            exit_px = self.open_trade.entry_price
        pnl = self._pnl_at_exit(self.open_trade, exit_px)
        self._close_trade(self.open_trade, pnl, "exchange_close")

    def _session_flatten_live(self) -> None:
        if self.settings.execution != "live" or not self.bingx_exec or not self.open_trade:
            return
        if not self.bingx_exec.has_open_position():
            self._sync_live_position()
            return
        try:
            self.bingx_exec.close_position_market(self.open_trade.direction, self.open_trade.position_size)
        except Exception as exc:
            self.logger.log_event({"decision": "flatten_error", "error": str(exc)})
            return
        exit_px = self.bingx_exec.fetch_exit_price_approx()
        if self.open_trade:
            pnl = self._pnl_at_exit(self.open_trade, exit_px)
            self._close_trade(self.open_trade, pnl, "session_flat")

    def _close_trade(self, trade: Trade, pnl: float, exit_reason: str) -> None:
        trade.closed_at = datetime.now(UTC)
        trade.realized_pnl = pnl
        trade.execution_status = f"closed_{exit_reason}"
        self.realized_pnl_today += pnl
        self.total_trades += 1
        if pnl >= 0:
            self.wins += 1
            self.gross_profit += pnl
        else:
            self.losses += 1
            self.gross_loss += abs(pnl)
        # Drawdown: Rückgang vom bisherigen Eigenkapital-Höchststand
        running_equity = self.settings.account_equity + self.realized_pnl_today
        if running_equity > self.peak_equity:
            self.peak_equity = running_equity
        drawdown = self.peak_equity - running_equity
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown
        self.logger.log_trade(trade)
        self.logger.write_daily_summary(
            f"trade_closed order={trade.order_id} pnl={pnl:.2f} day_pnl={self.realized_pnl_today:.2f}"
        )
        print(f"Position geschlossen: {exit_reason}, pnl={pnl:.2f}, day_pnl={self.realized_pnl_today:.2f}")
        self.open_trade = None

    def _print_status(self) -> None:
        print(
            f"execution={self.settings.execution} mode={self.settings.mode} equity={self.settings.account_equity:.2f} "
            f"day_pnl={self.realized_pnl_today:.2f} open={'yes' if self.open_trade else 'no'} "
            f"wins={self.wins} losses={self.losses} rej={self.rejections}"
        )

    def _trim_candles(self) -> None:
        max_len = 500
        if len(self.candles) > max_len:
            self.candles = self.candles[-max_len:]

    def step(self) -> None:
        self._refresh_equity_live()

        if self._session_end() and self.open_trade:
            if self.settings.execution == "live":
                self._session_flatten_live()
            else:
                t = self.open_trade
                exit_px = self._last_candle.close if self._last_candle else t.entry_price
                self._close_trade(t, self._pnl_at_exit(t, exit_px), "session_flat")
            if self.open_trade:
                return

        candle = self.datafeed.next_candle(self.settings.timeframe_minutes)
        if candle is None:
            self._sync_live_position()
            return

        self._last_candle = candle
        self.candles.append(candle)
        self._trim_candles()

        if self.settings.execution == "paper":
            self._mark_to_market(candle)
        else:
            self._sync_live_position()

        if self.open_trade:
            return

        if self.settings.timeframe_minutes < 5:
            self.rejections += 1
            self.rejection_counts["timeframe_below_5m"] += 1
            self.logger.log_event({"decision": "rejected", "rejectionReason": "timeframe_below_5m"})
            return

        if self._session_end():
            self.logger.log_event({"decision": "skipped", "reason": "session_end"})
            return

        if self._risk_guard():
            self.logger.log_event({"decision": "blocked", "reason": "daily_loss_limit_reached"})
            return

        strategy_result = self.strategy.evaluate(self.candles)
        if not strategy_result.signal:
            self.logger.log_event({"decision": "no_signal", "reason": strategy_result.rejection_reason})
            return

        signal = strategy_result.signal
        risk = validate_signal(
            signal=signal,
            equity=self.settings.account_equity,
            risk_per_trade=self.settings.risk_per_trade,
            min_rr=self.settings.min_rr,
            timeframe_minutes=self.settings.timeframe_minutes,
        )
        if not risk.ok:
            self.rejections += 1
            self.rejection_counts[risk.reason or "unknown"] += 1
            self.logger.log_event(
                {
                    "symbol": signal.symbol,
                    "mode": self.settings.mode,
                    "regime": signal.regime,
                    "setupName": signal.setup_name,
                    "direction": signal.direction,
                    "entryPrice": signal.entry,
                    "stopPrice": signal.stop,
                    "takeProfitPrice": signal.target,
                    "decision": "rejected",
                    "rejectionReason": risk.reason,
                    "rewardRiskRatio": risk.rr,
                }
            )
            print(f"WARNUNG: Signal abgelehnt ({risk.reason})")
            return

        # Spread-Check: Nur im Live-Modus prüfen ob Bid-Ask-Spread akzeptabel ist
        if self.settings.execution == "live" and self.bingx_exec:
            if not self.bingx_exec.check_spread():
                self.rejections += 1
                self.rejection_counts["spread_too_wide"] += 1
                self.logger.log_event(
                    {
                        "symbol": signal.symbol,
                        "decision": "rejected",
                        "rejectionReason": "spread_too_wide",
                        "max_spread_bps": self.settings.max_spread_bps,
                    }
                )
                print(f"WARNUNG: Signal abgelehnt (Spread zu groß, max={self.settings.max_spread_bps} bps)")
                return

        allowed = True
        if self.settings.mode == "manual":
            allowed = self._manual_confirm(signal, risk)
            if not allowed:
                self.rejections += 1
                self.rejection_counts["manual_reject_or_timeout"] += 1
                self.logger.log_event(
                    {
                        "symbol": signal.symbol,
                        "mode": self.settings.mode,
                        "regime": signal.regime,
                        "setupName": signal.setup_name,
                        "direction": signal.direction,
                        "entryPrice": signal.entry,
                        "stopPrice": signal.stop,
                        "takeProfitPrice": signal.target,
                        "decision": "rejected",
                        "rejectionReason": "manual_reject_or_timeout",
                    }
                )
                return

        trade = self._exchange.place_order(
            mode=self.settings.mode,
            signal=signal,
            position_size=risk.position_size,
            risk_percent=risk.risk_percent,
            rr=risk.rr,
        )
        self.logger.log_trade(trade)
        self.open_trade = trade
        print(
            f"Trade eroefnet: {trade.direction} {trade.setup_name} entry={trade.entry_price:.2f} "
            f"sl={trade.stop_price:.2f} tp={trade.take_profit_price:.2f} rr={trade.reward_risk_ratio:.2f}"
        )

    def run(self, steps: int) -> None:
        print(f"Start TradingEngine (execution={self.settings.execution}) ...")
        for i in range(steps):
            self.step()
            if i % 5 == 0:
                self._print_status()
            time.sleep(self.settings.loop_interval_sec)

        winrate = (self.wins / self.total_trades * 100.0) if self.total_trades else 0.0
        profit_factor = (self.gross_profit / self.gross_loss) if self.gross_loss > 0 else float("inf")
        expectancy = (self.realized_pnl_today / self.total_trades) if self.total_trades else 0.0
        # Ablehnungen nach Grund als lesbarer String (z.B. "rr_below_min=3 manual_reject_or_timeout=1")
        rej_detail = " ".join(f"{k}={v}" for k, v in sorted(self.rejection_counts.items()))
        self.logger.write_daily_summary(
            f"summary trades={self.total_trades} wins={self.wins} losses={self.losses} "
            f"winrate={winrate:.2f}% realized_pnl={self.realized_pnl_today:.2f} "
            f"profit_factor={profit_factor:.2f} expectancy={expectancy:.2f} "
            f"max_drawdown={self.max_drawdown:.2f} "
            f"rejections={self.rejections} [{rej_detail}]"
        )
        print("Run beendet.")
