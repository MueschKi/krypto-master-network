# Krypto Master Network v2 – Cloud-Paper-Architektur und spätere Kraken-Freigabe

**Stand:** 30.10.2026 · **Status:** Architekturspezifikation, keine laufende neue Cloud-Anwendung.

## 1. Ziel, Reihenfolge und unveränderliche Grenzen

Das Projekt soll sich auch bei geschlossenem iPhone/PC-Browser automatisch um abgeschlossene Krypto-Kerzen und später um *simulierte* Paper-Kauf-/Verkaufsentscheidungen kümmern. Die Web-App ist **Anzeigefläche und geschütztes Bedienfeld**, **nicht** die Trading-Engine und nicht der Auslöser der normalen Ausführung.

- **A – Issue #8:** MTF (1d, 4h, 1h, 15m) als read-only Cloudflare-Prototyp mit D1, UTC-Cron und mobiler PWA. **Kein Paper-Schreiben.**
- **B – Issue #9:** Cloud-Paper-Trading für zwei getrennte virtuelle Portfolios, erst nach Paritätsprüfung und ausdrücklich abgesichertem einmaligem Cutover.
- **C – Issue #10:** Optionale Kraken-Spot-Echtgeldintegration erst nach unabhängigem Sicherheitsreview und **separater ausdrücklicher Freigabe durch den Eigentümer**. Die hier beschriebene Entwicklung autorisiert *keine* Echtgeldorder.

**Verboten:** stille Strategieänderungen; Reset vorhandener Konten; simultane GitHub-/Cloud-Paper-Schreiber; Veröffentlichung von Zugangsdaten oder privaten Kontobewegungen im öffentlichen Repository; automatische Echtgeldfreigabe. Kein System kann Gewinne versprechen.

## 2. Hosting- und Laufzeitmodell

Cloudflare **Workers Free** ist *serverless*, kein ständig laufender Python-Prozess. Cron Triggers rufen einen `scheduled()`-Handler auf UTC-Basis auf; die Anwendung kann somit auch bei geschlossenem Browser periodisch arbeiten. Cron kann verspätet sein oder ausfallen. Ein eigener D1-Heartbeat zeigt `geplant / zuletzt gestartet / zuletzt erfolgreich / zuletzt fehlgeschlagen`. Alte Snapshots niemals als frisch ausgeben.

Aktuell dokumentierte Free-Grenzen u. a. **10 ms CPU-Zeit/Invocation**, **128 MB RAM**, **50 Subrequests/Invocation**, **100.000 Worker-Requests/Tag** und maximal **5 Cron Triggers/Account**. D1 Free: **5 Mio. gelesene Zeilen/Tag**, **100.000 geschriebene/Tag**, **5 GB Speicher**. Diese Zahlen vor Deployment anhand der aktuellen Cloudflare-Dokumentation prüfen. *Wartezeit auf Netzwerk und CPU-Zeit unterscheiden sich.*

Empfohlen: **TypeScript Worker + D1 + statische PWA**; separate Cron-Takte, intern nur tatsächlich fällige neue UTC-Kerzen bearbeiten. Teure Berechnungen pro Coin/Zeitfenster in kleine nachweislich kompatible Arbeitseinheiten aufteilen. Auf einer echten Free-Runtime messen, bevor die vollständige Master-Logik zugesagt wird; bei Überschreitung **fail-closed statt stillschweigendem Paid-Upgrade**. Eine Echtzeit-/tickbasierte Hochfrequenzlösung oder kontinuierliche WebSocket-Orderpflege ist damit **nicht** zugesichert.

