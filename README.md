# Krypto Master Network – v2.0 Phase A / Python v1.5.2

**Neu: isolierter Cloudflare-Phase-A-Prototyp** in [`cloudflare/`](cloudflare/): TypeScript Worker, UTC-Cron, D1, geschütztes dunkles Dashboard und mobile PWA. Lokal testbar, **nicht deployed; Cloudflare-Free-CPU-Budget noch nicht praktisch nachgewiesen**. Bestehende Python-Handelsmodule, Kontodateien, Berichtspfade und Paper-Workflows bleiben erhalten.

Installation, Anmeldung, Betrieb, iPhone-Nutzung, optionale reine Kontolesestände und offene Abnahmen: [Phase-A-Anleitung](docs/PHASE_A.md). Die folgende Dokumentation beschreibt weiterhin den bestehenden Python-Betrieb. [Repository-Prüfung und erhaltene Strukturen](docs/REPOSITORY_AUDIT_PHASE_A.md).


**Forschungs- und Paper-Trading-System für BTC/EUR, ETH/EUR, SOL/EUR und NEAR/EUR. Nur virtuelle Konten; keine echten Orders, keine Gewinngarantie und kein nachgewiesener Handelsvorteil.**

**Aktueller Stand (29.10.2026):** v1.5.2 auf `main`, 97 automatisierte Tests im [GitHub-CI-Lauf](https://github.com/MueschKi/krypto-master-network/actions/runs/40887673658) erfolgreich. Ein automatischer Paper-Lauf über `schedule` wurde am 29.10.2026 um 13:45 UTC [bestätigt](https://github.com/MueschKi/krypto-master-network/actions/runs/40884879154); für die unabhängige MTF-Automatik ist bisher nur ein manueller Erfolg belegt. Geplante GitHub-Zeiten sind **keine garantierten Ausführungszeitpunkte**.

## Auf einen Blick

| Modul | Funktion | Ergebnis |
|---|---|---|
| Master-Netzwerk | Zwölf regelbasierte Spezialisten auf abgeschlossenen 1d-Kerzen | `NETZWERK.md` |
| Original-Paper-Konto | Unveränderte Entry-Regeln, 7-%-Tagesschluss-Stopp | `TRADING_STATUS.md` |
| ATR-Trailing-Paper-Konto | Gleiche Entry-Regeln, 2,5× ATR14-Trailing-Stopp | `TRAILING_STATUS.md` |
| Kontovergleich | Zwei unabhängige virtuelle Startkonten à 1.000 € | `VERGLEICH_MASTER.md` |
| MTF-Beobachtung | 1d / 4h / 1h / 15m, **ohne** Einfluss auf beide Paper-Konten | `ZEITFENSTER.md` |

Die beiden Konten sind weiterhin getrennt. Zum dokumentierten Stand vom 29.10.2026 enthalten sie jeweils **1.000 € und null Trades**; letzter verarbeiteter UTC-Börsentag ist der **28.10.2026**. Kontowerte und Signale ändern sich nur nach einem tatsächlich erfolgreich veröffentlichten Lauf.

## Architektur

```text
                     Kraken (öffentlich, ohne Zugangsdaten)
                        /                     \
             1d-OHLCV-Daten              1d/4h/1h/15m-OHLCV
                    |                            |
             12 Spezialisten              Trend / Momentum / ATR
                    |                            |
             Master + Risiko-Veto           MTF-Beobachtung
                    |                            |
              9 Entry-Prüfungen          ZEITFENSTER.md + JSON
                    |
             Öffentliche Bid-/Ask-Quotes
                    |
         +----------+----------+
         |                     |
   Paper-Konto 7 %       Paper-Konto ATR 2,5x
   Tagesschluss-Stopp    Trailing-Schlusskurs-Stopp
         |                     |
   TRADING_STATUS.md      TRAILING_STATUS.md
         +----------+----------+
                    |
           VERGLEICH_MASTER.md

    Nur Simulation. Echtgeld-Orderadapter dauerhaft gesperrt.
```
## Spezialisten

- Datenqualität und Frische
- Trendanalyse (täglich / abgeschlossene Wochenkerzen)
- Preisstruktur und Breakouts
- Momentum (RSI/MACD)
- Volumen (u.a. OBV)
- Volatilität (ATR/Bollinger)
- Marktphasen (ADX)
- Support/Resistance
- Setup / theoretisches Chance-Risiko-Verhältnis
- Relative Stärke im Krypto-Korb
- Orderbuch/Spread (derzeit optional im Analysemodul, Paper-Engine prüft öffentlichen Spread zwingend)
- Übergeordnete Risikokontrolle

**Wichtig:** Auch zwölf unterschiedliche Module schaffen keine zwölf unabhängigen Datenquellen. Die meisten Signale beruhen auf denselben OHLCV-Kursen. Der Master verwendet feste, dokumentierte Bedingungen statt eine erfundene KI-„Sicherheit in Prozent“.

## Trading-Logik der zwei Paper-Konten

Beide Konten erhalten dieselben Master-Kaufsignale, führen jedoch ihre Stop-Strategie **unabhängig** aus. Das Original verwendet einen festen **7-%-Tagesschluss-Stopp** relativ zum Einstieg; der Vergleich verwendet einen **2,5× ATR14-Trailing-Stopp**, dessen Schwelle nur auf Basis abgeschlossener Kerzen nachgezogen und niemals abgesenkt wird. Beide Stopps sind **keine** Börsenaufträge und werden erst beim nächsten erfolgreichen Tageslauf geprüft.

- Der Master lässt nur einen technisch begründeten **Kaufkandidaten** zu, wenn die Risiko- und Datenqualitätsprüfung OK ist.
- Die getrennte Paper-Engine verarbeitet **BUY / SELL / HOLD / BLOCK**, niemals echte Börsenorders.
- Bestehende Positionen werden bei Master-Einstufung `SCHWACHER MARKT` oder einem **7-%-Tagesschluss-Stopp** am nächsten erfolgreichen Bot-Durchlauf zum aktuellen Orderbuchpreis simuliert verkauft.
- Ein Kauf verwendet höchstens 12 % des aktuellen Kontowerts je Coin. Gesamtexposure maximal etwa 45 %, zusätzlich begrenzt durch nominales Anfangskapital; mindestens 300 € EUR-Reserve.
- Nach einem Drawdown von 12 % vom bisher erreichten Depot-Hoch **dauerhafte Sperre weiterer Käufe bis zur manuellen Prüfung**. Bestehende Positionen können weiterhin verkauft werden.
- Gebührenannahme 0,4 % je Ausführung; zusätzliche modellierte Slippage 0,1 % gegenüber Bid/Ask. Mindestorder 15 €.
- Portfolio: nur Spot-Käufe/Verkäufe, **kein Shorting, keine Hebel, keine Kreditaufnahme**.
- Derselbe abgeschlossene UTC-Handelstag wird in jedem Konto höchstens einmal verarbeitet. Paper-Läufe sind über eine eigene Concurrency-Gruppe serialisiert; MTF und Paper können parallel laufen. Die sichere Veröffentlichung erkennt Änderungen am Konto und schützt vor Konflikten.
- Für aktuelle Paper-Signale ist **exakt die vollständig abgeschlossene UTC-Tageskerze des Vortags** erforderlich. Fehlende, doppelte, unsortierte, unplausible oder veraltete Rohdaten blockieren den Lauf; keine Preisersatzwerte, kein Auffüllen.

Der öffentliche Bid-/Ask-Snapshot ist keine Garantie für ausführbare Mengen oder Preise. Die Engine berücksichtigt weder vollständige Orderbuchtiefe noch echte Teilausführungen oder Börsenrestriktionen. Ohne dauerhaft laufenden Dienst ist dies keine durchgehende Stop-Überwachung. Tagesbasierte Kurslücken können zu erheblich größeren Verlusten führen. **Diese Grenzen schließen einen verantwortbaren Echtgeldbetrieb der aktuellen Version aus.**

## Betriebsarten

```bash
python -m pip install -r requirements.txt
python -m unittest discover -q   # vollständige Testsuite, Stand v1.5.2: 97 Tests
python trading.py demo        # künstliche Kurse, getrennte DEMO_TRADING.md
python trading.py analyse     # echte öffentliche Daten, ohne Transaktion
python trading.py paper       # echte öffentliche Daten, NUR simulierte Orders
```

`paper` benötigt **keine Zugangsdaten**: der Kursabruf verwendet ausschließlich öffentliche Kraken-Schnittstellen. Keine Börsenkonten und keine Wallets verbinden. **Wichtig:** Im Normalbetrieb müssen die beiden bestehenden, gültigen Kontodateien vorhanden sein. Sind sie gelöscht oder beschädigt, bricht der Lauf vor dem Netzwerkzugriff ab; es wird kein neues 1.000-€-Konto erzeugt. Eine ausdrücklich angeforderte Initialisierung ist ausschließlich für **neue** Konten vorgesehen und darf niemals zur Wiederherstellung einer vorhandenen Historie verwendet werden.

## Ergebnisse

- `TRADING_STATUS.md`: Original-Paper-Konto mit festem 7-%-Stopp.
- `TRAILING_STATUS.md`: separates Paper-Konto mit ATR-Trailing-Stopp.
- `VERGLEICH_MASTER.md`: gemeinsamer Vergleich der beiden simulierten Konten.
- `NETZWERK.md`: die zwölf Spezialanalysen für BTC, ETH, SOL und NEAR.
- `daten/master_paper_state.json` und `daten/master_trailing_state.json`: **zwei verbindliche, getrennte Kontodateien** einschließlich Trade- und Equity-Historie. Nicht löschen, zurücksetzen oder manuell verändern.
- `daten/netzwerk_analysen.json`: alle Einzelwerte maschinenlesbar.
- `ZEITFENSTER.md` und `daten/zeitfenster_analysen.json`: unabhängige MTF-Beobachtung, keine Handelsfreigabe.
- `DEMO_TRADING.md`: nur künstliche Demo, nicht Teil des produktiven Kontos, per `.gitignore` ausgeschlossen.

Kursdaten nur von **abgeschlossenen 1d-Kerzen**. Die Kraken-OHLC-Schnittstelle ist auf ca. 720 Kerzen begrenzt.

## Automatische tägliche Ausführung

Der Workflow [master-paper.yml](.github/workflows/master-paper.yml) ist auf `main` täglich für **04:17 und 06:47 UTC** geplant. Geplante `schedule`-Ereignisse verwenden automatisch den Modus `paper`; bei einem **manuellen** Start über **Actions → Run workflow** ist dagegen `demo` voreingestellt und `paper` muss ausdrücklich gewählt werden. Vor der Berechnung läuft die vollständige Testsuite. Ergebnisse und beide Kontodateien werden im Paper-Modus zunächst als GitHub-Artifact (7 Tage) gesichert; die Veröffentlichung auf `main` erfolgt danach über `paper_publish.py` mit Allowlist, Konfliktprüfung und bis zu drei normalen Fast-forward-Versuchen. Bei einer zwischenzeitlichen Kontoänderung bricht der Publisher ab, statt neuere Zustände zu überschreiben. Ein fehlgeschlagener Push ist als Workflow-Fehler sichtbar.

**Belegter Betriebsstand:** Am **29.10.2026 um 13:45 UTC** lief das Paper-Workflow-Ereignis `schedule` erfolgreich ([GitHub-Lauf](https://github.com/MueschKi/krypto-master-network/actions/runs/40884879154)); dies war noch **vor** dem Merge von v1.5.2. Der Lauf aktualisierte die Berichte, ohne einen neuen Handelstag zu buchen. Die v1.5.2-Persistenz wird erstmals bei einem späteren Lauf auf `main` produktiv erprobt. GitHub kann geplante Läufe verzögern oder auslassen: ein aktivierter Workflow beweist nicht die Zustellung jedes Cron-Ereignisses.

## Echtgeld-Schnittstelle

`trade_broker.LiveExchangeAdapter` ist eine **absichtlich gesperrte Schnittstelle**. Sowohl das Erzeugen des Adapters als auch `place_order` werfen `PermissionError`. Es gibt **keinen Schalter, keine API-Key-Konfiguration und keinen ausführbaren Echtgeld-Orderpfad**. Eine spätere Implementierung wäre ein eigenes Projekt mit getrennten Zugangsdaten, manueller Freigabe, zusätzlichen Sicherheitsprüfungen, Monitoring und unabhängiger Validierung.

## Nutzung

Auf dem iPhone das [Repository](https://github.com/MueschKi/krypto-master-network) in Safari öffnen (bei Bedarf **Desktop-Website anfordern**). Unter **Actions** den gewünschten Workflow auswählen und die Läufe beziehungsweise **Run workflow** öffnen. Die Ergebnisdateien sind anschließend unter **Code** und gegebenenfalls als Artifact im Workflow-Lauf verfügbar. Für den normalen Betrieb müssen keine Dateien manuell hochgeladen werden.

## v1.5: Multi-Timeframe-Beobachtung

Die neue, isolierte Analyse beobachtet BTC/EUR, ETH/EUR, SOL/EUR und NEAR/EUR auf
**1d, 4h, 1h und 15m**. Sie übergibt keine Signale an die beiden Paper-Konten.
Trading-Regeln, tägliche Paper-Läufe und Echtgeldsperre bleiben unverändert.

```bash
python mtf_analysis.py demo     # offline, deterministisch, künstliche Kurse
python mtf_analysis.py analyse  # nur öffentliche Kraken-Spotdaten, ohne Schlüssel
python -m unittest discover -q
```

Demo schreibt ausschließlich `DEMO_ZEITFENSTER.md` und `DEMO_ZEITFENSTER.json`
(beide ignoriert); Analyse schreibt `ZEITFENSTER.md` und
`daten/zeitfenster_analysen.json`. Ein BLOCKIERT-Bericht ist ein gültiges
Diagnoseergebnis und wird gespeichert, damit alte gültige Berichte nicht irreführen.
`OK` im Bericht bezeichnet nur die Freigabe der Datenprüfung, keine Kaufempfehlung.

`mtf_data.py` prüft Datenqualität und ruft mit injizierbarem Exchange höchstens
16 OHLCV-Abfragen mit Limit 720 sequenziell ab (Rate-Limit aktiv, 20s Timeout,
keine Wiederholungen). `mtf_trend.py`, `mtf_momentum.py` und `mtf_volatility.py`
berechnen EMA20/50/200, RSI14/MACD12/26/9 und ATR14. `net_timeframe_bot.py`
führt diese Beobachtungen zusammen; `mtf_analysis.py` schreibt die Berichte.

POSITIV/NEGATIV erfordern gleichgerichteten Trend und Momentum. ATR14 über
10 % des Schlusskurses blockiert als transparente Heuristik. Die Cross-Timeframe-
Auswertung verlangt Einstimmigkeit aller vier Fenster für POSITIV/NEGATIV;
gemischte Einstufungen ergeben NEUTRAL, jede Datensperre ergibt BLOCKIERT.
Widersprüche werden separat genannt. Es gibt keine Prognoseprozente.

Ausschließlich abgeschlossene Kerzen werden anhand UTC-Start plus exakter Dauer
verwendet; die Snapshot-Zeit wird vor dem Abruf eingefroren. Fehlende, veraltete,
doppelte, unsortierte oder unplausible Daten sowie NaN/inf blockieren. Nichts wird
aufgefüllt oder sortiert. Mindestens 250 abgeschlossene Kerzen sind erforderlich.
Die jüngste laut UTC-Raster erwartete Kerze muss vorhanden sein; auch kurze
Veröffentlichungsverzögerungen bei Kraken führen deshalb zu einer Sperre.

Kraken begrenzt OHLC auf etwa **720 Kerzen**: 15m ca. **7,5 Tage**, 1h ca.
**30 Tage**, 4h ca. **120 Tage**, 1d ca. 720 Tage, abzüglich laufender Kerze.
EMA/RSI/ATR sind rekursiv mit begrenztem Warm-up initialisiert; insbesondere
EMA200 hängt von der verfügbaren Historie ab. Fenster schließen unterschiedlich
und überlappen, sind also keine unabhängigen Beweise. Kein Intraday-Backtest.
Alle Zeitangaben sind **UTC**; Deutschland liegt im Winter eine, im Sommer zwei
Stunden davor. Indikatorwerte sind Beobachtungen historischer Kurse.

### Start und Berichte auf dem iPhone

1. Repository in Safari öffnen, bei Bedarf „Desktop-Website anfordern“.
2. **Actions → Krypto Master Network → Run workflow** öffnen.
3. Branch `main` und `mtf-demo` oder `mtf-analyse` wählen. Alternativ direkt den unabhängigen Workflow **MTF – unabhängige Beobachtung** manuell starten; dieser führt die echte öffentliche Beobachtung aus.
4. Den Lauf öffnen: Zusammenfassung und das Artefakt `multi-timeframe-berichte`
   enthalten die Markdown-/JSON-Dateien. Artefakte benötigen GitHub-Anmeldung.
5. Nur `mtf-analyse` auf `main` speichert die beiden Ergebnisdateien sicher auf
   `main`; Nebenbranches liefern ausschließlich Summary und Artifact. Danach lässt sich `ZEITFENSTER.md` direkt unter **Code** lesen.
   Demo committet nichts. Für die reine Beobachtung nicht `paper` auswählen.

Die Cron-Zeiten **04:17 und 06:47 UTC** verwenden weiterhin ausschließlich `paper`.
Es sind keine neuen Secrets, Wallets oder Exchange-Zugangsdaten nötig.


## v1.5.1: Unabhängiger MTF-Zeitplan und Betriebsdiagnose

[mtf-schedule.yml](.github/workflows/mtf-schedule.yml) läuft unabhängig vom
Paper-Workflow auf einem Standard-GitHub-Runner. Cron: `37 0,4,8,12,16,20 * * *`.
Die geplanten Zeiten liegen 37 Minuten nach den 4h-Kerzengrenzen:

| Workflow | UTC (täglich) | Deutschland MEZ (Winter) | Deutschland MESZ (Sommer) |
|---|---|---|---|
| MTF | 00:37, 04:37, 08:37, 12:37, 16:37, 20:37 | 01:37, 05:37, 09:37, 13:37, 17:37, 21:37 | 02:37, 06:37, 10:37, 14:37, 18:37, 22:37 |
| Paper | 04:17, 06:47 | 05:17, 07:47 | 06:17, 08:47 |

Das sind **sechs Snapshots pro Tag**, keine fortlaufende 15-Minuten-Überwachung.
Die UTC-Termine bleiben bei der Zeitumstellung gleich. Die Paper-Ausführung
verarbeitet weiterhin zwei getrennte Konten, jeden UTC-Handelstag höchstens
einmal; es gibt keine zusätzlichen Paper-Läufe oder neue Trading-Regeln.

### Ablauf und sichere Speicherung

Nach `pip install -r requirements.txt` und der gesamten Testsuite
(`python -m unittest discover -q`, einschließlich `test_mtf` und
`test_mtf_schedule`) startet der Wrapper ausschließlich
`python mtf_analysis.py analyse`. Er entfernt zuvor nur die beiden alten
MTF-Ergebnisdateien, prüft Snapshot-Zeit und Übereinstimmung von Markdown/JSON
und legt das neue Berichtspaar separat im Runner-Temp-Verzeichnis ab.
Fehlende Kraken-Daten liefern einen neuen, ausdrücklich **BLOCKIERT** markierten
Diagnosebericht. Er wird ebenso gespeichert wie ein OK-Bericht; alte OK-Daten
werden nicht als neuer Snapshot ausgegeben. Ein CLI-Absturz, Timeout oder
ungültiger Bericht erzeugt eine neue BLOCKIERT-Fehlerdiagnose und einen roten Job,
aber keinen Report-Commit. Fehlgeschlagene Installation/Tests verhindern die
Analyse; das Summary meldet, dass kein neuer Snapshot vorliegt.

Markdown und JSON stehen im Job Summary beziehungsweise im Artifact
`mtf-snapshot-<run_id>-<run_attempt>` bereit (Aufbewahrung **7 Tage**).
Das Artifact wird vor dem Push hochgeladen und bleibt bei GitHub-Schreibfehlern
erhalten. Bei abgebrochenem Runner oder gestörter Artifact-Schnittstelle kann
auch dieser Upload ausfallen; der Job meldet fehlende Dateien als Fehler.

Nur Läufe auf `main` veröffentlichen Berichte auf `main`. Der Publisher
`mtf_snapshot.py` verwendet einen separaten temporären Git-Worktree und committet
**ausschließlich** `ZEITFENSTER.md` und `daten/zeitfenster_analysen.json`, nur bei
Änderungen. Er holt vor jedem Push das aktuelle Remote-main und baut den
Berichtscommit darauf neu auf. So bleiben parallele Paper- oder Code-Commits
erhalten, ohne sie zu überschreiben. Maximal drei normale Fast-forward-Push-
Versuche, kein Force-Push. Bei Änderungen am Remote-Berichtspaar während des
Pushs bricht er mit Konflikt ab; gleich alte oder neuere Remote-Snapshots
verhindern den Push bereits über den UTC-Zeitstempel. Ungültige Zeitstempel
oder unvollständige Remote-Berichtspaare führen zum sicheren Abbruch.
Push-Fehler sind in Log und Summary sichtbar; Branch-Schutz wird nicht umgangen.

Der neue Workflow und die bisherigen manuellen `mtf-*`-Modi teilen die
Concurrency-Gruppe `mtf-snapshot-main` ohne Abbruch laufender Jobs. GitHub
garantiert keine FIFO-Reihenfolge und kann wartende Läufe ersetzen; deshalb
bleibt der Zeitstempelvergleich zusätzlich erforderlich. Auch der bisherige
manuelle `mtf-analyse`-Modus nutzt den sicheren Publisher auf `main`;
Nebenbranches speichern nur Summary und Artifact. Die Paper-Concurrency und
beide Paper-Kontodateien bleiben unverändert. Es werden ausschließlich öffentliche
Kraken-Daten abgerufen, keine neuen Secrets, OpenAI-API-Schlüssel, bezahlten
Dienste oder externen Scheduler eingerichtet. GitHub-Actions-Kontingente und
Repository-Einstellungen gelten weiterhin.

### Geplanten Start nachweisen und Fehler untersuchen

In **Actions → MTF – unabhängige Beobachtung** einen Lauf öffnen. Das Trigger-
Event muss **`schedule`** lauten (auch im Job Summary); **`workflow_dispatch`**
belegt lediglich einen manuellen Start über **Run workflow**. Alternativ mit
GitHub CLI: `gh run list --workflow mtf-schedule.yml --event schedule`.
Ein grüner Job mit BLOCKIERT-Bericht bedeutet erfolgreiche Diagnose einer
Datenstörung, keine Freigabe der Marktdaten. Details stehen im Bericht je
Coin/Zeitfenster. Ein roter Job verlangt Prüfung von Tests, Ausführung,
Artifact-Upload beziehungsweise Push im jeweiligen Schritt.

**Betriebsstand vom 29.10.2026:** Für **Paper** ist ein echtes, erfolgreiches `schedule`-Ereignis nachgewiesen ([Lauf](https://github.com/MueschKi/krypto-master-network/actions/runs/40884879154)). Für **MTF** ist bislang nur ein erfolgreicher **manueller** `workflow_dispatch`-Lauf nachgewiesen ([Lauf](https://github.com/MueschKi/krypto-master-network/actions/runs/40836826622)); der automatisierte MTF-Betrieb ist damit noch **nicht** verifiziert. Für zuvor fehlende Cron-Ereignisse ist keine eindeutige Ursache bewiesen. GitHub-Cron kann verspätet starten oder ausfallen; ohne ausgeführtes Ereignis kann GitHub Actions allein keinen versäumten Termin zuverlässig melden. Kein 100-%-Verfügbarkeitsversprechen. Bei Bedarf MTF manuell auf `main` ausführen und den manuellen Trigger korrekt kennzeichnen.


## v1.5.2: Paper-Persistenz und Datenintegrität

Die Sicherheitskorrekturen aus [Issue #6](https://github.com/MueschKi/krypto-master-network/issues/6) wurden mit [Pull Request #7](https://github.com/MueschKi/krypto-master-network/pull/7) auf `main` übernommen. Sie ändern **keine** Entry-/Exit-Regeln und keine bestehenden Paper-Kontodaten.

- **Kein stiller Kontoreset:** Fehlende oder beschädigte Kontodateien stoppen `python trading.py paper` bereits vor dem Kursabruf. Der explizite Operator-Modus `python trading.py init --account-path /pfad/zu/neuem-konto.json [--trailing]` erzeugt nur neue Dateien und verweigert das Überschreiben bestehender Dateien. **Nicht** auf vorhandene Paper-Konten anwenden.
- **Transaktionssichere Veröffentlichung:** `paper_publish.py` committet im Paper-Modus ausschließlich die sieben ausdrücklich erlaubten Konto-/Berichtsdateien in einem separaten Git-Worktree. Parallele MTF-Commits bleiben erhalten. Bei konkurrierender Kontoänderung oder veränderter Berechnungsgrundlage wird ohne Überschreiben abgebrochen; bis zu drei Fast-forward-Push-Versuche, **kein Force-Push**. Berichte sind davor sieben Tage als Workflow-Artifact gesichert.
- **Strenge 1d-Rohdatenprüfung:** Exakte, aufsteigende UTC-Tageskerzen, keine Lücken, doppelten oder unsortierten Bars; Prüfung **vor** der Ausrichtung der Märkte. Für die laufende Analyse zählt nur der vollständig abgeschlossene UTC-Vortag. Historische Replays prüfen zeitkausal ohne Bezug auf die heutige Uhr.
- **Validierte Kontohistorie:** Bilanz, historische Handelstage, Trade-Reihenfolge und Positionsmengen werden auf Plausibilität geprüft; beide bestehenden Kontodateien bleiben erhalten.
- **ATR-Forschung vereinheitlicht:** Die historische Variante `ATR-Trailing 2,5x` nutzt jetzt die unveränderte Produktions-Engine. Ältere historische Ergebnisse (insbesondere **+8,63 %** auf bereits bekannten Daten) müssen mit der korrigierten Forschung **neu berechnet** werden; sie sind keine unabhängige Renditeprognose.

**Abnahme:** [97 Tests mit Python 3.11 erfolgreich](https://github.com/MueschKi/krypto-master-network/actions/runs/40887673658). Die vollständige technische Erläuterung einschließlich Grenzen steht unter [docs/SAFETY_v1.5.2.md](docs/SAFETY_v1.5.2.md). Auch mit diesen Sicherungen gibt es kein Echtzeit-Monitoring, keine garantierten Stopps und keinen Echtgeld-Modus.

## Nächste Betriebsprüfungen

1. Einen tatsächlich durch `schedule` gestarteten **MTF**-Lauf einschließlich Report-Publikation auf `main` nachweisen; ein manueller Lauf reicht hierfür nicht.
2. Nach dem Merge v1.5.2 einen erfolgreichen **Paper**-Lauf inklusive Artifact und sicherer Veröffentlichung kontrollieren.
3. Versäumte UTC-Tage und ausgefallene Zeitpläne ausdrücklich erfassen: derzeit verarbeitet der Paper-Bot pro erfolgreich gestarteten Lauf nur den jüngsten zulässigen Tagesabschluss und holt fehlende Handelstage nicht rückwirkend automatisch nach.
4. Erst nach zusätzlicher unabhängiger Paper-Beobachtung Strategiequalität beurteilen; keine Echtgeldfreigabe.
