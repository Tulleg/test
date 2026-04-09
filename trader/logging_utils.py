from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from trader.models import Trade


class TradeLogger:
    def __init__(self, logs_dir: str) -> None:
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.trades_file = self.logs_dir / "trades.jsonl"
        self.summary_file = self.logs_dir / "daily_summary.log"

    def log_event(self, event: dict[str, Any]) -> None:
        payload = {"timestamp": datetime.now(UTC).isoformat(), **event}
        with self.trades_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload) + "\n")

    def log_trade(self, trade: Trade) -> None:
        payload = asdict(trade)
        payload["opened_at"] = trade.opened_at.isoformat()
        payload["closed_at"] = trade.closed_at.isoformat() if trade.closed_at else None
        self.log_event(payload)

    def write_daily_summary(self, text: str) -> None:
        stamp = datetime.now(UTC).isoformat()
        with self.summary_file.open("a", encoding="utf-8") as fh:
            fh.write(f"{stamp} {text}\n")

