from __future__ import annotations

import tkinter as tk
from typing import TYPE_CHECKING

import matplotlib
import matplotlib.figure
import mplfinance as mpf
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from trader.gui.theme import (
    BORDER,
    CHART_DOWN,
    CHART_GRID,
    CHART_UP,
    DANGER,
    PRIMARY,
    SUCCESS,
    SURFACE,
    SURFACE_ALT,
    TEXT,
    TEXT_MUTED,
)

if TYPE_CHECKING:
    from trader.gui.state import GUIState

matplotlib.use("Agg")

SICHTBARE_KERZEN = 80

_MARKET_COLORS = mpf.make_marketcolors(
    up=CHART_UP,
    down=CHART_DOWN,
    edge={"up": CHART_UP, "down": CHART_DOWN},
    wick={"up": CHART_UP, "down": CHART_DOWN},
    volume={"up": "#9ddfc7", "down": "#f4b4b4"},
)
_STYLE = mpf.make_mpf_style(
    base_mpf_style="default",
    marketcolors=_MARKET_COLORS,
    facecolor=SURFACE,
    edgecolor=BORDER,
    figcolor=SURFACE,
    gridcolor=CHART_GRID,
    gridstyle="-",
    y_on_right=False,
    rc={
        "axes.labelcolor": TEXT_MUTED,
        "axes.edgecolor": BORDER,
        "axes.titlecolor": TEXT,
        "xtick.color": TEXT_MUTED,
        "ytick.color": TEXT_MUTED,
    },
)


class ChartPanel(tk.Frame):
    """Zeigt einen Candlestick-Chart mit eingezeichneten Trade-Levels."""

    _last_trade = None

    def __init__(self, parent: tk.Widget, state: GUIState) -> None:
        super().__init__(parent, bg=SURFACE)
        self._state = state
        self._last_candle_count = 0

        self._fig = matplotlib.figure.Figure(figsize=(10, 6), dpi=100, facecolor=SURFACE)
        gs = self._fig.add_gridspec(2, 1, height_ratios=[3.6, 1], hspace=0.0)
        self._ax = self._fig.add_subplot(gs[0])
        self._ax_vol = self._fig.add_subplot(gs[1], sharex=self._ax)

        self._canvas = FigureCanvasTkAgg(self._fig, master=self)
        self._canvas.get_tk_widget().configure(bg=SURFACE, highlightthickness=0, bd=0)
        self._canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self._zeige_platzhalter()

    def _zeige_platzhalter(self) -> None:
        self._ax.clear()
        self._ax_vol.clear()
        self._ax.set_facecolor(SURFACE_ALT)
        self._ax_vol.set_facecolor(SURFACE_ALT)
        for axis in (self._ax, self._ax_vol):
            for spine in axis.spines.values():
                spine.set_color(BORDER)
        self._ax.text(
            0.5,
            0.58,
            "Warte auf Marktdaten",
            ha="center",
            va="center",
            transform=self._ax.transAxes,
            color=TEXT,
            fontsize=16,
            fontweight="bold",
        )
        self._ax.text(
            0.5,
            0.44,
            "Starte die Engine, um Candles, Volumen und aktive Levels zu sehen.",
            ha="center",
            va="center",
            transform=self._ax.transAxes,
            color=TEXT_MUTED,
            fontsize=10,
        )
        self._ax.set_xticks([])
        self._ax.set_yticks([])
        self._ax_vol.set_xticks([])
        self._ax_vol.set_yticks([])
        self._canvas.draw()

    def update(self, snap: dict) -> None:
        candles = snap["candles"]
        if len(candles) < 2:
            self._zeige_platzhalter()
            self._last_candle_count = 0
            self._last_trade = None
            return
        if len(candles) == self._last_candle_count and snap["open_trade"] is self._last_trade:
            return

        self._last_candle_count = len(candles)
        self._last_trade = snap["open_trade"]
        sichtbar = candles[-SICHTBARE_KERZEN:]

        df = pd.DataFrame(
            [
                {
                    "Date": c.ts,
                    "Open": c.open,
                    "High": c.high,
                    "Low": c.low,
                    "Close": c.close,
                    "Volume": c.volume,
                }
                for c in sichtbar
            ]
        )
        df.set_index("Date", inplace=True)

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
            self._ax.plot(df.index, df["Close"], color=PRIMARY, linewidth=1.8)

        for axis in (self._ax, self._ax_vol):
            axis.set_facecolor(SURFACE)
            axis.grid(color=CHART_GRID, linestyle="-", linewidth=0.7, alpha=0.7)
            for spine in axis.spines.values():
                spine.set_color(BORDER)

        trade = snap["open_trade"]
        if trade:
            self._ax.axhline(
                trade.entry_price,
                color=PRIMARY,
                linewidth=1.3,
                linestyle="--",
                label=f"Entry {trade.entry_price:.0f}",
            )
            self._ax.axhline(
                trade.stop_price,
                color=DANGER,
                linewidth=1.3,
                linestyle="--",
                label=f"SL {trade.stop_price:.0f}",
            )
            self._ax.axhline(
                trade.take_profit_price,
                color=SUCCESS,
                linewidth=1.3,
                linestyle="--",
                label=f"TP {trade.take_profit_price:.0f}",
            )
            self._ax.legend(
                loc="upper left",
                fontsize=8,
                facecolor=SURFACE_ALT,
                edgecolor=BORDER,
                labelcolor=TEXT,
            )

        self._ax.set_title("BTC Marktstruktur", color=TEXT, fontsize=11, loc="left", pad=10)
        self._ax_vol.set_ylabel("Vol", color=TEXT_MUTED, fontsize=8)
        self._fig.tight_layout(pad=0.8)
        self._canvas.draw()
