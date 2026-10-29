# Krypto Master Network – Trading Edition v1.1

**Prototyp: automatisches Paper Trading, keine echten Orders. Keine Gewinngarantie.**

## Architektur

```text
Öffentliche Kraken-Kursdaten (abgeschlossene 1d Kerzen)
                  |
       12 Analyse-Spezialisten
                  |
          Master-Entscheidung
       BUY-KANDIDAT / HOLD / SCHWACH
                  |
       Datenqualität + Risiko-Veto
                  |
      Orderbuch-Snapshot (öffentlich)
                  |
         PaperTradingEngine
        |              |
  Transaktionsbuch   Portfolio / Risikolimits
        \              /
         TRADING_STATUS.md

      LiveExchangeAdapter = hart gesperrt
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

## Trading-Logik (MVP)

- Der Master lässt nur einen technisch begründeten **Kaufkandidaten** zu, wenn die Risiko- und Datenqualitätsprüfung OK ist.
- Die getrennte Paper-Engine verarbeitet **BUY / SELL / HOLD / BLOCK**, niemals echte Börsenorders.
- Bestehende Positionen werden bei Master-Einstufung `SCHWACHER MARKT` oder einem **7-%-Tagesschluss-Stopp** am nächsten erfolgreichen Bot-Durchlauf zum aktuellen Orderbuchpreis simuliert verkauft.
- Ein Kauf verwendet höchstens 12 % des aktuellen Kontowerts je Coin. Gesamtexposure maximal etwa 45 %, zusätzlich begrenzt durch nominales Anfangskapital; mindestens 300 € EUR-Reserve.
- Nach einem Drawdown von 12 % vom bisher erreichten Depot-Hoch **dauerhafte Sperre weiterer Käufe bis zur manuellen Prüfung**. Bestehende Positionen können weiterhin verkauft werden.
- Gebührenannahme 0,4 % je Ausführung; zusätzliche modellierte Slippage 0,1 % gegenüber Bid/Ask. Mindestorder 15 €.
- Portfolio: nur Spot-Käufe/Verkäufe, **kein Shorting, keine Hebel, keine Kreditaufnahme**.
- Jeder abgeschlossene UTC-Handelstag wird höchstens einmal gebucht. Gleichzeitige GitHub-Actions-Läufe werden serialisiert.
- Fehlende, unplausible oder veraltete Daten stoppen den Durchlauf; keine stillen Preisersatzwerte.

Der öffentliche Bid-/Ask-Snapshot ist keine Garantie für ausführbare Mengen oder Preise. Die Engine berücksichtigt weder vollständige Orderbuchtiefe noch echte Teilausführungen oder Börsenrestriktionen. Ohne dauerhaft laufenden Dienst ist dies keine durchgehende Stop-Überwachung. Tagesbasierte Kurslücken können zu erheblich größeren Verlusten führen. **Diese Grenzen schließen einen verantwortbaren Echtgeldbetrieb der aktuellen Version aus.**

## Betriebsarten

```bash
python -m pip install -r requirements.txt
python -m unittest -q test_netzwerk test_trading
python trading.py demo        # künstliche Kurse, getrennte DEMO_TRADING.md
python trading.py analyse     # echte öffentliche Daten, ohne Transaktion
python trading.py paper       # echte öffentliche Daten, NUR simulierte Orders
```

`paper` benötigt **keine Zugangsdaten**: der Kursabruf verwendet ausschließlich öffentliche Kraken-Schnittstellen. Keine Börsenkonten und keine Wallets verbinden.

## Ergebnisse

- `TRADING_STATUS.md`: zentraler, mobil lesbarer Überblick über Depot, Signale und simulierte Orders.
- `NETZWERK.md`: die zwölf Spezialanalysen für BTC, ETH, SOL und NEAR.
- `daten/master_paper_state.json`: **einzige verbindliche Kontodatei** einschließlich unveränderlicher Trade-Historie. Nicht löschen, nicht manuell verändern.
- `daten/netzwerk_analysen.json`: alle Einzelwerte maschinenlesbar.
- `DEMO_TRADING.md`: nur künstliche Demo, nicht Teil des produktiven Kontos, per `.gitignore` ausgeschlossen.

Kursdaten nur von **abgeschlossenen 1d-Kerzen**. Die Kraken-OHLC-Schnittstelle ist auf ca. 720 Kerzen begrenzt.

## Automatische tägliche Ausführung

Der Workflow [master-paper.yml](.github/workflows/master-paper.yml) ist auf dem Standardbranch täglich für **04:17 und 06:47 UTC** geplant. Vor jedem Paper-Trading-Durchlauf werden alle fünf Softwaretestmodule ausgeführt; nur bei Erfolg folgen die Simulation und das Speichern der Ergebnisse. Die Läufe werden je Branch nacheinander ausgeführt; derselbe abgeschlossene UTC-Handelstag wird höchstens einmal gebucht. GitHub kann geplante Läufe verzögern oder auslassen. Unter **Actions → Run workflow** ist außerdem ein manueller Start möglich (Standardmodus: `demo`). Echtgeldhandel bleibt technisch gesperrt.

## Echtgeld-Schnittstelle

`trade_broker.LiveExchangeAdapter` ist eine **absichtlich gesperrte Schnittstelle**. Sowohl das Erzeugen des Adapters als auch `place_order` werfen `PermissionError`. Es gibt **keinen Schalter, keine API-Key-Konfiguration und keinen ausführbaren Echtgeld-Orderpfad**. Eine spätere Implementierung wäre ein eigenes Projekt mit getrennten Zugangsdaten, manueller Freigabe, zusätzlichen Sicherheitsprüfungen, Monitoring und unabhängiger Validierung.

## Nutzung

Zur Einrichtung auf dem iPhone siehe `ANLEITUNG_IPHONE.md` im Installationspaket. Der GitHub-Workflow liegt separat zum Einfügen bereit, weil die GitHub-Mobile-App vorhandene Dateien nicht direkt hochladen kann; über Safari funktioniert es.

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
3. Nach Freigabe/Merge Branch `main` und `mtf-demo` oder `mtf-analyse` wählen.
   Vor dem Merge stehen die neuen Dispatch-Optionen eventuell noch nicht zur
   Verfügung, weil GitHub den Workflow auf dem Standardbranch benötigt.
4. Den Lauf öffnen: Zusammenfassung und das Artefakt `multi-timeframe-berichte`
   enthalten die Markdown-/JSON-Dateien. Artefakte benötigen GitHub-Anmeldung.
5. Nur `mtf-analyse` committet die beiden neuen Ergebnisdateien auf dem gewählten
   Branch. Danach lässt sich `ZEITFENSTER.md` direkt unter **Code** lesen.
   Demo committet nichts. Für die reine Beobachtung nicht `paper` auswählen.

Die Cron-Zeiten **04:17 und 06:47 UTC** verwenden weiterhin ausschließlich `paper`.
Es sind keine neuen Secrets, Wallets oder Exchange-Zugangsdaten nötig.
