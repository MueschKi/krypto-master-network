# D1-Backup und Offline-Recovery ausschließlich am iPhone

Stand: Issue #18, 30.10.2026. PR #17 ist in main, die produktive Datenbank und
der produktive Worker können weiterhin vor Migration 0003 stehen. Dieser PR
führt **nichts** auf Cloudflare aus. Nur Code, lokale Fixture-Tests und PR-CI.

## Was vorbereitet ist und was gesperrt bleibt

Der Workflow **D1 - encrypted backup and offline recovery** hat ausschließlich
`workflow_dispatch`, erlaubt nur main im Originalrepository und verwendet keine
Zeitpläne, Merge-Trigger oder Cloudflare-Secrets in PR-CI. Ein Merge startet ihn
nicht. `backup` exportiert erst nach ausdrücklicher Freigabe die konkrete vorhandene
EU-D1; `recovery` lädt ausschließlich Ciphertext und prüft ihn lokal ohne Cloudflare-
Token. Keine Operation migriert, pausiert Cron, löscht Daten oder veröffentlicht.

Der alte Workflow **Cloudflare Phase A - manueller Test-Deploy** ist für
`operation=deploy` **technisch gesperrt**, auch bei Eingabe des alten Bestätigungsworts.
Remote-Migration und Veröffentlichung wurden aus diesem Pfad entfernt. `validate`,
`diagnose` und der bisherige ausdrücklich manuelle `bootstrap` bleiben bestehen;
für dieses vorhandene kmn ist kein Bootstrap erforderlich.

Warum kein automatisch entsperrendes Backup-Ticket? Der alte Worker schreibt nach
einem Export weiter. Ein grüner Recovery-Lauf beweist den Exportstand, aber keine
unveränderte aktuelle Schema-/Datenversion in D1. Eine zeitbasierte Freigabe oder
allein eine Run-ID wäre unzureichend. Vor dem späteren Rollout muss ein gesondert
geprüftes Gate bei pausierten Schreibern denselben Account, dieselbe UUID und den
konkreten unveränderten Daten-/Schemastand binden. Bis dahin bleibt Deploy gesperrt.
Es gibt keinen Override-Schalter in diesem PR.

## Vorbereitungen am iPhone – erst später separat genehmigen

Safari → GitHub → Repository → Settings. Gegebenenfalls „Desktop-Website
anfordern“, falls die mobile Oberfläche Environments/Actions nicht zeigt.
Diese Einrichtung ist **nicht** durch den Entwicklungsauftrag genehmigt:

1. Im Cloudflare-Dashboard Workers Free und D1 kmn prüfen. Die DB-UUID und
   Account-ID genau notieren; Region EEUR/WEUR ist kein EU-Jurisdiktionsnachweis.
   Im Workflow wird `jurisdiction=eu` über den kanonischen D1-GET geprüft.
2. GitHub → Settings → Environments → **cloudflare-backup** einrichten:
   ausschließlich Branch main, erforderlicher Reviewer Besitzer, kein Bypass
   durch ungeprüfte Branches. Bei einem alleinigen Besitzer muss eine eigene
   manuelle Freigabe möglich bleiben; „prevent self-review“ würde diesen blockieren.
   main durch Review/Branchschutz sichern. Der Workflow kann diese administrativen
   Einstellungen mit seinen minimalen Rechten nicht unabhängig attestieren.
3. Nur in diesem Environment zwei **Variables** setzen:
   `CLOUDFLARE_ACCOUNT_ID` (32 kleine Hex-Zeichen) und `KMN_D1_DATABASE_ID`
   (exakte kanonische UUID der vorhandenen kmn). Nicht aus einem Namen erraten.
4. Nur in diesem Environment ein **Secret** `CLOUDFLARE_BACKUP_API_TOKEN`
   hinterlegen: auf dieses Cloudflare-Konto begrenzter D1-Token, nur die für
   List/Detail/Export erforderlichen Rechte. Mit D1 Read beginnen; falls das
   Export-API zusätzliche Rechte verlangt, diese gezielt nach offizieller
   Berechtigungsdokumentation prüfen. Keine Workers-/DNS-/Billing-/Kraken-Rechte,
   kein globaler API-Key. Kein Tokenwert in Chat, Code, Issue oder Screenshot.