Kernmodule:
1. **Market ingress:** Öffentliche Kraken-Kerzen, strenge vollständige UTC-Rasterprüfung, Rate-Limit, Datenzeitstempel, eindeutige Symbolnormalisierung, Fail-Closed.
2. **MTF & Master:** Deterministische Signale und vorhandene Risiko-Gates, auf eingefrorenen Referenzdatensätzen gegen Python v1.5.2 getestet.
3. **Scheduler/claim:** D1-basierte einmalige Arbeit pro Symbol/Fenster/Kerzenabschluss, chronologische Signale, explizite Lückenmarkierung.
4. **Paper execution (nur Phase B):** Eine einzige autoritative cloudseitige Paper-Buchungskomponente pro getrenntem Konto, inklusive Kosten, Spread, Slippage, Stop-Logik.
5. **Read-only API/PWA:** PC und iPhone zeigen Live-Status, letzte abgeschlossene Kerzen, Signalursachen, Konto-/Positionswert, Gebühren, simulierte Trades, Historie, Ausfälle und Versionsnummer. Ohne Anmeldung keinerlei vertrauliche Bestands-/Kontoinformationen.

## 3. Schutz und Migrationsvertrag der bestehenden Konten

Die alten Quell-Dateien **`daten/master_paper_state.json`** und **`daten/master_trailing_state.json`** repräsentieren unabhängige Paper-Konten (beide zuletzt am 28.10.2026 mit 1.000 EUR, 0 Trades bestätigt). Ihre Vorgeschichte und ihre getrennten Exit-Politiken müssen erhalten bleiben. Die Konto-JSONs dürfen beim Ausbau nicht versehentlich ersetzt, reinitialisiert oder zu einem gemeinsamen Portfolio verschmolzen werden.

**Migrationsreihenfolge:**
1. GitHub-Konten validieren, Originalbytes und SHA-256 sichern; Cash, Positionen, History, Traderules und last_processed_day auslesen.
2. *Shadow-Betrieb:* Cloudflare rechnet mit identischem Daten-Snapshot nur lesend; keine Veränderung der beiden echten Paper-Konten. Python und Cloudflare auf Referenzdaten und neue geschlossene Handelstage vergleichen.
3. Sicherung und Cutover-Fenster: GitHub-Paper-Automatik vor Freigabe des neuen D1-Schreibers deaktivieren, laufende Jobs beenden, letzten Stand erneut sichern, Import-/Endsaldo überprüfen.
4. **Genau einen** aktiven Schreiber für die Paper-Konten durch serverseitige Konfiguration, Locks/Compare-and-set und D1-Constraints erzwingen. Nach Cutover ist D1 autoritativ, GitHub nur Code/Tests/ggf. datensparsame öffentliche Diagnosen.
5. Keine Neubuchung bereits verbuchter Tage. Keine rückwirkenden simulierten Fills zu heute verfügbaren Bid/Ask-Kursen, wenn der ursprüngliche Tageslauf ausgefallen ist. Solche Tage im Journal als *versäumt* markieren, für die Trade-Ausführung pausieren und eine nachvollziehbare manuelle Beurteilung verlangen.
6. Recovery nur aus versioniertem, überprüftem Backup; Import darf nie bestehende neuere Cloud-Konten überschreiben. Rollback benötigt dasselbe Einzelschreiber-Protokoll, keinen gleichzeitig laufenden Rückfall.

**Eintritte / Risiken / Kosten unverändert:** bestehende neun Entry-Gates und vier Spot-EUR-Paare; 12 % Einsatz je Coin, 45 % Exposure, mindestens 300 EUR Cashreserve; 12 % Drawdown-Halt für Neukäufe; bestehender Master 7-%-Schlusskurs-Stopp bzw. ATR-Trailing 2,5x. Modellierte Gebühr 0,4 % und Slippage 0,1 %. Keine Strategieänderung durch die Infrastrukturmigration.

## 4. Datenmodell und Exactly-once-Schutz

Empfohlene D1-Tabellen, getrennt von Phase-A-Marktdaten:

