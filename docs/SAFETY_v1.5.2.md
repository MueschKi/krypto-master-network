# v1.5.2 – Issue #6: Sicherheitskorrekturen und Abnahme

Basis: aktueller main `cf07b9860ffeeb6939f9dd7d5696b8c36a316c97` (29.10.2026).
Der lokale Ausgangsstand `165949e` unterscheidet sich nur durch Berichte;
dies wurde über GitHub Compare geprüft. Der PR wird direkt auf dem aktuellen
main-Tree aufgebaut. Keine Konto- oder generierten Berichtsdateien im PR.

## Paper-Publikation

`paper_publish.py` liest ausschließlich die sieben bisherigen Paper-Pfade.
Die zwei Konto-Blobs aus dem Berechnungs-Checkout (HEAD) bilden die unveränderliche
Konfliktbasis. Jeder Versuch holt den Remote-Branch neu und baut einen einzelnen
Commit in einem temporären, getrennten Worktree auf dessen aktuellem Stand.
Nur normaler Fast-forward-Push; weder Merge/Rebase noch Force-Push.
MTF-Commits bleiben erhalten. Bei Kontoänderung, Löschung oder Änderung der
Berechnungsgrundlage wird abgebrochen; ein neuer Lauf muss laden und neu rechnen.
Auch Änderungen vor dem ersten Fetch werden erkannt. Drei Push-Versuche, danach
FAILURE, roter Workflow und Fehlermeldung in Job Summary. Ergebnisse werden zuvor
für sieben Tage als Artifact gesichert. Der Publisher verändert den aufrufenden
Checkout und dessen Index nicht. Analyse publiziert nur Netzwerkberichte.

## Kontoerhaltung und Initialisierung

Fehlende/beschädigte Konten stoppen Paper bereits vor dem ersten Netzwerkzugriff.
Es gibt weder automatische Neuanlage noch automatische Reparatur/Reset.
Nur der ausdrücklich aufgerufene lokale Operator-Befehl legt eine neue Datei an:

```sh
python trading.py init --account-path /tmp/neues-paper-konto.json
python trading.py init --account-path /tmp/neues-trailing-konto.json --trailing
```

Exklusives Öffnen (`x`) verweigert vorhandene Dateien, auch bei parallelen
Initialisierungen. Dieser Modus ist nicht im Workflow auswählbar. Fehlende
Bestandsdateien müssen aus geprüfter Historie wiederhergestellt werden;
Initialisierung ist kein Wiederherstellungsverfahren.

State-Version bleibt 1.1. Numerik, positive Start-/Equitywerte, Höchstwert,
boolesche Risikosperre, ISO-Tage, eindeutige chronologische Equity-Historie,
letzter Kontotag/-wert, Trade-Reihenfolge, doppelte Ausführungen, Bestände und
Cash-Rekonstruktion werden geprüft. Rundungstoleranzen berücksichtigen die bereits
gespeicherten gerundeten Trades. Zusätzliche Metadaten bleiben zulässig.
Trailing-Stopps müssen positiv, endlich und unter dem bisherigen Peak liegen.

Unveränderte Bestandsdateien (SHA-256):

| Datei | SHA-256 |
| --- | --- |
| daten/master_paper_state.json | bff4f143257bde11920c3418a91e2e2900b77aaa0ac61d6edc69b589ac3b2f46 |
| daten/master_trailing_state.json | 0c6199afb854c821fdcc12481751e89c5611a8943ffb5767cac0bc6cfa993278 |

Git-Blob-IDs stimmen mit den über GitHub gelesenen main-Dateien überein:
`ff30674217249e864f6094107a3414514c4bf2bf` und
`1054620f47415d01fecfb3dfcf0fd0e66a3708e7`.
Beide enthalten unverändert ihre Historie vom 27./28.10.2026 und 1.000 EUR.

## Tagesdaten und Zeitkausalität

Rohdaten werden vor Filtern, Sortieren oder Ausrichten auf ein eindeutiges,
aufsteigendes, lückenloses UTC-Mitternachtsraster geprüft. Ein Abstand von zwei
Tagen ist bereits ein Fehler. Es wird nichts ergänzt oder repariert.
`aligned` prüft jeden Markt vor der Schnittmengenbildung. Die laufende Analyse
mit Referenztag verlangt exakt den abgeschlossenen UTC-Vortag; API-Lag sperrt
neue Paper-Ausführung. Eine aktuelle unvollständige Tageskerze wird verworfen.
Historische Replays ohne Referenztag bleiben unabhängig von der aktuellen Uhr;
OHLCV-Plausibilität und Rasterprüfung gelten weiterhin.

## ATR-Forschungsparität

Die alte Forschung setzte beim Einstieg Peak=Signal-Close; Produktion verwendet
Peak=max(Fill, Signal-Close). Beispiel des Regressionstests: Close 100,
simulierter Einstieg 110,15004, ATR 2, Anfangsstopp 105,15004. Am Folgetag Close
108 und ATR 1: alter Forschungsstopp 105,5, Produktionsstopp 107,65004.
Ein weiterer Close 106 hätte früher HOLD ergeben, produziert aber SELL.
Die bisherige Forschung ersetzte außerdem einen nichtpositiven Anfangsstopp durch
1e-9, während die Produktion den gesamten Lauf abbricht.

