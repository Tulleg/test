from __future__ import annotations

import argparse
import getpass
import os
import sys

from trader.config import Settings
from trader.engine import TradingEngine


def _clear() -> None:
    os.system("clear")


def _zeige_menue(s: Settings) -> None:
    """Gibt das Einstellungsmenü im Terminal aus."""
    _clear()
    print("=" * 50)
    print("   BingX BTC Perpetual Trader")
    print("=" * 50)
    print()
    print(f"  [1] Ausführung      : {s.execution}  (paper / live)")
    print(f"  [2] Modus           : {s.mode}  (manual / auto)")
    print(f"  [3] Kapital (paper) : {s.account_equity:.2f} USDT")
    print(f"  [4] Risiko/Trade    : {s.risk_per_trade * 100:.2f} %  (max 1%)")
    print(f"  [5] Min. CRV        : {s.min_rr:.1f}")
    print(f"  [6] Timeframe       : {s.timeframe_minutes} min")
    print(f"  [7] Schritte        : {s.loop_steps}")
    print(f"  [8] Interval        : {s.loop_interval_sec} Sek.")
    print(f"  [9] Session-Ende    : {s.session_end_hour_utc}:00 UTC")
    print()
    # API-Keys maskiert anzeigen
    key_anzeige = "*** (gesetzt)" if s.bingx_api_key else "(nicht gesetzt)"
    secret_anzeige = "*** (gesetzt)" if s.bingx_api_secret else "(nicht gesetzt)"
    print(f"  [A] API Key         : {key_anzeige}")
    print(f"  [B] API Secret      : {secret_anzeige}")
    print()
    print("  [S] Start")
    print("  [Q] Beenden")
    print()


def _frage(prompt: str, standard: str) -> str:
    """Fragt den Nutzer nach einem Wert, zeigt den Standard in Klammern."""
    antwort = input(f"  {prompt} [{standard}]: ").strip()
    # Wenn nichts eingegeben → Standard behalten
    return antwort if antwort else standard


def _interaktives_menue() -> Settings:
    """Zeigt das Menü und gibt die fertigen Settings zurück."""
    s = Settings.from_env()
    # Standard-Schritte für das Menü
    if not hasattr(s, "loop_steps"):
        s.loop_steps = 200

    while True:
        _zeige_menue(s)
        auswahl = input("  Auswahl: ").strip().lower()

        if auswahl == "1":
            wert = _frage("Ausführung (paper/live)", s.execution)
            if wert in ("paper", "live"):
                s.execution = wert  # type: ignore[assignment]
            else:
                input("  Ungültig. Enter drücken...")

        elif auswahl == "2":
            wert = _frage("Modus (manual/auto)", s.mode)
            if wert in ("manual", "auto"):
                s.mode = wert
            else:
                input("  Ungültig. Enter drücken...")

        elif auswahl == "3":
            try:
                s.account_equity = float(_frage("Kapital in USDT", str(s.account_equity)))
            except ValueError:
                input("  Ungültige Zahl. Enter drücken...")

        elif auswahl == "4":
            try:
                wert = float(_frage("Risiko in % (max 1.0)", str(s.risk_per_trade * 100)))
                # Sicherheitsgrenze: niemals mehr als 1% riskieren
                s.risk_per_trade = min(wert / 100, 0.01)
            except ValueError:
                input("  Ungültige Zahl. Enter drücken...")

        elif auswahl == "5":
            try:
                s.min_rr = float(_frage("Min. CRV", str(s.min_rr)))
            except ValueError:
                input("  Ungültige Zahl. Enter drücken...")

        elif auswahl == "6":
            try:
                wert = int(_frage("Timeframe in Minuten (min 5)", str(s.timeframe_minutes)))
                if wert >= 5:
                    s.timeframe_minutes = wert
                else:
                    input("  Mindestens 5 Minuten. Enter drücken...")
            except ValueError:
                input("  Ungültige Zahl. Enter drücken...")

        elif auswahl == "7":
            try:
                s.loop_steps = int(_frage("Anzahl Schritte", str(s.loop_steps)))
            except ValueError:
                input("  Ungültige Zahl. Enter drücken...")

        elif auswahl == "8":
            try:
                s.loop_interval_sec = int(_frage("Interval in Sekunden", str(s.loop_interval_sec)))
            except ValueError:
                input("  Ungültige Zahl. Enter drücken...")

        elif auswahl == "9":
            try:
                s.session_end_hour_utc = int(_frage("Session-Ende UTC-Stunde (0-23)", str(s.session_end_hour_utc)))
            except ValueError:
                input("  Ungültige Zahl. Enter drücken...")

        elif auswahl == "a":
            # getpass versteckt die Eingabe im Terminal
            key = getpass.getpass("  API Key (Eingabe versteckt): ")
            if key:
                s.bingx_api_key = key

        elif auswahl == "b":
            secret = getpass.getpass("  API Secret (Eingabe versteckt): ")
            if secret:
                s.bingx_api_secret = secret

        elif auswahl == "s":
            # Live-Modus ohne Keys → warnen
            if s.execution == "live" and (not s.bingx_api_key or not s.bingx_api_secret):
                input("  WARNUNG: Live-Modus ohne API-Keys! Bitte zuerst [A] und [B] setzen. Enter drücken...")
                continue
            _clear()
            return s

        elif auswahl == "q":
            _clear()
            print("Beendet.")
            sys.exit(0)


def run() -> None:
    # Wenn keine Argumente übergeben → interaktives Menü anzeigen
    if len(sys.argv) == 1:
        settings = _interaktives_menue()
        steps = settings.loop_steps
    else:
        # Argumente übergeben → wie bisher per CLI starten
        parser = argparse.ArgumentParser(description="BingX BTC Perpetual terminal trader (paper or live).")
        parser.add_argument("--mode", choices=["manual", "auto"], default="manual")
        parser.add_argument("--execution", choices=["paper", "live"], default=None)
        parser.add_argument("--steps", type=int, default=200)
        parser.add_argument("--timeframe", type=int, default=5)
        parser.add_argument("--equity", type=float, default=10000.0)
        parser.add_argument("--risk", type=float, default=0.01)
        parser.add_argument("--min-rr", type=float, default=2.0)
        parser.add_argument("--interval-sec", type=int, default=1)
        parser.add_argument("--session-end-hour-utc", type=int, default=23)
        parser.add_argument("--ccxt-symbol", type=str, default=None)
        args = parser.parse_args()

        settings = Settings.from_env(mode_override=args.mode)
        if args.execution is not None:
            settings.execution = args.execution  # type: ignore[assignment]
        settings.timeframe_minutes = args.timeframe
        settings.account_equity = args.equity
        settings.risk_per_trade = min(args.risk, 0.01)
        settings.min_rr = args.min_rr
        settings.loop_interval_sec = args.interval_sec
        settings.session_end_hour_utc = args.session_end_hour_utc
        if args.ccxt_symbol:
            settings.ccxt_symbol = args.ccxt_symbol
        steps = args.steps

    engine = TradingEngine(settings=settings)
    engine.run(steps=steps)
