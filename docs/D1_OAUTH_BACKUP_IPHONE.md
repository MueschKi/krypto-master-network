# Einmaliger persönlicher OAuth-D1-Export: sichere Vorbereitungsgrenze (#28)

**Status: vorbereitet, aber Anmeldung und Export gesperrt. Kein Backup erstellt.**
Die Entwicklung/PR-CI verwendet ausschließlich lokale synthetische Fixtures und
Mock-CLI, niemals persönliche OAuth-Anmeldung oder produktive Cloudflare-Aufrufe.
Der bestehende `CLOUDFLARE_BACKUP_API_TOKEN` bleibt unverändert.

## Ergebnis der offiziellen Recherche (31.10.2026)

Geprüft: offizielle [Wrangler-Login-Dokumentation](https://developers.cloudflare.com/workers/wrangler/commands/general/#login),
[Device-Login ohne lokalen Callback](https://developers.cloudflare.com/workers/wrangler/commands/general/#use-wrangler-login-without-a-local-callback-server),
[D1-Export](https://developers.cloudflare.com/d1/best-practices/import-export-data/#export-an-existing-d1-database)
und der durch `package-lock.json` gepinnte npm-Code **Wrangler 4.156.0**.
Der Offline-Vertrag `check_wrangler_oauth_contract.mjs` extrahiert ausschließlich
Scope-Tabelle und Command-Definitionen in eine VM ohne Netzwerk/Prozesszugriff;
der Login-Helper wird gemockt. Kein echter Login wird zum Prüfen aufgerufen.

| Frage | Nachgewiesen / Grenze |
| --- | --- |
| Device-Login? | `login --device`, `--browser=false`, `--scopes` als Liste, `--scopes-list`, `--use-keyring` vorhanden. |
| iPhone/Codespaces? | Device Grant RFC 8628 ohne localhost-Callback; konzeptionell geeignet für Remote-Shells. Keine Portfreigabe nötig. Echter Codespaces/iPhone-Login wurde ausdrücklich **nicht** getestet. |
| D1-Minimum? | Einziger angebotener D1-Scope: `d1:write` = „See and change D1 Databases.“ Kein `d1:read`, kein Export-only-Scope. |
| Zusätzliche Rechte? | Device-Code fordert intern immer `offline_access` an: Refresh-Credential-Risiko. Ohne explizite Scopes fordert Wrangler standardmäßig alle Scopes an. |
| Reicht nur `d1:write`? | Nicht produktiv bewiesen. Account-/User-Metadatenrechte könnten zusätzlich nötig sein. Keine automatische Erweiterung. Explizite Account-/UUID-Bindung vermeidet Wrangler-Accountauswahl, begrenzt aber **nicht** die OAuth-Grant-Reichweite. |
| D1 Read vs OAuth? | GET/SELECT-Probe #41135253283 erfolgreich; nativer Export mit bestehendem Read-Token scheiterte `CF=10000`. Das allein beweist keine universelle Berechtigungsregel. OAuth umgeht weder Kontomitgliedschaft noch Cloudflare-Berechtigungen. |

**Entscheidung: fail closed.** Ein sicher enger Export-Scope ist nicht verfügbar.
`prepare` endet daher bewusst mit Exit **2** und
`OAUTH_SCOPE_OWNER_APPROVAL_REQUIRED`; `login` und `export` werden vor jedem
Subprozess und vor dem Lesen von Zugangsdaten abgewiesen. Kein Override-Flag,
keine versteckte Umgebungsvariable und kein CI-OAuth-Pfad existieren.

## Jetzt auf dem iPhone: keine Shell-Befehle und kein Codespace nötig

1. PR und insbesondere diese Scope-Entscheidung prüfen. In GitHub → PR → Checks
   den Lauf **Phase A – Cloudflare read-only checks** öffnen. Er installiert die
   gepinnten Werkzeuge und führt automatisch die Offline-Verträge und die
   synthetische AES-256-/Recovery-Probe aus; keine Secrets, keine Backup-Artifacts.
2. Ein grüner Check bedeutet ausschließlich getestete Vorbereitung. **Nicht** den
   vorhandenen Actions-Backup als OAuth-Ersatz starten. Nicht Cron pausieren, solange
   kein konkreter späterer Exporttermin freigegeben ist.
3. Falls persönliches OAuth trotz der breiteren Rechte gewünscht ist: separat
   ausdrücklich die Risikoentscheidung für `d1:write` und implizites `offline_access`
   treffen. Keine Codes, Tokens oder Passphrase im Chat/Issue senden. Merge allein
   ist keine solche Freigabe. Danach muss ein separater geprüfter Umsetzungsschritt
   den tatsächlichen Login-/Exportpfad ergänzen; dieser PR führt ihn nicht aus.

Das ist die minimale Handlungsgrenze unter den Anforderungen von Issue #28.
Ein Ein-Klick-Produktivbackup wird hier bewusst nicht behauptet.

## Optional: Offline-Probe in einer schon vorhandenen isolierten Umgebung

**Vor Erstellung eines Codespace** unter GitHub Settings → Billing & licensing
Codespaces-Freikontingent, Speicher, Budget und Stop-Timeout prüfen. Bei nicht
sicher kostenfreiem Betrieb **keinen Codespace erstellen**; die PR-Checks reichen.
Gestoppte Codespaces können weiter Speicherkosten erzeugen. Keine Cloudflare-
Ressource, kein Paid-Upgrade und keine zusätzliche Datenbank sind nötig.
Siehe [GitHub Codespaces-Abrechnung](https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-codespaces/about-billing-for-github-codespaces).

In VS Code Web auf dem iPhone Menü → View → Command Palette → **Tasks: Run Task**:

1. **D1: 0 Gepinnte Werkzeuge installieren** (nur falls noch nicht installiert;
   npm-Download, keine Cloudflare-Anmeldung). Benötigt Node 24, Python ≥3.11 und
   GnuPG, wie PR-CI. Fehlen diese, PR-Checks nutzen; kein manueller Terminal-Setup nötig.
2. **D1: 1 Offline-Vorbereitung (OAuth gesperrt)**. Exit 2 ist die erwartete Sperre.
3. **D1: 2 Synthetische AES-256-Recovery-Probe**. Erwartet `VERIFIED SYNTHETIC ONLY`.

Kein Task startet beim Öffnen, keiner meldet an, keiner liest die produktive
UUID oder Secrets. Die Probe erzeugt einen zufälligen Testschlüssel und ein
synthetisches Schema 0001/0002; sie nutzt unverändert `encrypted_d1.pack`, GPG
AES-256/MDC und `encrypted_d1.recover` mit unabhängigem SQL-Import und
`storage_snapshot.restore`. Zwei frische Recovery-Durchgänge müssen gelingen,
bevor ausschließlich Ciphertext/Hash in einen **ebenfalls temporären** Ordner
kopiert werden. Danach wird alles entfernt. Das ist kein produktiver Herkunftsnachweis.
Vorhandene Negativtests decken auch Schema 0003, falschen Schlüssel, fremde UUID,
Entschlüsselungsfehler, Schemaänderung und Restore-Abweichungen ab.

## Verbindlicher Vertrag für einen später separat freigegebenen Online-Ablauf

Diese Liste beschreibt noch zu implementierende Gates, keine heutigen Buttons:

- **Vor Login:** ausschließlich frische isolierte Umgebung ohne globale Wrangler-
  Profile, injizierte API-Tokens, `.env`/`.dev.vars`, Credential-Sync, Terminal-
  Aufzeichnung oder öffentliche Ports. Nicht mit `wrangler login` bestehende
  Default-Credentials überschreiben. Privates temporäres Auth-/Log-Verzeichnis,
  Telemetrie aus, Raw-Logs verwerfen; Prozessgruppe vor Cleanup beenden.
- **Grant:** explizit geprüfte Scope-Auswahl, niemals unbeschränktes Standardlogin.
  Besitzer prüft persönlich Cloudflare-Domain/Konto/Consent und autorisiert am
  iPhone. Device-Code/URL nur in privater interaktiver Anzeige, nie Logs, Chat,
  Repository oder Artifacts. Abbruch/Timeout/ungültiger Scope/403: Stop ohne Retry,
  ohne Scope-Ausweitung und ohne Token-Fallback. Tatsächlich gewährte Scopes
  kontrollieren; widersprüchlicher Consent ist ein Fehler.
- **Identität vor und nach Export:** Account exakt
  `f0a60a3beddd872d99e04f88ad4b4ddb`, gültige UUID aus bestehendem geschützten
  Environment `KMN_D1_DATABASE_ID`, eindeutiger Name `kmn`, Jurisdiktion `eu`.
  GitHub-Environment-Variablen stehen Codespaces **nicht automatisch** zur Verfügung;
  eine geschützte Übernahme/Auswahl muss geprüft implementiert werden. Keine
  UUID raten, keine DB anlegen. Konfiguration explizit auf diese UUID binden.
- **Wartung vor manuellem Start:** Besitzer pausiert Cron **und sämtliche** D1-
  Schreiber separat, dokumentiert vorherigen Zustand und kontrolliert extern
  deren Stillstand: in-flight Requests/Queues/Jobs abgelaufen, Run-/Schreibaktivität
  über geeignetes Beobachtungsintervall unverändert, keine parallelen Clients.
  Für jeden Schreiber benannter Kontrollbeleg und frische Bestätigung erforderlich;
  bloßes Bestätigungswort ersetzt keine Kontrolle. Fehlender/widersprüchlicher
  Nachweis: Stop. Kein automatisches Cron-Edit. Export kann D1-Anfragen blockieren.
- **Manueller Exportstart:** eigene ausdrückliche Bestätigung nach Identitäts- und
  Wartungsprüfung. Ausschließlich nativer vollständiger Export über gepinnten
  Wrangler, keine Remote-SQL-Mutation, Migration, zweite DB, Trading oder Deploy.
  Free-Quoten/Größe vorab prüfen; keine automatische kostenpflichtige Erweiterung.
  Unbekannte Quoten oder nicht garantierbare Kostenfreiheit vorher klären.
- **Passphrase:** ≥32 zufällige Zeichen aus Passwortmanager, zweimaliger geschützter
  interaktiver Prompt, kein Echo/Fallback bei fehlendem TTY. Nicht als Argument,
  Environment, Datei oder Log weitergeben. GPG bekommt sie nur über stdin.
- **Prüfung/Archivierung:** `verified_package` stellt den wiederverwendbaren rein
  lokalen Abschluss bereit: bisherige AES-256-Pipeline, authentifizierte Entschlüsselung,
  zwei Recovery-Durchgänge mit je SQL- und SQLite-Restore, Schema-/Hashparität.
  Herkunftsmanifest muss erwartete Account/UUID/EU, Quellcommit, einmalige lokale
  Session-ID und Wartungsnachweis binden. Caller-Provenienz ist keine Cloudflare-
  Signatur. Fehlende Exportdatei, Netzwerkabbruch, Schemaänderung oder irgendein
  Restore-Fehler: keine Ausgabe. Nur `backup.tar.gz.gpg` und `ciphertext.sha256`
  privat herunterladen und in zwei eigene Ablagen archivieren; Schlüssel getrennt.
  Öffentlicher Hash beweist Transportintegrität, keinen unabhängigen Ursprung.
- **Abschluss:** Grant beim Anbieter widerrufen, lokale Refresh-/Access-Credentials
  und private temporäre Dateien best-effort entfernen, isolierte Umgebung löschen
  (nicht nur stoppen). Keine garantierte physische Secure-Erasure auf SSDs oder
  nach hartem Abbruch. Besitzer entscheidet separat über Wiederaufnahme des
  ursprünglichen Crons. Ein grüner Restore autorisiert weder Migration 0003 noch Deploy.

## Dashboard-Alternative

Die offizielle oben verlinkte D1-Exportanleitung beschreibt Wrangler. Ein gleichwertiger
Dashboard-Download mit überprüfbarer UUID/EU-Bindung, direkter AES-256-Verschlüsselung
und unabhängigen Restores ist damit **nicht belegt**. Eine etwaige Dashboard-SQL-
Downloadfunktion würde zunächst privaten Klartext auf dem iPhone hinterlassen.
Daher kein behaupteter sicherer Shortcut und kein Produktivtest in diesem PR.

## Offline-Verifikation der Vorbereitung

Lokal erfolgreich: **195 Python-Tests**, **152 Worker-Tests**, **12 Browser-Tests**
(iPhone/WebKit, Tablet/Chromium, Desktop/Chromium), `npm run check`, beide
Wrangler-Verträge, synthetische AES-256-Probe und `wrangler deploy --dry-run`.
Alle Daten-/API-Fälle sind synthetisch oder gemockt. Der Dry-Run veröffentlicht
nichts. GPG/GPG-Agent erben jetzt ausschließlich notwendige Basisvariablen;
Cloudflare-/GitHub-Credentials und Node-Injektionsvariablen werden nicht vererbt.

Für die lokale WebKit-Ausführung mussten fehlende Systembibliotheken temporär
unter `/tmp` ergänzt werden. Weil der Host-Cache diese nicht kennt, wurde die
Playwright-Host-Vorprüfung lokal übersprungen; **alle 12 eigentlichen Tests liefen**.
PR-CI installiert die normalen Browser-Systemabhängigkeiten unverändert mit
`playwright install --with-deps` und überspringt dort keine Prüfung.
