# BingX BTC Perpetual Trader

Automatisiertes Terminal-Trading-System für BTC Perpetual Futures auf der BingX-Börse.

Die App analysiert Marktdaten mit einer Hybrid-Strategie (Trend-Breakout + Mean-Reversion) und öffnet Positionen nach strikten Risikoregeln — entweder vollautomatisch oder mit manueller Bestätigung.

---

## Voraussetzungen

- Python 3.10 oder neuer
- Ein BingX-Account (nur für Live-Trading)

---

## Installation

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

---

## Starten

### Interaktives Menü (empfohlen)

Einfach ohne Argumente starten:

```bash
python3 main.py
```

Es öffnet sich ein Menü im Terminal, in dem du alle Einstellungen bequem setzen kannst:

```
==================================================
   BingX BTC Perpetual Trader
==================================================

  [1] Ausführung      : paper  (paper / live)
  [2] Modus           : manual  (manual / auto)
  [3] Kapital (paper) : 10000.00 USDT
  [4] Risiko/Trade    : 1.00 %  (max 1%)
  [5] Min. CRV        : 2.0
  [6] Timeframe       : 5 min
  [7] Schritte        : 200
  [8] Interval        : 2 Sek.
  [9] Session-Ende    : 23:00 UTC

  [A] API Key         : (nicht gesetzt)
  [B] API Secret      : (nicht gesetzt)

  [S] Start
  [Q] Beenden
```

Zahl oder Buchstabe eingeben → Wert ändern → `S` zum Starten.  
API-Keys werden versteckt eingegeben (kein Echo im Terminal).

---

### Direktstart per Argumente

Für Fortgeschrittene oder automatisierte Starts:

```bash
# Paper-Simulation, automatischer Modus
python3 main.py --mode auto --execution paper --steps 200

# Live-Trading, manuelle Bestätigung
export BINGX_API_KEY="dein_key"
export BINGX_API_SECRET="dein_secret"
python3 main.py --mode manual --execution live --steps 500
```

Alle verfügbaren Argumente:

| Argument | Standard | Bedeutung |
|---|---|---|
| `--mode` | `manual` | `manual` = du bestätigst jeden Trade, `auto` = vollautomatisch |
| `--execution` | `paper` | `paper` = Simulation, `live` = echte Orders auf BingX |
| `--steps` | `200` | Anzahl der Schleifen (jede Schleife = eine neue Kerze) |
| `--equity` | `10000` | Startkapital in USDT (nur Paper-Modus) |
| `--risk` | `0.01` | Risiko pro Trade (max. 1% = 0.01) |
| `--min-rr` | `2.0` | Mindest-CRV (Chance-Risiko-Verhältnis) |
| `--timeframe` | `5` | Kerzenlänge in Minuten (min. 5) |
| `--interval-sec` | `2` | Wartezeit zwischen zwei Schleifen in Sekunden |
| `--session-end-hour-utc` | `23` | Ab dieser UTC-Stunde werden keine neuen Trades mehr eröffnet |

---

## Modi erklärt

### Paper vs. Live

| | Paper | Live |
|---|---|---|
| Kapital | Simuliert | Echtes Geld auf BingX |
| Orders | Intern berechnet | Über BingX Futures API |
| API-Keys | Nicht nötig | Pflicht |
| Empfehlung | Zum Testen | Erst nach ausgiebigem Paper-Test |

### Manual vs. Auto

- **Manual:** Bei jedem Signal fragt die App: `confirm` oder `reject` eingeben (Timeout: 30 Sek.)
- **Auto:** Trades werden automatisch ausgeführt, sobald alle Regeln erfüllt sind

---

## Risikoregeln (fest eingebaut)

Diese Regeln können nicht deaktiviert werden:

- **Max. 1% Risiko pro Trade** — Positionsgröße wird automatisch berechnet
- **Mindest-CRV 1:2** — Ein Trade wird nur eröffnet, wenn das Ziel mindestens doppelt so weit entfernt ist wie der Stop-Loss
- **Kein Trading unter 5-Minuten-Kerzen**
- **Tagesverlustlimit:** Standardmäßig 3% des Eigenkapitals — danach werden keine neuen Positionen mehr eröffnet
- **Intraday-Regel:** Offene Positionen werden automatisch zum Session-Ende geschlossen

---

## Strategie

Die Hybrid-Strategie erkennt automatisch das aktuelle Marktregime:

- **Trend-Modus:** EMA(20) und EMA(50) liegen weit auseinander → sucht nach Breakouts über/unter Swing-Hochs/-Tiefs mit Volumenbestätigung
- **Range-Modus:** Markt bewegt sich seitwärts → sucht nach Mean-Reversion an den Bollinger-Bändern

---

## Live-Trading einrichten

1. BingX-Account erstellen und Futures aktivieren
2. API-Key erstellen — **nur Futures-Berechtigung**, keine Withdraw-Rechte!
3. App starten und Keys über das Menü eingeben (`[A]` und `[B]`)

Alternativ als Umgebungsvariablen:

```bash
export BINGX_API_KEY="dein_key"
export BINGX_API_SECRET="dein_secret"
```

---

## Logs

Nach jedem Lauf werden zwei Dateien im `logs/`-Ordner aktualisiert:

- **`trades.jsonl`** — Jeder einzelne Trade mit allen Details (Entry, Exit, PnL, Grund usw.)
- **`daily_summary.log`** — Tägliche Zusammenfassung mit KPIs:
  - Winrate, Profit Factor, Expectancy
  - Max. Drawdown
  - Ablehnungen nach Kategorie

---

## Projektstruktur

```
main.py                 → Einstiegspunkt
trader/
  cli.py                → Menü und Argument-Parser
  config.py             → Alle Einstellungen
  engine.py             → Hauptschleife und Trade-Logik
  strategy.py           → Hybrid-Strategie (Trend + Mean-Reversion)
  risk.py               → Risikoberechnung und Signal-Validierung
  indicators.py         → EMA, SMA, ATR, Standardabweichung
  models.py             → Datenklassen (Signal, Trade, Candle)
  exchange.py           → Paper-Exchange (Simulation)
  bingx_exchange.py     → Live-Orders über BingX API
  bingx_feed.py         → Marktdaten von BingX
  datafeed.py           → Mock-Datenfeed für Tests
  logging_utils.py      → Trade- und Summary-Logging
logs/
  trades.jsonl
  daily_summary.log
```
