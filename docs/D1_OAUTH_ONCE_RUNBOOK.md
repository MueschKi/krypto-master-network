# Einmaliges KMN-Backup mit Cloudflare OAuth (iPhone/Codespaces)

**Status: Code in PR #31 zur Prüfung; bis Merge keine Produktivaktion.** Dieses Programm ersetzt **nicht** die gesperrte D1-Read-Vollsicherung und ändert **nicht** den bestehenden GitHub-D1-Read-Token. Es darf nur von einer Person in einem eigenen isolierten Codespace mit interaktivem Terminal gestartet werden. Keine automatische Anmeldung, kein Auto-Merge, kein Deploy, keine Migration und keine Orders.

## Warum dieser Weg?

Der bestehende tokengebundene native D1-Export wurde von der Export-API abgewiesen (`CF=10000`). Die D1-Read-SQL-Abfrage funktioniert, ergibt aber keinen über mehrere Requests garantierten vollständigen Snapshot. Der **native D1-Export mit persönlichem Cloudflare-OAuth** ist deshalb ein einmaliger alternativer Weg, dessen Berechtigung und Funktionsfähigkeit erst beim ausdrücklich autorisierten Online-Lauf bestätigt werden können.

**Wrangler 4.156.0 bietet nur `d1:write` für D1; `offline_access` wird beim Device-Grant intern mitangefordert.** Diese Berechtigungen können deutlich mehr als einen Export; du hast sie für den **einmaligen Export** ausdrücklich akzeptiert. Die Einwilligung zur Codierung bedeutet **nicht**, dass der Export oder eine Datenbankmigration schon stattgefunden hat. Der eingegrenzte `--scopes d1:write`-Parameter begrenzt die angefragten Scopes, **nicht** die Rechte auf eine einzelne D1-UUID. Prüfung des Cloudflare-Zustimmungsdialogs bleibt entscheidend.

## Auf dem iPhone

0. **Vorbereitung:** Prüfe unter GitHub → Settings → Billing & licensing das Codespaces-Kontingent und ggf. Kostenbudget. Codespaces kann auch im Stoppzustand Speicher berechnen; keinen Codespace erstellen, wenn Kostenfreiheit erforderlich, aber nicht bestätigt ist.
1. Nach **Review, grünen Tests und bewusstem Merge** dieser Änderung: GitHub-Repository → **Code → Codespaces → Create codespace on main**. Wenn du bereits eine isolierte Umgebung hast, kannst du diese nach Prüfung verwenden. Codespace und Terminal nicht öffentlich teilen, keine Portfreigaben.
2. Öffne in VS Code Web die Befehlspalette → **Tasks: Run Task**. Wähle zuerst **D1: 0 Gepinnte Werkzeuge installieren**. Das führt nur `npm ci` im Ordner `cloudflare` aus und hat keinen Cloudflare-Zugriff.
3. Stelle den bestehenden Cloudflare-Worker-Cron kontrolliert aus; stelle sicher, dass keine ausstehenden Ausführungen, Queues, manuellen D1-Schreiber oder anderen Nutzer-Sessions mehr schreiben. Kontrolliere die Wirkung, **nicht nur den Klick**. Notiere den bisherigen Cron-Status. Das Programm verändert den Cron nicht.
4. Wähle dann **D1: 3 Einmal-Backup (OAuth, manuelle Freigabe)**. Hier musst du in einem privaten interaktiven Terminal exakt die geforderten Bestätigungswörter selbst eintippen. Die Codespace-Umgebung muss `CODESPACES=true` oder `CODESPACE_NAME` besitzen und der Repo-Branch muss `main` sein.
5. Nach der Wartungsbestätigung startet **Wrangler Device Login**, ausschließlich mit `--scopes d1:write`. Es zeigt `https://dash.cloudflare.com/oauth2/device` und einen kurzlebigen Code im **privaten Terminal**. Öffne die Cloudflare-Seite in Safari, prüfe den Account und die Berechtigungen und erteile dort persönlich die Freigabe. **Keinen Gerätecode, Token oder Passwort an ChatGPT/GitHub-Issues senden**.
6. Erst nach authentifizierter Cloudflare-GET-Detailprüfung auf **dieses vorhandene Konto**, **diese D1 UUID**, **Name `kmn`** und **`jurisdiction=eu`**, fordert der Task eine **zweite separate Freigabe zum eigentlichen Export**. Bei fehlendem Nachweis bricht er ab. Für den Export wird die dokumentierte native Wrangler-Funktion verwendet; sie kann D1-Anfragen vorübergehend blockieren.
7. Bei einem erfolgreichen Export fordert das Programm **zweimal deine mindestens 32 Zeichen lange Backup-Passphrase aus dem Passwortmanager** ohne Echo an. Es erstellt ausschließlich nach erfolgreichem SQL-Import, AES-256-Verschlüsselung und **zwei frischen unabhängigen Recovery-Durchgängen** die privaten Dateien:
   - `.kmn-oauth-backup-private/backup.tar.gz.gpg`
   - `.kmn-oauth-backup-private/ciphertext.sha256`
