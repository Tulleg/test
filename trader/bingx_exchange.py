from __future__ import annotations

from datetime import UTC, datetime

import ccxt

from trader.bingx_common import with_backoff
from trader.models import Signal, Trade


class BingXExecution:
    """BingX USDT perpetual: market entry with attached SL/TP (ccxt unified params)."""

    def __init__(self, exchange: ccxt.bingx, ccxt_symbol: str, display_symbol: str, max_spread_bps: float = 5.0) -> None:
        self.exchange = exchange
        self.ccxt_symbol = ccxt_symbol
        self.display_symbol = display_symbol
        self.max_spread_bps = max_spread_bps

    def check_spread(self) -> bool:
        """Prüft ob der aktuelle Bid-Ask-Spread innerhalb des erlaubten Limits liegt."""
        def _ticker() -> dict:
            return self.exchange.fetch_ticker(self.ccxt_symbol)

        ticker = with_backoff(_ticker)
        bid = ticker.get("bid")
        ask = ticker.get("ask")
        # Keine Spread-Daten verfügbar → Trade erlauben
        if not bid or not ask or float(bid) <= 0:
            return True
        spread_bps = ((float(ask) - float(bid)) / float(bid)) * 10_000
        return spread_bps <= self.max_spread_bps

    def fetch_equity_usdt(self) -> float:
        def _bal() -> dict:
            return self.exchange.fetch_balance()

        balance = with_backoff(_bal)
        usdt = balance.get("USDT") or {}
        total = usdt.get("total")
        if total is not None:
            return float(total)
        free = float(usdt.get("free") or 0)
        used = float(usdt.get("used") or 0)
        return free + used

    def place_order(self, mode: str, signal: Signal, position_size: float, risk_percent: float, rr: float) -> Trade:
        self.exchange.load_markets()
        side = "buy" if signal.direction == "long" else "sell"
        amount = float(self.exchange.amount_to_precision(self.ccxt_symbol, position_size))
        sl_trigger = float(self.exchange.price_to_precision(self.ccxt_symbol, signal.stop))
        tp_trigger = float(self.exchange.price_to_precision(self.ccxt_symbol, signal.target))

        bracket_params = {
            "stopLoss": {
                "triggerPrice": sl_trigger,
                "type": "STOP_MARKET",
                "workingType": "MARK_PRICE",
            },
            "takeProfit": {
                "triggerPrice": tp_trigger,
                "type": "TAKE_PROFIT_MARKET",
                "workingType": "MARK_PRICE",
            },
        }

        def _place(params: dict) -> dict:
            return self.exchange.create_order(self.ccxt_symbol, "market", side, amount, None, params)

        used_bracket = True
        try:
            order = with_backoff(lambda: _place(bracket_params))
        except ccxt.ExchangeError:
            used_bracket = False
            order = with_backoff(lambda: _place({}))

        now = datetime.now(UTC)
        order_id = str(order.get("id", ""))
        avg = order.get("average") or order.get("price") or signal.entry
        entry_price = float(avg) if avg is not None else signal.entry

        if entry_price == signal.entry and order.get("filled", 0):
            try:
                cost = float(order.get("cost") or 0)
                filled = float(order.get("filled") or 0)
                if filled > 0:
                    entry_price = cost / filled
            except (TypeError, ValueError):
                pass

        filled_amt = float(order.get("filled") or 0)
        size_for_exits = filled_amt if filled_amt > 0 else amount
        if not used_bracket and size_for_exits > 0:
            self._place_reduce_sl_tp(signal.direction, size_for_exits, sl_trigger, tp_trigger)

        return Trade(
            order_id=order_id,
            symbol=self.display_symbol,
            mode=mode,  # type: ignore[arg-type]
            regime=signal.regime,
            setup_name=signal.setup_name,
            direction=signal.direction,
            entry_price=entry_price,
            stop_price=signal.stop,
            take_profit_price=signal.target,
            risk_percent=risk_percent,
            reward_risk_ratio=rr,
            position_size=float(size_for_exits),
            decision="accepted",
            rejection_reason=None,
            execution_status="filled",
            opened_at=now,
        )

    def _place_reduce_sl_tp(self, direction: str, amount: float, sl_trigger: float, tp_trigger: float) -> None:
        close_side = "sell" if direction == "long" else "buy"
        amt = float(self.exchange.amount_to_precision(self.ccxt_symbol, amount))

        try:
            with_backoff(
                lambda: self.exchange.create_order(
                    self.ccxt_symbol,
                    "market",
                    close_side,
                    amt,
                    None,
                    {"reduceOnly": True, "stopLossPrice": sl_trigger},
                )
            )
        except ccxt.ExchangeError as exc:
            print(f"WARN: reduce SL failed: {exc}")

        try:
            with_backoff(
                lambda: self.exchange.create_order(
                    self.ccxt_symbol,
                    "market",
                    close_side,
                    amt,
                    None,
                    {"reduceOnly": True, "takeProfitPrice": tp_trigger},
                )
            )
        except ccxt.ExchangeError as exc:
            print(f"WARN: reduce TP failed: {exc}")

    def has_open_position(self) -> bool:
        return self.position_size() != 0.0

    def position_size(self) -> float:
        def _fetch() -> list:
            return self.exchange.fetch_positions([self.ccxt_symbol])

        positions = with_backoff(_fetch)
        for pos in positions:
            if pos.get("symbol") != self.ccxt_symbol:
                continue
            contracts = float(pos.get("contracts") or 0)
            if contracts != 0:
                return abs(contracts)
        return 0.0

    def close_position_market(self, direction: str, amount: float) -> dict:
        close_side = "sell" if direction == "long" else "buy"
        amt = float(self.exchange.amount_to_precision(self.ccxt_symbol, amount))

        def _close() -> dict:
            return self.exchange.create_order(
                self.ccxt_symbol,
                "market",
                close_side,
                amt,
                None,
                {"reduceOnly": True},
            )

        return with_backoff(_close)

    def fetch_exit_price_approx(self) -> float:
        def _t() -> dict:
            return self.exchange.fetch_ticker(self.ccxt_symbol)

        ticker = with_backoff(_t)
        last = ticker.get("last") or ticker.get("close")
        if last is None:
            return 0.0
        return float(last)
