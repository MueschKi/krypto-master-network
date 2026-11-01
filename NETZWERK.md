# Krypto Master Network – Zentrale Profi-Analyse

**Dieser Bericht enthält nur Analysen. Virtuelle Master-Orders stehen separat in `TRADING_STATUS.md`. Echtgeldhandel ist gesperrt.**

Erstellt (UTC): 2026-11-01T13:49:42+00:00  
Datenquelle: Nur abgeschlossene Kraken-Tageskerzen (optional separater Live-Orderbuch-Snapshot)  
Die Master-Einstufungen sind heuristische Beobachtungssignale, keine statistischen Wahrscheinlichkeiten.

## Master-Übersicht

| Coin | Trend | Struktur | Momentum | Volumen | ATR | Master |
|:--|:--|:--|:--|:--|--:|:--|
| BTC/EUR | POSITIV (+1) | NEGATIV (-1) | NEGATIV (-2) | NEGATIV (-1) | 2,56 % | ABWARTEN |
| ETH/EUR | NEUTRAL (+0) | NEGATIV (-1) | NEGATIV (-1) | NEGATIV (-1) | 3,73 % | ABWARTEN |
| SOL/EUR | NEUTRAL (+0) | NEGATIV (-1) | NEGATIV (-2) | NEGATIV (-1) | 4,11 % | ABWARTEN |
| NEAR/EUR | POSITIV (+1) | POSITIV (+1) | NEUTRAL (+0) | NEGATIV (-1) | 9,39 % | ABWARTEN |

## Einzelberichte der Spezialisten

### BTC/EUR · ABWARTEN

**Letzter Kurstag:** 2026-10-31

**Master-Begründung:** Kaufprüfung: 5 von 9 Bedingungen nicht erfüllt; Fehlt: Momentum positiv; Fehlt: Struktur mindestens neutral; Fehlt: Volumensignal mindestens neutral; Fehlt: Relatives Tagesvolumen mindestens 0,8; Fehlt: OBV steigend; Orderbuch/Spread nicht geprüft (historische Tagesanalyse); Widerspruch: Trend positiv, Momentum negativ

**Prüfung aller Kaufbedingungen:**

| Bedingung | Ergebnis |
|:--|:--|
| Trend positiv | OK |
| Momentum positiv | FEHLT |
| Struktur mindestens neutral | FEHLT |
| Volumensignal mindestens neutral | FEHLT |
| Relatives Tagesvolumen mindestens 0,8 | FEHLT |
| OBV steigend | FEHLT |
| Einstiegsszenario akzeptabel | OK |
| Nicht knapp unter Widerstand | OK |
| Risiko-Bot: freigegeben | OK |

| Spezialist | Signal | Fakten |
|:--|:--|:--|
| Datenqualität | OK | kerzen: 719,00, letzter_tag: 2026-10-31 |
| Trend (Tag/Woche) | POSITIV | kurs: 69435,10, ema20: 71981,25, sma50: 72505,31, sma200: 63600,31 |
| Marktstruktur | NEGATIV | hoch_20: 75525,60, tief_20: 68222,00, hoch_60: 77520,90, tief_60: 64927,20 |
| Momentum (RSI/MACD) | NEGATIV | rsi14: 37,38, macd_histogramm: -477,51, macd_histogramm_vortag: -455,16 |
| Volumen (relativ/OBV) | NEGATIV | volumen_faktor_20: 0,63, obv_10_tage_steigend: False, tageskurs_gestiegen: True |
| Volatilität (ATR/Bollinger) | NEUTRAL | atr14: 1778,71, atr14_prozent: 2,56, bollinger_breite_prozent: 8,27, risikostufe: NORMAL |
| Marktphase (ADX) | NEUTRAL | adx14: 20,15, plus_di14: 14,74, minus_di14: 29,49, phase: TRENDPHASE |
| Unterstützung/Widerstand | NEUTRAL | unterstuetzung: 64927,20, widerstand: 77520,90, abstand_widerstand_prozent: 11,65, abstand_unterstuetzung_prozent: 6,94 |
| Einstiegsgeometrie (ATR/Risiko) | NEUTRAL | indikative_einstiegsbasis: 69435,10, theoretischer_2atr_stop: 65877,67, 60t_widerstand: 77520,90, 60t_unterstuetzung: 64927,20 |
| Relative Stärke zu BTC | NEUTRAL | rendite_30_tage_prozent: -7,95, btc_30_tage_prozent: -7,95, relative_starke_pp: 0,00, korrelation_60_tage: 1,00 |
| Orderbuch/Spread | NICHT_GEMESSEN | — |
| Risikokontrolle | OK | kaufkandidat_erlaubt: True, atr_prozent: 2,56 |

