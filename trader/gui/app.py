from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox

from trader.config import Settings
from trader.engine import TradingEngine
from trader.gui.chart_panel import ChartPanel
from trader.gui.controls import ControlsPanel
from trader.gui.settings_panel import SettingsPanel
from trader.gui.state import GUIState
from trader.gui.status_panel import StatusPanel

BG = "#1e1e1e"
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
        self.configure(bg=BG)
        self.geometry("1300x800")
        self.minsize(900, 600)

        self._baue_layout()
        self._poll()  # startet den periodischen Update-Zyklus

    def _baue_layout(self) -> None:
        """Erstellt das Zwei-Spalten-Layout."""
        # Linke Spalte: Chart (nimmt den meisten Platz ein)
        linke_spalte = tk.Frame(self, bg=BG)
        linke_spalte.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Titel-Leiste über dem Chart
        titel = tk.Label(
            linke_spalte,
            text="BingX BTC Trader",
            bg=BG,
            fg="#4ac8ff",
            font=("monospace", 12, "bold"),
            pady=6,
        )
        titel.pack(fill=tk.X)

        self._chart = ChartPanel(linke_spalte, self._state)
        self._chart.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))

        # Rechte Spalte: Settings + Status + Controls
        rechte_spalte = tk.Frame(self, bg=BG, width=320)
        rechte_spalte.pack(side=tk.RIGHT, fill=tk.Y)
        rechte_spalte.pack_propagate(False)  # Breite festhalten

        self._settings_panel = SettingsPanel(rechte_spalte, self._settings)
        self._settings_panel.pack(fill=tk.X)

        tk.Frame(rechte_spalte, bg="#333333", height=1).pack(fill=tk.X)  # Trennlinie

        self._status_panel = StatusPanel(rechte_spalte)
        self._status_panel.pack(fill=tk.BOTH, expand=True)

        tk.Frame(rechte_spalte, bg="#333333", height=1).pack(fill=tk.X)  # Trennlinie

        self._controls = ControlsPanel(
            rechte_spalte,
            on_start=self._on_start,
            on_stop=self._on_stop,
            on_close_trade=self._on_close_trade,
        )
        self._controls.pack(fill=tk.X)

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

    def _zeige_signal_dialog(self, signal: dict) -> None:
        """Öffnet einen modalen Dialog zur manuellen Signal-Bestätigung."""
        self._signal_dialog_offen = True

        dlg = tk.Toplevel(self)
        dlg.title("Neues Trading-Signal")
        dlg.configure(bg="#1e1e1e")
        dlg.resizable(False, False)
        dlg.grab_set()  # Modal: blockiert das Hauptfenster

        # Richtungsanzeige
        ist_long = signal["direction"] == "long"
        pfeil = "▲ LONG" if ist_long else "▼ SHORT"
        farbe = "#44dd44" if ist_long else "#ff4444"

        tk.Label(dlg, text=pfeil, bg="#1e1e1e", fg=farbe,
                 font=("monospace", 18, "bold"), pady=10).pack()

        tk.Label(dlg, text=f"Setup: {signal.get('setup', '-')}", bg="#1e1e1e", fg="#cccccc",
                 font=("monospace", 10)).pack()

        # Preis-Details
        details = tk.Frame(dlg, bg="#252525", padx=16, pady=10)
        details.pack(fill=tk.X, padx=16, pady=8)

        def detail_zeile(bezeichnung: str, wert: str, wert_farbe: str = "#cccccc") -> None:
            zeile = tk.Frame(details, bg="#252525")
            zeile.pack(fill=tk.X, pady=2)
            tk.Label(zeile, text=bezeichnung, bg="#252525", fg="#888888",
                     font=("monospace", 9), width=12, anchor="w").pack(side=tk.LEFT)
            tk.Label(zeile, text=wert, bg="#252525", fg=wert_farbe,
                     font=("monospace", 9, "bold")).pack(side=tk.LEFT)

        detail_zeile("Entry:", f"{signal.get('entry', 0):.2f}")
        detail_zeile("Stop Loss:", f"{signal.get('stop', 0):.2f}", "#ff4444")
        detail_zeile("Take Profit:", f"{signal.get('target', 0):.2f}", "#44dd44")
        detail_zeile("CRV:", f"{signal.get('rr', 0):.2f}")

        # Buttons
        btn_frame = tk.Frame(dlg, bg="#1e1e1e", pady=8)
        btn_frame.pack()

        def bestaetigen() -> None:
            self._state.signal_response.put("confirm")
            self._signal_dialog_offen = False
            dlg.destroy()

        def ablehnen() -> None:
            self._state.signal_response.put("reject")
            self._signal_dialog_offen = False
            dlg.destroy()

        tk.Button(btn_frame, text="✓  Bestätigen", command=bestaetigen,
                  bg="#1a5c1a", fg="#44dd44", activebackground="#2a7a2a",
                  font=("monospace", 10, "bold"), relief=tk.FLAT,
                  padx=14, pady=7, cursor="hand2").pack(side=tk.LEFT, padx=6)

        tk.Button(btn_frame, text="✕  Ablehnen", command=ablehnen,
                  bg="#3a1a1a", fg="#ff6666", activebackground="#5a2a2a",
                  font=("monospace", 10, "bold"), relief=tk.FLAT,
                  padx=14, pady=7, cursor="hand2").pack(side=tk.LEFT, padx=6)

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
