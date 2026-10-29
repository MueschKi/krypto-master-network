# Krypto Master Network – Zentrale Profi-Analyse

**Dieser Bericht enthält nur Analysen. Virtuelle Master-Orders stehen separat in `TRADING_STATUS.md`. Echtgeldhandel ist gesperrt.**

Erstellt (UTC): 2026-10-29T13:46:05+00:00  
Datenquelle: Nur abgeschlossene Kraken-Tageskerzen (optional separater Live-Orderbuch-Snapshot)  
Die Master-Einstufungen sind heuristische Beobachtungssignale, keine statistischen Wahrscheinlichkeiten.

## Master-Übersicht

| Coin | Trend | Struktur | Momentum | Volumen | ATR | Master |
|:--|:--|:--|:--|:--|--:|:--|
| BTC/EUR | POSITIV (+1) | NEUTRAL (+0) | POSITIV (+1) | POSITIV (+2) | 2,30 % | ABWARTEN |
| ETH/EUR | NEUTRAL (+0) | NEGATIV (-1) | NEUTRAL (+0) | POSITIV (+1) | 3,68 % | ABWARTEN |
| SOL/EUR | NEUTRAL (+0) | NEUTRAL (+0) | NEUTRAL (+0) | POSITIV (+1) | 3,70 % | ABWARTEN |
| NEAR/EUR | POSITIV (+1) | POSITIV (+1) | POSITIV (+1) | POSITIV (+1) | 9,17 % | ABWARTEN |

## Einzelberichte der Spezialisten

### BTC/EUR · ABWARTEN

**Letzter Kurstag:** 2026-10-28

**Master-Begründung:** Kaufprüfung: 1 von 9 Bedingungen nicht erfüllt; Fehlt: Einstiegsszenario akzeptabel; Orderbuch/Spread nicht geprüft (historische Tagesanalyse)

**Prüfung aller Kaufbedingungen:**

| Bedingung | Ergebnis |
|:--|:--|
| Trend positiv | OK |
| Momentum positiv | OK |
| Struktur mindestens neutral | OK |
| Volumensignal mindestens neutral | OK |
| Relatives Tagesvolumen mindestens 0,8 | OK |
| OBV steigend | OK |
| Einstiegsszenario akzeptabel | FEHLT |
| Nicht knapp unter Widerstand | OK |
| Risiko-Bot: freigegeben | OK |

| Spezialist | Signal | Fakten |
|:--|:--|:--|
| Datenqualität | OK | kerzen: 719,00, letzter_tag: 2026-10-28 |
| Trend (Tag/Woche) | POSITIV | kurs: 72872,30, ema20: 72881,25, sma50: 72337,09, sma200: 63492,83 |
| Marktstruktur | NEUTRAL | hoch_20: 75525,60, tief_20: 70635,10, hoch_60: 77520,90, tief_60: 64927,20 |
| Momentum (RSI/MACD) | POSITIV | rsi14: 50,39, macd_histogramm: -210,28, macd_histogramm_vortag: -292,21 |
| Volumen (relativ/OBV) | POSITIV | volumen_faktor_20: 1,35, obv_10_tage_steigend: True, tageskurs_gestiegen: True |
| Volatilität (ATR/Bollinger) | NEUTRAL | atr14: 1674,91, atr14_prozent: 2,30, bollinger_breite_prozent: 5,13, risikostufe: NORMAL |
| Marktphase (ADX) | NEUTRAL | adx14: 17,48, plus_di14: 19,15, minus_di14: 20,91, phase: SEITWAERTS/UNSICHER |
| Unterstützung/Widerstand | NEUTRAL | unterstuetzung: 64927,20, widerstand: 77520,90, abstand_widerstand_prozent: 6,38, abstand_unterstuetzung_prozent: 12,24 |
| Einstiegsgeometrie (ATR/Risiko) | NEUTRAL | indikative_einstiegsbasis: 72872,30, theoretischer_2atr_stop: 69522,47, 60t_widerstand: 77520,90, 60t_unterstuetzung: 64927,20 |
| Relative Stärke zu BTC | NEUTRAL | rendite_30_tage_prozent: -0,74, btc_30_tage_prozent: -0,74, relative_starke_pp: 0,00, korrelation_60_tage: 1,00 |
| Orderbuch/Spread | NICHT_GEMESSEN | — |
| Risikokontrolle | OK | kaufkandidat_erlaubt: True, atr_prozent: 2,30 |

