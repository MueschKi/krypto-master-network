# D1-Export: Offline-Untersuchung zu Issue #22

Stand: 30.10.2026. Es wurden nur GitHub-Laufmetadaten/-Logs, öffentliche
Dokumentation und der durch `npm ci` integritätsgeprüfte Wrangler-Quellcode
untersucht. Keine produktive Cloudflare-Abfrage, kein Export und keine Änderung
an Token, Datenbank, Cron, Deployment oder Handel.

## Was der fehlgeschlagene Lauf belegt

[Backup #41129213133](https://github.com/MueschKi/krypto-master-network/actions/runs/41129213133)
auf Commit `db7f39c503d2e4aed5742c7120339134c8b4b82c` scheiterte am 30.10.2026
um 21:12:18 UTC, etwa drei Sekunden nach Beginn des Export-/Encrypt-/Restore-Schritts:
`FAILED stage=WRANGLER_EXPORT`. Setup/npm waren erfolgreich, Upload übersprungen,
Artifacts leer und Cleanup erfolgreich. Es existiert keine verifizierte neue
Sicherung aus diesem Lauf. Die ursprüngliche Unterprozessausgabe wurde verworfen
und lässt sich nachträglich nicht rekonstruieren. Ein HTTP-/Tokenfehler, ein
Downloadfehler oder ein CLI-/Konfigurationsfehler ist damit **nicht nachgewiesen**.

Der separate [GET-Diagnoselauf #41128846964](https://github.com/MueschKi/krypto-master-network/actions/runs/41128846964)
war erfolgreich. Das bestätigt Tokenstatus und Metadatenidentität zu diesem
Zeitpunkt, aber keine POST-Exportberechtigung und keine erfolgreiche Sicherung.

## Wrangler 4.156.0: belegter Ausführungspfad

Quelle ist das gesperrte npm-Paket `wrangler@4.156.0`,
`node_modules/wrangler/wrangler-dist/cli.js`, insbesondere die eingebetteten Module
`src/d1/export.ts`, `src/d1/utils.ts`, `src/user/user.ts`, `src/cfetch/index.ts`,
`../workers-utils/src/parse.ts`, `src/utils/log-file.ts` und `src/handle-errors.ts`.
[Upstream-Quellcode des Tags](https://github.com/cloudflare/workers-sdk/tree/wrangler%404.156.0/packages/wrangler/src).

- `d1ExportCommand` akzeptiert `--remote`, `--skip-confirmation` und `--output`;
  `--config` ist ein globaler Wrangler-Parameter. `--skip-confirmation` unterdrückt
  den Hinweis, dass die Datenbank während des Exports nicht verfügbar sein kann.
  Es ersetzt **keine** unserer Export-/Wartungsbestätigungen.
- Die temporäre TOML enthält den validierten Account und die exakte UUID unter
  dem Namen `kmn`. `getDatabaseByNameOrBinding()` gibt diese UUID direkt zurück,
  ohne D1-list- oder Name-zu-UUID-Aufruf. `requireAuth()` verwendet den bereitgestellten
  API-Token; mit explizitem `account_id` vermeidet `getOrSelectAccountId()` die
  automatische Account-/Mitgliedschaftssuche. Keine zusätzliche Listen- oder
  Account-Berechtigung ist aus diesem normalen Pfad ableitbar.
- `exportRemotely()` ruft `pollExport()` auf. Dieses startet und pollt denselben
  POST-Endpunkt `/accounts/{account_id}/d1/database/{database_id}/export` mit
  `output_format=polling`, `dump_options` und anschließendem `current_bookmark`.
  Nach `status=complete` wird die signierte Download-URL mit `undici.fetch()`
  abgerufen und der Body in die private SQL-Datei geschrieben.
- Bei Authentifizierungsfehlern kann Wranglers Fehlerbehandlung zusätzlich
  `whoami()` aufrufen. Solche Folgefehler beweisen keine fehlenden Rechte für den
  ursprünglichen Export. Der Parser ordnet deren Codes nicht dem Export zu.
- `throwFetchError()` und `renderError()` erzeugen den API-Routenheader und
  `[code: N]`-Notizen. Der APIError hält den HTTP-Status intern; die normale
  ParseError-Ausgabe zeigt ihn nicht an. Wir erraten keinen HTTP-Status aus einem
  Code. `9106`/`10000` sind im gepinnten Quellcode Authentifizierungsfehlercodes.
- Der Downloadfehler hat dagegen den festen Text
  `There was an error while downloading from the presigned URL with status code: N`.
  Dieser Status betrifft den **Download**, nicht die Export-API-Autorisierung.

Ein VM-Test führt die tatsächlichen relevanten Funktionen aus dem gesperrten
Bundle mit synthetischen Stubs aus: keine Account-/D1-Suche mit vollständigem
Binding, keine Rückfrage bei bestätigtem CLI-Flag, POST-Polling mit Bookmark.
Der VM-Kontext stellt weder `require`, `process` noch Netzwerkfunktionen bereit;
der Wrangler-CLI-Export wird im Test nicht gestartet.

CLI-Syntax, UUID-Auflösung und expliziter Account zeigten dabei keinen belegten
Export-Codefehler. Behoben wird der belegte Diagnosefehler: vollständiger Verlust
der Unterprozesssignale. Zusätzlich werden automatische private Debug-Logs jetzt
in eine private `.log`-Symlink auf `/dev/null` verworfen; Wrangler würde auch bei
`WRANGLER_LOG=error` intern Debug-Dateien anhängen. Der eigentliche Export-/Download-
und Verifikationspfad wird nicht durch eine ungeprüfte Alternative ersetzt.

## Berechtigungen: Fakten und offene Frage

Die [Export-Methodenseite](https://developers.cloudflare.com/api/resources/d1/subresources/database/methods/export/)
beschreibt POST, Polling und die zeitweise Nichtverfügbarkeit; sie enthält beim
Prüfstand keine eindeutige Accepted-Permissions-Zeile. Die
[Import-/Export-Anleitung](https://developers.cloudflare.com/d1/best-practices/import-export-data/)
und [Wrangler-Dokumentation](https://developers.cloudflare.com/workers/wrangler/commands/d1/)
belegen Befehl und Ablauf, aber nicht die konkrete Token-Autorisierung dieses Laufs.
Die [Permission-Referenz](https://developers.cloudflare.com/fundamentals/api/reference/permissions/)
beschreibt `D1 Read` als Lesezugriff und `D1 Edit`/`D1 Write` als Schreibzugriff.
Die [Datenbank-Löschmethode](https://developers.cloudflare.com/api/resources/d1/subresources/database/methods/delete/)
nennt ausdrücklich `D1 Write` als akzeptierte Berechtigung.

Weder HTTP POST allein noch der erfolgreiche GET-Preflight beweisen, ob `D1 Read`
für diesen Export genügt. Es gibt keinen Beleg, dass der aktuelle Lauf D1 Write
braucht. Daher **keine** Rechteerweiterung und kein Deployment-Token als Ersatz.
Sollte später eine spezifische, belastbare Quelle oder Diagnose einen Write-Scope
als notwendig nachweisen, bedeutet dessen Freigabe auch Schreib-/Löschrisiko für
die ausgewählten Ressourcen. Eine solche Änderung benötigt eine eigene bewusste
Risikoentscheidung des Besitzers; der Code ändert keine Rechte und versucht keine
anderen Credentials. Die neue Klasse `AUTH_DENIED` allein ist keine solche Freigabe.

## Sichere Ausgabe und Grenzen

Nur die bestehende Stage `WRANGLER_EXPORT` bekommt zusätzliche feste Felder:
`class`, numerisches `EXIT`, gegebenenfalls numerisches `CF` oder `HTTP`.

| class | Bedeutung |
| --- | --- |
| `AUTH_DENIED` | Exakter Export-API-Routenheader und numerischer CF-Code 9106/10000; kein erfundener HTTP-Status. |
| `API_ERROR` | Exakter Export-API-Routenheader, gegebenenfalls andere streng numerische CF-Codes. |
| `DOWNLOAD_AUTH_DENIED` | Download meldet HTTP 401/403; keine Aussage über POST-Rechte. |
| `DOWNLOAD_NOT_FOUND` / `DOWNLOAD_RATE_LIMIT` | Download meldet HTTP 404 bzw. 429. |
| `DOWNLOAD_SERVER_ERROR` / `DOWNLOAD_HTTP_ERROR` | Download meldet HTTP 5xx bzw. sonstigen gültigen Status. |
| `CLI_SYNTAX` / `CONFIG_INVALID` | Eng begrenzte bekannte CLI-/TOML-/Outputpfad-Fehlersignale. |
| `SPAWN_FAILED` / `TIMEOUT` / `INTERRUPTED` | Prozessstart, Frist oder Stream-/Prozessüberwachung fehlgeschlagen. |
| `OUTPUT_LIMIT` | Mehr als insgesamt 64 KiB stdout/stderr; Prozessgruppe beendet. |
| `UNKNOWN` | Kein eindeutiges bekanntes Signal, ungültige Kodierung/Kontrollzeichen, überlange Zeile oder widersprüchliche Signale. |

Beispiele: `FAILED stage=WRANGLER_EXPORT class=AUTH_DENIED EXIT=1 CF=10000`
oder `FAILED stage=WRANGLER_EXPORT class=DOWNLOAD_AUTH_DENIED EXIT=1 HTTP=403`.
Kein Rohtext, keine URLs, IDs, SQL, Tabellennamen, Token oder Passphrasen.
Numerische Exitcodes sind Prozesswerte, keine Cloudflare-Codes. Vorzeichen können
Unix-Signalabbrüche kennzeichnen. Die Parserregeln gelten für die gepinnte Version;
eine geänderte Ausgabe fällt sicher auf `UNKNOWN` zurück. Die Klassen sind
Diagnosehinweise; sie lösen weder Retry noch Rechteänderung aus.

Beide Pipes werden gleichzeitig in höchstens 64 KiB flüchtigen Speicher gelesen;
SGR-Farbcodes sind begrenzt, Signale pro Zeile auf 4096 Zeichen, Code-Kontext auf
16 Folgezeilen begrenzt. Keine Debug-Artefakte. Bei Timeout, Überlauf oder Streamfehler
werden Prozess und Nachkommen vor der temporären Bereinigung beendet. Exit 0 reicht
weiterhin nicht zur Freigabe eines Artifacts: nichtleerer Export, Verschlüsselung,
authentifizierte Entschlüsselung und beide lokalen Restore-Prüfungen bleiben Pflicht.
Alle anderen Stages und der separate GET-only-Diagnosemodus bleiben unverändert.
