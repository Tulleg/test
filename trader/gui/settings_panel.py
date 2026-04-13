from __future__ import annotations

import tkinter as tk

from trader.config import Settings
from trader.gui.theme import (
    BORDER,
    CARD_PAD,
    FONT_H2,
    SURFACE,
    SURFACE_ALT,
    TEXT,
    TEXT_MUTED,
    TEXT_SOFT,
    set_entry_style,
    set_radio_style,
    style_card,
)


class SettingsPanel(tk.Frame):
    """Zeigt die gleichen Kern-Einstellungen wie das CLI-Menü."""

    def __init__(self, parent: tk.Widget, settings: Settings) -> None:
        super().__init__(parent, bg=parent.cget("bg"))

        card = tk.Frame(self, bg=SURFACE, padx=CARD_PAD, pady=CARD_PAD)
        style_card(card)
        card.pack(fill=tk.X)

        tk.Label(card, text="Einstellungen", bg=SURFACE, fg=TEXT, font=FONT_H2).pack(anchor="w")
        tk.Label(
            card,
            text="Einspaltig aufgebaut, damit in der Sidebar nichts mehr überlappt.",
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=("TkDefaultFont", 9),
        ).pack(anchor="w", pady=(3, 14))

        form = tk.Frame(card, bg=SURFACE)
        form.pack(fill=tk.X)

        self._execution_var = tk.StringVar(value=settings.execution)
        self._source_var = tk.StringVar(value="live" if settings.live_feed else "mock")
        self._mode_var = tk.StringVar(value=settings.mode)
        self._equity_var = tk.DoubleVar(value=settings.account_equity)
        self._risk_var = tk.DoubleVar(value=round(settings.risk_per_trade * 100, 2))
        self._minrr_var = tk.DoubleVar(value=settings.min_rr)
        self._timeframe_var = tk.IntVar(value=settings.timeframe_minutes)
        self._interval_var = tk.IntVar(value=settings.loop_interval_sec)
        self._session_end_var = tk.IntVar(value=settings.session_end_hour_utc)
        self._timeout_var = tk.IntVar(value=settings.manual_timeout_sec)
        self._apikey_var = tk.StringVar(value=settings.bingx_api_key or "")
        self._apisecret_var = tk.StringVar(value=settings.bingx_api_secret or "")
        self._daily_loss_var = tk.DoubleVar(value=round(settings.daily_loss_limit_pct * 100, 1))

        self._editierbar: list[tk.Widget] = []
        row = 0

        def add_container(label: str, *, hint: str | None = None) -> tk.Frame:
            nonlocal row
            container = tk.Frame(form, bg=SURFACE)
            container.pack(fill=tk.X, pady=(0, 10))
            tk.Label(container, text=label, bg=SURFACE, fg=TEXT_MUTED, font=("TkDefaultFont", 9)).pack(anchor="w", pady=(0, 4))
            if hint:
                tk.Label(container, text=hint, bg=SURFACE, fg=TEXT_SOFT, font=("TkDefaultFont", 8)).pack(anchor="w", pady=(4, 0))
            row += 1
            return container

        def add_input(label: str, variable: tk.Variable, factory, *, hint: str | None = None) -> None:
            container = add_container(label, hint=hint)
            widget = factory(container, variable)
            widget.pack(fill=tk.X)
            self._editierbar.append(widget)

        def add_radio_group(label: str, variable: tk.StringVar, options: list[tuple[str, str]], *, hint: str | None = None) -> None:
            container = add_container(label, hint=hint)
            group = tk.Frame(container, bg=SURFACE_ALT, padx=10, pady=8)
            style_card(group, background=SURFACE_ALT, border=BORDER)
            group.pack(fill=tk.X)
            for option_row, (text, value) in enumerate(options):
                radio = tk.Radiobutton(group, text=text, variable=variable, value=value)
                set_radio_style(radio, background=SURFACE_ALT)
                radio.pack(anchor="w", pady=(0, 4) if option_row < len(options) - 1 else 0)
                self._editierbar.append(radio)

        add_radio_group("Ausführung", self._execution_var, [("Paper", "paper"), ("Live", "live")])
        add_radio_group("Datenquelle", self._source_var, [("Mock", "mock"), ("Live", "live")], hint="Wie im CLI-Menü: mock oder live.")
        add_radio_group("Modus", self._mode_var, [("Manual", "manual"), ("Auto", "auto")])

        symbol_box = add_container("Symbol")
        fixed_symbol = tk.Frame(symbol_box, bg=SURFACE_ALT, padx=10, pady=10)
        style_card(fixed_symbol, background=SURFACE_ALT, border=BORDER)
        fixed_symbol.pack(fill=tk.X)
        tk.Label(fixed_symbol, text="BTC/USDT:USDT", bg=SURFACE_ALT, fg=TEXT, font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
        tk.Label(fixed_symbol, text="Fest vorgegeben", bg=SURFACE_ALT, fg=TEXT_SOFT, font=("TkDefaultFont", 8)).pack(anchor="w", pady=(3, 0))

        add_input(
            "Kapital (paper) USDT",
            self._equity_var,
            lambda parent, var: _entry(parent, var),
        )
        add_input(
            "Risiko/Trade %",
            self._risk_var,
            lambda parent, var: _spinbox(parent, var, from_=0.1, to=1.0, increment=0.1, format="%.1f"),
            hint="CLI-Limit: maximal 1 %.",
        )
        add_input(
            "Min. CRV",
            self._minrr_var,
            lambda parent, var: _spinbox(parent, var, from_=1.0, to=10.0, increment=0.5, format="%.1f"),
        )
        add_input(
            "Timeframe (min)",
            self._timeframe_var,
            lambda parent, var: _spinbox(parent, var, from_=5, to=1440, increment=5, format="%0.0f"),
        )
        add_input(
            "Interval (sek)",
            self._interval_var,
            lambda parent, var: _spinbox(parent, var, from_=1, to=300, increment=1, format="%0.0f"),
        )
        add_input(
            "Session-Ende UTC",
            self._session_end_var,
            lambda parent, var: _spinbox(parent, var, from_=0, to=23, increment=1, format="%0.0f"),
        )
        add_input(
            "Signal-Timeout",
            self._timeout_var,
            lambda parent, var: _spinbox(parent, var, from_=5, to=300, increment=5, format="%0.0f"),
        )

        separator = tk.Frame(form, bg=BORDER, height=1)
        separator.pack(fill=tk.X, pady=(4, 12))

        tk.Label(form, text="BingX API", bg=SURFACE, fg=TEXT, font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
        tk.Label(form, text="Nur für Live-Ausführung nötig.", bg=SURFACE, fg=TEXT_MUTED, font=("TkDefaultFont", 9)).pack(anchor="w", pady=(2, 8))

        add_input("API Key", self._apikey_var, lambda parent, var: _entry(parent, var, show="*"))
        add_input("API Secret", self._apisecret_var, lambda parent, var: _entry(parent, var, show="*"))

    def sperren(self, gesperrt: bool) -> None:
        state = tk.DISABLED if gesperrt else tk.NORMAL
        for widget in self._editierbar:
            widget.config(state=state)

    def lese_settings(self) -> Settings:
        execution = self._execution_var.get()
        live_feed = self._source_var.get() == "live"
        interval = int(self._interval_var.get())
        if live_feed and interval < 10:
            interval = 30

        return Settings(
            symbol="BTC-USDT",
            ccxt_symbol="BTC/USDT:USDT",
            execution=execution,  # type: ignore[arg-type]
            mode=self._mode_var.get(),
            timeframe_minutes=max(5, int(self._timeframe_var.get())),
            risk_per_trade=min(self._risk_var.get() / 100.0, 0.01),
            min_rr=self._minrr_var.get(),
            account_equity=self._equity_var.get(),
            loop_interval_sec=interval,
            session_end_hour_utc=int(self._session_end_var.get()),
            daily_loss_limit_pct=self._daily_loss_var.get() / 100.0,
            live_feed=live_feed,
            manual_timeout_sec=int(self._timeout_var.get()),
            bingx_api_key=self._apikey_var.get() or None,
            bingx_api_secret=self._apisecret_var.get() or None,
        )


def _entry(parent: tk.Widget, variable: tk.Variable, *, show: str | None = None) -> tk.Entry:
    widget = tk.Entry(parent, textvariable=variable, show=show)
    set_entry_style(widget)
    return widget


def _spinbox(parent: tk.Widget, variable: tk.Variable, **kwargs: object) -> tk.Spinbox:
    widget = tk.Spinbox(parent, textvariable=variable, **kwargs)
    set_entry_style(widget)
    return widget
