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
