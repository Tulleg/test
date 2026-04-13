from __future__ import annotations

import re
import tkinter as tk
from typing import TYPE_CHECKING

import matplotlib
import matplotlib.figure
import mplfinance as mpf
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

if TYPE_CHECKING:
    from trader.gui.state import GUIState

matplotlib.use("Agg")

# Anzahl der sichtbaren Kerzen im Chart
SICHTBARE_KERZEN = 80

# Dunkles Chart-Theme passend zur App
_STYLE = mpf.make_mpf_style(
    base_mpf_style="nightclouds",
    facecolor="#1e1e1e",
    edgecolor="#444444",
    figcolor="#1e1e1e",
    gridcolor="#2a2a2a",
    gridstyle="--",
    rc={"axes.labelcolor": "#cccccc", "xtick.color": "#888888", "ytick.color": "#888888"},
)


def _strip_ansi(text: str) -> str:
    """Entfernt ANSI-Farbcodes aus einem String."""
    return re.sub(r"\033\[[0-9;]*m", "", text)


class ChartPanel(tk.Frame):
    """Zeigt einen Candlestick-Chart mit eingezeichneten Trade-Levels.

    Wird nur neu gerendert wenn sich die Kerzenzahl ändert, da canvas.draw()
    etwa 50-100ms dauert und die App sonst zu träge würde.
    """

    def __init__(self, parent: tk.Widget, state: GUIState) -> None:
        super().__init__(parent, bg="#1e1e1e")
        self._state = state
        self._last_candle_count = 0

        # Matplotlib Figure in Tkinter einbetten
        # Zwei separate Subplots: oben Kerzen (75%), unten Volumen (25%)
        self._fig = matplotlib.figure.Figure(figsize=(10, 6), dpi=100, facecolor="#1e1e1e")
        gs = self._fig.add_gridspec(2, 1, height_ratios=[3, 1], hspace=0.0)
        self._ax = self._fig.add_subplot(gs[0])
        self._ax_vol = self._fig.add_subplot(gs[1], sharex=self._ax)

        self._canvas = FigureCanvasTkAgg(self._fig, master=self)
        self._canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self._zeige_platzhalter()

    def _zeige_platzhalter(self) -> None:
        """Zeigt einen leeren Chart mit Hinweistext an."""
        self._ax.set_facecolor("#1e1e1e")
        self._ax.text(
            0.5, 0.5,
            "Engine starten um Chart zu laden...",
            ha="center", va="center",
            transform=self._ax.transAxes,
            color="#666666", fontsize=12,
        )
        self._canvas.draw()

    def update(self, snap: dict) -> None:
        """Aktualisiert den Chart mit den neuesten Kerzen und Trade-Levels."""
        candles = snap["candles"]

        # Nur neu zeichnen wenn echte neue Kerzen vorliegen
        if len(candles) < 2:
            return
        if len(candles) == self._last_candle_count and snap["open_trade"] is self._last_trade:
            return

        self._last_candle_count = len(candles)
        self._last_trade = snap["open_trade"]

        # Letzte N Kerzen für Lesbarkeit
        sichtbar = candles[-SICHTBARE_KERZEN:]

        # Candle-Daten in DataFrame umwandeln (mplfinance erwartet dieses Format)
        df = pd.DataFrame([
            {
                "Date": c.ts,
                "Open": c.open,
                "High": c.high,
                "Low": c.low,
                "Close": c.close,
                "Volume": c.volume,
            }
            for c in sichtbar
        ])
        df.set_index("Date", inplace=True)

        # Axes leeren und neu zeichnen
        self._ax.clear()
        self._ax_vol.clear()

        try:
            mpf.plot(
                df,
                type="candle",
                ax=self._ax,
                volume=self._ax_vol,
                style=_STYLE,
                warn_too_much_data=99999,
            )
        except Exception:
            # Fallback: einfache Linienchart wenn mplfinance Probleme hat
            self._ax.plot(df.index, df["Close"], color="#4a9eff", linewidth=1)

        # Trade-Levels einzeichnen wenn eine Position offen ist
        trade = snap["open_trade"]
        if trade:
            self._ax.axhline(
                trade.entry_price,
                color="#ffffff", linewidth=1.2, linestyle="--",
                label=f"Entry  {trade.entry_price:.0f}",
            )
            self._ax.axhline(
                trade.stop_price,
                color="#ff4444", linewidth=1.2, linestyle="--",
                label=f"SL      {trade.stop_price:.0f}",
            )
            self._ax.axhline(
                trade.take_profit_price,
                color="#44dd44", linewidth=1.2, linestyle="--",
                label=f"TP      {trade.take_profit_price:.0f}",
            )
            self._ax.legend(
                loc="upper left", fontsize=8,
                facecolor="#2a2a2a", edgecolor="#444444",
                labelcolor="#cccccc",
            )

        self._ax.set_facecolor("#1e1e1e")
        self._fig.tight_layout(pad=0.5)
        self._canvas.draw()

    # Initialisierung des letzten Trade-Zustands
    _last_trade = None
