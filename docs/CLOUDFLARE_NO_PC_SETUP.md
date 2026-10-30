# Cloudflare Free ohne eigenen PC: Einrichtung über GitHub Actions

**Stand:** Phase A · read-only Kraken-MTF-Beobachtung, KEIN automatisches Cloud-Paper-Trading und KEINE Echtgeld-Orderfunktion. Dieser PR deployed **nichts**. Erst eine später bewusst gestartete GitHub Action legt D1 an oder veröffentlicht den Worker.

## Was du selbst einmalig machen musst

Das Cloudflare-Konto ist erstellt. Zur Verbindung Cloudflare ↔ GitHub wird ein **eingeschränkter API-Token** benötigt. Aus Sicherheitsgründen kann weder Codex noch der Assistent ohne eine von dir autorisierte Verbindung auf dein Cloudflare-Konto zugreifen. Niemals Tokens, Passwörter oder vollständige Secrets in Chat, Issues, PRs oder Code schreiben.

### A. Account-ID in GitHub als Variable speichern

1. https://dash.cloudflare.com/ öffnen, Cloudflare-Account auswählen, **Account ID** kopieren (32 hexadezimale Zeichen, nicht Zone ID).
2. GitHub-Repository `MueschKi/krypto-master-network` → **Settings → Secrets and variables → Actions → Variables → New repository variable**.
3. Name: `CLOUDFLARE_ACCOUNT_ID`; Wert: kopierte Account ID.

### B. Cloudflare-API-Token direkt in GitHub als Secret hinterlegen

1. Im Cloudflare-Dashboard unter **Account API tokens** → **Create Token → Custom Token**.
2. Dem Token ausschließlich für deinen ausgewählten Cloudflare-Account die Rechte geben, eine **D1-Datenbank anzulegen und deren Schema zu bearbeiten** sowie einen **neuen Workers-Script-Dienst zu erstellen und zu aktualisieren**. Bei der aktuellen Rollenoberfläche sind für die Erstanlage D1-/Workers-Produktrechte bis **Admin/Create** erforderlich. Weder DNS-/Domainverwaltung noch Account-Vollzugriff gewähren. Bereits existierende Worker können später mit einem engeren Editor-Token betrieben werden.
3. Token einmalig kopieren und unter GitHub **Settings → Secrets and variables → Actions → Secrets → New repository secret** ablegen.
4. Exakter Secret-Name: `CLOUDFLARE_API_TOKEN`; Wert: der Token. Diese Zeichenfolge ist geheim. Du musst mir nur bestätigen, dass das Secret angelegt ist – **nicht den Wert mitteilen**.
5. Erhältst du bei der Ausführung eine Berechtigungsfehlermeldung, nicht pauschal auf einen globalen API-Key wechseln; Rechte gezielt korrigieren.

**Hinweis zur Sicherheit:** Die GitHub-Workflow-Datei ist öffentlich, aber Secrets bleiben privat. Änderungen an `main` sollten vor dem Merge geprüft werden, da Workflow-Code ein Secret verwenden darf. Den ersten Einrichtungs-Token nach erfolgreicher Einrichtung durch enger berechtigte Zugangsdaten ersetzen.

## Verbindliche Sicherheitsprüfungen (nach Code-Review)

