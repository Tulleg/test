from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from trader.config import Settings

BG = "#1e1e1e"
BG_ENTRY = "#2a2a2a"
FG = "#cccccc"
FG_DIM = "#888888"


class SettingsPanel(tk.Frame):
    """Zeigt alle Konfigurationsparameter als editierbare Eingabefelder.

    Gesperrte Felder (grau) können nicht verändert werden solange die Engine läuft.
    """

    def __init__(self, parent: tk.Widget, settings: Settings) -> None:
        super().__init__(parent, bg=BG, padx=8, pady=8)

        tk.Label(self, text="Einstellungen", bg=BG, fg=FG,
                 font=("monospace", 10, "bold")).pack(anchor="w", pady=(0, 6))

        form = tk.Frame(self, bg=BG)
        form.pack(fill=tk.X)

        # ── Variablen ────────────────────────────────────────────
        self._execution_var = tk.StringVar(value=settings.execution)
        self._mode_var = tk.StringVar(value=settings.mode)
        self._symbol_var = tk.StringVar(value=settings.ccxt_symbol)
        self._timeframe_var = tk.IntVar(value=settings.timeframe_minutes)
        self._risk_var = tk.DoubleVar(value=round(settings.risk_per_trade * 100, 2))
        self._minrr_var = tk.DoubleVar(value=settings.min_rr)
        self._equity_var = tk.DoubleVar(value=settings.account_equity)
        self._interval_var = tk.IntVar(value=settings.loop_interval_sec)
        self._session_end_var = tk.IntVar(value=settings.session_end_hour_utc)
        self._livefeed_var = tk.BooleanVar(value=settings.live_feed)
        self._daily_loss_var = tk.DoubleVar(value=round(settings.daily_loss_limit_pct * 100, 1))
        self._apikey_var = tk.StringVar(value=settings.bingx_api_key or "")
        self._apisecret_var = tk.StringVar(value=settings.bingx_api_secret or "")

        # Alle editierbaren Widgets für späteres Sperren
        self._editierbar: list[tk.Widget] = []

        def zeile(label: str, widget: tk.Widget, einheit: str = "") -> None:
            """Erstellt eine beschriftete Eingabezeile im Formular."""
            rahmen = tk.Frame(form, bg=BG)
            rahmen.pack(fill=tk.X, pady=1)
            tk.Label(rahmen, text=label, bg=BG, fg=FG_DIM,
                     font=("monospace", 8), width=18, anchor="w").pack(side=tk.LEFT)
            widget.pack(side=tk.LEFT, padx=(2, 0))
            if einheit:
                tk.Label(rahmen, text=einheit, bg=BG, fg=FG_DIM,
                         font=("monospace", 8)).pack(side=tk.LEFT, padx=(3, 0))
            self._editierbar.append(widget)

        # ── Felder ───────────────────────────────────────────────
        ex_box = ttk.Combobox(form, textvariable=self._execution_var,
                              values=["paper", "live"], width=10, state="readonly")
        zeile("Execution:", ex_box)

        mode_box = ttk.Combobox(form, textvariable=self._mode_var,
                                values=["manual", "auto"], width=10, state="readonly")
        zeile("Modus:", mode_box)

        symbol_entry = tk.Entry(form, textvariable=self._symbol_var, width=16,
                                bg=BG_ENTRY, fg=FG, insertbackground=FG, relief=tk.FLAT)
        zeile("Symbol:", symbol_entry)

        tf_spin = tk.Spinbox(form, textvariable=self._timeframe_var,
                             from_=1, to=1440, increment=5, width=6,
                             bg=BG_ENTRY, fg=FG, relief=tk.FLAT, buttonbackground=BG)
        zeile("Timeframe:", tf_spin, "min")

        risk_spin = tk.Spinbox(form, textvariable=self._risk_var,
                               from_=0.1, to=1.0, increment=0.1, width=6, format="%.1f",
                               bg=BG_ENTRY, fg=FG, relief=tk.FLAT, buttonbackground=BG)
        zeile("Risiko/Trade:", risk_spin, "%")

        rr_spin = tk.Spinbox(form, textvariable=self._minrr_var,
                             from_=1.0, to=10.0, increment=0.5, width=6, format="%.1f",
                             bg=BG_ENTRY, fg=FG, relief=tk.FLAT, buttonbackground=BG)
        zeile("Min. CRV:", rr_spin)

        equity_entry = tk.Entry(form, textvariable=self._equity_var, width=10,
                                bg=BG_ENTRY, fg=FG, insertbackground=FG, relief=tk.FLAT)
        zeile("Startkapital:", equity_entry, "$")

        interval_spin = tk.Spinbox(form, textvariable=self._interval_var,
                                   from_=5, to=300, increment=5, width=6,
                                   bg=BG_ENTRY, fg=FG, relief=tk.FLAT, buttonbackground=BG)
        zeile("Loop-Intervall:", interval_spin, "sek")

        session_spin = tk.Spinbox(form, textvariable=self._session_end_var,
                                  from_=0, to=23, increment=1, width=4,
                                  bg=BG_ENTRY, fg=FG, relief=tk.FLAT, buttonbackground=BG)
        zeile("Session-Ende:", session_spin, "UTC")

        loss_spin = tk.Spinbox(form, textvariable=self._daily_loss_var,
                               from_=0.5, to=10.0, increment=0.5, width=6, format="%.1f",
                               bg=BG_ENTRY, fg=FG, relief=tk.FLAT, buttonbackground=BG)
        zeile("Tagesverlust max:", loss_spin, "%")

        livefeed_check = tk.Checkbutton(form, variable=self._livefeed_var,
                                        bg=BG, fg=FG, selectcolor=BG_ENTRY,
                                        activebackground=BG, activeforeground=FG)
        zeile("Live-Kursdaten:", livefeed_check)

        # API-Schlüssel (verborgen)
        ttk.Separator(form, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)
        tk.Label(form, text="BingX API (nur Live)", bg=BG, fg=FG_DIM,
                 font=("monospace", 8, "italic")).pack(anchor="w")

        apikey_entry = tk.Entry(form, textvariable=self._apikey_var, width=20,
                                bg=BG_ENTRY, fg=FG, show="*", insertbackground=FG, relief=tk.FLAT)
        zeile("API Key:", apikey_entry)

        apisecret_entry = tk.Entry(form, textvariable=self._apisecret_var, width=20,
                                   bg=BG_ENTRY, fg=FG, show="*", insertbackground=FG, relief=tk.FLAT)
        zeile("API Secret:", apisecret_entry)

    def sperren(self, gesperrt: bool) -> None:
        """Sperrt/entsperrt alle Eingabefelder während die Engine läuft."""
        zustand = tk.DISABLED if gesperrt else tk.NORMAL
        readonly = "disabled" if gesperrt else "readonly"
        for widget in self._editierbar:
            if isinstance(widget, ttk.Combobox):
                widget.config(state=readonly)
            else:
                widget.config(state=zustand)

    def lese_settings(self) -> Settings:
        """Liest alle Felder aus und gibt ein neues Settings-Objekt zurück."""
        ccxt_symbol = self._symbol_var.get().strip()
        # Symbol ableiten: "BTC/USDT:USDT" → "BTC-USDT"
        basis = ccxt_symbol.split("/")[0] if "/" in ccxt_symbol else ccxt_symbol
        symbol = f"{basis}-USDT"

        return Settings(
            symbol=symbol,
            ccxt_symbol=ccxt_symbol,
            execution=self._execution_var.get(),  # type: ignore[arg-type]
            mode=self._mode_var.get(),
            timeframe_minutes=int(self._timeframe_var.get()),
            risk_per_trade=min(self._risk_var.get() / 100.0, 0.01),
            min_rr=self._minrr_var.get(),
            account_equity=self._equity_var.get(),
            loop_interval_sec=int(self._interval_var.get()),
            session_end_hour_utc=int(self._session_end_var.get()),
            daily_loss_limit_pct=self._daily_loss_var.get() / 100.0,
            live_feed=self._livefeed_var.get(),
            bingx_api_key=self._apikey_var.get() or None,
            bingx_api_secret=self._apisecret_var.get() or None,
        )
