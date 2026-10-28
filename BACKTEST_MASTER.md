# Krypto Master Network – Historischer Master-Backtest v1.2

**NUR HISTORISCHE SIMULATION. KEINE ECHTGELD-ORDERS. KEINE GEWINNPROGNOSE.**

Erstellt: 28.10.2026 21:22 UTC  
Datenquelle: **ECHTE KRAKEN-TAGESKURSE**  
Kursdaten: 2024-11-08 bis 2026-10-27 (719 Tageskerzen je Coin)  
Signalzeitraum: **2025-07-25 bis 2026-10-26**  
Ausführungszeitraum: **2025-07-26 bis 2026-10-27**  
Handelstage im historischen Replay: **459**; zuvor mindestens 260 Kerzen für Indikatoren.

## Kontovergleich

| Strategie | Endwert | Nettorendite | Max. Drawdown | Ausführungen |
|:--|--:|--:|--:|--:|
| **Master v1.1 – unveränderte Kaufregeln** | 1.001,26 € | +0.13 % | 10.39 % | 20 |
| Passiv 11,25 % je Coin, 55 % EUR | 952,39 € | -4.76 % | 30.09 % | 4 Käufe |
| EUR-Bargeld ohne Zinsen | 1.000,00 € | +0,00 % | 0,00 % | 0 |

## Handelsstatistik

- **Virtuelle Ausführungen:** 20 (11 Käufe / 9 Verkäufe).
- **Geschlossene Trades:** 9; davon profitabel: 0 (0.0 %)
- **Realisierte Gewinne/Verluste:** -91,92 €
- **Gebühren aller Master-Ausführungen:** 8,23 €; **modellierte Slippage:** 2,06 € (bereits in Kontowerten enthalten).
- **Positionen am Testende:** 2; EUR-Rest: 676,43 €.
- **Neue Käufe am Ende gesperrt:** NEIN.

## Warum hat der Master nicht gekauft?

Hier zählen wir jede einzelne Prüfung pro Coin und Signal-Tag. Die Bedingungen sind **nicht unabhängig**:

| Kaufbedingung, die nicht erfüllt wurde | Coin-Tage |
|:--|--:|
| Trend positiv | 1264 |
| Volumensignal mindestens neutral | 1037 |
| OBV steigend | 1037 |
| Momentum positiv | 1032 |
| Relatives Tagesvolumen mindestens 0,8 | 801 |
| Einstiegsszenario akzeptabel | 628 |
| Struktur mindestens neutral | 594 |
| Risiko-Bot: freigegeben | 53 |
| Nicht knapp unter Widerstand | 51 |

### Einstufungen des Masters

| Entscheidung | Coin-Tage |
|:--|--:|
| ABWARTEN | 1430 |
| SCHWACHER MARKT | 325 |
| RISIKOSPERRE | 53 |
| BEOBACHTEN: KAUFKANDIDAT | 28 |

### Tatsächliche Paper-Engine-Entscheidungen

- **Tage mit aktiver Kauf-Drawdown-Sperre:** 0 von 459.
| Ausführungsentscheidung / Grund | Coin-Tage |
|:--|--:|
| HOLD: ABWARTEN | 1125 |
| HOLD: Bestehende Position halten | 341 |
| HOLD: SCHWACHER MARKT | 324 |
| HOLD: RISIKOSPERRE | 26 |
| SELL: 7%-Tagesschluss-Stopp (keine garantierte Ausführung) | 8 |
| BUY: Virtueller Einsatz 120.00 EUR | 1 |
| BUY: Virtueller Einsatz 122.42 EUR | 1 |
| BUY: Virtueller Einsatz 120.41 EUR | 1 |
| BUY: Virtueller Einsatz 118.46 EUR | 1 |
| BUY: Virtueller Einsatz 120.48 EUR | 1 |
| BUY: Virtueller Einsatz 112.65 EUR | 1 |
| SELL: Master: schwacher Markt | 1 |
| BUY: Virtueller Einsatz 111.65 EUR | 1 |
| BUY: Virtueller Einsatz 110.43 EUR | 1 |
| BUY: Virtueller Einsatz 117.73 EUR | 1 |
| BUY: Virtueller Einsatz 121.23 EUR | 1 |
| BUY: Virtueller Einsatz 15.61 EUR | 1 |

### Käufe und Verkäufe pro Coin

| Coin | Käufe | Verkäufe | Realisiert |
|:--|--:|--:|--:|
| BTC/EUR | 2 | 1 | -10,56 € |
| ETH/EUR | 2 | 2 | -13,73 € |
| SOL/EUR | 4 | 4 | -49,19 € |
| NEAR/EUR | 3 | 2 | -18,43 € |

## Drei zeitlich aufeinanderfolgende Abschnitte

**Ein durchgehendes Konto**: Teilrenditen verwenden den Kontowert am Beginn des Abschnitts.

| Abschnitt (Signalbeginn bis Ausführung) | Master | Passiv | Max. Teilrückgang Master |
|:--|--:|--:|--:|
| 2025-07-25 – 2025-12-25 | -6.13 % | -14.83 % | 7.92 % |
| 2025-12-25 – 2026-05-27 | +5.83 % | -1.73 % | 6.19 % |
| 2026-05-27 – 2026-10-27 | +0.79 % | +13.79 % | 9.79 % |

## Wichtige methodische Grenzen

- **Kein echter historischer Spread:** Das Replay setzt einen fiktiven konstanten Bid/Ask-Gesamtspread von 0.15 % an (zusätzlich 0.4 % Gebühr und 0.1 % Slippage je Ausführung). Die echten vergangenen Orderbücher fehlen.
- Analysen verwenden nur bis zum jeweiligen Tagesschluss bekannte OHLCV-Daten; simulierte Ausführungen nutzen frühestens den **Open des Folgetages**.
- Eine Stop-Regel ist **kein echter Stop-Auftrag**. Stop-Signale werden nur täglich geprüft; Sprünge, Gaps, Spreads, Verzögerungen und Teilfüllungen sind nicht realistisch rekonstruiert.
- Der Drawdown wird aus den Modellwerten an den simulierten Ausführungszeitpunkten berechnet; intraday auftretende Verluste können höher gewesen sein.
- Das Master-Regelwerk war bereits auf Grundlage früherer Backtests entwickelt worden. **Diese Historie ist kein unabhängiger Out-of-Sample-Nachweis.** Keine automatische Optimierung in diesem Modul.
- Die Kraken-OHLC-Historie ist begrenzt. Weitere Marktphasen und echte neue Paper-Trades sind notwendig, bevor man von einem belastbaren Handelsvorteil sprechen kann.
- Die historische Simulation nutzt nicht das echte Orderbuch und misst keine Live-Latenz oder Börsenrestriktionen.
- **Der Backtest verändert `daten/master_paper_state.json` und das reale Paper-Demokonto NICHT.**

Maschinenlesbar: `daten/master_backtest_kurve.csv` und `daten/master_backtest_trades.csv`.
