# Diagnosebericht: GitHub Actions

Repository: https://github.com/MueschKi/krypto-master-network

Prüfstand: 29.10.2026, gegen 11:37 UTC

Grundlage: die zuvor in dieser Sitzung ausgeführten, ausschließlich lesenden GitHub-Abfragen. Für diesen Bericht wurde keine erneute Statusprüfung durchgeführt.

## Ergebnis

Alle drei bei GitHub registrierten Workflows waren zum Prüfzeitpunkt `active`. Kein Workflow wurde als `disabled_manually`, `disabled_inactivity` oder mit einem anderen deaktivierten Zustand gemeldet. Dennoch war kein einziger Lauf mit dem Ereignistyp `schedule` vorhanden.

| Workflow-Pfad | GitHub-Status | Konfigurierte Auslösung auf `main` |
|---|---|---|
| `.github/workflows/master-paper.yml` | `active` | Schedule täglich 04:17 und 06:47 UTC; zusätzlich manuell |
| `.github/workflows/mtf-schedule.yml` | `active` | Schedule täglich 00:37, 04:37, 08:37, 12:37, 16:37 und 20:37 UTC; zusätzlich manuell |
| `.github/workflows/mtf-tests.yml` | `active` | Pull Requests auf `main` und manuell; kein Schedule |

Der Aktivierungsstatus stammt unmittelbar aus GitHubs Workflow-API, nicht aus einer Interpretation der YAML-Dateien.

## Nachweise und Abfragen

Der gewünschte Befehl wurde erfolgreich ausgeführt:

```bash
gh workflow list --all --repo MueschKi/krypto-master-network --json name,path,state
```

Er lieferte diese drei Einträge:

```json
[
  {
    "name": "Krypto Master Network – Analyse, Paper und historische Diagnostik",
    "path": ".github/workflows/master-paper.yml",
    "state": "active"
  },
  {
    "name": "MTF – unabhängige Beobachtung",
    "path": ".github/workflows/mtf-schedule.yml",
    "state": "active"
  },
  {
    "name": "Softwaretests einschließlich Multi-Timeframe v1.5",
    "path": ".github/workflows/mtf-tests.yml",
    "state": "active"
  }
]
```

Weitere lesende Abfragen betrafen die Workflow-Metadaten, sämtliche vorhandenen Läufe, die YAML-Dateien auf dem Standardbranch, deren Commit-Historie, Repository-Metadaten und den Merge-Zeitpunkt von Pull Request #5.

```bash
gh api repos/MueschKi/krypto-master-network/actions/workflows
gh api 'repos/MueschKi/krypto-master-network/actions/runs?per_page=100'
gh api 'repos/MueschKi/krypto-master-network/actions/runs?event=schedule&per_page=100'
```

Die Schedule-Abfrage ergab:

```json
{"total_count":0,"workflow_runs":[]}
```

Die gesamte verfügbare Laufhistorie umfasste 15 Läufe: 13 mit `workflow_dispatch`, zwei mit `pull_request`. Alle waren abgeschlossen und erfolgreich. Es gab keinen vorhandenen Schedule-Lauf, dessen Job-Logs einen Fehler erklären könnten. Gelöschte Läufe lassen sich durch diese Abfrage nicht ausschließen.

## Untersuchung der fehlenden Schedule-Läufe

### master-paper.yml

- GitHub-Workflow-ID: `399893302`.
- Workflow bei GitHub angelegt: 28.10.2026, 20:47:42 UTC.
- Ursprünglicher Zeitplan: `43 3 * * *`, also täglich 03:43 UTC.
- Der Termin am 29.10.2026 um 03:43 UTC ist in der verfügbaren Laufhistorie nicht vorhanden.
- Commit `0a6653c5c93744a7ba66e55c6c02632738e2f165` vom 29.10.2026 um 05:44:44 UTC änderte den Zeitplan auf `17 4 * * *` und `47 6 * * *`.
- 04:17 UTC lag bei dieser Änderung bereits zurück. Aus dem neuen Zeitplan ergibt sich kein nachträglich zu erwartender Lauf für diesen Termin.
- Für 06:47 UTC ist ebenfalls kein Schedule-Lauf vorhanden.
- Der jüngste manuelle Lauf auf `main` startete am 29.10.2026 um 06:56:19 UTC und war erfolgreich: https://github.com/MueschKi/krypto-master-network/actions/runs/40832251384

### mtf-schedule.yml