- **Free-Tarif ist eine manuelle Betreiberbestätigung, kein API-Beleg.** Vor dem Workflow im Cloudflare-Dashboard im ausgewählten Account unter **Workers & Pages → Plans / Usage** prüfen, dass **Workers Free** gilt. Die Workflow-Aktion kann diesen Tarif nicht unabhängig beweisen. Kein Paid-Upgrade ausführen.
- Für **bootstrap** oder **deploy** verlangt GitHub das zusätzliche Textfeld `free_plan_confirmation` mit dem exakten Wert **`FREE`**. Ohne ihn werden **keine** Ressourcen verändert.
- Für **deploy** ist zusätzlich das Textfeld `deploy_confirmation` mit **`DEPLOY_READ_ONLY`** erforderlich. Das ist die ausdrückliche Bestätigung, dass remote D1-Migrationen ausgeführt und die reine Beobachtungs-App veröffentlicht werden dürfen. Ein Merge allein reicht nicht.
- Der Bootstrap- und Deploy-Code prüft bei jedem Zugriff **`wrangler d1 info kmn --json`** auf nachgewiesene EU-Jurisdiktion **`eu`**. Fehlt die Detailangabe oder liegt die Datenbank außerhalb der EU, **bricht der Workflow ab**, ohne diese Datenbank für einen Deploy zu verwenden. Nicht nachträglich verschieben: D1-Jurisdiktionen sind nach der Erstellung unveränderlich.
- Die Free-D1-Größe beträgt **maximal 500 MB je Datenbank**, nicht 5 GB. Vor einem langfristigen Betrieb gilt der gesonderte [Speicher-/Retention- und Messplan](CLOUDFLARE_STORAGE_BUDGET.md). **Kein automatisches Löschen historischer Daten.**

## Bei fehlgeschlagenem D1-Bootstrap: sichere Diagnose

Falls `bootstrap` bei `wrangler d1 list --json` fehlschlägt, den Vorgang **nicht** einfach wiederholen und auch **nicht** die Token-Rechte auf Vollzugriff erweitern.

Nach Merge dieses Diagnose-Fixes: **Actions → Cloudflare Phase A - manueller Test-Deploy → Run workflow** mit `operation=diagnose` und `main`. Beide Bestätigungsfelder bleiben **leer**. Dieser Modus führt nur einen Lesezugriff auf die Token-Verifizierung, eine lesende D1-REST-Liste und gegebenenfalls `wrangler d1 list --json` aus. **Keine** Datenbankanlage, Schemaänderung oder Veröffentlichung.

Ergebnis im Job-Log `Cloudflare-Zugriff sicher diagnostizieren`:

- **TOKEN: nicht erfolgreich verifiziert** → GitHub-Secret, Tokenstatus, IP-/Ablaufbeschränkung kontrollieren; keine geheimen Werte posten.
- **TOKEN: aktiv / D1: Datenbankliste nicht lesbar** → falscher Cloudflare-Account-Scope oder fehlende **Account → D1 Read/Edit**-Berechtigung wahrscheinlich. Verwende den exakten Cloudflare-Account, dessen Account-ID in GitHub als Variable gespeichert ist. Die Diagnose zeigt nur HTTP-Status und **numerische** Cloudflare-Codes, keine vollständigen API-Antworten.
- **D1: REST erfolgreich / WRANGLER fehlgeschlagen** → Problem möglicherweise Wrangler-/Versions- oder Konfigurationsabhängigkeit. Nicht pauschal Token-Rechte erhöhen.
- **DIAGNOSE OK** → Berechtigungs- und Listenzugriff funktionieren; `bootstrap` nach eigener Freigabe separat erneut ausführen.

Nur die Fehlerzeilen bzw. einen Screenshot **ohne Token** zur Analyse weitergeben. Das GitHub-Secret `CLOUDFLARE_API_TOKEN` darf niemals im Chat oder als Logauszug mit offengelegten Geheimnissen erscheinen. Die Cloudflare-Dokumentation bestätigt `d1 list --json` als gültigen Befehl; ein nichtnuller Exit-Code ist keine ausreichende Diagnose.

## Was GitHub danach vollständig automatisch übernimmt

Nach Prüfung und bewusstem Merge von PR #13 ist in GitHub unter **Actions → Cloudflare Phase A - manueller Test-Deploy → Run workflow** die Auswahl verfügbar. Branch **main** verwenden.