5. Im Passwortmanager auf dem iPhone eine neue zufällige ASCII-Passphrase mit
   mindestens **32 Zeichen**, empfohlen 48+, erzeugen. Unter eigenem Eintrag
   „KMN D1 Backup“ dauerhaft speichern und dann als Environment-Secret
   `D1_BACKUP_PASSPHRASE` kopieren. Keine Zeilenumbrüche. Nicht von GitHub/CI
   generieren und nicht im Run-Log ausgeben lassen. Secrets sind später nicht
   wieder aus GitHub auslesbar.
6. Ein unabhängiges Wiederherstellungsmittel einrichten: Passwortmanager-
   Recovery/Notfallzugang und die Passphrase in einem physisch geschützten
   Offline-Notfallumschlag. Nicht zusammen mit dem einzigen Ciphertext ablegen.
   Wiederherstellung des Passwortmanagerzugangs am iPhone prüfen. Ein verlorener
   GitHub-Secretwert ersetzt keine Schlüsselkopie; ohne Passphrase ist die
   verschlüsselte Sicherung nicht wiederherstellbar.

Die Schlüsselstrategie benötigt keinen PC. Normalfall: Passphrase aus dem
Passwortmanager in das GitHub-Environment-Secret setzen, später eine eigenständige
Recovery starten. Bei Account-/Secretverlust: GitHub-Zugang und das Environment
wiederherstellen, Passphrase aus der unabhängigen Kopie neu setzen und Recovery
mit vorhandenem Artifact durchführen. Für länger archivierte Dateien gilt: mit
OpenPGP-kompatibler, vertrauenswürdiger Software auf einem neu vertrauenswürdig
bereitgestellten Gerät/isolierten Runner wiederherstellen. Dieses Repository
stellt noch keinen Datei-Upload für abgelaufene Artifacts bereit. Vor Ablauf
rechtzeitig eine Recovery-Probe durchführen; App-Unterstützung am iPhone nicht
ungeprüft voraussetzen. Schlüsselwechsel dokumentieren: alte Schlüsselkopien
aufbewahren, solange alte Ciphertexte benötigt werden.

## A. Export und verschlüsseltes Backup freigeben

**Vorher getrennte Exportfreigabe und Wartungsfenster vereinbaren.** Ein laufender
D1-Export blockiert laut offizieller Dokumentation andere Datenbankanfragen.
Besitzer pausiert den **bestehenden** Beobachtungs-Cron im Cloudflare-Dashboard
nur nach eigener konkreter Freigabe und bestätigt, dass keine anderen Schreiber
aktiv sind. Weder dieser Workflow noch Codex erledigt oder verifiziert diese
Pause automatisch. Keine zweite Cron-/Paper-Instanz starten. Zeit der Pause und
vorherige Cron-Konfiguration ohne Secrets dokumentieren.

1. GitHub → Actions → **D1 - encrypted backup and offline recovery** → Run workflow.
2. Branch **main**, Operation **backup** wählen.
3. `confirmation`: **EXPORT_EXISTING_KMN**.
4. `maintenance_confirmation`: **OWNER_CONFIRMED_MAINTENANCE**.
   Dieses Wort ist eine bewusste Betreiberbestätigung, kein technischer Nachweis
   der Pause. Eine fehlende/falsche Bestätigung oder fehlende Secrets brechen ab.
5. Source-Run-ID leer lassen. Starten und gegebenenfalls das Environment separat
   unter „Review deployments“ freigeben. Die Environment-Bezeichnung erzeugt
   hier keinen Cloudflare-Deploy; sie schützt den Zugriff auf die Secrets.
6. Bis zum vollständig grünen Lauf warten, einschließlich Artifact-Upload und
   Cleanup. Erfolgsmeldung: „Encrypted backup and offline recovery verified.“
   Keine SQL-Zeilen, Tabelleninhalte oder privaten Hashes gehören in das Run-Log.
7. Unter Artifacts **kmn-encrypted-d1** herunterladen. ZIP enthält ausschließlich
   `backup.tar.gz.gpg` und `ciphertext.sha256`. In iPhone Dateien an einen eigenen
   geschützten Archivort und eine unabhängige zweite Ablage kopieren. Die
   Passphrase bleibt getrennt im Passwortmanager/Notfallumschlag.
