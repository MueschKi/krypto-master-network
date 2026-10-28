# Krypto Master Network v1.3 – Entry-/Exit-Diagnose

**NUR HISTORISCHE FORSCHUNG. KEINE ECHTGELD-ORDERS. KEINE AUTOMATISCHE STRATEGIEÄNDERUNG.**

Erstellt: 28.10.2026 21:38 UTC  
Datenquelle: **ECHTE KRAKEN-TAGESKURSE**  
Verfügbarer Kurszeitraum: 2024-11-08 bis 2026-10-27  
Simulierte Signal-Tage: **459**. Mindestens 260 Vorlaufkerzen.

## Gleiche historischen Preise und Handelskosten – Variantenvergleich

| Variante | Endwert | Nettorendite | Max. Rückgang | Ausführungen | Geschlossene Trades |
|:--|--:|--:|--:|--:|--:|
| Master unveraendert | 1.001,26 € | +0.13 % | 10.39 % | 20 | 9 |
| ATR-Stopp 2x | 1.021,50 € | +2.15 % | 10.59 % | 16 | 7 |
| ATR-Trailing 2,5x | 1.086,26 € | +8.63 % | 6.60 % | 20 | 10 |
| Ohne Volumen-Veto | 1.024,30 € | +2.43 % | 11.20 % | 18 | 8 |
| EMA20/SMA50 (Master-Limits) | 897,56 € | -10.24 % | 15.02 % | 40 | 20 |

**Methodik:** Identische Master-Signale, vier Coins, Startkapital 1.000 €, Risiko- und Cash-Obergrenzen. Simulierte Ausführung frühestens am nächsten Tages-Open, hypothetischer Gesamtspread 0,15 %, Gebühren 0.4 % und Zusatz-Slippage 0.1 % pro Ausführung.
Alle Varianten verwenden dieselben **bereits bekannten historischen Testdaten**. **Ein höherer Wert ist kein unabhängiger Wirksamkeitsnachweis.**

### Exakte Regeländerungen im Forschungstest

- **Master unverändert:** Originale neun Entry-Gates und 7-%-Schlusskurs-Stopp.
- **ATR-Stopp 2x:** gleiche Einstiegssignale, fester Einstiegskurs minus 2× ATR14 zum Kaufsignal; abgeschlossene Tagesschlusskurse lösen ggf. Verkauf zum nächsten Open aus.
- **ATR-Trailing 2,5x:** gleiche Einstiegssignale, Anfangsstopp Einstieg minus 2,5× ATR14; Nachziehen anhand bisher abgeschlossener Schlusskurse, nie absenken.
- **EMA20/SMA50 (Master-Limits):** einfache Trendfolge nach Kurs > SMA50 und EMA20 > SMA50; Verkauf bei Trendbruch, aber Positionslimits des Masters. **Keine exakte Reproduktion des alten separaten v0.4-Depots**.
- **Ohne Volumen-Veto:** reine Entry-Ablation: drei Volumen-/OBV-Bedingungen entfallen, alle übrigen Gates sowie das Risiko-Veto bleiben; ursprünglicher 7-%-Stopp.
- Keine Variable oder Parameter aus dem Vergleich wird in `trading.py`, `trade_engine.py` oder das echte Paper-Konto übernommen.

## Original-Master: Gewinne und offene Positionen getrennt

- Realisierte abgeschlossene Trades: **-91,92 €**.
- Bewertung offener Positionen relativ zu ihren Kosten: **93,18 €**.
- Zusammen ergibt das die Depotveränderung: **1,26 €**.
- Gewinner unter geschlossenen Trades: **0 von 9**.
- Geschlossene Trades nach Schlusskurs-Stopp: **8**.

## Exit-Diagnose pro abgeschlossenem Trade