1. **Operation `validate`**: führt Python-, TypeScript- und Worker-Tests und lokalen Dry-Run aus. **Keine Änderungen bei Cloudflare.**
2. **Operation `bootstrap`** (mit bestätigtem Free-Tarif, Eingabe **`FREE`**): prüft zuerst, ob Cloudflare bereits eine D1-Datenbank mit dem Namen **`kmn`** enthält. Nur falls nicht vorhanden, erstellt die Action sie mit **EU-Jurisdiktion**. Anschließend liest sie die echte Datenbank-ID über Wrangler aus und **prüft die juristische EU-Bindung anhand der Detailabfrage**. **Keine Tabellen und kein Worker-Deployment durch diese Operation.** Bei mehrdeutigem Namen oder API-Fehler wird sicher abgebrochen.
3. **Operation `deploy`** (zusätzlich **`DEPLOY_READ_ONLY`**): verwendet die bestehende `kmn`-ID, bereitet nur im temporären GitHub-Runner die Worker-D1-Konfiguration vor, spielt die zwei D1-Migrationen in die Cloud ein und veröffentlicht ausschließlich die **read-only MTF-App** auf `*.workers.dev`. **Nichts wird an den ursprünglichen Paper-Konten oder deren GitHub-Zeitplänen verändert.** Der Testbetrieb ist nicht automatisch für eine unbegrenzte Langzeitnutzung freigegeben; Speicherwachstum und CPU bleiben zu messen. Erst nach ausdrücklicher manueller Entscheidung ausführen, nicht im Rahmen des Test-PR.

Es wird **keine** GitHub-Variable `CF_D1_DATABASE_ID` mehr benötigt. Die ID ermittelt der neue Bootstrap-/Deploy-Workflow selbständig. Kein lokaler PC und keine GitHub-CLI sind erforderlich.

## Nach einem bewusst durchgeführten Deploy

1. Cloudflare Dashboard → **Workers & Pages → krypto-master-phase-a → Settings → Variables and Secrets**. Dort zwei **Worker-Secrets** anlegen:
   - `AUTH_USER`: eigenes Benutzerkürzel
   - `AUTH_PASSWORD`: neu generiertes, zufälliges Passwort mit mindestens 32 Zeichen
2. Einstellungen deployen/aktivieren. Bis diese Secrets gesetzt sind, verweigert die App **alle** Zugriffe (HTTP 401). Nur HTTPS-`workers.dev`-URL verwenden.
3. Beobachtungs-UI am PC und iPhone ausprobieren. Fehlende Zeitfenster sind als blockiert zu betrachten; die erste Gesamterfassung braucht mehrere Cron-Takte.
4. Im Cloudflare-Dashboard **Observability / Logs / Metrics** prüfen, ob Worker Scheduled-Invocations im **10-ms-Free-CPU-Budget**, D1- und Subrequest-Quoten bleiben. 720-OHLCV-Kerzen und UTC-Grenzübergänge testen. Lokale Walltime und grüner GitHub-CI-Test sind **kein** echter Free-Tier-Nachweis.
5. Bei CPU-/Quota-Überschreitung kein automatisches Upgrade. Betrieb pausieren und die Arbeitseinheiten in Codex neu aufteilen.

### Sicherheitsgrenzen

- Basic Auth hat noch keinen serverseitigen Logout und keine dedizierte Rate-Limit-Policy. Persönliche Paper-Konto-Lesestände sind auf dem öffentlichen Cloudflare-Worker **absichtlich gesperrt**; keine privaten Konto-JSONs/SQL-Dumps in D1 remote importieren.
- Kein Cloud-Paper-Trading und keine Kraken-Orders. Bestehende GitHub-Paper-Automatik bleibt alleinige Konto-Autorität.
- Der Worker ist serverlos und reagiert auf Cron; kein ununterbrochener Python- oder WebSocket-Daemon und keine garantierte minutengenaue Ausführung.
- Cloudflare-Free-Nutzung ist angestrebt, aber erst nach realen Messungen überprüfbar.

## Offizielle Dokumentation

- D1 Create/List: https://developers.cloudflare.com/workers/wrangler/commands/d1/
- GitHub Actions: https://developers.cloudflare.com/workers/ci-cd/external-cicd/github-actions/
- Rollen/Berechtigungen: https://developers.cloudflare.com/workers/authorization/
- Worker Secrets: https://developers.cloudflare.com/workers/configuration/secrets/
- Free-CPU und Quoten: https://developers.cloudflare.com/workers/platform/limits/
