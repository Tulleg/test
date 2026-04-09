from __future__ import annotations

import os
import time
from typing import Any

import ccxt


def timeframe_from_minutes(minutes: int) -> str:
    if minutes < 5:
        raise ValueError("timeframe must be >= 5 minutes")
    return f"{minutes}m"


def bingx_swap_public() -> ccxt.bingx:
    return ccxt.bingx(
        {
            "enableRateLimit": True,
            "options": {"defaultType": "swap"},
        }
    )


def bingx_swap_private(api_key: str | None, secret: str | None) -> ccxt.bingx:
    if not api_key or not secret:
        raise ValueError("BINGX_API_KEY and BINGX_API_SECRET are required for live execution")
    return ccxt.bingx(
        {
            "apiKey": api_key,
            "secret": secret,
            "enableRateLimit": True,
            "options": {"defaultType": "swap"},
        }
    )


def load_bingx_keys_from_env() -> tuple[str | None, str | None]:
    return os.getenv("BINGX_API_KEY"), os.getenv("BINGX_API_SECRET")


def with_backoff(fn: Any, max_retries: int = 4, base_delay: float = 0.5) -> Any:
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            return fn()
        except (ccxt.NetworkError, ccxt.DDoSProtection, ccxt.RequestTimeout) as exc:
            last_err = exc
            time.sleep(base_delay * (2**attempt))
    assert last_err is not None
    raise last_err