8. Numerische **Run-ID** aus der Browser-URL `/actions/runs/…` notieren, ebenso
   Quellcommit, Datum und GitHub-Artifact-Digest. Keine privaten Exportdetails
   öffentlich ins Issue kopieren. Ein Ciphertext-Hash allein ist kein Restore-Beleg.

Der Workflow prüft zunächst eindeutige D1-Namensauflösung, konkrete erwartete UUID
und EU-Jurisdiktion im erwarteten Konto. Er erstellt eine minimale temporäre
Wrangler-Konfiguration mit genau dieser Account-ID und UUID, exportiert vollständig
mit `wrangler d1 export kmn --remote --output=…`, und prüft die Identität erneut.
Es gibt keinen `create`, `execute --remote`, Remote-Restore oder Löschpfad.

SQL und SQLite liegen nur in `umask 077`-geschützten temporären Runner-Verzeichnissen.
Auch Wrangler-Logs bleiben dort. Subprozess-Ausgaben und Exception-Texte werden
nicht ins Log übernommen. Nach Fehlern/Erfolg werden temporäre Daten entfernt;
Cleanup läuft auch nach einem Upload-Fehler. Bei hartem Runner-Abbruch kann kein
Shell-Cleanup garantiert werden: ausschließlich kurzlebige GitHub-gehostete
Runner verwenden, keine wiederverwendbaren selbstgehosteten Maschinen. Keine
Behauptung einer physischen Secure-Erasure auf SSDs. Es gibt keinen Actions-Cache
und keinen Klartext-Upload, auch keinen Debug-Artifact-Upload.

Vor einem Upload erfolgen SQL-Import und SQLite-Integritäts-/Fremdschlüsselprüfung,
Kontrolle des erwarteten Phase-A-Schemas und der Migrationen 0001/0002 oder
0001/0002/0003, deterministische Rowcounts/Hashes aller Tabellen einschließlich
Analysen, Jobs, Runs, Gaps, Legacy-Batches und optionaler Kontodaten. Unbekanntes
Schema, fehlende Migrationen, leere/abgebrochene Exporte oder unerwartet leere
Pflichtjournale sind Fehler. Der Import kann keine anderen Dateien per ATTACH
öffnen oder SQLite-Erweiterungen laden.

Das verschlüsselte Paket enthält SQL, geprüften SQLite-Snapshot, Snapshot-Hash
und einen internen Herkunfts-/Prüfmanifest mit Account/UUID/EU, Run/Commit,
Schema-/Datenhashes und Zählungen. GnuPG verwendet AES-256 mit OpenPGP-MDC-
Integritätsschutz und iterierter SHA-512-Passphraseableitung. Die Passphrase
wird ausschließlich per stdin übergeben, niemals als Argument oder Schlüsseldatei.
Eine Entschlüsselung gilt nur mit erfolgreichem GPG-Status **GOODMDC** und
**DECRYPTION_OKAY**. Der zusätzliche öffentliche SHA-256 prüft Transportfehler;
er ersetzt nicht die kryptografische Integrität. Symmetrische Verschlüsselung
beweist keine unabhängige Signatur des Besitzers: jeder Schlüsselinhaber könnte
ein neues Paket erzeugen. Deshalb ebenfalls den erfolgreichen vertrauenswürdigen
main-Run und den verschlüsselten Herkunftsmanifest prüfen.

Das Paket wird noch vor Upload wieder entschlüsselt. Danach werden **zwei**
unabhängige Wiederherstellungen verglichen: neuer SQL-Import und der aus PR #17
bekannte `storage_snapshot.py`-Restore. Nur bei vollständiger Daten-/Schemaparität
werden die beiden öffentlichen Dateien bereitgestellt. Das beweist einen
lokalen Restore des Exportstands, keinen Remote-Restore und keinen aktuellen
unveränderten Live-Datenstand.

## B. Eigenständige Offline-Recovery freigeben

1. Actions → gleicher Workflow → main → Operation **recovery**.
2. `confirmation`: **OFFLINE_RECOVERY_ONLY**; Source-Run-ID des grünen Backups
   eingeben. Wartungsbestätigung leer lassen: diese Probe benötigt keine Cron-Pause.
