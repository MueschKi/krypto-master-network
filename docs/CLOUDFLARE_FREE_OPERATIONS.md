# Cloudflare Free: Überwachung, Kerzenspeicher und Recovery

Stand: 30.10.2026, Umsetzung von Issue #14. Dieser PR ändert nur Quellcode.
Merge, Remote-Migration, Veröffentlichung und spätere Cache-Löschung erfordern
jeweils getrennte Besitzerfreigaben. Kein Tarifwechsel und keine neuen Ressourcen.

## Verifizierte Limits und Messquelle

Die offiziellen Markdown-Dokumentationen wurden am 30.10.2026 gelesen:

- [D1 Limits](https://developers.cloudflare.com/d1/platform/limits/): 500 MB je
  Free-Datenbank, 5 GB je Account, 50 D1-API-Aufrufe je Worker-Invocation,
  100 gebundene Parameter, 100 kB SQL-Text, 2 MB maximale Zeilengröße.
  Ein `batch()` zählt laut aktueller Dokumentation als **ein** API-Aufruf;
  seine Statements und gelesenen/geschriebenen Zeilen bleiben kostenrelevant.
- [D1 Pricing](https://developers.cloudflare.com/d1/platform/pricing/):
  5 Mio. gelesene und 100.000 geschriebene Zeilen/UTC-Tag, accountweit.
- [Workers Limits](https://developers.cloudflare.com/workers/platform/limits/):
  10 ms CPU je HTTP- und Cron-Aufruf auf Free, 100.000 Requests/Tag.
- [D1 Return objects](https://developers.cloudflare.com/d1/worker-api/return-object/):
  `meta.size_after` enthält die Datenbankgröße, `rows_read` und `rows_written`
  die tatsächlichen Abfragekosten. SQL-/Walltime sind keine Worker-CPU-Zeit.

## Implementierter Schreibschutz

Migration `0003_storage_guard.sql` ist additiv. Alte `candle_batches`,
`analyses`, `runs`, `coverage_gaps` und Kontotabellen bleiben erhalten.
`storage_guard` enthält genau eine Mess-/Lease-Zeile; `raw_candles` ist ein
WITHOUT-ROWID-Cache mit Schlüssel `(symbol,timeframe,open_utc)`.

Vor jedem Cron-Aufruf erwirbt der Worker eine datenbankweite 60-Sekunden-Lease.
Ein konkurrierender Aufruf meldet BUSY und schreibt keine Rohdaten. Zwei Kraken-
Requests haben jeweils 15 Sekunden Timeout. Eine abgestürzte Instanz verliert
nach Ablauf der Lease ihr Schreibrecht; alte Eigentümer können danach weder
Rohkerzen noch Signale veröffentlichen. Die nächste Invocation kann übernehmen.

Größenmessung erfolgt frisch aus D1-Metadaten vor Beginn und nochmals nach dem
Fetch. Fehlende/ungültige Größe oder fehlendes Guard-Schema bedeutet UNKNOWN:
keine Kraken-Abfrage, keine neuen Rohkerzen und keine neue Signalfreigabe.
WARN gilt ab **250.000.000 Bytes**. STOP beginnt bereits ab **348.000.000 Bytes**:
2 MB Reserve vor der operativen 350-MB-Grenze für eine begrenzte Transaktion
und normalen Journal-/Index-Overhead. Oberhalb STOP werden auch keine neuen
Run-Journale angelegt, um nicht durch Fehlerlogs weiter Speicher zu verbrauchen;
die feste Lease-Zeile wird weiter aktualisiert und strukturierte Logs bleiben.

Die Reserve schützt den regulären einzelnen Worker-Schreiber, nicht vor
parallelen administrativen Imports oder externen Schreibern. Solche Änderungen
müssen bei pausierter Beobachtung stattfinden. Eine Datenbank mit tatsächlicher
Quota-Erschöpfung kann auch Lease-/Lesezugriffe ablehnen: dann keine Freigabe,
kein automatischer Upgrade- oder Löschversuch.

## Normalisierung und unveränderte Signale

Jede abgeschlossene, qualitätsgeprüfte Kerze wird einmal gespeichert. Ein
JSON-Parameter plus `json_each` verarbeitet bis zu 720 Kerzen in einem Statement;
keine 720 API-Aufrufe oder Überschreitung der Parametergrenze. Existierende
identische Kerzen werden ignoriert. Eine revidierte abgeschlossene Kerze löst
`CANDLE_CONFLICT` aus; die gesamte Veröffentlichung wird zurückgerollt. Keine
stille Umschreibung von Belegen: solche Fälle erfordern eine gesonderte Prüfung.

Rohkerzen und erfolgreiche Analyse werden in einem D1-Batch atomar veröffentlicht.
Lease-Eigentümer und Job-Eigentümer werden geprüft. Bereits vorhandene Analysen
werden nicht überschrieben. Fehlgeschlagene Versuche stehen im Run-/Job-Journal;
sie erzeugen keine neue Analyse. Damit bleibt ein älteres Fenster sichtbar und
wird durch die bestehende UTC-Frischeprüfung als stale/BLOCKIERT angezeigt.
Ein erfolgreicher Retry kann ein bislang fehlendes Fenster erstmals anlegen.

Die Strategie und ihre deterministische Berechnung bleiben gleich. Bestehende
Analysen und UI verwenden keinen Rohcache zum Anzeigen. Der lokale Retention-Test
entfernt deshalb ausschließlich Test-Cache-Zeilen und vergleicht unveränderte
Audit-Hashes. **Produktiv existiert kein Pruning-Aufruf, kein Lösch-Endpunkt und
kein geplanter Lösch-Cron.** Legacy-Batches werden nicht rückwirkend konvertiert.

## Diagnose und Quoten

Die authentifizierte GET-API `/api/diagnostics` liefert Größe, WARN/STOP/UNKNOWN,
alle 16 Fenster mit Qualität/stale/missing, die Zahl fehlender/gesperrter Fenster,
einen aus den letzten beiden Cron-Messpunkten abgeleiteten Speichertrend und
die D1-Kosten dieser Diagnoseabfrage. Der Trend ist eine kurzfristige Hochrechnung,
kein gemessener Tagesverbrauch. Im UI stehen die wichtigsten Werte unter System.
Bei Diagnoseausfall steht dort UNKNOWN; vorhandene Marktanalysen bleiben lesbar.

HTTP- und Cron-Logs enthalten ausschließlich Status/Fehlerklassen, D1-Aufrufe,
Statements, rows_read/rows_written, Vollständigkeit der Messung und Walltime.
Keine Header, Passwörter, URLs, fremden Fehlertexte oder privaten Kontopayloads.
Kraken HTTP 429 und API-Rate-Limits werden klassifiziert; Timeouts, HTTP-/Format-
Fehler und Kerzenkonflikte werden gesondert behandelt. Fehlen D1-Metadaten oder
schlägt eine Operation fehl, ist der Kostennachweis unvollständig.

Der Wrapper lässt höchstens 45 D1-API-Aufrufe je Invocation zu und reserviert
fünf unterhalb des Free-Limits. Das ist ein lokales Aufrufbudget, kein Nachweis
der accountweiten Tagesquoten. `cpu_ms`, `daily_quota_remaining` bleiben null,
`free_tier_verified` bleibt false. CPU-Abbrüche können den finally-Log verhindern;
dafür immer Cloudflares eigene Invocation-Metriken heranziehen.

## Lokale Verifikation und Speicherprognose

- Bestehende Python-/TS-/Worker-/D1-Paritätstests bleiben aktiv.
- Neue D1-Tests: 250-/350-MB-Grenzen, unbekannte Metadaten, gleichzeitige Aufrufe,
  720-Bar-Transaktion, immutable Konflikte, abgebrochene Batches, verwaiste Lease,
  partielle Migration, Auth-/Logging-Schutz, Rate-Limits und Querybudget.
- 30 tägliche Kollisionen: alle 16 Kombinationen mit rollierenden 720 Bars;
  gespeicherte/re-konstruktierte Kerzen ergeben exakt dieselben Indikatoren.
- Separates SQLite-Modell: **15.240 Ereignisse in 30 Tagen**, alle 508 täglichen
  BTC/ETH/SOL/NEAR-Fensterabschlüsse. Ausführung der echten Migrationen und des
  deduplizierenden Insert-/Trigger-Pfads. 26.744 Rohkerzen statt 15.240 vollständigen
  720er-Batches. Mit 2-kB-Analysepayloads, Jobs, Runs und sämtlichen Indizes:
  **68.554.752 Bytes**, letzter Modelltageszuwachs **2.252.800 Bytes**.
  Die Prognose enthält SQLite-Seiten und Index-Overhead; sie enthält keine bereits
  existierenden produktiven Legacy-Batches. Deren Größe muss addiert werden.
- Die Werte sind synthetisch. Die Testpreise, Signalpayloadgröße und Zahl der
  Runs sind Modellannahmen; Cron-Leerläufe/Fehler und echte Analysen verändern
  den Verbrauch. Auch normalisiert wachsen Signale und Journale weiter.
  Das Modell beweist keinen unbegrenzten kostenlosen Betrieb.
- Automatische Löschung bleibt unmöglich. Vor 250 MB Betrieb prüfen; spätestens
  am STOP-Gate kontrolliert pausieren und Speicherplan erneut freigeben.

## Backup, Hash und Restore vor jeder späteren Löschfreigabe

`cloudflare/scripts/storage_snapshot.py` arbeitet ausschließlich offline mit
lokalen SQLite-Dateien. Der Helfer öffnet die Quelle read-only, prüft SQLite-
Integrität/Fremdschlüssel, nutzt SQLite Backup API, erzeugt Dateien mit Modus 0600
und ein SHA-256-Manifest. Restore verifiziert den Hash, prüft erneut Integrität
und überschreibt niemals ein bestehendes Ziel. SHA-256 erkennt Beschädigung;
es ist keine Signatur gegen einen Angreifer, der auch das Manifest ändern kann.

1. Separate Export-/Retention-Freigabe einholen; Writer für einen konsistenten
   Vergleich pausieren. Keine geheimen oder privaten Exporte ins Repository/Chat.
2. Besitzer erstellt einen vollständigen D1-Export über den dafür autorisierten
   Kanal in ein geschütztes Verzeichnis außerhalb des Checkouts. SQL-Export nur
   in eine neue isolierte lokale SQLite-Datei importieren, niemals ungeprüft in
   eine produktive Datenbank. SQLite-Dateien nicht aus laufenden WAL-Dateisätzen
   zusammenkopieren; den gesonderten Export verwenden.
3. Offline: `python cloudflare/scripts/storage_snapshot.py backup SOURCE.sqlite BACKUP.sqlite`.
4. Offline: `python cloudflare/scripts/storage_snapshot.py restore BACKUP.sqlite RECOVERY.sqlite`.
5. Run-/Signal-/Gap-/Ledger-Zählungen und Hashes, Schema und repräsentative
   Fenster gegen den Export vergleichen; Recovery auf einer isolierten lokalen
   Worker-Instanz prüfen. Sicherung/Manifest getrennt geschützt verwahren.
6. Erst danach exakte Rohcache-Tabelle, UTC-Grenze, erwartete Zeilenanzahl,
   Wiederherstellungsbeleg und ausdrückliche Besitzerfreigabe dokumentieren.
   Dieser PR stellt **keinen** Remote-Restore-/Löschbefehl bereit. Eine spätere
   Bereinigung muss Vorher/Nachher-Zählungen und entfernte Cache-Zeilen protokollieren.

Die Tests prüfen einen kompletten Offline-Roundtrip, unveränderte Audit-Hashes,
Beschädigung und verweigertes Überschreiben. Ein echter D1-Export/Time-Travel-
Restore ist damit noch nicht getestet. Free Time Travel hat laut Dokumentation
sieben Tage; es ersetzt keine überprüfte lokale Sicherung.

## Freigabe und spätere Live-Abnahme

- [ ] Besitzer genehmigt Merge separat.
- [ ] Vor Remote-Migration: vollständigen Export/Recovery und Freespeicher prüfen;
  kumulierte Größe vorhandener Legacy-Daten messen. Pausierung separat abstimmen.
- [ ] Besitzer genehmigt Migration 0003 separat; nur additiv, kein Backfill/Pruning.
- [ ] Besitzer genehmigt Worker-Veröffentlichung separat; richtige UUID/EU-D1,
  Free-Tarif, unveränderte Auth-Secrets und ausschließlich Beobachtungs-Cron prüfen.
- [ ] Nach Veröffentlichung kurze kontrollierte Testphase freigeben. Dashboard:
  Workers & Pages → Worker → Metrics/Observability; Scheduled und HTTP getrennt,
  insbesondere `exceededCpu`/1102, CPU p50/p95/p99/Maximum und Fehleranteile messen.
  Vollständige 720 Bars, 00:00/4h/1h/15m-Kollisionen, Parallelität, Kraken 429,
  Timeouts und Wiederanlauf erfassen. Lokale Walltime ist **kein** 10-ms-Nachweis.
- [ ] D1 Dashboard → kmn → Metrics/Analytics: Größe und Tagesdifferenzen,
  rows_read/rows_written (inklusive Indizes, Retries und anderer Account-Nutzer),
  Fehler/Query-Latenzen über ein vollständiges UTC-Tagesfenster erfassen.
  Datum, Worker-Version, Fenster/Last und Messquelle protokollieren, keine Secrets.
- [ ] 16/16 aktuelle Qualitätsfenster und Storage-Status kontrollieren. Diagnose-
  endpoint hat keine administrativen Schreibfunktionen. 401 ohne Anmeldung testen.
- [ ] Bei CPU-/Quota-/Messfehlern Betrieb pausieren und Einheiten neu entwerfen;
  niemals Paid aktivieren. Fortsetzung erfordert bewertete Messdaten.
- [ ] Jede spätere Retention/Löschung separat freigeben, nicht durch Merge dieses PR.

## Rollback

Vor Veröffentlichung des neuen Workers bleibt die Produktion unverändert.
Bei späterem Rollback zuerst den Beobachtungs-Cron kontrolliert pausieren.
Keine Down-Migration und keine Datenlöschung: neue Tabellen/Indizes sind additiv
und können bestehen bleiben. Eine frühere Worker-Version ignoriert sie, würde
aber wieder volle Legacy-Batches schreiben. Deshalb niemals den alten Cron
unbeaufsichtigt fortsetzen. Zunächst lesender/pause Zustand, Speicherbudget und
Version prüfen; Wiederaufnahme separat freigeben. Paper-Schreiber, Konten und
Strategien werden durch diesen Ablauf nicht berührt.
