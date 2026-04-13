from __future__ import annotations

import tkinter as tk
from typing import Callable

from trader.gui.theme import CARD_PAD, FONT_H2, SURFACE, TEXT, TEXT_MUTED, set_button_style, style_card


class ControlsPanel(tk.Frame):
    """Start/Stop/Trade-Schließen Buttons."""

    def __init__(
        self,
        parent: tk.Widget,
        on_start: Callable[[], None],
        on_stop: Callable[[], None],
        on_close_trade: Callable[[], None],
        on_quit: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent, bg=parent.cget("bg"))

        card = tk.Frame(self, bg=SURFACE, padx=CARD_PAD, pady=CARD_PAD)
        style_card(card)
        card.pack(fill=tk.X)

        tk.Label(card, text="Aktionen", bg=SURFACE, fg=TEXT, font=FONT_H2).pack(anchor="w")
        tk.Label(
            card,
            text="Steuere die Engine und greife manuell in offene Trades ein.",
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=("TkDefaultFont", 9),
        ).pack(anchor="w", pady=(3, 12))

        row = tk.Frame(card, bg=SURFACE)
        row.pack(fill=tk.X, pady=(0, 8))
        row.grid_columnconfigure(0, weight=1)
        row.grid_columnconfigure(1, weight=1)

        self._start_btn = tk.Button(row, text="Engine starten", command=on_start)
        set_button_style(self._start_btn, variant="primary")
        self._start_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self._stop_btn = tk.Button(row, text="Engine stoppen", command=on_stop, state=tk.DISABLED)
        set_button_style(self._stop_btn, variant="danger")
        self._stop_btn.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        self._close_trade_btn = tk.Button(card, text="Trade schließen", command=on_close_trade, state=tk.DISABLED)
        set_button_style(self._close_trade_btn, variant="warning")
        self._close_trade_btn.pack(fill=tk.X)

        if on_quit is not None:
            quit_btn = tk.Button(card, text="App schließen", command=on_quit)
            set_button_style(quit_btn, variant="secondary")
            quit_btn.pack(fill=tk.X, pady=(8, 0))

    def setze_engine_laeuft(self, laeuft: bool) -> None:
        self._start_btn.config(state=tk.DISABLED if laeuft else tk.NORMAL)
        self._stop_btn.config(state=tk.NORMAL if laeuft else tk.DISABLED)

    def setze_trade_offen(self, offen: bool) -> None:
        self._close_trade_btn.config(state=tk.NORMAL if offen else tk.DISABLED)