Die ATR-Trailing-Forschung ruft jetzt die unveränderte Produktionsengine auf.
Damit stimmen Peak, Stop-Prüfung vor Nachziehen, Nichtabsenken, Risikobudget,
Idempotenz und Fail-closed-Verhalten überein. Historische Fills bleiben simulierte
nächste Opens; laufende Paper-Fills nutzen spätere öffentliche Bid/Ask-Snapshots.
Diese Ausführungsunterschiede bleiben methodisch bestehen.

Die vorher berichteten +8,63 % sind bekannte In-sample-Ergebnisse der alten
Forschung, kein unabhängiger Nachweis und keine erwartete oder garantierte
Rendite. Kein neuer historischer Live-Datenlauf wurde ausgeführt. Vor einem neuen
Vergleich müssen Ergebnisse mit der korrigierten Forschung neu berechnet werden.

## Tatsächlich ausgeführte Prüfung

Lokale Umgebung: Python 3.12.14, pandas 2.3.3, numpy 2.5.4.
Befehl: `/workspace/.venvs/krypto-master-network/bin/python -m unittest discover -q`.
Letzter vollständiger Lauf: **97 Tests, 4,131 s, OK** (78 bisherige + 19 neue).
Mehrere Zwischenläufe wurden zur Fehlerbehebung ausgeführt. Zu Beginn scheiterten
veraltete Tests, die automatische Kontoanlage und alte Forschungsfelder erwarteten;
diese verwenden nun expliziten Bootstrap bzw. Produktions-Trailing-Felder.

Gezielte neue Tests:

- Zwei lokale Klone und Bare-Remote: MTF-Push zwischen Fetch/Push bleibt erhalten;
  Retry erfolgreich; Konto-Race und Kontoänderung vor erstem Fetch brechen ab;
  abgelehnter Push endet nach exakt drei Versuchen; keine fremden Dateien gestaged;
  CLI meldet FAILURE; fehlende Ausgabe wird nicht publiziert; Analyse ohne Kontowrites.
- Beide fehlenden Kontodateien stoppen vor Netzwerkzugriff ohne Dateischreibzugriff;
  beschädigtes JSON/Schema bleibt unangetastet; expliziter Bootstrap verweigert Überschreiben.
- Einzelner fehlender Tag, Duplikate, unsortierte und verschobene Rohkerzen,
  Gap in einem Markt vor `aligned`, veraltete/aktuelle offene Tageskerzen,
  gültiger Vortag und zeitkausaler historischer Lauf.
- Explizites Gap-/ATR-Schrumpfungs-Szenario, Stop- und Portfolio-Parität,
  nichtpositiver ATR-Stopp ohne Mutation; State-Numerik, Historie und Risikosperre.

`git diff --check` für alle geänderten Quell-/Workflow-/Testdateien: erfolgreich.
Konto-Blob- und SHA-256-Vergleich: erfolgreich. Bestehende Tests für die technische
Echtgeldsperre bestehen. Unveränderte Strategie-Funktionen und Parameter des
Fixed-Engines werden separat gehasht; Broker, Trailing-Engine und Master-Signale
bleiben bytegleich gepinnt. Die alten MTF-Hash-Pins für absichtlich geänderte
Sicherheitsdateien wurden durch diese Verhaltensprüfungen ersetzt.

Python 3.11 und actionlint sind lokal nicht installiert. Der bestehende PR-Workflow
führt die gesamte Suite auf GitHub mit Python 3.11 aus; dessen tatsächliches
Ergebnis wird im PR geprüft. Kein lokales 3.11-/actionlint-Ergebnis wird behauptet.
Die lokalen pandas/numpy-Versionen geben DeprecationWarnings zu Timedelta aus;
die Suite besteht, dies ist kein nachgewiesener Laufzeitfehler.

## Grenzen

Kontokonflikte werden bewusst nicht automatisch zusammengeführt: Operator muss
den fehlgeschlagenen Lauf prüfen und auf frischem Checkout erneut starten.
Ein Ausfall zwischen lokalen Dateiersetzungen kann lokal ein unvollständiges
Bundle hinterlassen; GitHub veröffentlicht ausschließlich nach erfolgreichem
Berechnungsschritt als einzelnen Commit. Artifact ist eine Diagnose-/Sicherungskopie,
kein automatisch zu importierender Kontostand. Kontodateien niemals blind daraus
über einen neueren Stand kopieren.

Kein Zeitplan oder concurrency-Gruppe geändert. Die ungeklärte GitHub-Scheduler-
Diagnose bleibt separat und wird durch diese Änderungen nicht als gelöst erklärt.
MTF bleibt unabhängig. Keine neuen APIs, Secrets, Wallets oder Echtgeldintegration.
PR muss vor Übernahme geprüft werden; kein automatischer Merge.
