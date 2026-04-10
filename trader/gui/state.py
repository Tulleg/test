from __future__ import annotations

import queue
import threading
from dataclasses import dataclass, field

from trader.models import Candle, Trade


@dataclass
class GUIState:
    """Gemeinsamer, thread-sicherer Datenbehälter zwischen Engine und GUI.

    Die Engine schreibt hier rein (mit Lock), die GUI liest daraus (mit Lock).
    Kommandos fließen über Queues in beide Richtungen.
    """

    lock: threading.Lock = field(default_factory=threading.Lock)

    # Marktdaten und Trade-Zustand
    candles: list[Candle] = field(default_factory=list)
    open_trade: Trade | None = None

    # Statistiken
    equity: float = 0.0
    day_pnl: float = 0.0
    wins: int = 0
    losses: int = 0
    total_trades: int = 0
    status_msg: str = "Bereit"
    events: list[str] = field(default_factory=list)

    # Engine-Status
    running: bool = False

    # GUI → Engine: Kommandos ("stop_engine", "close_trade")
    command_queue: queue.Queue = field(default_factory=queue.Queue)

    # Engine → GUI: Signal zur manuellen Bestätigung
    pending_signal: dict | None = None

    # GUI → Engine: Antwort auf Signal ("confirm" | "reject")
    signal_response: queue.Queue = field(default_factory=queue.Queue)