3. Environment freigeben und bis zum vollständig grünen Lauf warten.
4. Erfolgsmeldung „Offline recovery verified. No Cloudflare write or restore.“
   zusammen mit Backup-/Recovery-Run-ID und Commit geschützt dokumentieren.
   Es entsteht kein Klartext-Artifact und es wird nichts in D1 geschrieben.

Der Recovery-Job bekommt **keinen Cloudflare-Token**. GitHub-Zugriff ist auf
`contents: read`, `actions: read` begrenzt. Er akzeptiert nur einen erfolgreichen
manuellen main-Lauf des exakt richtigen Workflows im Originalrepository,
weniger als sieben Tage alt, mit genau einem verfügbaren Backup-Artifact.
Account/UUID/EU aus dem verschlüsselten Manifest müssen zu den erwarteten
Environment-Variablen passen, Run/Commit zum nachgelesenen GitHub-Quelllauf.
Falscher Schlüssel, manipuliertes Paket/Manifest oder überschreibbares Ziel
führen zum Abbruch. Alle lokalen Wiederherstellungsdateien werden entfernt.

## Aufbewahrung und Fehler

GitHub-Artifacts sind **keine dauerhafte Sicherung**. Dieser Workflow setzt
`retention-days: 7`; Repository-/Organisationsrichtlinien können die Verfügbarkeit
zusätzlich einschränken. Public-Repositories haben normalerweise maximal 90 Tage
Artifact-Retention; hier werden bewusst sieben verlangt. Ciphertext ist öffentlich
abrufbar zu behandeln, daher keine kurzen oder wiederverwendeten Passphrasen.
Der Upload ist pro Sicherung auf 100 MB begrenzt; größere Pakete brechen ab,
keine automatische Aufteilung oder kostenpflichtige Speicherbuchung. Vor neuen
Backups GitHub-Speicher-/Actions-Quoten kontrollieren und rechtzeitig die eigenen
verschlüsselten Kopien archivieren. Der Workflow löscht keine älteren Artifacts.

Ein abgebrochener Export/Upload oder fehlgeschlagener Recovery-Lauf ist **kein**
Backup-Nachweis. Keine privaten Debuglogs anhängen; nur generischen Fehlerstatus,
Run-ID und Codecommit prüfen. Nach korrigierter Einrichtung erneut ausdrücklich
freigeben. Bei fehlendem/abgelaufenem Artifact neuen Export separat genehmigen
oder eigene archivierte Sicherung in einem dafür geprüften isolierten Ablauf
wiederherstellen lassen. Die Standard-Recovery lehnt alte/fehlende Artifacts ab.