**Einordnung:**
- **Trend (Tag/Woche):** Tag: uneinheitlich; Abgeschlossene Wochen: aufwärts
- **Marktstruktur:** Swings: tiefere Hochs/Tiefs; 20-Tage-Grenze: kein Ausbruch
- **Momentum (RSI/MACD):** RSI14 37.4 (über 70 = überkauft, nicht automatisch Verkauf); MACD-Histogramm zunehmend negativ
- **Volumen (relativ/OBV):** Volumen: 0.63× gegenüber 20 Tagen; 10-Tage-OBV: fallend oder gleich; Volumendaten sind börsenspezifisch, kein globales Krypto-Gesamtvolumen
- **Volatilität (ATR/Bollinger):** ATR14: 2.56% des Kurses; Bollinger-Bandbreite: 8.27%; Volatilität bestimmt Risiko/Positionsgröße, nicht die Kursrichtung
- **Marktphase (ADX):** ADX14 20.1: TRENDPHASE; DI-Richtung: ABWAERTS; ADX allein zeigt Trendstärke, keinen zukünftigen Gewinn
- **Unterstützung/Widerstand:** 60-Tage-Widerstand 77520.9000 EUR, Distanz 11.65%; 60-Tage-Unterstützung 64927.2000 EUR, Abstand 6.94%; Historische Niveaus sind keine garantierten Stop- oder Umkehrpunkte
- **Einstiegsgeometrie (ATR/Risiko):** Nur Szenario: Einstieg Schlusskurs 69435.1000, Abstand Stop 2×ATR; Historischer 60-Tage-Widerstand 77520.9000 (kein Kursziel); Indikatives Chance-Risiko-Verhältnis: 2.27; Schlusskurs-Stop/ATR schützt nicht vor Kurslücken, Spreads und Slippage
- **Relative Stärke zu BTC:** 30-Tage-Mehr-/Minderrendite zu BTC: +0.00 Prozentpunkte; 60-Tage-Korrelation zu BTC: 1.00; BTC ist der Vergleichsmaßstab, kein unabhängiger Kaufsignalgeber
- **Orderbuch/Spread:** Kein L2-Snapshot angefordert; keine Liquiditätsaussage möglich
- **Risikokontrolle:** Kein aktuelles Orderbuch: tatsächliche Ausführbarkeit nicht geprüft

### ETH/EUR · ABWARTEN

**Letzter Kurstag:** 2026-10-31

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
| Datenqualität | OK | kerzen: 719,00, letzter_tag: 2026-10-31 |
| Trend (Tag/Woche) | NEUTRAL | kurs: 2019,89, ema20: 2122,68, sma50: 2230,50, sma200: 1876,86 |
| Marktstruktur | NEGATIV | hoch_20: 2299,93, tief_20: 1938,00, hoch_60: 2466,25, tief_60: 1938,00 |
| Momentum (RSI/MACD) | NEGATIV | rsi14: 33,44, macd_histogramm: -10,93, macd_histogramm_vortag: -11,49 |
| Volumen (relativ/OBV) | NEGATIV | volumen_faktor_20: 1,48, obv_10_tage_steigend: False, tageskurs_gestiegen: True |
| Volatilität (ATR/Bollinger) | NEUTRAL | atr14: 75,29, atr14_prozent: 3,73, bollinger_breite_prozent: 11,62, risikostufe: NORMAL |
| Marktphase (ADX) | NEUTRAL | adx14: 30,29, plus_di14: 13,11, minus_di14: 31,18, phase: STARKER_TREND |
| Unterstützung/Widerstand | NEUTRAL | unterstuetzung: 1938,00, widerstand: 2466,25, abstand_widerstand_prozent: 22,10, abstand_unterstuetzung_prozent: 4,23 |
| Einstiegsgeometrie (ATR/Risiko) | NEUTRAL | indikative_einstiegsbasis: 2019,89, theoretischer_2atr_stop: 1869,31, 60t_widerstand: 2466,25, 60t_unterstuetzung: 1938,00 |
| Relative Stärke zu BTC | NEGATIV | rendite_30_tage_prozent: -16,02, btc_30_tage_prozent: -7,95, relative_starke_pp: -8,08, korrelation_60_tage: 0,93 |
| Orderbuch/Spread | NICHT_GEMESSEN | — |
| Risikokontrolle | OK | kaufkandidat_erlaubt: True, atr_prozent: 3,73 |

