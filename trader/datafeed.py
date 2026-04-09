from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

from trader.models import Candle


class MockDataFeed:
    def __init__(self, seed_price: float = 60_000.0) -> None:
        self.price = seed_price
        self.ts = datetime.now(UTC) - timedelta(minutes=300)

    def next_candle(self, timeframe_minutes: int = 5) -> Candle:
        self.ts = self.ts + timedelta(minutes=timeframe_minutes)
        drift = random.uniform(-0.0012, 0.0012)
        intrabar = random.uniform(0.0008, 0.0035)
        open_price = self.price
        close_price = max(1.0, open_price * (1.0 + drift))
        high = max(open_price, close_price) * (1.0 + intrabar)
        low = min(open_price, close_price) * (1.0 - intrabar)
        volume = random.uniform(50, 400)
        self.price = close_price
        return Candle(ts=self.ts, open=open_price, high=high, low=low, close=close_price, volume=volume)

