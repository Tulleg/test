# Requirements-Dokument: BingX BTC Perpetual Futures App

## 1. Zweck und Zielbild

Die App ist ein terminalbasiertes Intraday-Trading-System fuer BTC Perpetual Futures auf BingX.
Sie soll Handelsentscheidungen regelbasiert treffen und ausfuehren, mit strikt begrenztem Risiko pro Trade.

Primaires Ziel:
- Kapitalerhalt und konsistente Ausfuehrung eines regelbasierten Ansatzes
- Maximal 1% Kontorisiko pro Trade
- Mindest Chance-Risiko-Verhaeltnis (CRV) von 1:2
- Lueckenlose Protokollierung aller Signale, Entscheidungen und Ergebnisse

Nicht-Ziele:
- Kein Handel auf Timeframes unter 5 Minuten
- Kein Swing- oder Overnight-Halten von Positionen
- Kein discretionary Trading ausser expliziter manueller Trade-Bestaetigung im Manual-Modus

## 2. Produktumfang und Scope

- Handelsinstrument: `BTC-USDT Perpetual` auf BingX
- Plattform: Terminal/CLI-App (Linux-kompatibel)
- Betriebsarten: `manual` und `auto`
- Handelsstil: intraday-only
- Datenauflosung: mindestens 5m, optional 15m/1h als Kontext

## 3. Betriebsmodi

### 3.1 Manual-Modus

- Jeder Trade muss vor Order-Placement manuell bestaetigt werden.
- Bei aktivem Signal wird ein Warnsignal im Terminal angezeigt (visuell klar hervorgehoben, optional akustisch konfigurierbar).
- Vor Bestaetigung muessen angezeigt werden:
  - Richtung (Long/Short)
  - Entry-Preis
  - Stop-Loss
  - Take-Profit
  - Positionsgroesse
  - erwartetes CRV
  - Grund fuer Signal (Setup + Marktregime)
- Ohne Bestaetigung innerhalb eines konfigurierbaren Timeouts wird kein Trade platziert.

### 3.2 Auto-Modus

- Trades werden automatisch ausgefuehrt, sofern alle Pflichtregeln erfuellt sind.
- Ein Warnsignal wird trotzdem geloggt und im Terminal angezeigt.
- Bei Regelverletzung (z. B. CRV < 1:2, Risiko > 1%) wird der Trade zwingend abgelehnt.

## 4. Harte Risiko- und Money-Management-Regeln

Diese Regeln sind nicht ueberschreibbar und gelten in beiden Modi:

1. **Maximalrisiko pro Trade**
   - `riskPerTrade <= 1.00%` vom aktuellen Kontostand (equity-basiert).

2. **Mindest-CRV**
   - `reward:risk >= 2.0`.
   - Falls kleiner, kein Trade.

3. **Automatische SL/TP-Setzung**
   - Jeder Trade muss vor Ausfuehrung einen gueltigen Stop-Loss und Profit-Target besitzen.
   - Keine Order ohne Schutzparameter.

4. **Positionsgroesse**
   - Berechnung aus Kontorisiko und Stop-Distanz.
   - Formel (konzeptionell):
     - `positionSize = maxRiskAmount / abs(entryPrice - stopPrice)`
   - Muss Ticksize, Lot-Step und minimale Ordergroesse der Boerse respektieren.

5. **Intraday-Risikobegrenzung**
   - Tagesverlustlimit (z. B. 3R oder 3% Equity) als Muss-Konfiguration.
   - Nach Erreichen des Limits: kein weiterer Trade bis naechster Handelstag.

6. **Exposure-Regel**
   - Maximal eine offene BTC-Position gleichzeitig.

## 5. Zeit- und Marktregeln

- Keine Signalgenerierung und keine Ausfuehrung unterhalb `5m`.
- Erlaubte Signaltimeframes: `5m` (Minimum), optional `15m` als Bestaetigung.
- Nur intraday:
  - Vor Tagesende muessen alle Positionen geschlossen werden.
  - Kein Overnight-Halten.

## 6. Hybrid-Strategie (profitabel-orientiert)

Die Strategie kombiniert Trendfolge und Mean-Reversion, basierend auf einem Marktregime-Filter.

### 6.1 Regime-Erkennung

Die App muss den Markt pro Signal als `trend` oder `range` klassifizieren.
Beispielhaft ueber:
- ADX/ATR-Charakteristik
- Distanz zu EMA-Baendern
- Struktur von Hochs/Tiefs

Nur das zum Regime passende Setup darf aktiv werden.

### 6.2 Trend-Setup (Breakout/Momentum)

Ziel: Teilnahme an intraday Momentum-Phasen.

Pflichtbedingungen (beispielhafte Spezifikation):
- Preis ueber (Long) oder unter (Short) Trendfilter (z. B. EMA50 auf 5m)
- Breakout ueber/unter lokale Struktur (z. B. letzte Swing-Range)
- Volumen-/Volatilitaetsfilter bestaetigt den Impuls
- Kein Entry direkt in nahe Gegenstruktur mit unzureichendem Raum fuer CRV >= 1:2

Stop-Loss:
- unter/ueber letztem validen Swing oder ATR-basiert (strikter, objektiver Wert)

Take-Profit:
- mindestens 2R vom initialen Risikoabstand

### 6.3 Mean-Reversion-Setup (Ruecklauf)

Ziel: Ausnutzung kurzfristiger Ueberdehnung in Seitwaertsphasen.

Pflichtbedingungen (beispielhafte Spezifikation):
- Regime ist `range`
- Preis ist statistisch ueberdehnt relativ zu VWAP/Band-Referenz
- Rueckkehrsignal (z. B. Momentum-Abschwaechung) liegt vor
- Liquiditaet ausreichend, Spread in akzeptablem Bereich

