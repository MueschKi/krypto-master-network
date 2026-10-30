# Issue #25: D1-Read-Vollsicherung bleibt gesperrt

Entscheidung vom 30.10.2026: Unter den vorgegebenen Rechten und ohne einen
extern belastbar nachgewiesenen unveränderlichen Quellstand lässt sich eine
allgemeine, vollständige und konsistente Sicherung über die D1-Read-API derzeit
**nicht garantieren**. Deshalb wird kein Extractor freigegeben, kein Backup erzeugt
und kein erfolgreicher Backup-Status implementiert. Das ist der ausdrücklich in
[#25](https://github.com/MueschKi/krypto-master-network/issues/25) vorgesehene
Abbruchfall, keine abgeschlossene Implementierung einer Vollsicherung.

Der vom Besitzer gemeldete Lauf
[#41135253283](https://github.com/MueschKi/krypto-master-network/actions/runs/41135253283)
mit `D1_READ_PROBE HTTP=200` erfüllt das Rechte-/Probe-Gate. Er beweist keine
Datentreue, Snapshot-Isolation, Quotenreserve oder Wiederherstellbarkeit. In dieser
Entwicklung wurde er weder wiederholt noch ein produktiver Cloudflare-Aufruf
getätigt. Es gibt keine neuen Rechte, Tokens, Schreiberstopps oder Planänderungen.

## Durchgesetztes Verhalten

`python cloudflare/scripts/d1_backup_ci.py backup-readonly` ist ausschließlich ein
reservierter **Verweigerungspfad**: Exit 1 und genau
`FAILED stage=D1_READ_CONSISTENCY_UNPROVEN` auf stderr, kein stdout. Er endet vor
Identitäts-/Secret-Prüfungen, Netzwerk, temporären Dateien, Verschlüsselung oder
Veröffentlichung. Auch `BACKUP_READ_ONLY_KMN` und
`OWNER_CONFIRMED_MAINTENANCE` können die Sperre nicht übergehen. Es gibt keinen
Fallback zu Wrangler und keinen Workflow-Dispatch für diesen Modus. Die bestehenden
getrennten Modi `read-probe`, `diagnose`, `backup` (nativer Export) und `recovery`
werden dadurch nicht freigegeben oder automatisch aufgerufen.

AES-256/GPG, authentifizierte Entschlüsselung, die beiden unabhängigen lokalen
SQL-/SQLite-Restores und Commit-/Run-/Account-/UUID-Provenienz bleiben bestehen.
Sie werden nicht als Ersatz für fehlenden Quellenbeweis verwendet. Nur Ciphertext
und SHA256 dürften nach bestandenen Gates veröffentlicht werden; dieser gesperrte
Pfad erreicht die Veröffentlichung überhaupt nicht. Daher entstehen auch bei
Abbruch keine neuen privaten Dateien, die zurückbleiben könnten.

## Entscheidender Konsistenzbeweis fehlt

Die offiziellen [Query](https://developers.cloudflare.com/api/resources/d1/subresources/database/methods/query/)-
und [Raw](https://developers.cloudflare.com/api/resources/d1/subresources/database/methods/raw/)-Routen
bieten lesende SQL-Ergebnisse, aber keinen dokumentierten unveränderlichen
Snapshot-Handle für beliebig viele Seiten. Die
[Sessions-Dokumentation](https://developers.cloudflare.com/d1/worker-api/d1-database/#withsession)
verspricht ausdrücklich „sequential consistency“. Ein Bookmark startet eine neue
Session **mindestens** auf dessen Stand; es fixiert keinen historischen Stand.
`first-primary` wählt den Startpunkt, sperrt keine nachfolgenden Schreiber.
`batch()` ist transaktional innerhalb des Aufrufs; das ergibt keine fortsetzbare
Transaktion über mehrere HTTP-Requests. Ein SQL-`BEGIN` über getrennte Requests
ist kein dokumentiertes Session-Protokoll und wird nicht ausprobiert.

Ein einzelner Batch könnte unter begrenzten Bedingungen einen kleinen Datenbestand
konsistent lesen. Er ist kein allgemeiner Ersatz für eine paginierte Vollsicherung:
Schemaabhängige Abfragen müssen vorbereitet werden, Daten- und Antwortgrößen sind
nicht vorab bewiesen, und der ganze API-Aufruf muss innerhalb von 30 Sekunden
enden. Es wird nicht behauptet, dass jeder denkbare Read-Export unmöglich wäre;
für diese Quelle und diesen allgemeinen Auftrag fehlt die erforderliche Garantie.

Der lokale Gegenbeispieltest beobachtet zwei identische vollständige Randscans
`AA`, liest dazwischen mit eindeutigem Keyset erst `A`, dann `B`, während die Quelle
atomar von `AA` zu `BB` und zurück wechselt. Der Extract `AB` hatte nie als
Datenbankzustand existiert. Anzahl und Schlüssel sind trotzdem korrekt. Vollständige
Digests könnten einen solchen gemischten Extract erkennen, beweisen bei
übereinstimmenden Ergebnissen aber weiterhin keine Schreiberquieszenz: Ein
Schreiber kann zwischen allen Beobachtungen schreiben und zurückschreiben (ABA).
Eine Bestätigung ist eine Bedienhandlung, kein technischer Nachweis dafür, dass
alle Worker, Cron-, manuelle API-, Import- und sonstigen Schreiber ausgeschlossen
sind. Ein solcher externer Ausschluss samt Gültigkeitsintervall liegt nicht vor.

## Weitere Gates bleiben offen, nicht stillschweigend bestanden

| Bereich | Voraussetzung für eine spätere Freigabe |
| --- | --- |
| Schema und Historie | Vollständige Introspection von Tabellen, `table_xinfo`, PK, Indizes einschließlich Kollationen/Ausdrücken, Triggern und FKs gegen die freigegebenen Migrationen; keine unbekannten Objekte auslassen. 0001+0002 oder 0001+0002+0003 zulassen, 0003 nicht produktiv voraussetzen. `d1_migrations` vollständig einschließlich IDs/Zeitstempeln und notwendigen SQLite-Zustand wie `sqlite_sequence` erhalten; interne D1-Objekte ausdrücklich klassifizieren. Der bestehende lokale Recovery-Vergleich allein ist keine vollständige Remote-Schema-Zulassung. |
| Pagination | Stabile eindeutige Keysets, zusammengesetzte PK und `WITHOUT ROWID`, tatsächliche Kollation, Sortierrichtung und NULL-Semantik nachweisen. `TEXT PRIMARY KEY` in gewöhnlichen SQLite-Tabellen kann NULL erlauben; nicht als pauschale Nicht-NULL-Garantie verwenden. OFFSET, bloße Seitenlängen und Rowcounts reichen nicht. Duplikate, fehlende Seiten/Zeilen, Grenzwerte und Drifts müssen geschlossen scheitern; unbekanntes Schema oder fehlender stabiler Schlüssel ebenfalls. |
| NULL / INTEGER | Typmarkierte serverseitige Darstellung vor JSON; NULL von leerem Text/BLOB unterscheiden, signed 64-bit min/max als dezimale TEXT-Werte erhalten. JSON-Zahlen können bereits vor Python gerundet sein. |
| TEXT / BLOB | Bytegenauer Hex-Transport vor JSON mit validierter Länge und Typmarkierung, insbesondere Unicode, Quotes, Newlines, NUL und leere Werte. UTF-8-/SQLite-Encoding-Grenzen explizit prüfen. `quote(TEXT)` und Python `iterdump()` schneiden NUL-Text ab. Hex verdoppelt die Nutzdatengröße. |
| REAL | Bitgenauen Transport für tatsächlich unterstützte REAL-Werte unabhängig nachweisen, einschließlich Subnormalzahlen, Extremen, Vorzeichen von Null und Verhalten bei Infinity/NaN. `quote()` ist kein allgemeiner Bitcodec. Keine ungeprüfte Erweiterung wie `ieee754()` oder numerische JSON-Rundreise voraussetzen. Ohne Codec fest datentypbezogen abbrechen. |
| Quellenbeweis | Deterministische vollständige typisierte Schema-/Daten-Digests aus einer konsistenten Quelle und Parität zum unabhängigen Restore; nicht nur Gleichheit zweier aus demselben Extract abgeleiteter Dateien. Kein vorhandener Recovery-Check darf dafür entfallen. |
| Transport und Abschluss | Harte Stream-/Antwort-/Zeilen-/Statement-/Zeitbudgets, striktes JSON, erwartete Ergebnismenge, nachvollziehbare Endmarke und Vollständigkeitsprüfung. HTTP 200 oder eine kurze Seite ist kein Vollständigkeitsbeweis. Timeouts, Truncation, 429, Schemaänderungen und Quotenfehler ohne Artifact beenden; kein stiller Retry auf verändertem Stand. |

`test_d1_read_backup_limits.py` liefert unabhängige synthetische Gegenbeispiele
für ABA/Keyset, NUL, INTEGER- und REAL-Transport. Ein weiterer Test nimmt absichtlich
einen NUL-verstümmelten Extract des freigegebenen Schemas, verschlüsselt ihn mit der
vorhandenen AES-256-Pipeline und führt beide unabhängigen Restores aus. Beide
Restores stimmen überein, unterscheiden sich aber nachweislich von der separat
aufbewahrten lokalen Quelle. Das zeigt die Grenze der Recovery-Parität; es ist kein
positiver End-to-End-Beweis eines Read-Extractors. Einen solchen erfolgreich zu
simulieren und als Quellenbeweis auszugeben würde das offene Gate verschleiern.

## Free-Tarif und Größenbudget

Die [Preise](https://developers.cloudflare.com/d1/platform/pricing/) nennen
5 Mio. gelesene Zeilen pro Tag, 100.000 geschriebene Zeilen pro Tag und 5 GB
Gesamtspeicher. Gelesene Zeilen sind **gescannte**, nicht nur ausgelieferte Zeilen.
Ein mögliches Budget müsste mindestens
`bestehende Tageslast + Extract-Scans + Quellen-Digest-Scans + Integritäts-/Schema-Scans + begrenzte Retries + Reserve <= 5 Mio.`
nachweisen. Zwei volle Scans kosten bereits mindestens `2*N`; nicht indizierte
Keysets oder OFFSET können pro Seite erneut scannen und deutlich mehr kosten.
Es wurde keine freie produktive Reserve festgestellt. Ohne nachgewiesenes Budget
keine Freigabe und keine Testabfragen zum Verbrauch dieser Reserve.

Die offiziellen [Limits](https://developers.cloudflare.com/d1/platform/limits/)
nennen 500 MB pro Free-Datenbank, 2.000.000 Byte pro Zeile/STRING/BLOB,
100.000 Byte SQL, 100 Parameter und 30 Sekunden **für den gesamten API-Batch**.
Ein großer JSON-Aggregatwert kann schon am Stringlimit scheitern; Hex kann eine
sonst gültige große Einzelzelle über das Limit bringen. Ein kleiner Seiten-LIMIT
begrenzt weder Bytes noch gescannte Zeilen. Die am 30.10.2026 veröffentlichte
Dokumentation kündigt zusätzlich ein 50-MB-Abfrageergebnislimit **ab 04.11.2026**
an; es wird nicht als bereits aktiver Schutz angenommen. Auch dieses Limit macht
eine 500-MB-Datenbank nicht zu einem garantiert in einem Request lesbaren Backup.
Die 50 Abfragen pro Free-Worker-Aufruf sind kein Budget für externe REST-Requests.
Sieben Tage Free Time Travel ersetzen kein portables Offline-Backup.

## Quellenprüfung und spätere Neubewertung

Die Dokumentationsseiten antworteten in dieser Entwicklungsumgebung mit HTTP 403.
Sessions, Typen, Limits und die Preistabelle wurden deshalb aus den öffentlichen
Originalquellen des offiziellen Repositories
[cloudflare/cloudflare-docs](https://github.com/cloudflare/cloudflare-docs/tree/production/src/content/docs/d1)
gelesen (`worker-api/d1-database.mdx`, `worker-api/index.mdx`,
`platform/limits.mdx`, `platform/pricing.mdx` sowie
`src/content/partials/workers/d1-pricing.mdx`). Das sind Dokumentationszugriffe,
keine produktiven Datenbankabfragen. Die API-Rechtebewertung aus #24 bleibt bestehen;
die erfolgreiche Probe wird nicht erneut als Vollsicherung umgedeutet.

Eine spätere Neubewertung braucht entweder einen dokumentierten Read-Snapshot mit
vollständigem verlustfreiem Transport innerhalb der Limits oder extern belegte
vollständige Schreiberquieszenz für das gesamte Verfahren sowie alle weiteren
[Gates](D1_READ_ONLY_BACKUP_GATES.md). Dafür wären neue Entwicklung, Review und vor
jedem produktiven Zugriff eine eigene ausdrückliche Besitzerfreigabe nötig. Es
wird hier weder D1 Edit angefordert noch ein Export, Restore, Import, eine Migration,
ein Deployment, eine Cron-Änderung oder ein Trade durchgeführt.
