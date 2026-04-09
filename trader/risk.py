from __future__ import annotations

from dataclasses import dataclass

from trader.models import Signal


@dataclass
class RiskCheck:
    ok: bool
    reason: str | None
    position_size: float = 0.0
    risk_percent: float = 0.0
    rr: float = 0.0


def rr_ratio(signal: Signal) -> float:
    risk = abs(signal.entry - signal.stop)
    reward = abs(signal.target - signal.entry)
    if risk <= 0:
        return 0.0
    return reward / risk


def compute_position_size(equity: float, risk_per_trade: float, entry: float, stop: float) -> float:
    risk_amount = equity * risk_per_trade
    stop_dist = abs(entry - stop)
    if stop_dist <= 0:
        return 0.0
    return risk_amount / stop_dist


def validate_signal(
    signal: Signal,
    equity: float,
    risk_per_trade: float,
    min_rr: float,
    timeframe_minutes: int,
) -> RiskCheck:
    if timeframe_minutes < 5:
        return RiskCheck(ok=False, reason="timeframe_below_5m")
    if risk_per_trade > 0.01:
        return RiskCheck(ok=False, reason="risk_per_trade_above_1pct")
    if signal.direction == "long" and not (signal.stop < signal.entry < signal.target):
        return RiskCheck(ok=False, reason="invalid_long_sl_tp")
    if signal.direction == "short" and not (signal.target < signal.entry < signal.stop):
        return RiskCheck(ok=False, reason="invalid_short_sl_tp")

    rr = rr_ratio(signal)
    if rr < min_rr:
        return RiskCheck(ok=False, reason="rr_below_min", rr=rr)

    size = compute_position_size(equity, risk_per_trade, signal.entry, signal.stop)
    if size <= 0:
        return RiskCheck(ok=False, reason="size_invalid", rr=rr)

    return RiskCheck(ok=True, reason=None, position_size=size, risk_percent=risk_per_trade * 100.0, rr=rr)

