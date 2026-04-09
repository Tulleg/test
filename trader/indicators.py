from __future__ import annotations

from statistics import mean


def sma(values: list[float], period: int) -> float:
    if len(values) < period:
        return mean(values) if values else 0.0
    return mean(values[-period:])


def stddev(values: list[float], period: int) -> float:
    window = values[-period:] if len(values) >= period else values
    if len(window) < 2:
        return 0.0
    m = mean(window)
    var = sum((x - m) ** 2 for x in window) / (len(window) - 1)
    return var**0.5


def ema(values: list[float], period: int) -> float:
    """Exponential Moving Average – neuere Werte werden stärker gewichtet."""
    if not values:
        return 0.0
    # Multiplikator: je kürzer die Periode, desto stärker reagiert die EMA auf neue Preise
    k = 2.0 / (period + 1)
    result = values[0]
    for v in values[1:]:
        result = v * k + result * (1 - k)
    return result


def atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> float:
    if not highs or not lows or not closes:
        return 0.0
    trs: list[float] = []
    prev_close = closes[0]
    for h, l, c in zip(highs, lows, closes):
        tr = max(h - l, abs(h - prev_close), abs(l - prev_close))
        trs.append(tr)
        prev_close = c
    return sma(trs, period)