Cloudflare Free Time Travel bietet laut [Dokumentation](https://developers.cloudflare.com/d1/reference/time-travel/)
sieben Tage; kein Ersatz für die verschlüsselte, extern archivierte Sicherung.
Ein Restore darüber ist eine **produktive Schreiboperation** und durch diesen
PR weder implementiert noch genehmigt.

## C. Späterer Rollout – weiterhin gesperrt

Folgende Freigaben bleiben getrennt erforderlich:

- Review und Merge dieses PR; dadurch keinerlei Cloudflare-Aktion.
- Secret-/Environment-Einrichtung sowie konkret genehmigte Wartung/Cron-Pause.
- Konkreter D1-Export; danach erfolgreiche eigenständige Offline-Recovery.
- Implementierung/Review eines belastbaren Live-Datenversions-Gates und frischer
  Nachweis für exakt denselben pausierten Datenstand. Die heutige Sperre nicht
  durch Umbenennen einer Run-ID oder alte Bestätigungswörter umgehen.
- **Separate Migration-0003-Freigabe**, anschließend **separate Worker-Deploy-
  Freigabe**. Kein gemeinsamer, automatisch nachgeschalteter Workflow in diesem PR.
- Nach genehmigtem Rollout Freigabe des kontrollierten Beobachtungstests und der
  Wiederaufnahme des ursprünglichen Crons. Niemals eine zweite Instanz erzeugen.

Die neue Worker-Konfiguration bindet Cloudflares nicht geheime `version_metadata`.
`/api/status` und System im UI zeigen `build_id` (eindeutige veröffentlichte
Cloudflare-Versions-UUID); Ohne Binding ist sie null; lokale Emulatoren können eine Test-ID liefern. Diese ist eine
Buildkennung, kein Git-SHA: beim später freigegebenen Rollout Version-ID und
Quellcommit gemeinsam protokollieren. Der noch laufende alte Worker zeigt sie
nicht; dieser PR aktualisiert ihn nicht.

Danach ausschließlich authentifiziert `/api/diagnostics`, alle 16 Fenster,
Speichergröße/-trend sowie echte CPU-/D1-Dashboardmetriken kontrollieren.
10-ms-Free-CPU, accountweite D1-Tagesquoten und Langzeitbetrieb bleiben bis zu
realen Messungen **unbestätigt**. Lokal erfolgreiche Tests sind kein CPU-Beleg.
Kein Paid-Upgrade. Bei Fehlern nach eigener Freigabe Cron pausieren und die
Version prüfen; Tabellen/Legacy-/Auditdaten behalten. Keine Down-Migration,
keine automatische Remote-Wiederherstellung. Alte Worker-Versionen können wieder
redundante Batches schreiben: Rollback nur kontrolliert nach Pause und Review.

## Verifikation dieses PR

Alle neuen Backup-/Sicherheitsprüfungen verwenden ausschließlich synthetische
lokale SQL-/SQLite-Fixtures, Fake-API-Antworten und temporäre Testschlüssel.
Tests prüfen vor/nach 0003, Schema-/Datenparität, falsche UUID/EU, fehlende Secrets,
Manipulation von Ciphertext und internen Hashes, unsichere Archive, bestehenden
Zieldateien, fehlende/alte/fehlgeschlagene Runs, Export-/Recovery-Abbruch,
Upload-Auswahl/Cleanup und die Deploy-Sperre. PR-CI verwendet keine Cloudflare-
oder Backup-Secrets und lädt keine Sicherung hoch. Bestehende Python-, Worker-,
D1-, Mobile-Tests und Wrangler-Dry-Run bleiben erforderlich.

Offizielle Referenzen:
[Cloudflare Export](https://developers.cloudflare.com/d1/best-practices/import-export-data/),
[D1 Time Travel](https://developers.cloudflare.com/d1/reference/time-travel/),
[GitHub Artifact Retention](https://docs.github.com/en/actions/using-workflows/storing-workflow-data-as-artifacts),
[GnuPG](https://www.gnupg.org/documentation/manuals/gnupg/).

## Sichere Diagnose nach fehlgeschlagenem Backup (Issue #20)

Lauf [41126219688](https://github.com/MueschKi/krypto-master-network/actions/runs/41126219688)
auf Commit `f57a3ac691981761be202ec950a3dd3e9c07f44b` scheiterte am
30.10.2026 zwischen 20:49:29 und 20:49:32 UTC im gemeinsamen Export-/Encrypt-/Restore-Schritt.
Checkout, Python, Node und npm waren erfolgreich, Upload und Recovery wurden übersprungen;
Cleanup war erfolgreich. Der Log enthält keine Stufe und erlaubt **keine Aussage zur
Ursache** oder zu Datenverlust. Der PR führt keinen Retry und keine produktive Abfrage aus.

Auf dem iPhone **nach Merge**:

1. GitHub → Actions → **D1 - encrypted backup and offline recovery** → Run workflow.
2. Branch **main**, `operation=diagnose`, `confirmation=DIAGNOSE_EXISTING_KMN`.
   Wartungsbestätigung und Source-Run-ID bleiben leer. Bestehendes Environment
   `cloudflare-backup` gegebenenfalls wie bisher freigeben.
3. Im Diagnosejob den festen `stage`-Code und gegebenenfalls `HTTP`/numerische `CF`-Codes lesen.
   Keine Secrets oder Rohantworten teilen. Diagnose lädt keine Artifacts hoch.
4. Bei fehlenden Rechten ausschließlich die minimal benötigte Berechtigung für den
   Backup-Token und den vorgesehenen Account prüfen. Keine automatische Erweiterung,
   kein Ersatz durch einen breiten Deployment-Token, niemals pauschal D1 Edit vergeben.
5. Erst danach einen **neuen, separaten** Backup-Lauf bewusst freigeben: vorher den
   bestehenden Beobachtungs-Cron selbst wieder pausieren und anschließend die bestehenden
   `EXPORT_EXISTING_KMN`- und `OWNER_CONFIRMED_MAINTENANCE`-Bestätigungen setzen.
   Ein erfolgreicher Diagnosejob autorisiert weder Export noch Deployment.

Wenn kein Export läuft, darf der Betreiber den ursprünglichen Beobachtungs-Cron
zwischenzeitlich bewusst wieder aktivieren. Actions startet oder pausiert keinen Cron.

Die Diagnose braucht keine Backup-Passphrase. Sie prüft den lokal gesperrten Wrangler
gegen die Lockfile-Version und GPG-Verfügbarkeit ohne Cloudflare-Token im Unterprozess.
Danach erfolgen ausschließlich GET `/user/tokens/verify`, paginierte D1-Liste im
konfigurierten Account und Detailprüfung der exakten UUID, `name=kmn`, `jurisdiction=eu`.
Es gibt keinen SQL-/Datenzeilenzugriff, POST-Export, Schreibzugriff oder Deploy.
REST GET ersetzt bewusst `wrangler d1 list --json`, dessen zusätzliche Rechte bei
eingeschränkten Tokens scheitern können. Fehlende oder unbekannte Identität bricht ab.

| Stufe | Prüfung / nächster manueller Schritt |
| --- | --- |
| `ENV_CONTEXT` | Manueller main-/Repository-Kontext, Diagnosebestätigung, Wrapper/GPG oder aktiver Tokenstatus. HTTP 401/403 hier betrifft Token-Verifikation. |
| `SECRET_FORMAT` | Vorhandensein/Format von Account, UUID, Token oder Backup-Passphrase; Werte niemals loggen. |
| `D1_LIST` | GET-Listenrecht, eindeutiger Name und exakte UUID im vorgesehenen Account; 401/403 ist gezielt dieser GET-Prüfung zugeordnet. |
| `D1_DETAIL_EU` | GET-Detailrecht und exakte UUID/Name/EU-Jurisdiktion. Keine automatische Neuanlage oder Verschiebung. |
| `WRANGLER_EXPORT` | Nur separat bestätigter Backup-Lauf: Export fehlgeschlagen/abgebrochen. Keine rohe Wrangler-Ausgabe. |
| `EXPORT_EMPTY` | Exportdatei fehlt oder ist leer. |
| `SQL_IMPORT` | Ausschließlich lokale SQL-Importprüfung fehlgeschlagen. |
| `SCHEMA_MISMATCH` | Lokale Tabellen-/Migrations-/Schemaprüfung fehlgeschlagen. |
| `GPG_ENCRYPT` / `GPG_DECRYPT` | Verschlüsselung bzw. authentifizierte Entschlüsselung fehlgeschlagen. |
| `RESTORE_PARITY` | Lokale Snapshot-/Restore-/Provenienzprüfung fehlgeschlagen. |
| `ARTIFACT_LIMIT` | Ciphertext überschreitet die zulässige Größe oder ist ungültig. |
| `ARTIFACT_UPLOAD` | Veröffentlichung des verifizierten Ciphertexts oder Actions-Upload fehlgeschlagen. |

Nur diese festen Stufen, API-HTTP-Status und streng numerische Cloudflare-Fehlercodes
werden von den Diagnose-/Backup-Skripten ausgegeben. Unbekannte Drittanbieterfehler,
Antworttexte, URLs, SQL, IDs, Tabellen-/Zeilenhashes und Secrets werden unterdrückt.
Private temporäre Wrangler-/GPG-Dateien werden gelöscht und nie als Debug-Artifact hochgeladen.
Ein erfolgreicher GET-Preflight beweist **keine** Exportberechtigung: die
[Export API](https://developers.cloudflare.com/d1/best-practices/import-export-data/)
verwendet POST; ob der konkrete D1-Read-Token dafür genügt, bleibt ohne spezifischen
Beleg offen. Der Export verwendet das dokumentierte
[`--skip-confirmation`](https://developers.cloudflare.com/workers/wrangler/commands/d1/)
für nichtinteraktive CI, ausschließlich hinter den bestehenden ausdrücklichen
Export-/Wartungs-Gates. Deployment bleibt gesperrt.