**Einordnung:**
- **Trend (Tag/Woche):** Tag: uneinheitlich; Abgeschlossene Wochen: uneinheitlich
- **Marktstruktur:** Swings: tiefere Hochs/Tiefs; 20-Tage-Grenze: kein Ausbruch
- **Momentum (RSI/MACD):** RSI14 33.4 (über 70 = überkauft, nicht automatisch Verkauf); MACD-Histogramm ohne eindeutigen Schub
- **Volumen (relativ/OBV):** Volumen: 1.48× gegenüber 20 Tagen; 10-Tage-OBV: fallend oder gleich; Volumendaten sind börsenspezifisch, kein globales Krypto-Gesamtvolumen
- **Volatilität (ATR/Bollinger):** ATR14: 3.73% des Kurses; Bollinger-Bandbreite: 11.62%; Volatilität bestimmt Risiko/Positionsgröße, nicht die Kursrichtung
- **Marktphase (ADX):** ADX14 30.3: STARKER_TREND; DI-Richtung: ABWAERTS; ADX allein zeigt Trendstärke, keinen zukünftigen Gewinn
- **Unterstützung/Widerstand:** 60-Tage-Widerstand 2466.2500 EUR, Distanz 22.10%; 60-Tage-Unterstützung 1938.0000 EUR, Abstand 4.23%; Historische Niveaus sind keine garantierten Stop- oder Umkehrpunkte
- **Einstiegsgeometrie (ATR/Risiko):** Nur Szenario: Einstieg Schlusskurs 2019.8900, Abstand Stop 2×ATR; Historischer 60-Tage-Widerstand 2466.2500 (kein Kursziel); Indikatives Chance-Risiko-Verhältnis: 2.96; Schlusskurs-Stop/ATR schützt nicht vor Kurslücken, Spreads und Slippage
- **Relative Stärke zu BTC:** 30-Tage-Mehr-/Minderrendite zu BTC: -8.08 Prozentpunkte; 60-Tage-Korrelation zu BTC: 0.93; BTC ist der Vergleichsmaßstab, kein unabhängiger Kaufsignalgeber
- **Orderbuch/Spread:** Kein L2-Snapshot angefordert; keine Liquiditätsaussage möglich
- **Risikokontrolle:** Kein aktuelles Orderbuch: tatsächliche Ausführbarkeit nicht geprüft

### SOL/EUR · ABWARTEN

**Letzter Kurstag:** 2026-10-31

**Master-Begründung:** Kaufprüfung: 6 von 9 Bedingungen nicht erfüllt; Fehlt: Trend positiv; Fehlt: Momentum positiv; Fehlt: Struktur mindestens neutral; Fehlt: Volumensignal mindestens neutral; Fehlt: Relatives Tagesvolumen mindestens 0,8; Fehlt: OBV steigend; Orderbuch/Spread nicht geprüft (historische Tagesanalyse)

**Prüfung aller Kaufbedingungen:**

| Bedingung | Ergebnis |
|:--|:--|
| Trend positiv | FEHLT |
| Momentum positiv | FEHLT |
| Struktur mindestens neutral | FEHLT |
| Volumensignal mindestens neutral | FEHLT |
| Relatives Tagesvolumen mindestens 0,8 | FEHLT |
| OBV steigend | FEHLT |
| Einstiegsszenario akzeptabel | OK |
| Nicht knapp unter Widerstand | OK |
| Risiko-Bot: freigegeben | OK |

