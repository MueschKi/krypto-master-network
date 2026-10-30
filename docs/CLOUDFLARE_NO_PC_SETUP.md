# Cloudflare Free – Einrichtung ohne eigenen PC (Phase A)

**Status:** Anleitung + separater manueller GitHub-Actions-Workflow. **Kein Deployment in diesem PR.** Nur lesende Kraken-MTF-Beobachtung, keine Paper-Konto-Migration, kein Broker/keine Echtgeld-Orders. Keine kostenpflichtige Cloudflare-Aktivierung.

## 1. Cloudflare-D1-Datenbank im Browser anlegen

1. Bei https://dash.cloudflare.com/ anmelden und das richtige Account-Konto auswählen.
2. Im Bereich **D1 SQL database** (unter Storage & databases, abhängig von Dashboard-Version) **Create database** wählen.
3. **Name genau** `kmn`. Optional EU-Jurisdiktion festlegen (vor Anlage bewusst entscheiden: regionale Datenbindung ist später nicht beliebig änderbar); ansonsten Standort nahe Europa auswählen.
4. Nach Erstellung die **Database ID (UUID)** kopieren und zunächst privat aufbewahren. **Keine** SQL-Tabellen manuell anlegen: Die zwei vorhandenen Repository-Migrationen erzeugt später der einmalig manuell gestartete GitHub-Workflow.
5. Keine persönlichen Kontodateien importieren.

## 2. Cloudflare-Account-ID und eingeschränkten API-Token vorbereiten

1. Unter **Workers & Pages → Account details** die **Account ID** kopieren. Alternativ über die globale Dashboard-Suche `Copy account ID`.
2. In Cloudflare den Bereich **Account API Tokens** öffnen, **Create Token / Custom Token** auswählen.
3. Einen dedizierten Token für dieses Repository erstellen. Benötigt **Account: Workers Scripts Edit** (bzw. entsprechende Workers-Deploy-Berechtigung) und **Account: D1 Edit** (D1-Migrationsschreibrecht), möglichst nur für das betreffende Konto und ggf. konkrete Ressourcen. **Kein globaler API-Key**, keine breitflächigen Administrator-, DNS- oder Auszahlungsrechte.
4. Token nach dem Erstellen einmal kopieren und **niemals in ein Issue, einen PR, eine Chatnachricht, Repository-Datei oder einen Screenshot** schreiben. Bei versehentlicher Offenlegung sofort widerrufen/rotieren.

## 3. Repository-Konfiguration über die GitHub-Weboberfläche

Im privaten Einstellungen-Bereich des Repositories `MueschKi/krypto-master-network` → **Settings → Secrets and variables → Actions**:

- Tab **Variables** → `CLOUDFLARE_ACCOUNT_ID` = Account ID (32 hex chars).
- Tab **Variables** → `CF_D1_DATABASE_ID` = UUID der frisch angelegten D1-Datenbank namens `kmn`.
- Tab **Secrets** → `CLOUDFLARE_API_TOKEN` = eingeschränkter API-Token.

Account-ID und D1-ID sind Kennungen, keine Zugangsschlüssel. Nur der Token ist ein Secret. **Alle Werte direkt in GitHub eingeben**, nicht im Chat senden. Nicht mit D1-`database_name` oder Cloudflare-`Zone ID` verwechseln.

## 4. Workflows zusammenführen und bewusst auslösen

Der PR stellt `.github/workflows/cloudflare-manual-deploy.yml` bereit. Der Workflow kann **erst nach bewusstem Merge** in den Default-Branch ausgewählt werden. Er läuft **niemals automatisch** bei Push, Pull Request oder Cron.

GitHub → Repository → **Actions → Cloudflare Phase A - manueller Test-Deploy → Run workflow**:
1. Branch `main` und Operation `validate` wählen. Es laufen Python-/TypeScript-/Cloudflare-Tests und **lokaler** Wrangler-Dry-Run; kein Deployment.
2. Erst nach erfolgreichen Tests, mit geprüften GitHub-Variablen/Secret und **ausdrücklichem Betreiber-Entschluss**, Operation `deploy` wählen. Der Workflow prüft die ID-Formate, erzeugt **nur im GitHub-Runner** eine temporäre Konfiguration mit der echten D1-ID, führt die D1-Migrationen mit `--remote` aus und veröffentlicht die Worker-Dateien auf einer `*.workers.dev`-Adresse.
3. Das Repository und die beiden bestehenden Paper-Konto-JSON werden **nicht** durch diesen Workflow verändert.
4. Im Action-Log die Worker-URL ablesen. Direkt nach dem ersten Deploy antwortet der Worker zunächst mit **401 / Anmeldung erforderlich**, weil noch keine Anmelde-Secrets gesetzt sind. **Nicht** aus Unsicherheit die Zugangsdaten in die URL oder in den Browser-Quellcode einfügen.