**Einordnung:**
- **Trend (Tag/Woche):** Tag: uneinheitlich; Abgeschlossene Wochen: aufwärts
- **Marktstruktur:** Swings: gemischt; 20-Tage-Grenze: kein Ausbruch
- **Momentum (RSI/MACD):** RSI14 50.4 (über 70 = überkauft, nicht automatisch Verkauf); MACD-Histogramm ohne eindeutigen Schub
- **Volumen (relativ/OBV):** Volumen: 1.35× gegenüber 20 Tagen; 10-Tage-OBV: steigend; Volumendaten sind börsenspezifisch, kein globales Krypto-Gesamtvolumen
- **Volatilität (ATR/Bollinger):** ATR14: 2.30% des Kurses; Bollinger-Bandbreite: 5.13%; Volatilität bestimmt Risiko/Positionsgröße, nicht die Kursrichtung
- **Marktphase (ADX):** ADX14 17.5: SEITWAERTS/UNSICHER; DI-Richtung: ABWAERTS; ADX allein zeigt Trendstärke, keinen zukünftigen Gewinn
- **Unterstützung/Widerstand:** 60-Tage-Widerstand 77520.9000 EUR, Distanz 6.38%; 60-Tage-Unterstützung 64927.2000 EUR, Abstand 12.24%; Historische Niveaus sind keine garantierten Stop- oder Umkehrpunkte
- **Einstiegsgeometrie (ATR/Risiko):** Nur Szenario: Einstieg Schlusskurs 72872.3000, Abstand Stop 2×ATR; Historischer 60-Tage-Widerstand 77520.9000 (kein Kursziel); Indikatives Chance-Risiko-Verhältnis: 1.39; Schlusskurs-Stop/ATR schützt nicht vor Kurslücken, Spreads und Slippage
- **Relative Stärke zu BTC:** 30-Tage-Mehr-/Minderrendite zu BTC: +0.00 Prozentpunkte; 60-Tage-Korrelation zu BTC: 1.00; BTC ist der Vergleichsmaßstab, kein unabhängiger Kaufsignalgeber
- **Orderbuch/Spread:** Kein L2-Snapshot angefordert; keine Liquiditätsaussage möglich
- **Risikokontrolle:** Kein aktuelles Orderbuch: tatsächliche Ausführbarkeit nicht geprüft

### ETH/EUR · ABWARTEN

**Letzter Kurstag:** 2026-10-28

**Master-Begründung:** Kaufprüfung: 4 von 9 Bedingungen nicht erfüllt; Fehlt: Trend positiv; Fehlt: Momentum positiv; Fehlt: Struktur mindestens neutral; Fehlt: Relatives Tagesvolumen mindestens 0,8; Orderbuch/Spread nicht geprüft (historische Tagesanalyse)

**Prüfung aller Kaufbedingungen:**

| Bedingung | Ergebnis |
|:--|:--|
| Trend positiv | FEHLT |
| Momentum positiv | FEHLT |
| Struktur mindestens neutral | FEHLT |
| Volumensignal mindestens neutral | OK |
| Relatives Tagesvolumen mindestens 0,8 | FEHLT |
| OBV steigend | OK |
| Einstiegsszenario akzeptabel | OK |
| Nicht knapp unter Widerstand | OK |
| Risiko-Bot: freigegeben | OK |