| Spezialist | Signal | Fakten |
|:--|:--|:--|
| Datenqualität | OK | kerzen: 719,00, letzter_tag: 2026-10-31 |
| Trend (Tag/Woche) | NEUTRAL | kurs: 85,45, ema20: 91,71, sma50: 96,55, sma200: 77,28 |
| Marktstruktur | NEGATIV | hoch_20: 101,06, tief_20: 82,44, hoch_60: 109,90, tief_60: 82,44 |
| Momentum (RSI/MACD) | NEGATIV | rsi14: 31,57, macd_histogramm: -0,70, macd_histogramm_vortag: -0,66 |
| Volumen (relativ/OBV) | NEGATIV | volumen_faktor_20: 0,54, obv_10_tage_steigend: False, tageskurs_gestiegen: False |
| Volatilität (ATR/Bollinger) | NEUTRAL | atr14: 3,51, atr14_prozent: 4,11, bollinger_breite_prozent: 13,08, risikostufe: NORMAL |
| Marktphase (ADX) | NEUTRAL | adx14: 31,14, plus_di14: 11,61, minus_di14: 31,08, phase: STARKER_TREND |
| Unterstützung/Widerstand | NEUTRAL | unterstuetzung: 82,44, widerstand: 109,90, abstand_widerstand_prozent: 28,61, abstand_unterstuetzung_prozent: 3,65 |
| Einstiegsgeometrie (ATR/Risiko) | NEUTRAL | indikative_einstiegsbasis: 85,45, theoretischer_2atr_stop: 78,43, 60t_widerstand: 109,90, 60t_unterstuetzung: 82,44 |
| Relative Stärke zu BTC | NEGATIV | rendite_30_tage_prozent: -18,84, btc_30_tage_prozent: -7,95, relative_starke_pp: -10,90, korrelation_60_tage: 0,86 |
| Orderbuch/Spread | NICHT_GEMESSEN | — |
| Risikokontrolle | OK | kaufkandidat_erlaubt: True, atr_prozent: 4,11 |

**Einordnung:**
- **Trend (Tag/Woche):** Tag: uneinheitlich; Abgeschlossene Wochen: uneinheitlich
- **Marktstruktur:** Swings: tiefere Hochs/Tiefs; 20-Tage-Grenze: kein Ausbruch
- **Momentum (RSI/MACD):** RSI14 31.6 (über 70 = überkauft, nicht automatisch Verkauf); MACD-Histogramm zunehmend negativ
- **Volumen (relativ/OBV):** Volumen: 0.54× gegenüber 20 Tagen; 10-Tage-OBV: fallend oder gleich; Volumendaten sind börsenspezifisch, kein globales Krypto-Gesamtvolumen
- **Volatilität (ATR/Bollinger):** ATR14: 4.11% des Kurses; Bollinger-Bandbreite: 13.08%; Volatilität bestimmt Risiko/Positionsgröße, nicht die Kursrichtung
- **Marktphase (ADX):** ADX14 31.1: STARKER_TREND; DI-Richtung: ABWAERTS; ADX allein zeigt Trendstärke, keinen zukünftigen Gewinn
- **Unterstützung/Widerstand:** 60-Tage-Widerstand 109.9000 EUR, Distanz 28.61%; 60-Tage-Unterstützung 82.4400 EUR, Abstand 3.65%; Historische Niveaus sind keine garantierten Stop- oder Umkehrpunkte
- **Einstiegsgeometrie (ATR/Risiko):** Nur Szenario: Einstieg Schlusskurs 85.4500, Abstand Stop 2×ATR; Historischer 60-Tage-Widerstand 109.9000 (kein Kursziel); Indikatives Chance-Risiko-Verhältnis: 3.48; Schlusskurs-Stop/ATR schützt nicht vor Kurslücken, Spreads und Slippage
- **Relative Stärke zu BTC:** 30-Tage-Mehr-/Minderrendite zu BTC: -10.90 Prozentpunkte; 60-Tage-Korrelation zu BTC: 0.86; BTC ist der Vergleichsmaßstab, kein unabhängiger Kaufsignalgeber
- **Orderbuch/Spread:** Kein L2-Snapshot angefordert; keine Liquiditätsaussage möglich
- **Risikokontrolle:** Kein aktuelles Orderbuch: tatsächliche Ausführbarkeit nicht geprüft

### NEAR/EUR · ABWARTEN

**Letzter Kurstag:** 2026-10-31

**Master-Begründung:** Kaufprüfung: 4 von 9 Bedingungen nicht erfüllt; Fehlt: Momentum positiv; Fehlt: Volumensignal mindestens neutral; Fehlt: Relatives Tagesvolumen mindestens 0,8; Fehlt: OBV steigend; Orderbuch/Spread nicht geprüft (historische Tagesanalyse)

**Prüfung aller Kaufbedingungen:**