- GitHub-Workflow-ID: `400319203`.
- Die Datei gelangte mit Pull Request #5 am 29.10.2026 um 07:26:15 UTC auf `main`.
- GitHub registrierte den Workflow um 07:26:17 UTC.
- Zeitplan: `37 0,4,8,12,16,20 * * *`.
- Der erste Termin nach dem Merge war 08:37 UTC. Bis zur Prüfung gegen 11:37 UTC war dafür kein Schedule-Lauf vorhanden.
- Die Termine 00:37 und 04:37 UTC lagen vor dem Merge; dafür war noch kein Lauf dieses Workflows auf `main` zu erwarten.
- Der manuelle Lauf auf `main` vom 29.10.2026 um 07:39:22 UTC war erfolgreich: https://github.com/MueschKi/krypto-master-network/actions/runs/40836826622

### mtf-tests.yml

Dieser Workflow besitzt keinen `schedule`-Trigger. Fehlende zeitgesteuerte Ausführungen sind hier erwartetes Verhalten. Die zwei vorhandenen Pull-Request-Läufe waren erfolgreich.

## Ursachenbewertung

| Mögliche Ursache | Bewertung anhand der erhobenen Daten |
|---|---|
| Aktuell manuell oder anderweitig deaktivierter Workflow | Ausgeschlossen für den Prüfzeitpunkt: alle drei Zustände sind `active`. |
| Frühere zeitweilige Deaktivierung | Nicht geklärt. Der aktuelle Status ist keine vollständige Änderungshistorie. |
| Schedule-Datei fehlt auf dem Standardbranch | Trifft zum Prüfzeitpunkt nicht zu: beide Dateien liegen auf `main`; `main` ist der Standardbranch. |
| Termin lag vor Einführung des Zeitplans | Erklärt die genannten frühen Termine bei MTF und den neuen Master-Termin 04:17 UTC. Erklärt nicht die übrigen fehlenden Termine. |
| Repository archiviert, deaktiviert oder Fork | Trifft nicht zu: `archived=false`, `disabled=false`, `fork=false`. |
| Automatische Abschaltung wegen 60 Tagen Inaktivität | Passt nicht: Repository erst am 28.10.2026 um 20:43:23 UTC erstellt; aktueller Status zudem `active`. |
| Fehler in einem gestarteten Schedule-Job | Kein entsprechender Lauf vorhanden. Erfolgreiche manuelle Läufe belegen die grundsätzliche Ausführbarkeit, aber keine funktionierende Schedule-Zustellung. |
| Verzögerung oder Verwerfen durch GitHubs Scheduler | Allgemein möglich; für die konkreten fehlenden Ereignisse nicht nachgewiesen. |
| Repositoryweite Actions-Einstellungen oder übergeordnete Richtlinien | Nicht vollständig prüfbar: der Lesezugriff auf die Actions-Einstellungen wurde verweigert. |

Die eindeutige Ursache für die fehlenden fälligen Schedule-Ausführungen bleibt offen. `active` bestätigt die Aktivierung, garantiert aber keine Zustellung jedes Cron-Ereignisses.

## Berechtigungsgrenze

Folgende lesende Abfrage schlug fehl:

```bash
gh api repos/MueschKi/krypto-master-network/actions/permissions
```

GitHub antwortete mit HTTP 403:

```json
{
  "message": "Resource not accessible by integration",
  "documentation_url": "https://docs.github.com/rest/actions/permissions#get-github-actions-permissions-for-a-repository",
  "status": "403"
}
```

Der verwendeten Integration fehlt für diesen Endpunkt die Repository-Berechtigung **Administration: read**. Die Berechtigungen zum Lesen der Workflow-Zustände und der Laufhistorie waren dagegen ausreichend. Die allgemeine Repository-Abfrage meldete administrative Benutzerrechte; diese ersetzen nicht die Endpunkt-Berechtigungen der verwendeten Integration.

Ein anfänglicher lokaler Netzwerkzugriffsfehler beim CLI-Aufruf wurde durch die zulässige Netzwerkfreigabe für die lesende Abfrage behoben und verhinderte die Statusprüfung nicht.

## Empfohlene nächste lesende Prüfungen

1. Mit einer Integration mit `Administration: read` die repositoryweiten Actions-Einstellungen prüfen und gegebenenfalls übergeordnete Richtlinien einsehen.
2. Nach einem weiteren fälligen Termin die Laufhistorie erneut mit `event=schedule` abfragen. Für MTF war zum Prüfzeitpunkt 12:37 UTC der nächste Termin.
3. Bei fortgesetztem Ausbleiben den GitHub-Status beziehungsweise GitHub Support mit Repository, Workflow-IDs und den fehlenden UTC-Terminen abgleichen.
4. Falls verfügbar, die Änderungshistorie der Workflow-Aktivierung auf eine frühere Deaktivierung prüfen.

Diese Empfehlungen wurden nicht ausgeführt. Es wurden keine Repository-Dateien verändert, keine Workflows gestartet, aktiviert oder deaktiviert und kein Pull Request erstellt. Der Bericht wurde zunächst separat außerhalb des Repository-Verzeichnisses erstellt und anschließend auf ausdrücklichen Wunsch in den Branch `main` übernommen.