| Coin | Einstieg (Open) | Ausstieg (Open) | Haltedauer (Bars) | Netto realisiert | MFE* | MAE* | Exit-Grund |
|:--|:--|:--|--:|--:|--:|--:|:--|
| BTC/EUR | 2025-08-14 | 2025-08-20 | 6 | -10,56 € | +0.00 % | -7.84 % | 7%-Tagesschluss-Stopp (keine garantierte Ausführung) |
| SOL/EUR | 2025-08-29 | 2025-09-02 | 4 | -11,21 € | +0.00 % | -9.75 % | 7%-Tagesschluss-Stopp (keine garantierte Ausführung) |
| NEAR/EUR | 2025-09-19 | 2025-09-23 | 4 | -10,07 € | +3.39 % | -13.53 % | 7%-Tagesschluss-Stopp (keine garantierte Ausführung) |
| SOL/EUR | 2025-09-11 | 2025-09-26 | 15 | -17,24 € | +12.12 % | -14.42 % | 7%-Tagesschluss-Stopp (keine garantierte Ausführung) |
| ETH/EUR | 2025-08-09 | 2025-11-04 | 87 | -12,19 € | +22.03 % | -13.87 % | 7%-Tagesschluss-Stopp (keine garantierte Ausführung) |
| NEAR/EUR | 2026-05-21 | 2026-08-19 | 90 | -8,37 € | +81.39 % | -9.13 % | Master: schwacher Markt |
| SOL/EUR | 2026-08-28 | 2026-09-02 | 5 | -10,13 € | +0.00 % | -9.64 % | 7%-Tagesschluss-Stopp (keine garantierte Ausführung) |
| ETH/EUR | 2026-09-22 | 2026-10-09 | 17 | -1,55 € | +1.68 % | -11.53 % | 7%-Tagesschluss-Stopp (keine garantierte Ausführung) |
| SOL/EUR | 2026-09-19 | 2026-10-26 | 37 | -10,62 € | +11.90 % | -10.34 % | 7%-Tagesschluss-Stopp (keine garantierte Ausführung) |

*MFE = größter zwischenzeitlicher Kursanstieg, MAE = stärkster Rückgang gegenüber dem Einstiegspreis. Reine Kursbewegungen **ohne Gebühren**; nur vollständige Tageskerzen zwischen Einstiegs- und Ausstiegs-Open, die beiden Fülltage werden bewusst ausgeschlossen. Bei kurzer Haltedauer können Werte fehlen. Diese Zukunftsdaten werden niemals für die Handelsentscheidung genutzt.

## Entry-Diagnose: Was wurde rückblickend verpasst?

Nach BLOCK/HOLD wird die **rein hypothetische** 7-Tage-Bewegung vom nächsten Open bis zum Open sieben Tage später ausgewertet. Ein Plus von mindestens 3 % ist kein realisierbarer Netto-Tradinggewinn. Überlappende Gates werden einzeln gezählt.

| Nicht erfülltes Entry-Gate | Untersuchte Fälle | Danach mindestens +3 % | Anteil |
|:--|--:|--:|--:|
| Trend positiv | 1250 | 391 | 31.3 % |
| Volumensignal mindestens neutral | 1023 | 343 | 33.5 % |
| OBV steigend | 1023 | 343 | 33.5 % |
| Momentum positiv | 1008 | 318 | 31.5 % |
| Relatives Tagesvolumen mindestens 0,8 | 782 | 233 | 29.8 % |
| Einstiegsszenario akzeptabel | 617 | 173 | 28.0 % |
| Struktur mindestens neutral | 592 | 191 | 32.3 % |
| Risiko-Bot: freigegeben | 52 | 21 | 40.4 % |
| Nicht knapp unter Widerstand | 51 | 16 | 31.4 % |

## Interpretation und Sicherheitsgrenzen

- **Selektionsbias:** Die Regeln und der historische Datenausschnitt waren bereits bekannt. Die Varianten sind Diagnoseexperimente, keine unberührten Out-of-sample-Ergebnisse.
- Future-7d-Bewegungen und MFE/MAE dürfen ausschließlich **nachträglich** ausgewertet werden.
- Gleichzeitige Signale, Korrelationscluster und überlappende 7-Tage-Fenster sind nicht unabhängig.
- Historische Bid/Ask-Quotes und Intraday-Orderabfolge sind nicht verfügbar. Tages-Schlusskurs-Stopps bieten keinen garantierten Ausstiegspreis.
- Die Forschung stellt keinen Echtgeld-Broker bereit und verändert das laufende Paper-Konto **nicht**.
- Zuerst neue, bisher ungesehene Paper-Zeiträume und ggf. längere unabhängige Daten evaluieren.

Maschinenlesbar: `daten/master_v13_trades.csv`, `daten/master_v13_entry.csv` und `daten/master_v13_kurven.csv`.