8. Lade **nur diese beiden Dateien** privat herunter und sichere sie an **zwei** getrennten geschützten Orten. Passwortmanager-Passphrase **getrennt** aufbewahren; ohne diese ist die Sicherung nicht wiederherstellbar. Keine Klartext-SQL-Dateien herunterladen oder in GitHub committen. Der Ausgabeordner ist per `.gitignore` ausgeschlossen, aber das allein ist **kein** Zugangsschutz.
9. Der Task versucht auch bei Fehlern `wrangler logout`, was laut Cloudflare OAuth-Zugangsdaten widerruft. Prüfe zusätzlich <https://dash.cloudflare.com/profile/authorizations> und widerrufe verbleibende Wrangler-OAuth-Autorisierungen. **Lösche anschließend den gesamten Codespace**, nicht bloß stoppen; der Runner-Bereich wird best-effort bereinigt und nicht garantiert physisch sicher gelöscht.
10. Wenn nichts mehr auf die DB zugreift und du die Sicherung verifiziert hast, kannst du den ursprünglich notierten Cron wieder aktivieren. Ohne aktuellen Datenstand-/Versionsabgleich autorisiert auch dieser erfolgreiche Export **keine** Migration 0003 oder Worker-Deployment.

## Sicherheitsgrenzen

- Das Tool erstellt keine Cloudflare-Ressourcen, verändert keine D1-Daten, und startet keinen Worker-Deploy/Handel. Es verwendet ein eigenständiges temporäres Wrangler-OAuth-Verzeichnis und übergibt keine Codespace-/GitHub-Secrets an Wrangler. Die OAuth-Device-Code-Ausgabe erscheint ausschließlich im privaten interaktiven Terminal.
- Der OAuth-Token wird nur flüchtig im Python-Prozess für die *offizielle lesende D1-Metadatenabfrage* benutzt; ein unerwarteter Authentifizierungstyp oder eine Weiterleitung blockiert. Keine rohe API-Antwort wird angezeigt.
- Nach dem Export muss der volle SQL-Export importierbar sein, alle erwarteten Schemata enthalten und positive Historie haben. Die bestehende GPG-Pipeline prüft Datenparität und zwei SQL-/SQLite-Restores. Bei Abweichung keine Backupdateien.
- Die Schreibpause wird vom Besitzer separat kontrolliert und bestätigt; das Programm kann externe Cloudflare-Schreibquellen **nicht** unabhängig endgültig ausschließen. Der native Cloudflare-Export bietet eine eigene konsistente Exportfunktion, aber eine menschliche Wartungsbestätigung ist kein technischer Snapshot-Beweis für andere Zugriffspfade.
- Der Export enthält bei normaler Durchführung Klartext nur kurzzeitig auf dem isolierten Codespace-Dateisystem und anschließend im flüchtigen Archivierungspfad. Temporäre Dateien werden best-effort entfernt. Keine physische Secure-Erasure-Garantie.
- Eine erfolgreiche Anmeldung garantiert keinen erfolgreichen Export. Bei Export-Autorisierung, Größenlimit, fehlender EU-Zuordnung, Quoten-/Netzwerkfehler oder fehlgeschlagener Recovery: **Abbruch ohne Backup-Erfolg**. Keine automatische Scope-Erweiterung.

**Quellen:** [Wrangler Login und Logout](https://developers.cloudflare.com/workers/wrangler/commands/general/), [Cloudflare OAuth-Zugriffe widerrufen](https://developers.cloudflare.com/fundamentals/oauth/authorizing-an-application/), [D1 Import/Export](https://developers.cloudflare.com/d1/best-practices/import-export-data/).
