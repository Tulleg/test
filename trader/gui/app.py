from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

from trader.config import Settings
from trader.engine import TradingEngine
from trader.gui.chart_panel import ChartPanel
from trader.gui.controls import ControlsPanel
from trader.gui.settings_panel import SettingsPanel
from trader.gui.state import GUIState
from trader.gui.status_panel import StatusPanel
from trader.gui.theme import (
    BORDER,
    CARD_PAD,
    DANGER,
    DANGER_BG,
    FONT_H1,
    FONT_H2,
    INFO,
    INFO_BG,
    OUTER_PAD,
    SECTION_GAP,
    SUCCESS,
    SUCCESS_BG,
    SURFACE,
    SURFACE_ALT,
    TEXT,
    TEXT_MUTED,
    WINDOW_BG,
    configure_ttk_styles,
    section_title,
    set_button_style,
    style_card,
    tag_label,
)

POLL_INTERVALL_MS = 500  # Wie oft die GUI aktualisiert wird (Millisekunden)


class TradingApp(tk.Tk):
    """Haupt-Fenster der Trading-GUI.

    Layout:
    ┌──────────────────────────────────┬──────────────────┐
    │                                  │  Settings Panel  │
    │      Candlestick Chart           ├──────────────────┤
    │                                  │  Status Panel    │
    │                                  ├──────────────────┤
    │                                  │ Controls         │
    └──────────────────────────────────┴──────────────────┘
    """

    def __init__(self, settings: Settings) -> None:
        super().__init__()

        self._settings = settings
        self._state = GUIState(equity=settings.account_equity)
        self._engine: TradingEngine | None = None
        self._engine_thread: threading.Thread | None = None
        self._signal_dialog_offen = False

        # Fenster konfigurieren
        self.title("BingX BTC Trader")
        self.configure(bg=WINDOW_BG)
        self.geometry("1360x860")
        self.minsize(1080, 680)
        configure_ttk_styles(self)

        self._baue_layout()
        self._poll()  # startet den periodischen Update-Zyklus

    def _baue_layout(self) -> None:
        """Erstellt Dashboard- und Settings-Tab."""
        shell = tk.Frame(self, bg=WINDOW_BG, padx=OUTER_PAD, pady=OUTER_PAD)
        shell.pack(fill=tk.BOTH, expand=True)

        header = tk.Frame(shell, bg=WINDOW_BG)
        header.pack(fill=tk.X, pady=(0, SECTION_GAP))

        brand = tk.Frame(header, bg=WINDOW_BG)
        brand.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(brand, text="BingX BTC Trader", bg=WINDOW_BG, fg=TEXT, font=FONT_H1).pack(anchor="w")
        tk.Label(
            brand,
            text="Modernisiertes Trading-Dashboard mit Live-Status, Chart und klarer Kontrollstruktur.",
            bg=WINDOW_BG,
            fg=TEXT_MUTED,
            font=("TkDefaultFont", 10),
        ).pack(anchor="w", pady=(4, 0))

        header_badges = tk.Frame(header, bg=WINDOW_BG)
        header_badges.pack(side=tk.RIGHT, anchor="n")
        self._run_badge = tag_label(header_badges, "Bereit", fg=INFO, bg=INFO_BG)
        self._run_badge.pack(anchor="e")
        self._header_status = tk.Label(header_badges, text="Engine inaktiv", bg=WINDOW_BG, fg=TEXT_MUTED, font=("TkDefaultFont", 9))
        self._header_status.pack(anchor="e", pady=(6, 0))

        notebook = ttk.Notebook(shell, style="App.TNotebook")
        notebook.pack(fill=tk.BOTH, expand=True)

        dashboard_tab = tk.Frame(notebook, bg=WINDOW_BG)
        settings_tab = tk.Frame(notebook, bg=WINDOW_BG)
        notebook.add(dashboard_tab, text="Dashboard")
        notebook.add(settings_tab, text="Einstellungen")

        content = tk.Frame(dashboard_tab, bg=WINDOW_BG)
        content.pack(fill=tk.BOTH, expand=True)

        linke_spalte = tk.Frame(content, bg=WINDOW_BG)
        linke_spalte.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        chart_card = tk.Frame(linke_spalte, bg=SURFACE, padx=CARD_PAD, pady=CARD_PAD)
        style_card(chart_card)
        chart_card.pack(fill=tk.BOTH, expand=True, padx=(0, SECTION_GAP))

        chart_head = section_title(chart_card, "Marktübersicht", "Candlesticks, Volumen und aktive Trade-Levels")
        chart_head.pack(fill=tk.X, pady=(0, 12))

        self._chart = ChartPanel(chart_card, self._state)
        self._chart.pack(fill=tk.BOTH, expand=True)

        rechte_spalte = tk.Frame(content, bg=WINDOW_BG, width=440)
        rechte_spalte.pack(side=tk.RIGHT, fill=tk.Y)
        rechte_spalte.pack_propagate(False)

        self._controls = ControlsPanel(
            rechte_spalte,
            on_start=self._on_start,
            on_stop=self._on_stop,
            on_close_trade=self._on_close_trade,
            on_quit=self._on_schliessen,
        )
        self._controls.pack(fill=tk.X, pady=(0, SECTION_GAP))

        self._status_panel = StatusPanel(rechte_spalte)
        self._status_panel.pack(fill=tk.BOTH, expand=True)

        settings_shell = tk.Frame(settings_tab, bg=WINDOW_BG, padx=2, pady=2)
        settings_shell.pack(fill=tk.BOTH, expand=True)
        self._settings_panel = SettingsPanel(settings_shell, self._settings)
        self._settings_panel.pack(fill=tk.X, anchor="n")

        # Fenster-Schließen-Event abfangen
        self.protocol("WM_DELETE_WINDOW", self._on_schliessen)

    def _poll(self) -> None:
        """Wird alle 500ms aufgerufen – liest GUIState und aktualisiert alle Widgets.

        Wichtig: Diese Funktion läuft im Main-Thread (Tkinter-Event-Loop).
        Sie liest unter Lock aus dem State und gibt den Lock sofort wieder frei.
        Die Widget-Updates danach laufen ohne Lock.
        """
        # Thread-sicherer Snapshot aller Daten
        with self._state.lock:
            snap = {
                "candles": list(self._state.candles),
                "open_trade": self._state.open_trade,
                "equity": self._state.equity,
                "day_pnl": self._state.day_pnl,
                "wins": self._state.wins,
                "losses": self._state.losses,
                "total_trades": self._state.total_trades,
                "status_msg": self._state.status_msg,
                "events": list(self._state.events),
                "running": self._state.running,
                "pending_signal": self._state.pending_signal,
            }

        # Widgets aktualisieren (Lock ist schon frei)
        self._chart.update(snap)
        self._status_panel.update(snap)
        self._controls.setze_engine_laeuft(snap["running"])
        self._controls.setze_trade_offen(snap["open_trade"] is not None)
        self._setze_header_status(snap)

        # Manuelles Signal zur Bestätigung?
        if snap["pending_signal"] and not self._signal_dialog_offen:
            self._zeige_signal_dialog(snap["pending_signal"])

        # Wenn Engine gestoppt hat, Settings wieder freischalten
        if not snap["running"] and self._engine is not None:
            if self._engine_thread and not self._engine_thread.is_alive():
                self._settings_panel.sperren(False)
                self._engine = None

        # Nächsten Poll planen
        self.after(POLL_INTERVALL_MS, self._poll)

    def _on_start(self) -> None:
        """Startet die Trading-Engine in einem Background-Thread."""
        settings = self._settings_panel.lese_settings()

        # Frischen State vorbereiten
        self._state = GUIState(
            equity=settings.account_equity,
            running=True,
        )

        try:
            self._engine = TradingEngine(settings)
        except Exception as exc:
            messagebox.showerror("Fehler beim Starten", str(exc))
            return

        self._settings_panel.sperren(True)

        self._engine_thread = threading.Thread(
            target=self._engine.run_gui_mode,
            args=(self._state,),
            daemon=True,  # Thread endet automatisch wenn das Fenster geschlossen wird
            name="TradingEngine",
        )
        self._engine_thread.start()

    def _on_stop(self) -> None:
        """Sendet Stop-Kommando an die Engine."""
        self._state.command_queue.put("stop_engine")

    def _on_close_trade(self) -> None:
        """Sendet Schließ-Kommando für die offene Position an die Engine."""
        self._state.command_queue.put("close_trade")

    def _setze_header_status(self, snap: dict) -> None:
        running = snap["running"]
        pnl = snap["day_pnl"]
        badge_text = "Aktiv" if running else "Bereit"
        badge_fg = SUCCESS if running else INFO
        badge_bg = SUCCESS_BG if running else INFO_BG
        self._run_badge.config(text=badge_text, fg=badge_fg, bg=badge_bg)
        status_text = snap["status_msg"] or ("Engine aktiv" if running else "Engine inaktiv")
        if pnl < 0:
            status_text = f"{status_text}  |  Tag {pnl:.2f} $"
        elif pnl > 0:
            status_text = f"{status_text}  |  Tag +{pnl:.2f} $"
        self._header_status.config(text=status_text)

    def _zeige_signal_dialog(self, signal: dict) -> None:
        """Öffnet einen modalen Dialog zur manuellen Signal-Bestätigung."""
        self._signal_dialog_offen = True

        dlg = tk.Toplevel(self)
        dlg.title("Neues Trading-Signal")
        dlg.configure(bg=WINDOW_BG)
        dlg.resizable(False, False)
        dlg.grab_set()  # Modal: blockiert das Hauptfenster

        # Richtungsanzeige
        ist_long = signal["direction"] == "long"
        pfeil = "▲ LONG" if ist_long else "▼ SHORT"
        farbe = SUCCESS if ist_long else DANGER
        hintergrund = SUCCESS_BG if ist_long else DANGER_BG

        shell = tk.Frame(dlg, bg=WINDOW_BG, padx=OUTER_PAD, pady=OUTER_PAD)
        shell.pack(fill=tk.BOTH, expand=True)

        card = tk.Frame(shell, bg=SURFACE, padx=CARD_PAD, pady=CARD_PAD)
        style_card(card)
        card.pack(fill=tk.BOTH, expand=True)

        top = tk.Frame(card, bg=SURFACE)
        top.pack(fill=tk.X)
        tag_label(top, pfeil, fg=farbe, bg=hintergrund).pack(anchor="w")
        tk.Label(card, text="Neues Trading-Signal", bg=SURFACE, fg=TEXT, font=FONT_H2).pack(anchor="w", pady=(12, 4))
        tk.Label(
            card,
            text=f"Setup: {signal.get('setup', '-')}",
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=("TkDefaultFont", 10),
        ).pack(anchor="w")

        ttk.Separator(card, orient=tk.HORIZONTAL, style="App.Horizontal.TSeparator").pack(fill=tk.X, pady=14)

        details = tk.Frame(card, bg=SURFACE_ALT, padx=16, pady=12)
        style_card(details, background=SURFACE_ALT, border=BORDER)
        details.pack(fill=tk.X)

        def detail_zeile(bezeichnung: str, wert: str, wert_farbe: str = "#cccccc") -> None:
            zeile = tk.Frame(details, bg=SURFACE_ALT)
            zeile.pack(fill=tk.X, pady=3)
            tk.Label(zeile, text=bezeichnung, bg=SURFACE_ALT, fg=TEXT_MUTED,
                     font=("TkDefaultFont", 9), width=12, anchor="w").pack(side=tk.LEFT)
            tk.Label(zeile, text=wert, bg=SURFACE_ALT, fg=wert_farbe,
                     font=("TkDefaultFont", 10, "bold")).pack(side=tk.LEFT)

        detail_zeile("Entry:", f"{signal.get('entry', 0):.2f}")
        detail_zeile("Stop Loss:", f"{signal.get('stop', 0):.2f}", DANGER)
        detail_zeile("Take Profit:", f"{signal.get('target', 0):.2f}", SUCCESS)
        detail_zeile("CRV:", f"{signal.get('rr', 0):.2f}", TEXT)

        # Buttons
        btn_frame = tk.Frame(card, bg=SURFACE, pady=4)
        btn_frame.pack(fill=tk.X, pady=(16, 0))

        def bestaetigen() -> None:
            self._state.signal_response.put("confirm")
            self._signal_dialog_offen = False
            dlg.destroy()

        def ablehnen() -> None:
            self._state.signal_response.put("reject")
            self._signal_dialog_offen = False
            dlg.destroy()

        confirm = tk.Button(btn_frame, text="Signal bestätigen", command=bestaetigen)
        set_button_style(confirm, variant="primary")
        confirm.pack(side=tk.LEFT)

        reject = tk.Button(btn_frame, text="Ablehnen", command=ablehnen)
        set_button_style(reject, variant="danger")
        reject.pack(side=tk.LEFT, padx=(10, 0))

        # Fenster-Schließen = Ablehnen
        dlg.protocol("WM_DELETE_WINDOW", ablehnen)

        # Dialog zentrieren
        dlg.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - dlg.winfo_width()) // 2
        y = self.winfo_y() + (self.winfo_height() - dlg.winfo_height()) // 2
        dlg.geometry(f"+{x}+{y}")

    def _on_schliessen(self) -> None:
        """Sauber beenden: Engine stoppen, dann Fenster schließen."""
        if self._state.running:
            self._state.command_queue.put("stop_engine")
        self.destroy()