| Spezialist | Signal | Fakten |
|:--|:--|:--|
| Datenqualität | OK | kerzen: 719,00, letzter_tag: 2026-10-28 |
| Trend (Tag/Woche) | NEUTRAL | kurs: 2113,82, ema20: 2160,76, sma50: 2237,49, sma200: 1875,96 |
| Marktstruktur | NEGATIV | hoch_20: 2309,43, tief_20: 2037,54, hoch_60: 2466,25, tief_60: 2036,02 |
| Momentum (RSI/MACD) | NEUTRAL | rsi14: 41,13, macd_histogramm: -5,79, macd_histogramm_vortag: -8,87 |
| Volumen (relativ/OBV) | POSITIV | volumen_faktor_20: 0,74, obv_10_tage_steigend: True, tageskurs_gestiegen: True |
| Volatilität (ATR/Bollinger) | NEUTRAL | atr14: 77,71, atr14_prozent: 3,68, bollinger_breite_prozent: 9,79, risikostufe: NORMAL |
| Marktphase (ADX) | NEUTRAL | adx14: 28,03, plus_di14: 16,32, minus_di14: 24,51, phase: STARKER_TREND |
| Unterstützung/Widerstand | NEUTRAL | unterstuetzung: 2036,02, widerstand: 2466,25, abstand_widerstand_prozent: 16,67, abstand_unterstuetzung_prozent: 3,82 |
| Einstiegsgeometrie (ATR/Risiko) | NEUTRAL | indikative_einstiegsbasis: 2113,82, theoretischer_2atr_stop: 1958,39, 60t_widerstand: 2466,25, 60t_unterstuetzung: 2036,02 |
| Relative Stärke zu BTC | NEGATIV | rendite_30_tage_prozent: -10,58, btc_30_tage_prozent: -0,74, relative_starke_pp: -9,84, korrelation_60_tage: 0,92 |
| Orderbuch/Spread | NICHT_GEMESSEN | — |
| Risikokontrolle | OK | kaufkandidat_erlaubt: True, atr_prozent: 3,68 |

**Einordnung:**
- **Trend (Tag/Woche):** Tag: uneinheitlich; Abgeschlossene Wochen: uneinheitlich
- **Marktstruktur:** Swings: tiefere Hochs/Tiefs; 20-Tage-Grenze: kein Ausbruch
- **Momentum (RSI/MACD):** RSI14 41.1 (über 70 = überkauft, nicht automatisch Verkauf); MACD-Histogramm ohne eindeutigen Schub
- **Volumen (relativ/OBV):** Volumen: 0.74× gegenüber 20 Tagen; 10-Tage-OBV: steigend; Volumendaten sind börsenspezifisch, kein globales Krypto-Gesamtvolumen
- **Volatilität (ATR/Bollinger):** ATR14: 3.68% des Kurses; Bollinger-Bandbreite: 9.79%; Volatilität bestimmt Risiko/Positionsgröße, nicht die Kursrichtung
- **Marktphase (ADX):** ADX14 28.0: STARKER_TREND; DI-Richtung: ABWAERTS; ADX allein zeigt Trendstärke, keinen zukünftigen Gewinn
- **Unterstützung/Widerstand:** 60-Tage-Widerstand 2466.2500 EUR, Distanz 16.67%; 60-Tage-Unterstützung 2036.0200 EUR, Abstand 3.82%; Historische Niveaus sind keine garantierten Stop- oder Umkehrpunkte
- **Einstiegsgeometrie (ATR/Risiko):** Nur Szenario: Einstieg Schlusskurs 2113.8200, Abstand Stop 2×ATR; Historischer 60-Tage-Widerstand 2466.2500 (kein Kursziel); Indikatives Chance-Risiko-Verhältnis: 2.27; Schlusskurs-Stop/ATR schützt nicht vor Kurslücken, Spreads und Slippage
- **Relative Stärke zu BTC:** 30-Tage-Mehr-/Minderrendite zu BTC: -9.84 Prozentpunkte; 60-Tage-Korrelation zu BTC: 0.92; BTC ist der Vergleichsmaßstab, kein unabhängiger Kaufsignalgeber
- **Orderbuch/Spread:** Kein L2-Snapshot angefordert; keine Liquiditätsaussage möglich
- **Risikokontrolle:** Kein aktuelles Orderbuch: tatsächliche Ausführbarkeit nicht geprüft

