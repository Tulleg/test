from __future__ import annotations

import tkinter as tk
from typing import Callable

BG = "#1e1e1e"


class ControlsPanel(tk.Frame):
    """Start/Stop/Trade-Schließen Buttons.

    Die Callbacks werden von app.py übergeben – dieses Panel
    enthält nur die UI-Logik, keine Geschäftslogik.
    """

    def __init__(
        self,
        parent: tk.Widget,
        on_start: Callable[[], None],
        on_stop: Callable[[], None],
        on_close_trade: Callable[[], None],
    ) -> None:
        super().__init__(parent, bg=BG, padx=8, pady=8)

        self._start_btn = tk.Button(
            self,
            text="▶  Start",
            command=on_start,
            bg="#1a5c1a",
            fg="#44dd44",
            activebackground="#2a7a2a",
            activeforeground="#44ff44",
            font=("monospace", 10, "bold"),
            relief=tk.FLAT,
            padx=10,
            pady=6,
            cursor="hand2",
        )
        self._start_btn.pack(fill=tk.X, pady=(0, 4))

        self._stop_btn = tk.Button(
            self,
            text="■  Stop",
            command=on_stop,
            bg="#3a1a1a",
            fg="#ff6666",
            activebackground="#5a2a2a",
            activeforeground="#ff4444",
            font=("monospace", 10, "bold"),
            relief=tk.FLAT,
            padx=10,
            pady=6,
            cursor="hand2",
            state=tk.DISABLED,
        )
        self._stop_btn.pack(fill=tk.X, pady=(0, 4))

        self._close_trade_btn = tk.Button(
            self,
            text="✕  Trade schließen",
            command=on_close_trade,
            bg="#3a2a00",
            fg="#ffcc44",
            activebackground="#5a4a00",
            activeforeground="#ffdd66",
            font=("monospace", 9),
            relief=tk.FLAT,
            padx=10,
            pady=5,
            cursor="hand2",
            state=tk.DISABLED,
        )
        self._close_trade_btn.pack(fill=tk.X)

    def setze_engine_laeuft(self, laeuft: bool) -> None:
        """Passt Button-Zustände an je nachdem ob die Engine aktiv ist."""
        self._start_btn.config(state=tk.DISABLED if laeuft else tk.NORMAL)
        self._stop_btn.config(state=tk.NORMAL if laeuft else tk.DISABLED)

    def setze_trade_offen(self, offen: bool) -> None:
        """Aktiviert/deaktiviert den Trade-Schließen-Button."""
        self._close_trade_btn.config(state=tk.NORMAL if offen else tk.DISABLED)
