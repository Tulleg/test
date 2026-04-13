from __future__ import annotations

import re
import tkinter as tk

from trader.gui.theme import (
    BORDER,
    CARD_PAD,
    DANGER,
    DANGER_BG,
    FONT_H2,
    FONT_KPI,
    INFO,
    INFO_BG,
    SECTION_GAP,
    SUCCESS,
    SUCCESS_BG,
    SURFACE,
    SURFACE_ALT,
    TEXT,
    TEXT_MUTED,
    TEXT_SOFT,
    style_card,
    tag_label,
)


def _strip_ansi(text: str) -> str:
    return re.sub(r"\033\[[0-9;]*m", "", text)


class StatusPanel(tk.Frame):
    """Zeigt Echtzeit-Statistiken, offene Position und Event-Log an."""

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent, bg=parent.cget("bg"))

        overview = tk.Frame(self, bg=SURFACE, padx=CARD_PAD, pady=CARD_PAD)
        style_card(overview)
        overview.pack(fill=tk.X, pady=(0, SECTION_GAP))

        tk.Label(overview, text="Live-Status", bg=SURFACE, fg=TEXT, font=FONT_H2).pack(anchor="w")
        tk.Label(
            overview,
            text="Equity, Tagesergebnis und Systemstatus auf einen Blick.",
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=("TkDefaultFont", 9),
        ).pack(anchor="w", pady=(3, 12))

        kpi_row = tk.Frame(overview, bg=SURFACE)
        kpi_row.pack(fill=tk.X)
        kpi_row.grid_columnconfigure(0, weight=1)
        kpi_row.grid_columnconfigure(1, weight=1)

        self._equity_value = self._kpi_card(kpi_row, "Equity")
        self._equity_value.master.grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=(0, 8))
        self._pnl_value = self._kpi_card(kpi_row, "Tages-PnL")
        self._pnl_value.master.grid(row=0, column=1, sticky="ew", padx=(6, 0), pady=(0, 8))
        self._trades_value = self._kpi_card(kpi_row, "Trades / Winrate")
        self._trades_value.master.grid(row=1, column=0, columnspan=2, sticky="ew")

        self._status_note = tk.Label(overview, text="Bereit", bg=SURFACE, fg=TEXT_MUTED, font=("TkDefaultFont", 9))
        self._status_note.pack(anchor="w", pady=(12, 0))

        position = tk.Frame(self, bg=SURFACE, padx=CARD_PAD, pady=CARD_PAD)
        style_card(position)
        position.pack(fill=tk.X, pady=(0, SECTION_GAP))

        header = tk.Frame(position, bg=SURFACE)
        header.pack(fill=tk.X)
        tk.Label(header, text="Offene Position", bg=SURFACE, fg=TEXT, font=FONT_H2).pack(side=tk.LEFT)
        self._position_badge = tag_label(header, "Kein Trade", fg=INFO, bg=INFO_BG)
        self._position_badge.pack(side=tk.RIGHT)

        self._trade_main = tk.Label(
            position,
            text="Keine offene Position",
            bg=SURFACE,
            fg=TEXT_SOFT,
            font=("TkDefaultFont", 10),
            justify=tk.LEFT,
            anchor="w",
        )
        self._trade_main.pack(fill=tk.X, pady=(12, 10))

        metrics = tk.Frame(position, bg=SURFACE)
        metrics.pack(fill=tk.X)
        metrics.grid_columnconfigure(0, weight=1)
        metrics.grid_columnconfigure(1, weight=1)
        metrics.grid_columnconfigure(2, weight=1)
        self._entry_value = self._mini_metric(metrics, "Entry")
        self._entry_value.master.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self._stop_value = self._mini_metric(metrics, "Stop")
        self._stop_value.master.grid(row=0, column=1, sticky="ew", padx=6)
        self._target_value = self._mini_metric(metrics, "Target")
        self._target_value.master.grid(row=0, column=2, sticky="ew", padx=(6, 0))

        self._unrealized = tk.Label(position, text="", bg=SURFACE, fg=TEXT_MUTED, font=("TkDefaultFont", 10, "bold"))
        self._unrealized.pack(anchor="w", pady=(12, 0))

        log_card = tk.Frame(self, bg=SURFACE, padx=CARD_PAD, pady=CARD_PAD)
        style_card(log_card)
        log_card.pack(fill=tk.BOTH, expand=True)

        tk.Label(log_card, text="Ereignisse", bg=SURFACE, fg=TEXT, font=FONT_H2).pack(anchor="w")
        tk.Label(
            log_card,
            text="Laufende Entscheidungen, Orders und Systemmeldungen.",
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=("TkDefaultFont", 9),
        ).pack(anchor="w", pady=(3, 12))

        text_shell = tk.Frame(log_card, bg=SURFACE_ALT)
        style_card(text_shell, background=SURFACE_ALT, border=BORDER)
        text_shell.pack(fill=tk.BOTH, expand=True)

        self._events_text = tk.Text(
            text_shell,
            height=10,
            bg=SURFACE_ALT,
            fg=TEXT,
            font=("TkFixedFont", 9),
            state=tk.DISABLED,
            wrap=tk.WORD,
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=10,
        )
        self._events_text.pack(fill=tk.BOTH, expand=True)

    def _kpi_card(self, parent: tk.Widget, title: str) -> tk.Label:
        card = tk.Frame(parent, bg=SURFACE_ALT, padx=12, pady=12)
        style_card(card, background=SURFACE_ALT, border=BORDER)
        tk.Label(card, text=title, bg=SURFACE_ALT, fg=TEXT_MUTED, font=("TkDefaultFont", 9)).pack(anchor="w")
        value = tk.Label(card, text="--", bg=SURFACE_ALT, fg=TEXT, font=FONT_KPI)
        value.pack(anchor="w", pady=(8, 0))
        return value

    def _mini_metric(self, parent: tk.Widget, title: str) -> tk.Label:
        card = tk.Frame(parent, bg=SURFACE_ALT, padx=10, pady=10)
        style_card(card, background=SURFACE_ALT, border=BORDER)
        tk.Label(card, text=title, bg=SURFACE_ALT, fg=TEXT_MUTED, font=("TkDefaultFont", 8)).pack(anchor="w")
        value = tk.Label(card, text="--", bg=SURFACE_ALT, fg=TEXT, font=("TkDefaultFont", 10, "bold"))
        value.pack(anchor="w", pady=(6, 0))
        return value

    def update(self, snap: dict) -> None:
        self._equity_value.config(text=f"{snap['equity']:,.2f} $")

        pnl = snap["day_pnl"]
        pnl_prefix = "+" if pnl >= 0 else ""
        self._pnl_value.config(text=f"{pnl_prefix}{pnl:.2f} $", fg=SUCCESS if pnl >= 0 else DANGER)

        total = snap["total_trades"]
        wins = snap["wins"]
        wr = (wins / total * 100) if total else 0
        self._trades_value.config(text=f"{total} / {wr:.0f}%")
        self._status_note.config(text=snap["status_msg"])

        trade = snap["open_trade"]
        if trade:
            ist_long = trade.direction == "long"
            badge_text = "LONG" if ist_long else "SHORT"
            self._position_badge.config(
                text=badge_text,
                fg=SUCCESS if ist_long else DANGER,
                bg=SUCCESS_BG if ist_long else DANGER_BG,
            )
            self._trade_main.config(text=f"{trade.setup_name}  |  CRV {trade.reward_risk_ratio:.1f}", fg=TEXT)
            self._entry_value.config(text=f"{trade.entry_price:.0f}", fg=TEXT)
            self._stop_value.config(text=f"{trade.stop_price:.0f}", fg=DANGER)
            self._target_value.config(text=f"{trade.take_profit_price:.0f}", fg=SUCCESS)

            candles = snap["candles"]
            if candles:
                last_close = candles[-1].close
                if ist_long:
                    unrealized = (last_close - trade.entry_price) * trade.position_size
                else:
                    unrealized = (trade.entry_price - last_close) * trade.position_size
                prefix = "+" if unrealized >= 0 else ""
                self._unrealized.config(
                    text=f"Unrealized PnL: {prefix}{unrealized:.2f} $",
                    fg=SUCCESS if unrealized >= 0 else DANGER,
                )
            else:
                self._unrealized.config(text="")
        else:
            self._position_badge.config(text="Kein Trade", fg=INFO, bg=INFO_BG)
            self._trade_main.config(text="Keine offene Position", fg=TEXT_SOFT)
            self._entry_value.config(text="--", fg=TEXT_SOFT)
            self._stop_value.config(text="--", fg=TEXT_SOFT)
            self._target_value.config(text="--", fg=TEXT_SOFT)
            self._unrealized.config(text="")

        self._events_text.config(state=tk.NORMAL)
        self._events_text.delete("1.0", tk.END)
        for ev in snap["events"]:
            self._events_text.insert(tk.END, _strip_ansi(ev) + "\n")
        self._events_text.config(state=tk.DISABLED)
        self._events_text.see(tk.END)