### SOL/EUR · ABWARTEN

**Letzter Kurstag:** 2026-10-28

**Master-Begründung:** Kaufprüfung: 2 von 9 Bedingungen nicht erfüllt; Fehlt: Trend positiv; Fehlt: Momentum positiv; Orderbuch/Spread nicht geprüft (historische Tagesanalyse)

**Prüfung aller Kaufbedingungen:**

| Bedingung | Ergebnis |
|:--|:--|
| Trend positiv | FEHLT |
| Momentum positiv | FEHLT |
| Struktur mindestens neutral | OK |
| Volumensignal mindestens neutral | OK |
| Relatives Tagesvolumen mindestens 0,8 | OK |
| OBV steigend | OK |
| Einstiegsszenario akzeptabel | OK |
| Nicht knapp unter Widerstand | OK |
| Risiko-Bot: freigegeben | OK |

| Spezialist | Signal | Fakten |
|:--|:--|:--|
| Datenqualität | OK | kerzen: 719,00, letzter_tag: 2026-10-28 |
| Trend (Tag/Woche) | NEUTRAL | kurs: 91,79, ema20: 93,83, sma50: 96,63, sma200: 77,06 |
| Marktstruktur | NEUTRAL | hoch_20: 104,28, tief_20: 88,06, hoch_60: 109,90, tief_60: 82,90 |
| Momentum (RSI/MACD) | NEUTRAL | rsi14: 41,77, macd_histogramm: -0,32, macd_histogramm_vortag: -0,48 |
| Volumen (relativ/OBV) | POSITIV | volumen_faktor_20: 0,84, obv_10_tage_steigend: True, tageskurs_gestiegen: True |
| Volatilität (ATR/Bollinger) | NEUTRAL | atr14: 3,40, atr14_prozent: 3,70, bollinger_breite_prozent: 10,90, risikostufe: NORMAL |
| Marktphase (ADX) | NEUTRAL | adx14: 28,02, plus_di14: 15,34, minus_di14: 24,37, phase: STARKER_TREND |
| Unterstützung/Widerstand | NEUTRAL | unterstuetzung: 82,90, widerstand: 109,90, abstand_widerstand_prozent: 19,73, abstand_unterstuetzung_prozent: 10,72 |
| Einstiegsgeometrie (ATR/Risiko) | NEUTRAL | indikative_einstiegsbasis: 91,79, theoretischer_2atr_stop: 84,99, 60t_widerstand: 109,90, 60t_unterstuetzung: 82,90 |
| Relative Stärke zu BTC | NEGATIV | rendite_30_tage_prozent: -12,19, btc_30_tage_prozent: -0,74, relative_starke_pp: -11,45, korrelation_60_tage: 0,85 |
| Orderbuch/Spread | NICHT_GEMESSEN | — |
| Risikokontrolle | OK | kaufkandidat_erlaubt: True, atr_prozent: 3,70 |

