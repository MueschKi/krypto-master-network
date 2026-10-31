# Krypto Master Network – Zentrale Profi-Analyse

**Dieser Bericht enthält nur Analysen. Virtuelle Master-Orders stehen separat in `TRADING_STATUS.md`. Echtgeldhandel ist gesperrt.**

Erstellt (UTC): 2026-10-31T10:28:13+00:00  
Datenquelle: Nur abgeschlossene Kraken-Tageskerzen (optional separater Live-Orderbuch-Snapshot)  
Die Master-Einstufungen sind heuristische Beobachtungssignale, keine statistischen Wahrscheinlichkeiten.

## Master-Übersicht

| Coin | Trend | Struktur | Momentum | Volumen | ATR | Master |
|:--|:--|:--|:--|:--|--:|:--|
| BTC/EUR | POSITIV (+1) | NEGATIV (-2) | NEGATIV (-2) | NEGATIV (-2) | 2,59 % | ABWARTEN |
| ETH/EUR | NEUTRAL (+0) | NEGATIV (-1) | NEGATIV (-2) | NEGATIV (-2) | 3,92 % | ABWARTEN |
| SOL/EUR | NEUTRAL (+0) | NEGATIV (-1) | NEGATIV (-2) | POSITIV (+2) | 4,22 % | ABWARTEN |
| NEAR/EUR | POSITIV (+1) | POSITIV (+1) | NEUTRAL (+0) | NEGATIV (-1) | 9,90 % | ABWARTEN |

## Einzelberichte der Spezialisten

### BTC/EUR · ABWARTEN

**Letzter Kurstag:** 2026-10-30

**Master-Begründung:** Kaufprüfung: 4 von 9 Bedingungen nicht erfüllt; Fehlt: Momentum positiv; Fehlt: Struktur mindestens neutral; Fehlt: Volumensignal mindestens neutral; Fehlt: OBV steigend; Orderbuch/Spread nicht geprüft (historische Tagesanalyse); Widerspruch: Trend positiv, Momentum negativ

**Prüfung aller Kaufbedingungen:**

| Bedingung | Ergebnis |
|:--|:--|
| Trend positiv | OK |
| Momentum positiv | FEHLT |
| Struktur mindestens neutral | FEHLT |
| Volumensignal mindestens neutral | FEHLT |
| Relatives Tagesvolumen mindestens 0,8 | OK |
| OBV steigend | FEHLT |
| Einstiegsszenario akzeptabel | OK |
| Nicht knapp unter Widerstand | OK |
| Risiko-Bot: freigegeben | OK |

| Spezialist | Signal | Fakten |
|:--|:--|:--|
| Datenqualität | OK | kerzen: 719,00, letzter_tag: 2026-10-30 |
| Trend (Tag/Woche) | POSITIV | kurs: 69225,40, ema20: 72249,27, sma50: 72448,33, sma200: 63567,55 |
| Marktstruktur | NEGATIV | hoch_20: 75525,60, tief_20: 69520,10, hoch_60: 77520,90, tief_60: 64927,20 |
| Momentum (RSI/MACD) | NEGATIV | rsi14: 36,21, macd_histogramm: -455,16, macd_histogramm_vortag: -358,22 |
| Volumen (relativ/OBV) | NEGATIV | volumen_faktor_20: 3,30, obv_10_tage_steigend: False, tageskurs_gestiegen: False |
| Volatilität (ATR/Bollinger) | NEUTRAL | atr14: 1792,14, atr14_prozent: 2,59, bollinger_breite_prozent: 7,80, risikostufe: NORMAL |
| Marktphase (ADX) | NEUTRAL | adx14: 19,13, plus_di14: 15,10, minus_di14: 30,20, phase: SEITWAERTS/UNSICHER |
| Unterstützung/Widerstand | NEUTRAL | unterstuetzung: 64927,20, widerstand: 77520,90, abstand_widerstand_prozent: 11,98, abstand_unterstuetzung_prozent: 6,62 |
| Einstiegsgeometrie (ATR/Risiko) | NEUTRAL | indikative_einstiegsbasis: 69225,40, theoretischer_2atr_stop: 65641,11, 60t_widerstand: 77520,90, 60t_unterstuetzung: 64927,20 |
| Relative Stärke zu BTC | NEUTRAL | rendite_30_tage_prozent: -6,17, btc_30_tage_prozent: -6,17, relative_starke_pp: 0,00, korrelation_60_tage: 1,00 |
| Orderbuch/Spread | NICHT_GEMESSEN | — |
| Risikokontrolle | OK | kaufkandidat_erlaubt: True, atr_prozent: 2,59 |

