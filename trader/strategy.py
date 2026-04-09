from __future__ import annotations

from dataclasses import dataclass

from trader.indicators import atr, ema, sma, stddev
from trader.models import Candle, Signal


@dataclass
class StrategyResult:
    signal: Signal | None
    rejection_reason: str | None = None


class HybridStrategy:
    def __init__(self, symbol: str, min_rr: float) -> None:
        self.symbol = symbol
        self.min_rr = min_rr

    def evaluate(self, candles: list[Candle]) -> StrategyResult:
        if len(candles) < 60:
            return StrategyResult(signal=None, rejection_reason="not_enough_data")

        closes = [c.close for c in candles]
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        volumes = [c.volume for c in candles]
        last = candles[-1]

        ema_fast = ema(closes, 20)
        ema_slow = ema(closes, 50)
        vol_mean = sma(volumes, 20)
        vol_now = volumes[-1]
        range_std = stddev(closes, 20)
        atr_now = atr(highs, lows, closes, 14)

        regime = "trend" if abs(ema_fast - ema_slow) > (0.15 * atr_now) else "range"

        if regime == "trend":
            swing_high = max(highs[-8:-1])
            swing_low = min(lows[-8:-1])
            if last.close > ema_slow and last.close >= swing_high and vol_now >= 0.85 * vol_mean:
                stop = max(swing_low, last.close - 1.5 * atr_now)
                target = last.close + max((last.close - stop) * self.min_rr, 2.0 * atr_now)
                return StrategyResult(
                    signal=Signal(
                        symbol=self.symbol,
                        regime="trend",
                        setup_name="trend_breakout",
                        direction="long",
                        entry=last.close,
                        stop=stop,
                        target=target,
                        confidence=0.68,
                        reason="trend breakout above swing high with volume confirmation",
                    )
                )
            if last.close < ema_slow and last.close <= swing_low and vol_now >= 0.85 * vol_mean:
                stop = min(swing_high, last.close + 1.5 * atr_now)
                target = last.close - max((stop - last.close) * self.min_rr, 2.0 * atr_now)
                return StrategyResult(
                    signal=Signal(
                        symbol=self.symbol,
                        regime="trend",
                        setup_name="trend_breakout",
                        direction="short",
                        entry=last.close,
                        stop=stop,
                        target=target,
                        confidence=0.68,
                        reason="trend breakdown below swing low with volume confirmation",
                    )
                )
            # Fallback momentum entry to avoid missing persistent directional moves.
            if last.close > ema_fast + 0.4 * atr_now:
                stop = last.close - 1.2 * atr_now
                target = last.close + (last.close - stop) * self.min_rr
                return StrategyResult(
                    signal=Signal(
                        symbol=self.symbol,
                        regime="trend",
                        setup_name="trend_breakout",
                        direction="long",
                        entry=last.close,
                        stop=stop,
                        target=target,
                        confidence=0.56,
                        reason="trend momentum continuation above fast average",
                    )
                )
            if last.close < ema_fast - 0.4 * atr_now:
                stop = last.close + 1.2 * atr_now
                target = last.close - (stop - last.close) * self.min_rr
                return StrategyResult(
                    signal=Signal(
                        symbol=self.symbol,
                        regime="trend",
                        setup_name="trend_breakout",
                        direction="short",
                        entry=last.close,
                        stop=stop,
                        target=target,
                        confidence=0.56,
                        reason="trend momentum continuation below fast average",
                    )
                )
            return StrategyResult(signal=None, rejection_reason="trend_setup_not_triggered")

        basis = sma(closes, 20)
        band = max(1.2 * range_std, 0.8 * atr_now)
        upper = basis + band
        lower = basis - band
        if last.close < lower:
            stop = last.close - max(atr_now, 0.6 * band)
            target = basis
            return StrategyResult(
                signal=Signal(
                    symbol=self.symbol,
                    regime="range",
                    setup_name="mean_reversion",
                    direction="long",
                    entry=last.close,
                    stop=stop,
                    target=target,
                    confidence=0.61,
                    reason="range mean reversion from lower band",
                )
            )
        if last.close > upper:
            stop = last.close + max(atr_now, 0.6 * band)
            target = basis
            return StrategyResult(
                signal=Signal(
                    symbol=self.symbol,
                    regime="range",
                    setup_name="mean_reversion",
                    direction="short",
                    entry=last.close,
                    stop=stop,
                    target=target,
                    confidence=0.61,
                    reason="range mean reversion from upper band",
                )
            )

        return StrategyResult(signal=None, rejection_reason="range_setup_not_triggered")