**Einordnung:**
- **Trend (Tag/Woche):** Tag: uneinheitlich; Abgeschlossene Wochen: uneinheitlich
- **Marktstruktur:** Swings: gemischt; 20-Tage-Grenze: kein Ausbruch
- **Momentum (RSI/MACD):** RSI14 41.8 (über 70 = überkauft, nicht automatisch Verkauf); MACD-Histogramm ohne eindeutigen Schub
- **Volumen (relativ/OBV):** Volumen: 0.84× gegenüber 20 Tagen; 10-Tage-OBV: steigend; Volumendaten sind börsenspezifisch, kein globales Krypto-Gesamtvolumen
- **Volatilität (ATR/Bollinger):** ATR14: 3.70% des Kurses; Bollinger-Bandbreite: 10.90%; Volatilität bestimmt Risiko/Positionsgröße, nicht die Kursrichtung
- **Marktphase (ADX):** ADX14 28.0: STARKER_TREND; DI-Richtung: ABWAERTS; ADX allein zeigt Trendstärke, keinen zukünftigen Gewinn
- **Unterstützung/Widerstand:** 60-Tage-Widerstand 109.9000 EUR, Distanz 19.73%; 60-Tage-Unterstützung 82.9000 EUR, Abstand 10.72%; Historische Niveaus sind keine garantierten Stop- oder Umkehrpunkte
- **Einstiegsgeometrie (ATR/Risiko):** Nur Szenario: Einstieg Schlusskurs 91.7900, Abstand Stop 2×ATR; Historischer 60-Tage-Widerstand 109.9000 (kein Kursziel); Indikatives Chance-Risiko-Verhältnis: 2.66; Schlusskurs-Stop/ATR schützt nicht vor Kurslücken, Spreads und Slippage
- **Relative Stärke zu BTC:** 30-Tage-Mehr-/Minderrendite zu BTC: -11.45 Prozentpunkte; 60-Tage-Korrelation zu BTC: 0.85; BTC ist der Vergleichsmaßstab, kein unabhängiger Kaufsignalgeber
- **Orderbuch/Spread:** Kein L2-Snapshot angefordert; keine Liquiditätsaussage möglich
- **Risikokontrolle:** Kein aktuelles Orderbuch: tatsächliche Ausführbarkeit nicht geprüft

### NEAR/EUR · ABWARTEN

**Letzter Kurstag:** 2026-10-28

**Master-Begründung:** Kaufprüfung: 2 von 9 Bedingungen nicht erfüllt; Fehlt: Relatives Tagesvolumen mindestens 0,8; Fehlt: Einstiegsszenario akzeptabel; Orderbuch/Spread nicht geprüft (historische Tagesanalyse)

**Prüfung aller Kaufbedingungen:**

| Bedingung | Ergebnis |
|:--|:--|
| Trend positiv | OK |
| Momentum positiv | OK |
| Struktur mindestens neutral | OK |
| Volumensignal mindestens neutral | OK |
| Relatives Tagesvolumen mindestens 0,8 | FEHLT |
| OBV steigend | OK |
| Einstiegsszenario akzeptabel | FEHLT |
| Nicht knapp unter Widerstand | OK |
| Risiko-Bot: freigegeben | OK |

| Spezialist | Signal | Fakten |
|:--|:--|:--|
| Datenqualität | OK | kerzen: 719,00, letzter_tag: 2026-10-28 |
| Trend (Tag/Woche) | POSITIV | kurs: 4,24, ema20: 4,27, sma50: 3,90, sma200: 2,16 |
| Marktstruktur | POSITIV | hoch_20: 5,35, tief_20: 3,80, hoch_60: 5,35, tief_60: 1,54 |
| Momentum (RSI/MACD) | POSITIV | rsi14: 50,64, macd_histogramm: -0,08, macd_histogramm_vortag: -0,10 |
| Volumen (relativ/OBV) | POSITIV | volumen_faktor_20: 0,36, obv_10_tage_steigend: True, tageskurs_gestiegen: True |
| Volatilität (ATR/Bollinger) | RISIKO | atr14: 0,39, atr14_prozent: 9,17, bollinger_breite_prozent: 25,72, risikostufe: HOCH |
| Marktphase (ADX) | NEUTRAL | adx14: 24,53, plus_di14: 16,31, minus_di14: 18,45, phase: TRENDPHASE |
| Unterstützung/Widerstand | NEUTRAL | unterstuetzung: 1,54, widerstand: 5,35, abstand_widerstand_prozent: 26,05, abstand_unterstuetzung_prozent: 175,90 |
| Einstiegsgeometrie (ATR/Risiko) | NEUTRAL | indikative_einstiegsbasis: 4,24, theoretischer_2atr_stop: 3,47, 60t_widerstand: 5,35, 60t_unterstuetzung: 1,54 |
| Relative Stärke zu BTC | NEUTRAL | rendite_30_tage_prozent: 0,15, btc_30_tage_prozent: -0,74, relative_starke_pp: 0,89, korrelation_60_tage: 0,39 |
| Orderbuch/Spread | NICHT_GEMESSEN | — |
| Risikokontrolle | OK | kaufkandidat_erlaubt: True, atr_prozent: 9,17 |

