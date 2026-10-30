# Krypto Master Network v2.0 – Phase A

Status: lokal testbarer, isolierter Cloudflare-Prototyp zu [Issue #8](https://github.com/MueschKi/krypto-master-network/issues/8). Architektur: [PR #11](https://github.com/MueschKi/krypto-master-network/pull/11). Kein Deployment, kein Free-Tier-Nachweis und keine Paper-Migration. Die bestehende GitHub-Paper-Automatik bleibt unverändert alleiniger Kontoschreiber.

## Installation und lokale Bedienung

Voraussetzungen: Python 3.11+, Node 24, npm. Aus dem Repository:

```sh
python -m pip install -r requirements.txt
python -m unittest discover -q
cd cloudflare
npm ci
npm run check
npm test
npx playwright install --with-deps chromium webkit
npm run test:mobile
npm run db:local
```

Für die lokale Anmeldung `.dev.vars` im Ordner `cloudflare/` anlegen (gitignored): `AUTH_USER="owner"` und `AUTH_PASSWORD="..."`, jeweils auf eigener Zeile. Ein zufälliges Passwort mit mindestens 32 ASCII-Zeichen verwenden; z.B. mit `python -c "import secrets; print(secrets.token_urlsafe(32))"` erzeugen. Keine Zugangsdaten in Git, URL, Browser-Speicher oder öffentliche Screenshots schreiben. `npm run dev -- --test-scheduled` startet die App. Browser unter `http://localhost:8787` öffnen; der Browser zeigt einen HTTP-Anmeldedialog. Ohne korrekt konfigurierte Secrets sind **auch statische Assets** gesperrt.

Lokal einen Scheduler-Takt auslösen: `curl 'http://localhost:8787/__scheduled?cron=*+*+*+*+*'`. Dieser Wrangler-Test-Endpunkt ist ausschließlich Teil des lokalen Simulators, keine Worker-Steuerungs-API. Pro Aufruf wird höchstens eine fällige Coin-/Fenster-Einheit bearbeitet. Nach einem Kaltstart brauchen alle 16 Fenster mehrere Minuten/Takte; bis dahin ist die Gesamtauswertung BLOCKIERT. Keine Kurse werden erfunden, aufgefüllt oder aus alten Repository-Berichten als live übernommen.

## Oberfläche

- Übersicht: Heartbeat, zuletzt erfolgreicher Einzeljob und vier Märkte. Ein erfolgreicher Einzeljob bedeutet nicht, dass alle Märkte freigegeben sind.
- Analyse: jedes Zeitfenster mit Kerzenschluss, Berechnungszeit, Datenstatus, drei MTF-Spezialisten und Indikatoren. Gesamtfreigabe nur bei vier gültigen Fenstern; Trend-/Momentum-Einstimmigkeit und ATR-Veto entsprechen Python.
- Portfolio: zwei **optional importierte, unveränderliche Lesekopien** mit Datum, Quell-SHA-256, Cash, letztem Kontowert, Positionen, Trades und Equity-Verlauf. Keine Neubewertung mit heutigen Kursen, keine Live-Synchronisierung und keine Cloud-Buchungen.
- Historie: je letzte 100 Läufe und Analysen; alle Einträge bleiben in D1. Lücken zwischen vorhandenen UTC-Takten werden sichtbar gemacht. Vor dem ersten Lauf kann kein vorheriger Ausfall rekonstruiert werden.
- System: Version, Verbindung, letzte Fehler und ausdrücklich offener Free-Tier-Nachweis. Bei Netzwerk-/DB-Fehlern werden bestehende Anzeigeinhalte gesperrt.

Die PWA verwendet Manifest, PNG-Icons und einen Service Worker **ohne Offline-Datencache**. Auf dem iPhone nach später freigegebenem HTTPS-Deployment in Safari anmelden, Teilen → Zum Home-Bildschirm. Browser-/WebKit-Tests ersetzen keine Prüfung auf einem physischen iPhone; insbesondere Wiederanmeldung im installierten PWA-Modus ist noch real zu prüfen. HTTP Basic hat keinen anwendungsseitigen Logout und keine Sitzungsablaufsteuerung; Browser-Schließen löscht Anmeldedaten nicht zuverlässig. Für das private Einbenutzer-PoC ist ein langes zufälliges Secret über HTTPS die kostenfreie Authentifizierungsalternative zu Access. Für Mehrbenutzerbetrieb ist GitHub-OAuth mit kurzlebigen HttpOnly-Sessions eine separate Erweiterung. Keine bezahlte Access-/Domain-Einrichtung erforderlich.

## Bestehende Konten ausschließlich lesen

Optional nach lokaler DB-Einrichtung, aus `cloudflare/`:

```sh
python scripts/account_snapshot.py > private-accounts.sql
npx wrangler d1 execute kmn --local --file private-accounts.sql
```

Der Export öffnet die beiden Originaldateien **nur lesend**, ruft die bestehenden Validatoren auf, erhält alle Historien und versieht den Import mit SHA-256 und Importzeit. Die SQL-Datei ist privat und ignoriert. `INSERT` verweigert wiederholten Import statt einen vorhandenen Snapshot zu überschreiben. Das ist keine Migration autoritativer Konten. Keine Kontodaten in `public/`, CI-Artefakte oder PR-Text kopieren. Ein Remote-Import wäre nach späterer Deployment-Freigabe ein gesonderter bewusster Bedienvorgang. Auch dann bleiben GitHub-Dateien und GitHub-Automatik maßgeblich.

## Cloudflare-Einrichtung – hier nicht ausgeführt

Noch erforderlich: eigenes Free-Konto, Wrangler-Anmeldung, D1-Datenbank, private Secrets, manuell freizugebendes Deployment und echte Messungen. Keine Kreditkarte, kein Upgrade oder kostenpflichtiger Dienst ist Bestandteil dieses PRs.

1. Aktuelle Cloudflare-Free-Limits prüfen: [Workers](https://developers.cloudflare.com/workers/platform/limits/), [D1](https://developers.cloudflare.com/d1/platform/limits/), [D1-Preise](https://developers.cloudflare.com/d1/platform/pricing/).
2. Nach ausdrücklicher Deployment-Freigabe `npx wrangler login`, `npx wrangler d1 create kmn`. Die zurückgelieferte ID in einer lokalen Kopie `wrangler.local.toml` eintragen und dort dieselben Bindings/Assets/Cron konfigurieren. Die eingecheckte Null-ID ist ein Platzhalter.
3. Mit `--config wrangler.local.toml` die D1-Migrationen remote anwenden und `wrangler secret put AUTH_USER` sowie `wrangler secret put AUTH_PASSWORD` ausführen. Keine privaten Kraken-Schlüssel einrichten.
4. Erst nach Freigabe manuell deployen; dieses Repository enthält **keinen** Deploy-Workflow und kein npm-Deploy-Script. Die Konfiguration enthält einen UTC-Minuten-Cron. App auf `workers.dev` ausschließlich über HTTPS betreiben.
5. Zunächst kontrollierte Beobachtungs-/Benchmark-Abnahme: alle Fenster, Ausfälle, Authentifizierung, iPhone und Quoten prüfen. Kein automatisches Aktivieren weiterer Strategien.

## Architektur, Persistenz und Fehlerfälle

`src/mtf.ts`: öffentliche Kraken-OHLC, maximal 720 Rohkerzen, UTC-Raster, Mindesthistorie 250 abgeschlossene Kerzen, plausible positive Preise und nichtnegatives Volumen, exakte letzte erwartete Kerze. Keine Sortierung, Deduplizierung, Interpolation oder Resampling. Die ca. 720 verfügbaren Kerzen begrenzen den Rückblick (15m ca. 7,5 Tage, 1h 30 Tage, 4h 120 Tage, 1d 720 Tage); insbesondere EMA200 hat einen begrenzten Warm-up. Laufende Kerzen sind ausgeschlossen. Keine Toleranz für fehlende neueste Kerzen; auch Börsenverzögerungen sperren.

`src/scheduler.ts`: ein Symbol/Fenster pro Cron-Aufruf, längere Fenster zuerst. D1-Claim über UNIQUE-Schlüssel `(symbol,timeframe,candle_close)` mit 5-Minuten-Lease. Parallelstarts veröffentlichen nicht doppelt; Lease-Eigentümer wird bei atomarem D1-batch geprüft. Erfolgreiche Berechnungen bleiben abgeschlossen, **auch wenn das Volatilitätsveto das Signal blockiert**. Daten-/Netzfehler werden als BLOCKED samt Diagnose gespeichert und nach 30 Minuten erneut versucht. Verspätete Events >5 Minuten werden protokolliert und nicht historisch nachgerechnet; neue Takte bearbeiten nur aktuelle Abschlüsse. Netzwerk-Timeout 15 Sekunden. Laufende/abgestürzte Jobs und fehlende Heartbeats bleiben sichtbar; keine Verfügbarkeitsgarantie. Bei D1-Ausfall können Laufprotokolle nicht zuverlässig in D1 geschrieben werden; Plattform-Logs bleiben notwendig.

D1 speichert Laufjournal, Claims, Rohkerzen-Batches, Analysen und optionale private Kontolesestände. Rohkerzen werden als begrenzte JSON-Batches gespeichert, nicht 720 einzelne Schreiboperationen pro Aufruf. Veröffentlichung und Jobstatus erfolgen transaktional. API ist nur lesend: `GET /api/status`, `/api/markets` (`/api/mtf`), `/api/runs`, `/api/history`, `/api/accounts`. Alle Pfade authentifiziert, Schreibmethoden verweigert, keine Steuerungs-/Order-Endpunkte. Kein CORS-Zugriff; CSP, Frame-Schutz, HTTPS/HSTS und `no-store`. Der Worker importiert keinerlei Python-Trading-Modul und kennt keinen privaten Kraken-Endpunkt.

## Parität und tatsächlich geprüfte Grenzen

80 deterministische synthetische Fälle: vier Coins × vier Zeitfenster × Seed-150/konstant/steigend/fallend/Volatilitätsveto. `scripts/reference.py` erzeugt mit eingefrorenem UTC-Snapshot `1793232000000` die Python-Referenz gegen die unveränderten Module. Die generierte große Fixture wird nicht eingecheckt; sie wird vor jedem Test ohne Netzwerk erzeugt. Signale exakt gleich; getestete Toleranz `abs(TS−Python) <= 1e-10 * max(1,abs(Python))`. Gemessen: maximale absolute Abweichung `9.947598300641403e-14`, skalierte Abweichung `9.947598300641404e-16`. EMA-Saat am ersten Schluss; RSI am ersten Delta; ATR am ersten True Range, Wilder 1/14; MACD 12/26/9; EMAs 20/50/200 und Veto >10 % unverändert. Keine belegte Parität der zwölf Master-Spezialisten – diese wurden nicht portiert.

Lokal geprüft: TypeScript, Worker-Ausführung in workerd/Miniflare, echte lokale D1-Migrationen und SQL-Transaktionen, Idempotenz/Parallelität, verspätete Takte, Kraken-Fehlerfakes, Netzunterbrechung, Auth/Schreibschutz, Datenfrische und Kontobytes beim Export. `wrangler deploy --dry-run` baut lokal und deployt nicht. `elapsed_ms` ist **Walltime**, `cpu_ms:null` bedeutet ungemessen. Ein lokaler Test ist **kein** Free-Tier-Nachweis.

Vor echter Abnahme pro Invocation mindestens 10-ms-CPU-Budget mit Sicherheitsmarge, 128 MB, Subrequests, täglich 100.000 Requests sowie D1-Zeilen-/Speicherquoten prüfen. Maximal zwei öffentliche Kraken-Requests pro Arbeitseinheit (Marktstatus und OHLC); regulär ca. 500 fällige Marktjobs/Tag und 1.440 Cron-Takte, bei Störungen mehr Versuche bis maximal ein Job/Takt. Hinzu kommen UI-Abfragen (fünf pro Minute und offenem Client) und D1-Reads. Abschätzungen sind keine Messwerte. Indizes begrenzen Tagesjob-Suchen und Statusabfragen. Rohkerzen und Historie wachsen: tatsächliche Bytes/Tag messen, vor Erreichen der Free-Datenbankgrenze exportieren und einen separat überprüften Aufbewahrungsplan festlegen. Kein stilles Löschen von Auditdaten. Kein unbegrenzter kostenloser Langzeitbetrieb zugesagt.

Für den echten Test Workers-Observability verwenden, CPU-Zeiten der Scheduled Invocations, Fehler (insbesondere CPU-Limit), Subrequests, Speicher-/D1-Quoten und warm/kalt getrennt protokollieren. Repräsentativ 720 Kerzen und Ausfälle testen, nicht nur Mittelwerte. Falls 10 ms nicht sicher unterschritten werden: Arbeit weiter zerlegen oder Free-Betrieb als nicht nachgewiesen ablehnen; niemals still auf Paid upgraden. Diese Messungen sind ohne Nutzerkonto und autorisiertes Deployment **offen**.

## Spätere Phasen

Issue #9: Master-Spezialisten portieren und vergleichen; separat Backup/Hash-/History-Validierung, Shadow-Betrieb, Ledger/Fixed-Point, atomare Buchungen, genau ein Schreiber und expliziter Cutover. GitHub-Automatik erst nach Freigabe umschalten. Keine rückwirkenden Fills zu heutigen Kursen.

Issue #10: separate spätere Sicherheitsprüfung und ausdrückliche Freigabe. Phase A enthält weder Echtgeldadapter noch Order-, Wallet- oder Auszahlungsfunktionen.

## Lokales Prüfprotokoll (30.10.2026)

- Python 3.12: **98 Tests erfolgreich**, einschließlich aller 97 bisherigen Tests und zusätzlichem bytegetreuen Kontoschutz beim Export.
- TypeScript: `npm run check` erfolgreich.
- Cloudflare-Testintegration / workerd / D1: **112 Tests erfolgreich**, darunter 80 Python-Paritätsfälle, Markt-/Kerzenvalidierung, atomare Rohdatenpersistenz, Wiederanlauf abgelaufener Claims, Parallelstarts, Cron-Handler, Authentifizierung von Assets/API, Schreibsperre und DB-/Netzausfall.
- `npm audit`: **0 bekannte Schwachstellen**, einschließlich Entwicklungsabhängigkeiten (Momentaufnahme, keine Garantie für zukünftige Meldungen).
- `wrangler deploy --dry-run`: lokaler Build erfolgreich; kein Upload/Deployment.
- Git-Diff-Prüfung: bestehende Python-Dateien, beide Kontodateien, alle vorhandenen daten/-Ergebnisse und drei bisherigen Workflows unverändert gegenüber der Ausgangsbasis. Die separat ergänzte CI führt nur Tests und einen lokalen Build aus.
- Kein echter Cloudflare-Free-, Speicher-, CPU- oder Remote-Cron-Nachweis. Kein physischer iPhone-/installierter-PWA-Nachweis.

- Playwright: **9/9 Browserprüfungen erfolgreich** (iPhone/WebKit 390×844, Tablet/Chromium 768×1024, Desktop/Chromium 1440×1000). Geprüft: Navigation, kein horizontaler Überlauf, Verbindungsabbruch, fehlende Imports und Text-/XSS-Sicherheit bei gefüllten Analysen. WebKit-Systembibliotheken wurden nur unter `/tmp` ergänzt; wegen des systemweiten ldconfig-Prüfers wurde die Host-Vorabprüfung übersprungen, die echten Browserprüfungen wurden vollständig ausgeführt. CI installiert die Bibliotheken regulär mit `playwright install --with-deps`.
- Wrangler-D1-Migration und Import beider privaten Lesestände zusätzlich über die dokumentierten **lokalen** CLI-Befehle erfolgreich ausgeführt; keine Remote-Datenbank verbunden.
