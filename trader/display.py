from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trader.models import Candle, Trade

# ANSI-Farbcodes
GRUEN = "\033[32m"
ROT = "\033[31m"
GELB = "\033[33m"
CYAN = "\033[36m"
GRAU = "\033[90m"
FETT = "\033[1m"
RESET = "\033[0m"

BREITE = 56  # Innenbreite der Box (ohne Rahmen)


def _pnl_farbe(wert: float) -> str:
    """Gibt den Wert farbig formatiert zurück (grün = positiv, rot = negativ)."""
    farbe = GRUEN if wert >= 0 else ROT
    vorzeichen = "+" if wert >= 0 else ""
    return f"{farbe}{vorzeichen}{wert:.2f} ${RESET}"


def _zeile(inhalt: str) -> str:
    """Baut eine Box-Zeile mit Rahmen. Inhalt wird auf Breite abgeschnitten."""
    # ANSI-Codes nicht in len() zählen → sichtbare Länge berechnen
    sichtbar = _sichtbare_laenge(inhalt)
    auffuellung = max(0, BREITE - sichtbar)
    return f"║  {inhalt}{' ' * auffuellung}  ║"


def _sichtbare_laenge(text: str) -> int:
    """Berechnet die angezeigte Länge ohne ANSI-Escape-Codes."""
    import re
    return len(re.sub(r"\033\[[0-9;]*m", "", text))


def _trennlinie() -> str:
    return "╠" + "═" * (BREITE + 4) + "╣"


def _kopfzeile() -> str:
    return "╔" + "═" * (BREITE + 4) + "╗"


def _fusszeile() -> str:
    return "╚" + "═" * (BREITE + 4) + "╝"


class StatusDisplay:
    def __init__(self, max_events: int = 4) -> None:
        self.events: list[str] = []
        self.max_events = max_events

    def add_event(self, msg: str) -> None:
        """Fügt ein Ereignis mit Zeitstempel in den Puffer ein."""
        zeit = datetime.now(UTC).strftime("%H:%M:%S")
        self.events.append(f"{GRAU}[{zeit}]{RESET}  {msg}")
        # Älteste Einträge entfernen wenn der Puffer voll ist
        if len(self.events) > self.max_events:
            self.events.pop(0)

    def draw(
        self,
        *,
        symbol: str,
        execution: str,
        mode: str,
        equity: float,
        day_pnl: float,
        total_trades: int,
        wins: int,
        losses: int,
        open_trade: Trade | None,
        last_candle: Candle | None,
        current_step: int,
        total_steps: int,
        status_msg: str,
    ) -> None:
        """Löscht das Terminal und zeichnet die Status-Box neu."""
        # Terminal leeren und Cursor nach oben
        print("\033[2J\033[H", end="")

        winrate = (wins / total_trades * 100) if total_trades else 0.0
        zeilen: list[str] = []

        # ── Kopfzeile ────────────────────────────────────────────
        zeilen.append(_kopfzeile())
        titel = f"{FETT}BingX BTC Trader{RESET}  ·  {symbol}  ·  {CYAN}{execution}{RESET}  ·  {mode}"
        zeilen.append(_zeile(titel))
        zeilen.append(_trennlinie())

        # ── Kapital & PnL ────────────────────────────────────────
        kapital_str = f"Kapital: {FETT}{equity:,.2f} ${RESET}"
        pnl_str = f"Tag PnL: {_pnl_farbe(day_pnl)}"
        zeilen.append(_zeile(f"{kapital_str}    {pnl_str}"))

        trades_str = (
            f"Trades: {total_trades}  ·  "
            f"{GRUEN}Wins: {wins}{RESET}  ·  "
            f"{ROT}Losses: {losses}{RESET}  ·  "
            f"Win: {winrate:.0f}%"
        )
        zeilen.append(_zeile(trades_str))
        zeilen.append(_trennlinie())

        # ── Offene Position ──────────────────────────────────────
        if open_trade:
            pfeil = "▲" if open_trade.direction == "long" else "▼"
            richtung_farbe = GRUEN if open_trade.direction == "long" else ROT
            kopf = (
                f"{richtung_farbe}{FETT}{pfeil} {open_trade.direction.upper()}{RESET}"
                f"  {open_trade.setup_name}"
            )
            zeilen.append(_zeile(kopf))
            zeilen.append(_zeile(
                f"Entry: {open_trade.entry_price:.0f}  "
                f"SL: {open_trade.stop_price:.0f}  "
                f"TP: {open_trade.take_profit_price:.0f}  "
                f"CRV: {open_trade.reward_risk_ratio:.1f}"
            ))
            # Unrealized PnL aus letzter Kerze berechnen
            if last_candle:
                if open_trade.direction == "long":
                    unrealized = (last_candle.close - open_trade.entry_price) * open_trade.position_size
                else:
                    unrealized = (open_trade.entry_price - last_candle.close) * open_trade.position_size
                zeilen.append(_zeile(f"Unrealized PnL:  {_pnl_farbe(unrealized)}"))
        else:
            zeilen.append(_zeile(f"{GRAU}Keine offene Position{RESET}"))

        zeilen.append(_trennlinie())

        # ── Ereignis-Log ─────────────────────────────────────────
        if self.events:
            for event in self.events:
                zeilen.append(_zeile(event))
        else:
            zeilen.append(_zeile(f"{GRAU}Noch keine Ereignisse{RESET}"))

        zeilen.append(_trennlinie())

        # ── Statuszeile ──────────────────────────────────────────
        fortschritt = f"Schritt {current_step} / {total_steps}"
        zeilen.append(_zeile(f"{GRAU}{fortschritt}{RESET}  ·  {status_msg}"))
        zeilen.append(_fusszeile())

        print("\n".join(zeilen))
