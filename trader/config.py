from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

ExecutionMode = Literal["paper", "live"]


@dataclass
class Settings:
    symbol: str = "BTC-USDT"
    ccxt_symbol: str = "BTC/USDT:USDT"
    execution: ExecutionMode = "paper"
    mode: str = "manual"
    timeframe_minutes: int = 5
    intraday_only: bool = True
    risk_per_trade: float = 0.01
    min_rr: float = 2.0
    daily_loss_limit_pct: float = 0.03
    account_equity: float = 10_000.0
    max_open_positions: int = 1
    fees_bps: float = 4.0
    max_spread_bps: float = 5.0
    manual_timeout_sec: int = 30
    logs_dir: str = "logs"
    loop_steps: int = 200
    loop_interval_sec: int = 2
    session_end_hour_utc: int = 23
    bingx_api_key: str | None = None
    bingx_api_secret: str | None = None

    @classmethod
    def from_env(cls, mode_override: str | None = None) -> "Settings":
        mode = mode_override or os.getenv("TRADER_MODE", "manual")
        execution_raw = os.getenv("TRADER_EXECUTION", "paper").lower()
        execution: ExecutionMode = "live" if execution_raw == "live" else "paper"
        return cls(
            mode=mode,
            execution=execution,
            ccxt_symbol=os.getenv("TRADER_CCXT_SYMBOL", "BTC/USDT:USDT"),
            timeframe_minutes=int(os.getenv("TRADER_TIMEFRAME_MIN", "5")),
            risk_per_trade=min(float(os.getenv("TRADER_RISK_PER_TRADE", "0.01")), 0.01),
            min_rr=float(os.getenv("TRADER_MIN_RR", "2.0")),
            daily_loss_limit_pct=float(os.getenv("TRADER_DAILY_LOSS_LIMIT", "0.03")),
            account_equity=float(os.getenv("TRADER_ACCOUNT_EQUITY", "10000")),
            loop_interval_sec=int(os.getenv("TRADER_LOOP_INTERVAL_SEC", "2")),
            session_end_hour_utc=int(os.getenv("TRADER_SESSION_END_HOUR_UTC", "23")),
            bingx_api_key=os.getenv("BINGX_API_KEY"),
            bingx_api_secret=os.getenv("BINGX_API_SECRET"),
        )