| Tabelle | Wichtige Spalten / Invarianten |
|---|---|
| `paper_accounts` | `account_id PK`, `strategy_id`, `version`, `mode='PAPER'`, `last_processed_day_utc`, Import-Hash; eindeutiger Bestand |
| `paper_positions` | `(account_id,symbol) PK`, Mengen, Einstieg, Kosten, bei ATR Peak/Stop |
| `signal_decisions` | `decision_id PK`, `(strategy_id,symbol,candle_close_utc) UNIQUE`, regelbasierte Begründung, Quellhash |
| `paper_intents` | `intent_id PK`, `(account_id,symbol,day_utc,side) UNIQUE`, CREATED/RESERVED/FILLED/REJECTED |
| `paper_ledger` | `entry_id PK`, `intent_id UNIQUE`, Cash-/Coin-Veränderungen, Gebühr/Slippage, Zeitpunkt, unveränderbares Audit |
| `paper_equity` | `(account_id,day_utc) PK`, Kontowert, Cash, Positionenbezug, Snapshot-Zeit |
| `run_journal` | `run_id PK`, geplante/gestartete/abgeschlossene Zeit, Version, Ergebnis, Fehler, Quoten-/CPU-Messung |
| `control_state` | genau ein autorisierter Modus/Writer-Epoch, PAUSED-Flag, Risiko-Halt, Version/Änderungszeit |

**Atomizität:** Eine verbindliche simulierte Buchung muss als *eine* transaktionale Änderung von Intent, Ledger, Cash, Positionen, Equity-/Tagescursor stattfinden (D1 `batch()` kann transaktional ausführen). Constraints und erwartete Zustandsversion verhindern Doppelbuchung/Überholung bei parallelen Cron-Runs; ein Unique-Konflikt ist **kein** Anlass, einen zweiten Fill zu erzeugen. Ein fehlgeschlagener Commit darf Konto und Ledger nicht auseinanderlaufen lassen. Kein Eintrag in `paper_ledger` ohne belegten, passenden Intent.

**Zahlen:** Geld, Kurse und Mengen als explizite Dezimalwerte/fixed-point, nicht beiläufig mit JavaScript-Fließkomma zusammenrechnen. Skalierung, Rundungsregeln und Ausführungstoleranzen in Tests festhalten und mit der Python-Referenz vergleichen. Gleiche Inputs müssen reproduzierbare Outputs ergeben.

## 5. Schnittstelle und Oberfläche

Minimal read-only API: `GET /api/status`, `GET /api/markets`, `GET /api/mtf`, `GET /api/accounts`, `GET /api/accounts/:id/trades`, `GET /api/runs`. Geschützte Bedienhandlungen später separat: `POST /api/control/pause` und `POST /api/control/resume` mit Authentifizierung, CSRF-/Replay-Schutz, Audit-Eintrag, serverseitiger Rollenprüfung und Sicherheitsbestätigung.

Dashboard für PC/iPhone:
- System-Ampel mit `PAPER / PAUSED / DATA_STALE / ERROR` sowie letztem/erwartetem Lauf.
- BTC, ETH, SOL, NEAR mit 1d/4h/1h/15m, Datenqualität und exakt datierter Signalbegründung.
- Original- und ATR-Paper-Konto getrennt mit Cash, Investitionsquote, Positionen, historischen simulierten Orders, Gebühren, P&L, Drawdown und Sperren.
- Chronologisches Journal aller Entscheidungen, nicht nur ausgeführter Trades; separate Anzeige von Trading-Fehlern, ignorierten Signalen und versäumten Terminen.
- Keine Zugangsdaten in lokaler Browser-Speicherung; sicherer Login, HTTP-only sichere Sessions, kurze Sitzungsdauer, serverseitige Kontrolle. Öffentliche Assets enthalten keine privaten Handelsdaten.

## 6. Spätere Kraken-Echtgeldintegration – eigenständige Genehmigungspflicht

**Kein Echtgeldcode wird durch diese Spezifikation aktiviert.** Eine Live-Version muss als separater Broker-Adapter mit eigener Sicherheitsprüfung entstehen; niemals den Paper-Fill direkt durch ein HTTP-`AddOrder` ersetzen.

