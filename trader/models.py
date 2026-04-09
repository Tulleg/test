from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


Direction = Literal["long", "short"]
Regime = Literal["trend", "range"]
SetupName = Literal["trend_breakout", "mean_reversion"]


@dataclass
class Candle:
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class Signal:
    symbol: str
    regime: Regime
    setup_name: SetupName
    direction: Direction
    entry: float
    stop: float
    target: float
    confidence: float
    reason: str


@dataclass
class Trade:
    order_id: str
    symbol: str
    mode: Literal["manual", "auto"]
    regime: Regime
    setup_name: SetupName
    direction: Direction
    entry_price: float
    stop_price: float
    take_profit_price: float
    risk_percent: float
    reward_risk_ratio: float
    position_size: float
    decision: Literal["accepted", "rejected"]
    rejection_reason: str | None
    execution_status: str
    opened_at: datetime
    closed_at: datetime | None = None
    realized_pnl: float = 0.0
    fees: float = 0.0