## 5. Anmeldung im Cloudflare-Dashboard setzen

Im Cloudflare-Dashboard → **Workers & Pages → krypto-master-phase-a → Settings → Variables and Secrets → Add** jeweils **Typ Secret**:

- `AUTH_USER`: ein nichtöffentliches Benutzerkürzel (z.B. `owner`).
- `AUTH_PASSWORD`: ein neu generiertes zufälliges langes Passwort von **mindestens 32 Zeichen**; kein sonst genutztes Passwort.

Nach Eingabe **Deploy** zur Aktivierung. Die App verwendet derzeit HTTP Basic über HTTPS; deshalb **kein anwendungsseitiger Logout und keine widerrufbare Sitzung**. Browser können Basic-Zugangsdaten behalten. Dies ist nur eine erste Einbenutzer-Beobachtungsoberfläche.

**Papier-Kontolesestände auf dem öffentlichen Worker bleiben absichtlich gesperrt**, selbst nach dem Login. Diese erst nach separater Authentifizierungs-/Session-Härtung freigeben; keine privaten D1-Importe in Remote-D1 durchführen.

## 6. Phase-A-Betriebs- und Free-Tier-Nachweis

1. Die HTTPS-Worker-URL im PC-/iPhone-Browser aufrufen und Basic-Zugangsdaten eingeben.
2. Startseite: `BEOBACHTUNG` / keine Orders, Systemstatus und 16 MTF-Fenster. Nach Kaltstart benötigen diese mehrere Cron-Takte; für gültige Freigabe müssen die 16 Kerzenanalysen jeweils aktuell und ohne Datenqualitätsfehler sein. Volatilitätsveto kann auch bei qualitativ guten Daten `BLOCKIERT` auslösen.
3. Dashboard → Worker → **Observability / Logs / Metrics**: CPU-Zeit je Cron und HTTP, Worker-Fehler, D1-Quoten, Speicher/Bytes, Kraken-HTTP-Fehler und ausgelassene Fenster beobachten. **10 ms CPU-Zeit/Invocation im Free-Tier** samt Sicherheitsmarge nachweisen; besonders Vollerfassung von 720 Kerzen, UTC-Tageswechsel und Fehler-/Retry-Pfad. `elapsed_ms` in D1 ist *Walltime*, kein CPU-Messwert.
4. Falls CPU/Quoten überschritten werden, **nicht** kostenpflichtig upgraden; Dienst pausieren bzw. Cron entfernen und die Arbeitsaufteilung mit Codex nachbessern.
5. Mobile PWA später auf physischem iPhone testen. Keine Rendite- oder 24/7-Verfügbarkeitsgarantie.

### Bereits vorhandene Grenzen

- Free Worker ≠ ständig laufender Python-Prozess. Ein Minutentakt ist *geplant*, nicht garantiert.
- Aktiv: öffentliche Kraken-Daten, MTF-Analyse, D1-Logs, read-only API, mobile PWA.
- **Nicht aktiv**: automatische Cloud-Paper-Käufe, Kraken-Echtgeldorders, Remote-Papierkonten, Kontoimport, Wallet-/Auszahlungsfunktionen.
- GitHub-Paper-Workflows und Originalkonten bleiben für die bisherigen simulierten täglichen Aktivitäten autoritativ.
- Kein Cloudflare-Billing-Upgrade/keine Auto-Zahlungen.

### Dokumentation

- https://developers.cloudflare.com/d1/get-started/
- https://developers.cloudflare.com/fundamentals/account/find-account-and-zone-ids/
- https://developers.cloudflare.com/workers/ci-cd/external-cicd/github-actions/
- https://developers.cloudflare.com/workers/configuration/secrets/
- https://developers.cloudflare.com/workers/platform/limits/
- https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets
