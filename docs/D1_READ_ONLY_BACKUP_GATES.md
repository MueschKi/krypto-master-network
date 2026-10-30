# D1 Read: sichere Probe und offene Gates für die Vollsicherung (#24)

Prüfstand: 30.10.2026. Dieser PR liefert den ausdrücklich erlaubten ersten Teil:
**`read-probe`, kein `backup-readonly` und kein neues Backup-Artifact.** Während der
Entwicklung wurden nur öffentliche Dokumentation, Repository-Code und synthetische
Fixtures verwendet; keine produktiven Cloudflare-Aufrufe.

## Offiziell belegte Rechte und Reichweite der Probe

Die Cloudflare-Methodenseiten für
[Query](https://developers.cloudflare.com/api/resources/d1/subresources/database/methods/query/)
und [Raw](https://developers.cloudflare.com/api/resources/d1/subresources/database/methods/raw/)
nennen ausdrücklich **D1 Read oder D1 Write** als Accepted Permissions. Beide sind
POST-Endpunkte; die HTTP-Methode allein macht eine reine SELECT-Abfrage nicht zu
einer SQL-Schreiboperation. `/export` ist ein anderer Endpunkt. Der neuere Lauf
[#41131909001](https://github.com/MueschKi/krypto-master-network/actions/runs/41131909001)
meldete dort `AUTH_DENIED CF=10000`; daraus folgt kein Auftrag zur Rechteerweiterung.

`read-probe` verwendet ausschließlich den bestehenden Backup-Read-Token, nach
manuellem main-Dispatch und eigener Bestätigung `READ_ONLY_PROBE_KMN` unter
`cloudflare-backup`. Zuerst laufen die vorhandenen GET-Prüfungen für Account,
eindeutige kmn-UUID, Name und `jurisdiction=eu`. Danach erfolgt **genau ein** POST
auf die feste `/query`-Route mit genau einer fest im Code definierten SELECT-Abfrage:
Sie liest nur `sqlite_master`, begrenzt auf eine Tabellen-Metadatenzeile, und gibt
nur eine konstante Markierung zurück. Weder Namen noch private Tabellenzeilen,
Zeilenanzahlen oder SQL werden geloggt. Es gibt keinen frei eingebbaren SQL-Text,
keinen alternativen Host, keine Redirects, Retries oder Fallbacks, keine Passphrase,
kein Wrangler/GPG, keine Dateien mit Antwortdaten und keine Artifacts. Ohne Dateien
mit Antwortdaten ist auch nach Timeout/Abbruch kein privates Arbeitsverzeichnis zu
bereinigen. Der Job hat ein fünfminütiges Limit; einzelne HTTP-Aufrufe 20 Sekunden.

Erfolg erfordert HTTP 200, valide UTF-8-JSON-Antwort ohne doppelte Schlüssel oder
NaN/Infinity, erfolgreiches Envelope und genau ein erfolgreiches Resultat mit genau
der erwarteten ganzzahligen Markierung. Zusätzlich verlangt die Probe
`meta.changed_db=false`, `meta.changes=0`, `meta.rows_written=0`. Diese Felder sind
in der API-Dokumentation optional; fehlen sie, wird **nicht** stillschweigend Erfolg
behauptet, sondern sicher abgebrochen. Auch eine leere oder abweichende Antwort
ist kein Erfolg. Es werden keine Ergebnisdaten ausgegeben.

Ausgaben beschränken sich auf `VERIFIED stage=D1_READ_PROBE HTTP=200` oder
`FAILED stage=D1_READ_PROBE class=<feste Klasse>`, gegebenenfalls mit validiertem
HTTP-Status und streng numerischen CF-Codes. Klassen: `AUTH_DENIED`, `RATE_LIMIT`,
`API_UNAVAILABLE`, `HTTP_ERROR`, `NETWORK_ERROR`, `TIMEOUT`, `RESPONSE_LIMIT`,
`RESPONSE_INVALID`, `RESULT_INVALID`, `UNKNOWN`. Das gemeinsame Antwortlimit beträgt
16 KiB. Fehler-Rohtexte, URLs, IDs, SQL, Secrets und Antwortinhalte bleiben intern.
GET-Identitätsfehler behalten ihre bestehenden sicheren Stufen.

Ein Erfolg belegt nur diese eng begrenzte Leseoperation zum Prüfzeitpunkt. Er ist
**kein** Beleg für alle Tabellen, Typen, Pagination, Snapshot-Konsistenz, Quotenreserve,
Verschlüsselung oder Wiederherstellung und erteilt keine Backup-/Deploy-Freigabe.
Die Probe braucht keine Cron-Pause. Der bestehende native `backup`-Modus bleibt ein
getrenntes, ausdrücklich bestätigungspflichtiges Verfahren; es gibt keinen
heimlichen Wechsel zwischen ihm und der Probe. Er wird durch diesen PR nicht
repariert oder erneut gestartet. Ein erfolgreicher Probelauf hat kein Artifact und
besteht deshalb nicht die bestehenden Recovery-Quelllauf-/Artifact-Gates.

## Warum die Vollsicherung noch nicht veröffentlicht wird

1. **Kein dokumentierter, requestübergreifender Snapshot.** Eine Keyset-Pagination
   benötigt mehrere Requests. Die API beschreibt keinen dabei fixierten Lesestand.
   [D1-Sessions](https://developers.cloudflare.com/d1/worker-api/d1-database/#withsession)
   garantieren sequenzielle Konsistenz, nicht unveränderliche Daten über alle Seiten.
   Ein einzelnes transaktionales Batch ist keine beliebig große, requestübergreifende
   Pagination. Ein Operator-Schreiberstopp muss alle Schreiber betreffen; ein
   Cron-Stopp allein beweist das nicht. Zwei identische vollständige Digests können
   zwischenzeitliche Änderungen mit Rückkehr zum Ausgangszustand (ABA) nicht generell
   ausschließen. Wir erklären zwei Scans deshalb nicht zu einem atomaren Backup.
2. **Typgenauigkeit ist nicht durch JSON garantiert.** Die
   [Worker-Typdokumentation](https://developers.cloudflare.com/d1/worker-api/)
   beschreibt interne signed 64-bit INTEGER, fehlenden BigInt-Support in der API
   und die JavaScript-Grenze `Number.MAX_SAFE_INTEGER`. Ein Python-JSON-Parser kann
   bereits vor der Übertragung gerundete Werte nicht rekonstruieren. `quote()`
   allein löst es nicht: SQLite schneidet NUL-Text in SQL-Literalen ab; REAL benötigt
   einen separat belegten bitgenauen Transport und unabhängige Validierung. Ein
   erfolgreicher SELECT auf Metadaten beweist diese Fähigkeiten nicht.
3. **Vollständigkeit und Schema-/Datenintegrität sind noch nicht bewiesen.** Es gibt
   keine getestete Umsetzung aller unten genannten Gates. Eine anschließende
   AES-256-Verschlüsselung würde fehlende/gerundete/inkonsistente Daten lediglich
   verschlüsseln. Auch zwei gleiche Restores eines fehlerhaften Extracts belegen
   keine Parität zur Quelle. Deshalb kein scheinbar vollständiges Artifact und kein
   deaktivierter Integritätscheck, um einen grünen Lauf zu erhalten.

## Vor Veröffentlichung von `backup-readonly` nachzuweisen

Diese Voraussetzungen werden in [Folge-Issue #25](https://github.com/MueschKi/krypto-master-network/issues/25) bearbeitet. Es gibt in
diesem PR bewusst keine aufrufbare oder halb fertige Snapshot-Implementierung.

| Gate | Erforderlicher Nachweis |
| --- | --- |
| Rechte / Probe | Separat genehmigte erfolgreiche Probe mit dem bestehenden Read-Token; keine Write-/Edit-, DNS- oder Worker-Adminrechte, keine neuen Tokens. |
| Konsistenz | Belastbarer Schutz eines unveränderten Quelldatenstands über alle Requests oder extern nachgewiesene vollständige Schreiberquieszenz mit klarer Grenze der Garantie. Ohne diesen Nachweis kein Artifact. Vor/nach Schema-, Tabellen-, Rowcount- und vollständige deterministische Daten-Digest-Prüfungen; Drifts und unbeobachtbare Zustände brechen ab. |
| Schema | Nur explizit freigegebene Migrationen 0001+0002 und optional 0003; 0003 ist nicht als produktiv migriert anzunehmen. Vollständiger Abgleich von Tabellen, Spalten, PK, Indizes, Triggern und FKs mit `sqlite_master`/dokumentierter Introspection. `d1_migrations` und für Wiederherstellung erforderlicher SQLite-Zustand erhalten. Unbekannte Benutzerobjekte nie stillschweigend auslassen. |
| Pagination | Deterministisches Keyset mit stabilen eindeutigen Schlüsseln einschließlich Composite PK und `WITHOUT ROWID`; passende Kollationen/NULL-Regeln. Jede Seite, jede Zeile genau einmal; keine unbewiesene OFFSET-Lösung; fehlende/duplizierte Seiten, Abbrüche und geänderte Daten erkennen. Harte Größen-/Zeilenlimits, nur begrenzte lesende Retries. |
| Typen | Serverseitige typmarkierte TEXT-/Hex-Kodierung vor JSON-Übertragung, keine numerischen 64-bit-JSON-Werte. NULL, Unicode, Quotes, Newlines, Embedded NUL, BLOB, min/max signed INTEGER und REAL bitgenau erhalten oder mit festem datentypbezogenem Code abbrechen. Alle Sonderfälle mit unabhängigen SQLite-Fixtures beweisen. |
| Quelle ↔ Restore | Vollständige Quelle-/Client-Digests über Schema und deterministische typisierte Zeilen; SQL-Import und unabhängiger SQLite-Restore müssen zur Quelle passen. Gleiche Hashes zweier bereits verlustbehafteter lokaler Kopien reichen nicht. |
| Artifact / Provenienz | Private Runner-Dateien, vorhandenes GPG/AES-256 und vorhandene Passphrase, extern gesicherter Recovery-Schlüssel, Commit-/Account-/UUID-/Run-Bindung, erlaubte Quelloperation und erfolgreiche Probenherkunft. Nur Ciphertext + SHA256 in `kmn-encrypted-d1`, bestehende Recovery-Gates erhalten. Cleanup auch bei Abbruch. |
| Bedienung | Eigenes `backup-readonly`, `BACKUP_READ_ONLY_KMN` + `OWNER_CONFIRMED_MAINTENANCE`; Benutzer stoppt alle Schreiber/Cron separat. Probe ist keine Backup-Freigabe. Kein automatischer Retry, Cron-Wechsel, Import, Migration, Deployment oder Trading-Cutover. |
| Tests | Gesamten synthetischen paginierten Extract → SQL-Import → AES-256-Artifact → unabhängigen Restore testen, einschließlich leerer Tabellen, 0001+0002/optional 0003, Typ-Sonderfälle, große Seiten, Lücken/Duplikate, sich ändernde Quelle, fremde Tabellen/Trigger, HTTP-/Streamfehler und Secret-/Raw-Log-CANARYs. |

## Free-Plan und dokumentierte Grenzen

[Pricing](https://developers.cloudflare.com/d1/platform/pricing/) nennt für Free
5 Millionen gelesene Zeilen/Tag, 100.000 geschriebene Zeilen/Tag und 5 GB
Gesamtspeicher. Es zählen gescannte, nicht nur zurückgegebene Zeilen; LIMIT allein
beweist kein kleines Scanbudget. Vollständige doppelte Scans und zusätzliche
Integritätsabfragen müssen zusammen mit dem laufenden Betrieb budgetiert werden.
Eine tatsächliche freie Quotenreserve wurde mangels produktiver Abfragen nicht
festgestellt. Es gibt keine Planänderung.

[Limits](https://developers.cloudflare.com/d1/platform/limits/) nennt unter anderem
2 MB pro Zeile/STRING/BLOB, 100 KB pro SQL-Statement, 100 gebundene Parameter und
30 Sekunden maximale SQL-Abfragedauer. Der künftige Extract darf Größenlimits nicht
als Erfolg mit abgeschnittenen Daten behandeln. Die Probe ist bewusst viel kleiner.
Free Time Travel umfasst laut derselben Quelle sieben Tage; das ist kein Nachweis
für ein portables, unabhängig getestetes und verschlüsseltes Backup. Es wird keine
Time-Travel-Operation ausgeführt und kein nicht vorhandenes Backup versprochen.