**Einordnung:**
- **Trend (Tag/Woche):** Tag: uneinheitlich; Abgeschlossene Wochen: aufwärts
- **Marktstruktur:** Swings: tiefere Hochs/Tiefs; 20-Tage-Grenze: Durchbruch unten
- **Momentum (RSI/MACD):** RSI14 36.2 (über 70 = überkauft, nicht automatisch Verkauf); MACD-Histogramm zunehmend negativ
- **Volumen (relativ/OBV):** Volumen: 3.30× gegenüber 20 Tagen; 10-Tage-OBV: fallend oder gleich; Volumendaten sind börsenspezifisch, kein globales Krypto-Gesamtvolumen
- **Volatilität (ATR/Bollinger):** ATR14: 2.59% des Kurses; Bollinger-Bandbreite: 7.80%; Volatilität bestimmt Risiko/Positionsgröße, nicht die Kursrichtung
- **Marktphase (ADX):** ADX14 19.1: SEITWAERTS/UNSICHER; DI-Richtung: ABWAERTS; ADX allein zeigt Trendstärke, keinen zukünftigen Gewinn
- **Unterstützung/Widerstand:** 60-Tage-Widerstand 77520.9000 EUR, Distanz 11.98%; 60-Tage-Unterstützung 64927.2000 EUR, Abstand 6.62%; Historische Niveaus sind keine garantierten Stop- oder Umkehrpunkte
- **Einstiegsgeometrie (ATR/Risiko):** Nur Szenario: Einstieg Schlusskurs 69225.4000, Abstand Stop 2×ATR; Historischer 60-Tage-Widerstand 77520.9000 (kein Kursziel); Indikatives Chance-Risiko-Verhältnis: 2.31; Schlusskurs-Stop/ATR schützt nicht vor Kurslücken, Spreads und Slippage
- **Relative Stärke zu BTC:** 30-Tage-Mehr-/Minderrendite zu BTC: +0.00 Prozentpunkte; 60-Tage-Korrelation zu BTC: 1.00; BTC ist der Vergleichsmaßstab, kein unabhängiger Kaufsignalgeber
- **Orderbuch/Spread:** Kein L2-Snapshot angefordert; keine Liquiditätsaussage möglich
- **Risikokontrolle:** Kein aktuelles Orderbuch: tatsächliche Ausführbarkeit nicht geprüft

### ETH/EUR · ABWARTEN

**Letzter Kurstag:** 2026-10-30

**Master-Begründung:** Kaufprüfung: 5 von 9 Bedingungen nicht erfüllt; Fehlt: Trend positiv; Fehlt: Momentum positiv; Fehlt: Struktur mindestens neutral; Fehlt: Volumensignal mindestens neutral; Fehlt: OBV steigend; Orderbuch/Spread nicht geprüft (historische Tagesanalyse)

**Prüfung aller Kaufbedingungen:**

| Bedingung | Ergebnis |
|:--|:--|
| Trend positiv | FEHLT |
| Momentum positiv | FEHLT |
| Struktur mindestens neutral | FEHLT |
| Volumensignal mindestens neutral | FEHLT |
| Relatives Tagesvolumen mindestens 0,8 | OK |
| OBV steigend | FEHLT |
| Einstiegsszenario akzeptabel | OK |
| Nicht knapp unter Widerstand | OK |
| Risiko-Bot: freigegeben | OK |

| Spezialist | Signal | Fakten |
|:--|:--|:--|
| Datenqualität | OK | kerzen: 719,00, letzter_tag: 2026-10-30 |
| Trend (Tag/Woche) | NEUTRAL | kurs: 2009,64, ema20: 2133,50, sma50: 2233,48, sma200: 1876,61 |
| Marktstruktur | NEGATIV | hoch_20: 2299,93, tief_20: 1988,26, hoch_60: 2466,25, tief_60: 1988,26 |
| Momentum (RSI/MACD) | NEGATIV | rsi14: 31,70, macd_histogramm: -11,49, macd_histogramm_vortag: -9,76 |
| Volumen (relativ/OBV) | NEGATIV | volumen_faktor_20: 2,93, obv_10_tage_steigend: False, tageskurs_gestiegen: False |
| Volatilität (ATR/Bollinger) | NEUTRAL | atr14: 78,78, atr14_prozent: 3,92, bollinger_breite_prozent: 11,95, risikostufe: NORMAL |
| Marktphase (ADX) | NEUTRAL | adx14: 29,49, plus_di14: 13,18, minus_di14: 31,98, phase: STARKER_TREND |
| Unterstützung/Widerstand | NEUTRAL | unterstuetzung: 1988,26, widerstand: 2466,25, abstand_widerstand_prozent: 22,72, abstand_unterstuetzung_prozent: 1,08 |
| Einstiegsgeometrie (ATR/Risiko) | NEUTRAL | indikative_einstiegsbasis: 2009,64, theoretischer_2atr_stop: 1852,08, 60t_widerstand: 2466,25, 60t_unterstuetzung: 1988,26 |
| Relative Stärke zu BTC | NEGATIV | rendite_30_tage_prozent: -15,20, btc_30_tage_prozent: -6,17, relative_starke_pp: -9,02, korrelation_60_tage: 0,93 |
| Orderbuch/Spread | NICHT_GEMESSEN | — |
| Risikokontrolle | OK | kaufkandidat_erlaubt: True, atr_prozent: 3,92 |

