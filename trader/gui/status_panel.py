from __future__ import annotations

import re
import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trader.gui.state import GUIState

# Farben für das dunkle Theme
BG = "#1e1e1e"
BG_SECTION = "#252525"
FG = "#cccccc"
FG_DIM = "#666666"
GRUEN = "#44dd44"
ROT = "#ff4444"
CYAN = "#4ac8ff"
GELB = "#ffcc44"


def _strip_ansi(text: str) -> str:
    """Entfernt ANSI-Farbcodes aus einem String."""
    return re.sub(r"\033\[[0-9;]*m", "", text)


class StatusPanel(tk.Frame):
    """Zeigt Echtzeit-Statistiken, offene Position und Event-Log an.

    Wird alle 500ms durch die Poll-Funktion in app.py aktualisiert.
    """

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent, bg=BG, padx=8, pady=8)

        # ── Statistiken ──────────────────────────────────────────
        stats_frame = tk.LabelFrame(self, text="Statistiken", bg=BG, fg=FG, font=("monospace", 9))
        stats_frame.pack(fill=tk.X, pady=(0, 6))

        self._equity_var = tk.StringVar(value="Equity: --")
        self._pnl_var = tk.StringVar(value="Tag PnL: --")
        self._trades_var = tk.StringVar(value="Trades: 0  Wins: 0  Losses: 0  WR: --%")
        self._status_var = tk.StringVar(value="Bereit")

        tk.Label(stats_frame, textvariable=self._equity_var, bg=BG, fg=FG,
                 font=("monospace", 10, "bold"), anchor="w").pack(fill=tk.X, padx=4, pady=1)
        self._pnl_label = tk.Label(stats_frame, textvariable=self._pnl_var, bg=BG, fg=FG,
                                   font=("monospace", 10), anchor="w")
        self._pnl_label.pack(fill=tk.X, padx=4, pady=1)
        tk.Label(stats_frame, textvariable=self._trades_var, bg=BG, fg=FG,
                 font=("monospace", 9), anchor="w").pack(fill=tk.X, padx=4, pady=1)
        tk.Label(stats_frame, textvariable=self._status_var, bg=BG, fg=FG_DIM,
                 font=("monospace", 9), anchor="w").pack(fill=tk.X, padx=4, pady=1)

        # ── Offene Position ──────────────────────────────────────
        pos_frame = tk.LabelFrame(self, text="Offene Position", bg=BG, fg=FG, font=("monospace", 9))
        pos_frame.pack(fill=tk.X, pady=(0, 6))

        self._trade_var = tk.StringVar(value="Keine offene Position")
        self._trade_label = tk.Label(pos_frame, textvariable=self._trade_var, bg=BG, fg=FG_DIM,
                                     font=("monospace", 9), anchor="w", justify=tk.LEFT)
        self._trade_label.pack(fill=tk.X, padx=4, pady=4)

        self._unrealized_var = tk.StringVar(value="")
        self._unrealized_label = tk.Label(pos_frame, textvariable=self._unrealized_var, bg=BG,
                                          font=("monospace", 9, "bold"), anchor="w")
        self._unrealized_label.pack(fill=tk.X, padx=4, pady=(0, 4))

        # ── Event-Log ────────────────────────────────────────────
        log_frame = tk.LabelFrame(self, text="Ereignisse", bg=BG, fg=FG, font=("monospace", 9))
        log_frame.pack(fill=tk.BOTH, expand=True)

        self._events_text = tk.Text(
            log_frame,
            height=8,
            bg="#161616",
            fg=FG,
            font=("monospace", 8),
            state=tk.DISABLED,
            wrap=tk.WORD,
            relief=tk.FLAT,
        )
        self._events_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

    def update(self, snap: dict) -> None:
        """Aktualisiert alle Widgets mit den neuesten Daten aus dem Snapshot."""
        # Equity
        self._equity_var.set(f"Equity: {snap['equity']:,.2f} $")

        # Tag-PnL (farbig)
        pnl = snap["day_pnl"]
        vorz = "+" if pnl >= 0 else ""
        self._pnl_var.set(f"Tag PnL: {vorz}{pnl:.2f} $")
        self._pnl_label.config(fg=GRUEN if pnl >= 0 else ROT)

        # Trades-Statistik
        total = snap["total_trades"]
        wins = snap["wins"]
        losses = snap["losses"]
        wr = (wins / total * 100) if total else 0
        self._trades_var.set(f"Trades: {total}  Wins: {wins}  Losses: {losses}  WR: {wr:.0f}%")

        # Status-Nachricht
        self._status_var.set(snap["status_msg"])

        # Offene Position
        trade = snap["open_trade"]
        if trade:
            pfeil = "▲ LONG" if trade.direction == "long" else "▼ SHORT"
            self._trade_var.set(
                f"{pfeil}  –  {trade.setup_name}\n"
                f"Entry: {trade.entry_price:.0f}  "
                f"SL: {trade.stop_price:.0f}  "
                f"TP: {trade.take_profit_price:.0f}  "
                f"CRV: {trade.reward_risk_ratio:.1f}"
            )
            self._trade_label.config(
                fg=GRUEN if trade.direction == "long" else ROT
            )

            # Unrealized PnL aus letzter Kerze
            candles = snap["candles"]
            if candles:
                last_close = candles[-1].close
                if trade.direction == "long":
                    unrealized = (last_close - trade.entry_price) * trade.position_size
                else:
                    unrealized = (trade.entry_price - last_close) * trade.position_size
                vorz = "+" if unrealized >= 0 else ""
                self._unrealized_var.set(f"Unrealized PnL: {vorz}{unrealized:.2f} $")
                self._unrealized_label.config(fg=GRUEN if unrealized >= 0 else ROT)
            else:
                self._unrealized_var.set("")
        else:
            self._trade_var.set("Keine offene Position")
            self._trade_label.config(fg=FG_DIM)
            self._unrealized_var.set("")

        # Event-Log (ANSI-Codes entfernen)
        self._events_text.config(state=tk.NORMAL)
        self._events_text.delete("1.0", tk.END)
        for ev in snap["events"]:
            self._events_text.insert(tk.END, _strip_ansi(ev) + "\n")
        self._events_text.config(state=tk.DISABLED)
        self._events_text.see(tk.END)  # zum neuesten Event scrollen