**Vor einer Echtgeldorder**:
- Eine längere *unabhängige* Paper-/Forward-Testphase mit nachvollziehbarem Nettoergebnis nach Spread, Gebühren und Slippage sowie Verlust-/Ausfallanalyse. Gewinne sind nicht garantiert.
- Kraken **Spot-only**, ausschließlich konkret freigegebene EUR-Paare, kein Margin/Futures/Leverage, kein Kredit, keine Short-Positionen.
- Dedizierter API-Key mit minimalen Guthaben-/Orderabfrage-, Ordererstellungs- und Stornorechten, **niemals Auszahlung oder Änderung von Auszahlungsadressen**; sichere Secrets serverseitig, Rotation/Revocation; bei Bedarf getrennte Read- und Trade-Keys.
- Explizit freigegebene Limits für Gesamtbudget, Positionsgröße, täglichen und kumulierten Verlust, offene Orders, Orderfrequenz, Gebühren-/Spread-/Slippage-Grenze und erlaubte Handelszeiten. **Keine unbekannten Beträge raten.**
- Ein signiertes und atomar persistiertes Order-Intent mit deterministischer Client-Order-ID. Auf Timeout oder unbekannte Antwort **nicht blind erneut senden**, sondern zuvor offene/geschlossene Kraken-Orders, Fills und Balances mit dem Journal abgleichen. Teilfills, Duplikate, Statusänderungen und Maintenance korrekt behandeln.
- **Not-Aus:** blockiert neue Orders serverseitig und storniert nach Berechtigung offene Orders. Er garantiert weder sofortigen Verkauf noch den Stop-Preis. Absicherung offener Positionen durch geeignete börsenseitige Orders nur nach Prüfung von Verfügbarkeit, Kosten, Semantik und dem Gesamtrisiko. Eine sporadische Serverless-Cron-Ausführung ist keine 24/7-Stopüberwachung.
- Fail-Closed bei veralteten Kursen, unerwarteter Kontodifferenz, nicht erreichbarer Börse, Rate-Limits, nicht sicher bestätigter Order, fehlendem Auth-Status oder verletztem Verlustlimit.
- Separate spätere manuelle Freigabe, dokumentierter Security-Review und detaillierte Fault-Injection-Tests. Falls Cloudflare Free erforderliche Schutzreaktionen nicht zuverlässig abbildet, **keine Live-Freigabe** auf dieser Infrastruktur.

## 7. Tests / Annahmekriterien

**A:** MTF aus Issue #8, CPU- und D1-Quoten real messen; alle 16 Zeitfenster inklusive UTC-Lücken, veralteter Daten, Blockiersignal und iPhone-Ansicht korrekt; keine Paper-Mutation.

**B:** Python-vs-Worker-Parität, beide Konto-Strategien und Risikolimits, unveränderte Daten/History nach Import; doppelte/parallele Cron-Events, Crash zwischen Berechnung/Commit, Netzwerk-Timeout, D1-Rollback, veraltete Orderbuchdaten und übersprungene Tage reproduzierbar. Fehlerszenarien dürfen **keine** Doppelorders/Resets erzeugen. Nur nach separater Cutover-Freigabe live als *Paper*.

**C:** Rein spätere Testmatrix: doppelte Netzwerkantwort, Order erfolgreich aber Timeout, Partial Fill, Kraken-Maintenance, Daten-/Datenbankausfall, falsche Uhr, Erreichen Verlustlimit, Not-Aus während offener Order und Neustart mit Reconciliation. Test auf realer Zielinfrastruktur erst nach separater Autorisierung.

## 8. Quellinformationen

- Cloudflare Workers: https://developers.cloudflare.com/workers/platform/limits/
- Cloudflare Cron: https://developers.cloudflare.com/workers/configuration/cron-triggers/
- Cloudflare D1 (Batch): https://developers.cloudflare.com/d1/worker-api/d1-database/
- Cloudflare D1 Free-Quoten: https://developers.cloudflare.com/d1/platform/pricing/
- Kraken Spot-API: https://www.kraken.com/de/pro/trading-api
- Kraken API-Key-Berechtigungen: https://support.kraken.com/articles/360000919966-how-to-create-an-api-key

**Review-Status:** Spezifikation zur Diskussion; noch keine neue Cloud-Applikation oder produktive Kontomigration. Jede Implementierungsphase erhält einen eigenen PR ohne Auto-Merge.