**Einordnung:**
- **Trend (Tag/Woche):** Tag: uneinheitlich; Abgeschlossene Wochen: uneinheitlich
- **Marktstruktur:** Swings: tiefere Hochs/Tiefs; 20-Tage-Grenze: kein Ausbruch
- **Momentum (RSI/MACD):** RSI14 31.7 (über 70 = überkauft, nicht automatisch Verkauf); MACD-Histogramm zunehmend negativ
- **Volumen (relativ/OBV):** Volumen: 2.93× gegenüber 20 Tagen; 10-Tage-OBV: fallend oder gleich; Volumendaten sind börsenspezifisch, kein globales Krypto-Gesamtvolumen
- **Volatilität (ATR/Bollinger):** ATR14: 3.92% des Kurses; Bollinger-Bandbreite: 11.95%; Volatilität bestimmt Risiko/Positionsgröße, nicht die Kursrichtung
- **Marktphase (ADX):** ADX14 29.5: STARKER_TREND; DI-Richtung: ABWAERTS; ADX allein zeigt Trendstärke, keinen zukünftigen Gewinn
- **Unterstützung/Widerstand:** 60-Tage-Widerstand 2466.2500 EUR, Distanz 22.72%; 60-Tage-Unterstützung 1988.2600 EUR, Abstand 1.08%; Historische Niveaus sind keine garantierten Stop- oder Umkehrpunkte
- **Einstiegsgeometrie (ATR/Risiko):** Nur Szenario: Einstieg Schlusskurs 2009.6400, Abstand Stop 2×ATR; Historischer 60-Tage-Widerstand 2466.2500 (kein Kursziel); Indikatives Chance-Risiko-Verhältnis: 2.90; Schlusskurs-Stop/ATR schützt nicht vor Kurslücken, Spreads und Slippage
- **Relative Stärke zu BTC:** 30-Tage-Mehr-/Minderrendite zu BTC: -9.02 Prozentpunkte; 60-Tage-Korrelation zu BTC: 0.93; BTC ist der Vergleichsmaßstab, kein unabhängiger Kaufsignalgeber
- **Orderbuch/Spread:** Kein L2-Snapshot angefordert; keine Liquiditätsaussage möglich
- **Risikokontrolle:** Kein aktuelles Orderbuch: tatsächliche Ausführbarkeit nicht geprüft

### SOL/EUR · ABWARTEN

**Letzter Kurstag:** 2026-10-30

**Master-Begründung:** Kaufprüfung: 3 von 9 Bedingungen nicht erfüllt; Fehlt: Trend positiv; Fehlt: Momentum positiv; Fehlt: Struktur mindestens neutral; Orderbuch/Spread nicht geprüft (historische Tagesanalyse)

**Prüfung aller Kaufbedingungen:**

| Bedingung | Ergebnis |
|:--|:--|
| Trend positiv | FEHLT |
| Momentum positiv | FEHLT |
| Struktur mindestens neutral | FEHLT |
| Volumensignal mindestens neutral | OK |
| Relatives Tagesvolumen mindestens 0,8 | OK |
| OBV steigend | OK |
| Einstiegsszenario akzeptabel | OK |
| Nicht knapp unter Widerstand | OK |
| Risiko-Bot: freigegeben | OK |