**Einordnung:**
- **Trend (Tag/Woche):** Tag: uneinheitlich; Abgeschlossene Wochen: aufwärts
- **Marktstruktur:** Swings: höhere Hochs/Tiefs; 20-Tage-Grenze: kein Ausbruch
- **Momentum (RSI/MACD):** RSI14 50.6 (über 70 = überkauft, nicht automatisch Verkauf); MACD-Histogramm ohne eindeutigen Schub
- **Volumen (relativ/OBV):** Volumen: 0.36× gegenüber 20 Tagen; 10-Tage-OBV: steigend; Volumendaten sind börsenspezifisch, kein globales Krypto-Gesamtvolumen
- **Volatilität (ATR/Bollinger):** ATR14: 9.17% des Kurses; Bollinger-Bandbreite: 25.72%; Volatilität bestimmt Risiko/Positionsgröße, nicht die Kursrichtung
- **Marktphase (ADX):** ADX14 24.5: TRENDPHASE; DI-Richtung: ABWAERTS; ADX allein zeigt Trendstärke, keinen zukünftigen Gewinn
- **Unterstützung/Widerstand:** 60-Tage-Widerstand 5.3500 EUR, Distanz 26.05%; 60-Tage-Unterstützung 1.5384 EUR, Abstand 175.90%; Historische Niveaus sind keine garantierten Stop- oder Umkehrpunkte
- **Einstiegsgeometrie (ATR/Risiko):** Nur Szenario: Einstieg Schlusskurs 4.2445, Abstand Stop 2×ATR; Historischer 60-Tage-Widerstand 5.3500 (kein Kursziel); Indikatives Chance-Risiko-Verhältnis: 1.42; Schlusskurs-Stop/ATR schützt nicht vor Kurslücken, Spreads und Slippage
- **Relative Stärke zu BTC:** 30-Tage-Mehr-/Minderrendite zu BTC: +0.89 Prozentpunkte; 60-Tage-Korrelation zu BTC: 0.39; BTC ist der Vergleichsmaßstab, kein unabhängiger Kaufsignalgeber
- **Orderbuch/Spread:** Kein L2-Snapshot angefordert; keine Liquiditätsaussage möglich
- **Risikokontrolle:** Hohe Volatilität: im Paper Trading besonders vorsichtig; Kein aktuelles Orderbuch: tatsächliche Ausführbarkeit nicht geprüft

## Regeln und Grenzen

- Analyse-Bots sind unabhängige Module, aber ihre Kursdaten und Indikatoren sind statistisch abhängig.
- Der Master nutzt feste Bestätigungsbedingungen, keine beliebige Stimmenmehrheit.
- ATR = Schwankungsmaß, RSI/MACD = Momentum, EMA/SMA = Trend; keine Garantie für Gewinne.
- Ein einmaliger Orderbuch-Snapshot sagt nichts über langfristigen Orderfluss oder Spoofing aus.
- Die Master-Analyse führt selbst keine Orders aus; die separate Trading-Engine verwaltet ein neues, unabhängiges Demokonto. Bestehende KI-/Trend-/Opt-Trend-Depots bleiben unverändert.
- Für echten Handel fehlen u.a. Ausführungsmodell, robuste OOS-Tests und individuelles Risikobudget.

Maschinenlesbare Einzelwerte: `daten/netzwerk_analysen.json`.