Stop-Loss:
- hinter Extrempunkt der Ueberdehnung (plus Sicherheitsabstand)

Take-Profit:
- Ruecklaufziel mit mindestens 2R, sonst kein Trade

### 6.4 Setup-Qualitaetsfilter

Ein Trade wird nur freigegeben, wenn alle Bedingungen erfuellt sind:
- gueltiges Regime
- gueltiges Setup
- Risiko <= 1%
- CRV >= 1:2
- Intraday-/Zeitfensterregel eingehalten
- keine aktive Sperre (Tagesverlustlimit, Wartungsmodus, API-Fehler)

## 7. Order- und Ausfuehrungslogik

1. Signal erzeugen
2. Risiko- und Regelpruefung
3. Positionsgroesse berechnen
4. SL/TP berechnen
5. Modusabhaengige Ausfuehrung:
   - `manual`: User-Bestaetigung abwarten
   - `auto`: direkt platzieren
6. Positionsueberwachung:
   - Exit bei TP/SL
   - Optional: Break-even-Regel nach 1R
7. Abschluss und Logging

Fehlerbehandlung:
- Bei API-Fehlern keine "blind retry loops" ohne Backoff.
- Bei inkonsistentem Orderstatus muss ein Safety-Check den Realzustand gegen Boersenstatus validieren.

## 8. Terminal UX Anforderungen

Die App laeuft vollstaendig im Terminal und muss folgende Ansichten bereitstellen:

- **Live-Status**
  - Modus (`manual`/`auto`)
  - Kontostand, Tages-PnL, offene Position, unrealized PnL
- **Signalpanel**
  - Setup-Typ, Richtung, Entry, SL, TP, CRV, Risiko in %
- **Warnsignal**
  - Klarer Hinweis bei neuem Signal und bei Regelverstoessen
- **Manual Prompt**
  - Eindeutige Eingabe fuer `confirm/reject`
- **Event-Ausgabe**
  - Zeitgestempelte System- und Trade-Events

## 9. Logging und Ergebnisspeicherung

Alle Ergebnisse muessen persistent gespeichert werden.

### 9.1 Log-Dateien

- `logs/trades.jsonl` (strukturierte Einzelereignisse)
- `logs/daily_summary.log` (lesbare Tageszusammenfassung)

### 9.2 Pflichtfelder pro Signal/Trade

- timestamp (UTC)
- symbol
- mode (manual/auto)
- regime (trend/range)
- setupName
- direction
- entryPrice
- stopPrice
- takeProfitPrice
- riskPercent
- rewardRiskRatio
- positionSize
- decision (accepted/rejected)
- rejectionReason (falls abgelehnt)
- orderId / executionStatus
- realizedPnL
- fees
- tradeDuration

### 9.3 KPI-Auswertung (mindestens taeglich)

- Anzahl Trades
- Winrate
- Durchschnittlicher Gewinn/Verlust
- Profit Factor
- Expectancy
- Max Drawdown (intraday und rollierend)
- Anteil abgelehnter Signale inkl. Grundkategorien

## 10. Konfiguration

Mindestens folgende Konfigurationswerte muessen vorhanden sein:

- API-Zugangsdaten (sicher geladen, nicht im Klartext im Code)
- Modus (`manual`/`auto`)
- Risiko pro Trade (hart gedeckelt auf 1%)
- Tagesverlustlimit
- erlaubte Handelszeiten
- Standard-Timeframe (>= 5m)
- Parameter fuer Regime-, Trend- und Mean-Reversion-Filter
- Log-Pfade

## 11. Nicht-funktionale Anforderungen

- Zuverlaessigkeit: robuster Umgang mit API-Fehlern und Netzwerkunterbrechungen
- Nachvollziehbarkeit: jede Entscheidung ist im Log rekonstruierbar
- Sicherheit: keine Secrets im Repository; Nutzung von Umgebungsvariablen
- Performance: Signalgenerierung und Ausfuehrungschecks innerhalb weniger Sekunden pro Kerze
- Bedienbarkeit: klare CLI-Ausgaben, eindeutige Fehlermeldungen

## 12. Akzeptanzkriterien (testbar)

1. Ein Trade mit berechnetem Risiko > 1% wird immer abgelehnt.
2. Ein Trade mit CRV < 1:2 wird immer abgelehnt.
3. Unterhalb des 5m-Charts werden keine Signale verarbeitet.
4. Im Manual-Modus wird ohne Bestaetigung keine Order platziert.
5. Jeder ausgefuehrte Trade besitzt beim Entry gesetzten SL und TP.
6. Jeder Trade/Signal-Entscheid wird mit Pflichtfeldern geloggt.
7. Bei Erreichen des Tagesverlustlimits werden weitere Trades blockiert.
8. Vor Handelstag-Ende sind keine offenen Positionen vorhanden.

## 13. Empfehlung fuer profitable Umsetzung (im Rahmen der Anforderungen)

Die profitabelste realistische Ausrichtung innerhalb dieses Lastenhefts ist:
- Regime-gesteuerte Hybridlogik (Trend nur in Trendphasen, Mean-Reversion nur in Range-Phasen)
- Strikte Selectivity statt hoher Trade-Frequenz
- Harte Risikobegrenzung (1% max, bevorzugt 0.5%-0.75% als Startwert im Livebetrieb)
- Laufende KPI-Review und parameterarme Iteration (Overfitting vermeiden)

Hinweis:
Profitabilitaet kann nicht garantiert werden. Sie ist von Marktregime, Ausfuehrungsqualitaet, Gebuehren/Slippage und Disziplin bei der Regelbefolgung abhaengig.
