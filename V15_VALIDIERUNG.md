# v1.5 – Umsetzung und Validierung

Basis: GitHub-main `4924873d7fba242fcdfa29d96f1566260ec50b83`, Issue #2.
Die neuere README-Änderung auf main wurde übernommen. Alle übrigen vorhandenen
Dateien wurden anhand der GitHub-Blob-IDs mit der Arbeitskopie verglichen.

Neue Komponenten: `mtf_data.py` (öffentlicher Abruf und Datenqualitätsmodul),
`mtf_trend.py`, `mtf_momentum.py`, `mtf_volatility.py`, `net_timeframe_bot.py`,
`mtf_analysis.py`. Ausgabe: Markdown plus JSON mit Versionsschema 1.5,
UTC-Snapshot, Datenqualität und Kerzenzeiten je Fenster, Indikatoren,
Begründungen, Kreuzwidersprüchen und methodischen Grenzen.

## Tests

`python -m unittest discover -q`: **68 Tests bestanden**, davon 56 bestehende
und 12 neue Tests. Einschließlich `test_trailing_v14`, Echtgeldausschluss und
bestehender Handelsregressionen. Der gleiche Lauf mit der vorhandenen
Projekt-venv (Python 3.12) bestand ebenfalls vor dem abschließenden zusätzlichen
Test für Exchange-Initialisierungsfehler (67 Tests); CI verwendet Python 3.11.
Dort traten DeprecationWarnings aus vorhandenem Pandas-Resampling auf.

Neue Tests: 16 Symbol/Fenster-Kombinationen, eingefrorene UTC-Zeit, exakt beim
Kerzenschluss und 1 ms davor, Ausschluss laufender und zukünftiger Kurse,
NaN/inf, Plausibilität, fehlende/duplizierte/unsortierte/veraltete Kerzen,
zu kurze Historie, deterministische Offline-Demo mit gesperrten Sockets,
flache/steigende/fallende Kursreihen, ATR-Veto, Kreuzwidersprüche,
fehlgeschlagene öffentliche Requests und Exchange-Initialisierung,
begrenzte injizierte Abrufe, Ausgabepfade und Workflow-Routing.

Geschützte Python-Dateien werden in CI zusätzlich gegen SHA256-Basiswerte
geprüft. Kontostände und Statusberichte wurden beim Abschluss bytegenau gegen
den Ausgangsstand geprüft; ihre dynamischen Inhalte werden bewusst nicht in CI
festgeschrieben, damit die bisherigen täglichen Paper-Läufe weiterlaufen können.
Demo und Analyse schreiben in Tests ausschließlich ihre erlaubten Ausgabepfade.

`python mtf_analysis.py demo`: erfolgreich, wiederholbare JSON-/Markdown-Ausgabe.
Beispiel des festen Snapshots `2026-10-29T00:00:00+00:00`:

| Coin | 1d | 4h | 1h | 15m | Gesamt |
|---|---|---|---|---|---|
| BTC/EUR | NEUTRAL | NEUTRAL | NEUTRAL | NEUTRAL | NEUTRAL |
| ETH/EUR | NEUTRAL | POSITIV | NEUTRAL | POSITIV | NEUTRAL |
| SOL/EUR | NEUTRAL | POSITIV | NEUTRAL | NEUTRAL | NEUTRAL |
| NEAR/EUR | NEUTRAL | NEUTRAL | POSITIV | POSITIV | NEUTRAL |

Das sind ausschließlich künstliche Daten, keine aktuellen Marktsignale.

`python mtf_analysis.py analyse` mit installiertem ccxt 4.5.90: der öffentliche
Kraken-Aufruf scheiterte in dieser Umgebung mit `NetworkError` beim Abruf der
Marktliste. Korrektes Ergebnis: **BLOCKIERT für alle 16 Fenster**, keine
Indikatoren; Fehlerursache in `ZEITFENSTER.md` und JSON dokumentiert.
Ein erfolgreicher echter Kraken-Abruf konnte hier nicht bestätigt werden.
Der initiale Bericht im PR ist deshalb ausdrücklich ein gesperrter Bericht.

`git diff --check`: erfolgreich. GitHub-Actions-Läufe werden hierdurch nicht als
bereits ausgeführt behauptet; der PR enthält einen eigenen Read-only-Testworkflow.

## Sicherheit und Grenzen

Keinerlei Änderung an Kauf-/Verkaufsregeln oder Paper-Engines, Kontodateien,
Trading-Statusberichten, `market.get_daily()` oder Echtgeldausschluss.
Kein Import aus Trading-Komponenten, kein Orderpfad, keine Secrets/Wallets.
Die beiden Cron-Ausdrücke, Standardmodus `paper` und bisherige Commit-Listen
bleiben erhalten. MTF-Demo committet nichts; MTF-Analyse ausschließlich ihre
zwei neuen Ergebnisdateien. Read-only-PR-CI läuft getrennt von Simulationen.

Kraken-Historie maximal ca. 720 Kerzen, begrenzter EMA200-Warm-up, UTC,
unterschiedliche Kerzenschlusszeiten, korrelierte Zeitfenster und feste
heuristische Klassifikation statt Prognose. Strikte Aktualität kann bei
Veröffentlichungsverzögerungen blockieren. Gesperrte Berichte werden absichtlich
mit Exitcode 0 gespeichert; das ist keine Freigabe für Signale oder Handel.

Nutzung auf dem iPhone und manuelle Actions: siehe README, Abschnitt v1.5.
