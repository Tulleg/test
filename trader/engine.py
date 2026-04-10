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
from trader.display import StatusDisplay
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
        # Display und Laufzeit-Tracking
        self.display = StatusDisplay()
        self._status_msg = "Warte auf Signal..."
        self._candle_count = 0
        self._start_time = datetime.now(UTC)

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
            if settings.live_feed:
                # Echter Marktdaten-Feed, aber Orders werden nur simuliert (kein echtes Geld)
                self.datafeed = BingXDataFeed(settings.ccxt_symbol, settings.timeframe_minutes)
                self.candles = self.datafeed.warmup(200)
            else:
                self.datafeed = MockDataFeed()
            self._exchange = PaperExchange()

    def _refresh_equity_live(self) -> None:
        if self.settings.execution == "live" and self.bingx_exec:
            try:
                self.settings.account_equity = self.bingx_exec.fetch_equity_usdt()
            except Exception as exc:
                self.logger.log_event({"decision": "equity_fetch_error", "error": str(exc)})

    def _redraw(self) -> None:
        """Zeichnet die Status-Box neu."""
        laufzeit = datetime.now(UTC) - self._start_time
        self.display.draw(
            symbol=self.settings.symbol,
            execution=self.settings.execution,
            mode=self.settings.mode,
            equity=self.settings.account_equity,
            day_pnl=self.realized_pnl_today,
            total_trades=self.total_trades,
            wins=self.wins,
            losses=self.losses,
            open_trade=self.open_trade,
            last_candle=self._last_candle,
            candle_count=self._candle_count,
            laufzeit=laufzeit,
            status_msg=self._status_msg,
        )

    def _manual_confirm(self, signal: Signal, risk: RiskCheck) -> bool:
        self._status_msg = "Bestätigung erforderlich"
        self._redraw()
        # Signal-Details klar unterhalb der Box ausgeben
        pfeil = "▲ LONG" if signal.direction == "long" else "▼ SHORT"
        print()
        print("  ┌─── NEUES SIGNAL ──────────────────────────────────┐")
        print(f"  │  {pfeil}  {signal.setup_name} ({signal.regime})")
        print(f"  │  Entry:  {signal.entry:.2f}")
        print(f"  │  Stop:   {signal.stop:.2f}")
        print(f"  │  Target: {signal.target:.2f}")
        print(f"  │  CRV:    {risk.rr:.2f}   Risiko: {risk.risk_percent:.2f}%   Größe: {risk.position_size:.4f}")
        print(f"  │  Grund:  {signal.reason}")
        print("  └───────────────────────────────────────────────────┘")
        print(f"\n  → confirm / reject  (Timeout: {self.settings.manual_timeout_sec}s): ", end="", flush=True)
        ready, _, _ = select.select([sys.stdin], [], [], self.settings.manual_timeout_sec)
        if not ready:
            print("timeout")
            self.display.add_event(f"Signal Timeout: {signal.direction.upper()} @ {signal.entry:.0f}")
            self._status_msg = "Timeout – Signal abgelehnt"
            return False
        answer = sys.stdin.readline().strip().lower()
        if answer == "confirm":
            self.display.add_event(f"Signal bestätigt: {signal.direction.upper()} @ {signal.entry:.0f}")
        else:
            self.display.add_event(f"Signal abgelehnt: {signal.direction.upper()} @ {signal.entry:.0f}")
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
        vorzeichen = "+" if pnl >= 0 else ""
        self.display.add_event(
            f"Geschlossen: {exit_reason}  PnL: {vorzeichen}{pnl:.2f} $  "
            f"Tag: {vorzeichen}{self.realized_pnl_today:.2f} $"
        )
        self._status_msg = "Warte auf Signal..."
        self.open_trade = None

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
            if self.open_trade:
                self._status_msg = "Position offen – warte auf neue Kerze"
            else:
                self._status_msg = "Warte auf neue Kerze..."
            return

        self._last_candle = candle
        self._candle_count += 1
        self.candles.append(candle)
        self._trim_candles()

        if self.settings.execution == "paper":
            self._mark_to_market(candle)
        else:
            self._sync_live_position()

        if self.open_trade:
            self._status_msg = "Position offen"
            return

        if self.settings.timeframe_minutes < 5:
            self.rejections += 1
            self.rejection_counts["timeframe_below_5m"] += 1
            self.logger.log_event({"decision": "rejected", "rejectionReason": "timeframe_below_5m"})
            self._status_msg = "Abgelehnt: Timeframe unter 5 min"
            return

        if self._session_end():
            self.logger.log_event({"decision": "skipped", "reason": "session_end"})
            self._status_msg = "Session beendet – kein Trading"
            return

        if self._risk_guard():
            self.logger.log_event({"decision": "blocked", "reason": "daily_loss_limit_reached"})
            self._status_msg = "Tagesverlust-Limit erreicht"
            return

        strategy_result = self.strategy.evaluate(self.candles)
        if not strategy_result.signal:
            self._status_msg = f"Kein Signal ({strategy_result.rejection_reason})"
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
            self.display.add_event(f"Signal abgelehnt: {risk.reason}")
            self._status_msg = f"Signal abgelehnt: {risk.reason}"
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
                self.display.add_event(f"Signal abgelehnt: Spread zu groß (max {self.settings.max_spread_bps} bps)")
                self._status_msg = "Signal abgelehnt: Spread zu groß"
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
        self.display.add_event(
            f"Trade eröffnet: {trade.direction.upper()} @ {trade.entry_price:.0f}  "
            f"SL: {trade.stop_price:.0f}  TP: {trade.take_profit_price:.0f}"
        )
        self._status_msg = "Position offen"

    def _manuell_schliessen(self) -> None:
        """Schließt die offene Position sofort zum letzten bekannten Preis."""
        if not self.open_trade:
            return
        if self.settings.execution == "live" and self.bingx_exec:
            self._session_flatten_live()
        else:
            exit_px = self._last_candle.close if self._last_candle else self.open_trade.entry_price
            pnl = self._pnl_at_exit(self.open_trade, exit_px)
            self._close_trade(self.open_trade, pnl, "manual_close")

    def _warte_mit_anzeige(self, sekunden: int) -> str | None:
        """Wartet N Sekunden, zeichnet Display jede Sekunde neu und prüft auf Tastaturbefehle.
        Gibt 'q' zurück wenn der Nutzer beenden will, sonst None."""
        for _ in range(max(1, sekunden)):
            self._redraw()
            # Non-blocking: 1 Sekunde auf Eingabe warten
            bereit, _, _ = select.select([sys.stdin], [], [], 1.0)
            if bereit:
                zeile = sys.stdin.readline().strip().lower()
                if zeile == "c":
                    if self.open_trade:
                        self._manuell_schliessen()
                        self.display.add_event("Position manuell geschlossen")
                    else:
                        self.display.add_event("Keine offene Position zum Schließen")
                elif zeile == "q":
                    return "q"
        return None

    def _schreibe_summary(self) -> None:
        winrate = (self.wins / self.total_trades * 100.0) if self.total_trades else 0.0
        profit_factor = (self.gross_profit / self.gross_loss) if self.gross_loss > 0 else float("inf")
        expectancy = (self.realized_pnl_today / self.total_trades) if self.total_trades else 0.0
        rej_detail = " ".join(f"{k}={v}" for k, v in sorted(self.rejection_counts.items()))
        self.logger.write_daily_summary(
            f"summary trades={self.total_trades} wins={self.wins} losses={self.losses} "
            f"winrate={winrate:.2f}% realized_pnl={self.realized_pnl_today:.2f} "
            f"profit_factor={profit_factor:.2f} expectancy={expectancy:.2f} "
            f"max_drawdown={self.max_drawdown:.2f} "
            f"rejections={self.rejections} [{rej_detail}]"
        )

    def run(self) -> None:
        self._start_time = datetime.now(UTC)
        try:
            while True:
                self.step()
                cmd = self._warte_mit_anzeige(self.settings.loop_interval_sec)
                if cmd == "q":
                    break
        except KeyboardInterrupt:
            pass
        finally:
            # Summary immer schreiben, egal wie die App beendet wird
            self._schreibe_summary()
            print("\nRun beendet.")
