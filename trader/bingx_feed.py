from __future__ import annotations

from datetime import UTC, datetime

import ccxt

from trader.bingx_common import bingx_swap_public, timeframe_from_minutes, with_backoff
from trader.models import Candle


def _row_to_candle(row: list) -> Candle:
    ts_ms, o, h, l, c, v = row
    return Candle(
        ts=datetime.fromtimestamp(ts_ms / 1000.0, tz=UTC),
        open=float(o),
        high=float(h),
        low=float(l),
        close=float(c),
        volume=float(v),
    )


class BingXDataFeed:
    """Public OHLCV from BingX perpetual (swap) markets."""

    def __init__(self, ccxt_symbol: str, timeframe_minutes: int = 5) -> None:
        if timeframe_minutes < 5:
            raise ValueError("BingX feed requires timeframe >= 5m")
        self._exchange: ccxt.bingx = bingx_swap_public()
        self.ccxt_symbol = ccxt_symbol
        self._tf = timeframe_from_minutes(timeframe_minutes)
        self._last_emitted_ts: int | None = None

    def warmup(self, limit: int = 200) -> list[Candle]:
        def _fetch() -> list:
            return self._exchange.fetch_ohlcv(self.ccxt_symbol, self._tf, limit=limit)

        ohlcv = with_backoff(_fetch)
        if len(ohlcv) >= 2:
            ohlcv = ohlcv[:-1]
        candles = [_row_to_candle(row) for row in ohlcv]
        if candles:
            self._last_emitted_ts = int(candles[-1].ts.timestamp() * 1000)
        return candles

    def next_candle(self, timeframe_minutes: int) -> Candle | None:
        if timeframe_minutes < 5:
            raise ValueError("timeframe must be >= 5 minutes")
        tf = timeframe_from_minutes(timeframe_minutes)
        if tf != self._tf:
            self._tf = tf

        def _fetch() -> list:
            return self._exchange.fetch_ohlcv(self.ccxt_symbol, self._tf, limit=3)

        ohlcv = with_backoff(_fetch)
        if len(ohlcv) < 2:
            return None
        closed_row = ohlcv[-2]
        ts_ms = int(closed_row[0])
        if self._last_emitted_ts is not None and ts_ms <= self._last_emitted_ts:
            return None
        self._last_emitted_ts = ts_ms
        return _row_to_candle(closed_row)