| Spezialist | Signal | Fakten |
|:--|:--|:--|
| Datenqualität | OK | kerzen: 719,00, letzter_tag: 2026-10-30 |
| Trend (Tag/Woche) | NEUTRAL | kurs: 86,23, ema20: 92,37, sma50: 96,61, sma200: 77,20 |
| Marktstruktur | NEGATIV | hoch_20: 101,06, tief_20: 84,98, hoch_60: 109,90, tief_60: 82,90 |
| Momentum (RSI/MACD) | NEGATIV | rsi14: 32,78, macd_histogramm: -0,66, macd_histogramm_vortag: -0,59 |
| Volumen (relativ/OBV) | POSITIV | volumen_faktor_20: 3,13, obv_10_tage_steigend: True, tageskurs_gestiegen: True |
| Volatilität (ATR/Bollinger) | NEUTRAL | atr14: 3,64, atr14_prozent: 4,22, bollinger_breite_prozent: 13,34, risikostufe: NORMAL |
| Marktphase (ADX) | NEUTRAL | adx14: 30,03, plus_di14: 11,98, minus_di14: 32,06, phase: STARKER_TREND |
| Unterstützung/Widerstand | NEUTRAL | unterstuetzung: 82,90, widerstand: 109,90, abstand_widerstand_prozent: 27,45, abstand_unterstuetzung_prozent: 4,02 |
| Einstiegsgeometrie (ATR/Risiko) | NEUTRAL | indikative_einstiegsbasis: 86,23, theoretischer_2atr_stop: 78,94, 60t_widerstand: 109,90, 60t_unterstuetzung: 82,90 |
| Relative Stärke zu BTC | NEGATIV | rendite_30_tage_prozent: -17,24, btc_30_tage_prozent: -6,17, relative_starke_pp: -11,06, korrelation_60_tage: 0,86 |
| Orderbuch/Spread | NICHT_GEMESSEN | — |
| Risikokontrolle | OK | kaufkandidat_erlaubt: True, atr_prozent: 4,22 |

**Einordnung:**
- **Trend (Tag/Woche):** Tag: uneinheitlich; Abgeschlossene Wochen: uneinheitlich
- **Marktstruktur:** Swings: tiefere Hochs/Tiefs; 20-Tage-Grenze: kein Ausbruch
- **Momentum (RSI/MACD):** RSI14 32.8 (über 70 = überkauft, nicht automatisch Verkauf); MACD-Histogramm zunehmend negativ
- **Volumen (relativ/OBV):** Volumen: 3.13× gegenüber 20 Tagen; 10-Tage-OBV: steigend; Volumendaten sind börsenspezifisch, kein globales Krypto-Gesamtvolumen
- **Volatilität (ATR/Bollinger):** ATR14: 4.22% des Kurses; Bollinger-Bandbreite: 13.34%; Volatilität bestimmt Risiko/Positionsgröße, nicht die Kursrichtung
- **Marktphase (ADX):** ADX14 30.0: STARKER_TREND; DI-Richtung: ABWAERTS; ADX allein zeigt Trendstärke, keinen zukünftigen Gewinn
- **Unterstützung/Widerstand:** 60-Tage-Widerstand 109.9000 EUR, Distanz 27.45%; 60-Tage-Unterstützung 82.9000 EUR, Abstand 4.02%; Historische Niveaus sind keine garantierten Stop- oder Umkehrpunkte
- **Einstiegsgeometrie (ATR/Risiko):** Nur Szenario: Einstieg Schlusskurs 86.2300, Abstand Stop 2×ATR; Historischer 60-Tage-Widerstand 109.9000 (kein Kursziel); Indikatives Chance-Risiko-Verhältnis: 3.25; Schlusskurs-Stop/ATR schützt nicht vor Kurslücken, Spreads und Slippage
- **Relative Stärke zu BTC:** 30-Tage-Mehr-/Minderrendite zu BTC: -11.06 Prozentpunkte; 60-Tage-Korrelation zu BTC: 0.86; BTC ist der Vergleichsmaßstab, kein unabhängiger Kaufsignalgeber
- **Orderbuch/Spread:** Kein L2-Snapshot angefordert; keine Liquiditätsaussage möglich
- **Risikokontrolle:** Kein aktuelles Orderbuch: tatsächliche Ausführbarkeit nicht geprüft

### NEAR/EUR · ABWARTEN

**Letzter Kurstag:** 2026-10-30

**Master-Begründung:** Kaufprüfung: 3 von 9 Bedingungen nicht erfüllt; Fehlt: Momentum positiv; Fehlt: Volumensignal mindestens neutral; Fehlt: OBV steigend; Orderbuch/Spread nicht geprüft (historische Tagesanalyse)

**Prüfung aller Kaufbedingungen:**

