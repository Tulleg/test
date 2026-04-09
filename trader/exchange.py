from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from trader.models import Signal, Trade


@dataclass
class ExecutionResult:
    order_id: str
    status: str
    fill_price: float


class PaperExchange:
    def place_order(self, mode: str, signal: Signal, position_size: float, risk_percent: float, rr: float) -> Trade:
        now = datetime.now(UTC)
        order_id = f"paper-{uuid4().hex[:10]}"
        return Trade(
            order_id=order_id,
            symbol=signal.symbol,
            mode=mode,  # type: ignore[arg-type]
            regime=signal.regime,
            setup_name=signal.setup_name,
            direction=signal.direction,
            entry_price=signal.entry,
            stop_price=signal.stop,
            take_profit_price=signal.target,
            risk_percent=risk_percent,
            reward_risk_ratio=rr,
            position_size=position_size,
            decision="accepted",
            rejection_reason=None,
            execution_status="filled",
            opened_at=now,
        )