| Bedingung | Ergebnis |
|:--|:--|
| Trend positiv | OK |
| Momentum positiv | FEHLT |
| Struktur mindestens neutral | OK |
| Volumensignal mindestens neutral | FEHLT |
| Relatives Tagesvolumen mindestens 0,8 | FEHLT |
| OBV steigend | FEHLT |
| Einstiegsszenario akzeptabel | OK |
| Nicht knapp unter Widerstand | OK |
| Risiko-Bot: freigegeben | OK |

| Spezialist | Signal | Fakten |
|:--|:--|:--|
| Datenqualität | OK | kerzen: 719,00, letzter_tag: 2026-10-31 |
| Trend (Tag/Woche) | POSITIV | kurs: 3,97, ema20: 4,16, sma50: 4,00, sma200: 2,20 |
| Marktstruktur | POSITIV | hoch_20: 5,35, tief_20: 3,49, hoch_60: 5,35, tief_60: 1,58 |
| Momentum (RSI/MACD) | NEUTRAL | rsi14: 47,16, macd_histogramm: -0,09, macd_histogramm_vortag: -0,11 |
| Volumen (relativ/OBV) | NEGATIV | volumen_faktor_20: 0,64, obv_10_tage_steigend: False, tageskurs_gestiegen: True |
| Volatilität (ATR/Bollinger) | RISIKO | atr14: 0,37, atr14_prozent: 9,39, bollinger_breite_prozent: 25,83, risikostufe: HOCH |
| Marktphase (ADX) | NEUTRAL | adx14: 24,73, plus_di14: 14,76, minus_di14: 23,30, phase: TRENDPHASE |
| Unterstützung/Widerstand | NEUTRAL | unterstuetzung: 1,58, widerstand: 5,35, abstand_widerstand_prozent: 34,71, abstand_unterstuetzung_prozent: 151,42 |
| Einstiegsgeometrie (ATR/Risiko) | NEUTRAL | indikative_einstiegsbasis: 3,97, theoretischer_2atr_stop: 3,23, 60t_widerstand: 5,35, 60t_unterstuetzung: 1,58 |
| Relative Stärke zu BTC | NEUTRAL | rendite_30_tage_prozent: -7,06, btc_30_tage_prozent: -7,95, relative_starke_pp: 0,89, korrelation_60_tage: 0,44 |
| Orderbuch/Spread | NICHT_GEMESSEN | — |
| Risikokontrolle | OK | kaufkandidat_erlaubt: True, atr_prozent: 9,39 |

**Einordnung:**
- **Trend (Tag/Woche):** Tag: uneinheitlich; Abgeschlossene Wochen: aufwärts
- **Marktstruktur:** Swings: höhere Hochs/Tiefs; 20-Tage-Grenze: kein Ausbruch
- **Momentum (RSI/MACD):** RSI14 47.2 (über 70 = überkauft, nicht automatisch Verkauf); MACD-Histogramm ohne eindeutigen Schub
- **Volumen (relativ/OBV):** Volumen: 0.64× gegenüber 20 Tagen; 10-Tage-OBV: fallend oder gleich; Volumendaten sind börsenspezifisch, kein globales Krypto-Gesamtvolumen
- **Volatilität (ATR/Bollinger):** ATR14: 9.39% des Kurses; Bollinger-Bandbreite: 25.83%; Volatilität bestimmt Risiko/Positionsgröße, nicht die Kursrichtung
- **Marktphase (ADX):** ADX14 24.7: TRENDPHASE; DI-Richtung: ABWAERTS; ADX allein zeigt Trendstärke, keinen zukünftigen Gewinn
- **Unterstützung/Widerstand:** 60-Tage-Widerstand 5.3500 EUR, Distanz 34.71%; 60-Tage-Unterstützung 1.5796 EUR, Abstand 151.42%; Historische Niveaus sind keine garantierten Stop- oder Umkehrpunkte
- **Einstiegsgeometrie (ATR/Risiko):** Nur Szenario: Einstieg Schlusskurs 3.9715, Abstand Stop 2×ATR; Historischer 60-Tage-Widerstand 5.3500 (kein Kursziel); Indikatives Chance-Risiko-Verhältnis: 1.85; Schlusskurs-Stop/ATR schützt nicht vor Kurslücken, Spreads und Slippage
- **Relative Stärke zu BTC:** 30-Tage-Mehr-/Minderrendite zu BTC: +0.89 Prozentpunkte; 60-Tage-Korrelation zu BTC: 0.44; BTC ist der Vergleichsmaßstab, kein unabhängiger Kaufsignalgeber
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