| Bedingung | Ergebnis |
|:--|:--|
| Trend positiv | OK |
| Momentum positiv | FEHLT |
| Struktur mindestens neutral | OK |
| Volumensignal mindestens neutral | FEHLT |
| Relatives Tagesvolumen mindestens 0,8 | OK |
| OBV steigend | FEHLT |
| Einstiegsszenario akzeptabel | OK |
| Nicht knapp unter Widerstand | OK |
| Risiko-Bot: freigegeben | OK |

| Spezialist | Signal | Fakten |
|:--|:--|:--|
| Datenqualität | OK | kerzen: 719,00, letzter_tag: 2026-10-30 |
| Trend (Tag/Woche) | POSITIV | kurs: 3,85, ema20: 4,18, sma50: 3,97, sma200: 2,19 |
| Marktstruktur | POSITIV | hoch_20: 5,35, tief_20: 3,60, hoch_60: 5,35, tief_60: 1,56 |
| Momentum (RSI/MACD) | NEUTRAL | rsi14: 44,97, macd_histogramm: -0,11, macd_histogramm_vortag: -0,11 |
| Volumen (relativ/OBV) | NEGATIV | volumen_faktor_20: 1,51, obv_10_tage_steigend: False, tageskurs_gestiegen: True |
| Volatilität (ATR/Bollinger) | RISIKO | atr14: 0,38, atr14_prozent: 9,90, bollinger_breite_prozent: 31,72, risikostufe: HOCH |
| Marktphase (ADX) | NEUTRAL | adx14: 24,91, plus_di14: 13,40, minus_di14: 24,39, phase: TRENDPHASE |
| Unterstützung/Widerstand | NEUTRAL | unterstuetzung: 1,56, widerstand: 5,35, abstand_widerstand_prozent: 38,99, abstand_unterstuetzung_prozent: 147,09 |
| Einstiegsgeometrie (ATR/Risiko) | NEUTRAL | indikative_einstiegsbasis: 3,85, theoretischer_2atr_stop: 3,09, 60t_widerstand: 5,35, 60t_unterstuetzung: 1,56 |
| Relative Stärke zu BTC | NEGATIV | rendite_30_tage_prozent: -18,36, btc_30_tage_prozent: -6,17, relative_starke_pp: -12,19, korrelation_60_tage: 0,44 |
| Orderbuch/Spread | NICHT_GEMESSEN | — |
| Risikokontrolle | OK | kaufkandidat_erlaubt: True, atr_prozent: 9,90 |

**Einordnung:**
- **Trend (Tag/Woche):** Tag: uneinheitlich; Abgeschlossene Wochen: aufwärts
- **Marktstruktur:** Swings: höhere Hochs/Tiefs; 20-Tage-Grenze: kein Ausbruch
- **Momentum (RSI/MACD):** RSI14 45.0 (über 70 = überkauft, nicht automatisch Verkauf); MACD-Histogramm ohne eindeutigen Schub
- **Volumen (relativ/OBV):** Volumen: 1.51× gegenüber 20 Tagen; 10-Tage-OBV: fallend oder gleich; Volumendaten sind börsenspezifisch, kein globales Krypto-Gesamtvolumen
- **Volatilität (ATR/Bollinger):** ATR14: 9.90% des Kurses; Bollinger-Bandbreite: 31.72%; Volatilität bestimmt Risiko/Positionsgröße, nicht die Kursrichtung
- **Marktphase (ADX):** ADX14 24.9: TRENDPHASE; DI-Richtung: ABWAERTS; ADX allein zeigt Trendstärke, keinen zukünftigen Gewinn
- **Unterstützung/Widerstand:** 60-Tage-Widerstand 5.3500 EUR, Distanz 38.99%; 60-Tage-Unterstützung 1.5578 EUR, Abstand 147.09%; Historische Niveaus sind keine garantierten Stop- oder Umkehrpunkte
- **Einstiegsgeometrie (ATR/Risiko):** Nur Szenario: Einstieg Schlusskurs 3.8491, Abstand Stop 2×ATR; Historischer 60-Tage-Widerstand 5.3500 (kein Kursziel); Indikatives Chance-Risiko-Verhältnis: 1.97; Schlusskurs-Stop/ATR schützt nicht vor Kurslücken, Spreads und Slippage
- **Relative Stärke zu BTC:** 30-Tage-Mehr-/Minderrendite zu BTC: -12.19 Prozentpunkte; 60-Tage-Korrelation zu BTC: 0.44; BTC ist der Vergleichsmaßstab, kein unabhängiger Kaufsignalgeber
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
