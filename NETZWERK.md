# Krypto Master Network – Zentrale Profi-Analyse

**Dieser Bericht enthält nur Analysen. Virtuelle Master-Orders stehen separat in `TRADING_STATUS.md`. Echtgeldhandel ist gesperrt.**

Erstellt (UTC): 2026-10-30T10:55:04+00:00  
Datenquelle: Nur abgeschlossene Kraken-Tageskerzen (optional separater Live-Orderbuch-Snapshot)  
Die Master-Einstufungen sind heuristische Beobachtungssignale, keine statistischen Wahrscheinlichkeiten.

## Master-Übersicht

| Coin | Trend | Struktur | Momentum | Volumen | ATR | Master |
|:--|:--|:--|:--|:--|--:|:--|
| BTC/EUR | POSITIV (+1) | NEGATIV (-1) | NEGATIV (-2) | NEGATIV (-2) | 2,53 % | ABWARTEN |
| ETH/EUR | NEUTRAL (+0) | NEGATIV (-2) | NEGATIV (-2) | POSITIV (+1) | 3,89 % | ABWARTEN |
| SOL/EUR | NEUTRAL (+0) | NEGATIV (-2) | NEGATIV (-2) | NEGATIV (-2) | 4,16 % | ABWARTEN |
| NEAR/EUR | POSITIV (+1) | NEUTRAL (+0) | NEGATIV (-1) | NEGATIV (-2) | 10,39 % | ABWARTEN |

## Einzelberichte der Spezialisten

### BTC/EUR · ABWARTEN

**Letzter Kurstag:** 2026-10-29

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
| Datenqualität | OK | kerzen: 719,00, letzter_tag: 2026-10-29 |
| Trend (Tag/Woche) | POSITIV | kurs: 69587,60, ema20: 72567,57, sma50: 72382,43, sma200: 63537,61 |
| Marktstruktur | NEGATIV | hoch_20: 75525,60, tief_20: 70635,10, hoch_60: 77520,90, tief_60: 64927,20 |
| Momentum (RSI/MACD) | NEGATIV | rsi14: 37,33, macd_histogramm: -358,22, macd_histogramm_vortag: -210,28 |
| Volumen (relativ/OBV) | NEGATIV | volumen_faktor_20: 2,57, obv_10_tage_steigend: False, tageskurs_gestiegen: False |
| Volatilität (ATR/Bollinger) | NEUTRAL | atr14: 1762,14, atr14_prozent: 2,53, bollinger_breite_prozent: 6,60, risikostufe: NORMAL |
| Marktphase (ADX) | NEUTRAL | adx14: 18,04, plus_di14: 16,38, minus_di14: 27,49, phase: SEITWAERTS/UNSICHER |
| Unterstützung/Widerstand | NEUTRAL | unterstuetzung: 64927,20, widerstand: 77520,90, abstand_widerstand_prozent: 11,40, abstand_unterstuetzung_prozent: 7,18 |
| Einstiegsgeometrie (ATR/Risiko) | NEUTRAL | indikative_einstiegsbasis: 69587,60, theoretischer_2atr_stop: 66063,33, 60t_widerstand: 77520,90, 60t_unterstuetzung: 64927,20 |
| Relative Stärke zu BTC | NEUTRAL | rendite_30_tage_prozent: -5,65, btc_30_tage_prozent: -5,65, relative_starke_pp: 0,00, korrelation_60_tage: 1,00 |
| Orderbuch/Spread | NICHT_GEMESSEN | — |
| Risikokontrolle | OK | kaufkandidat_erlaubt: True, atr_prozent: 2,53 |

**Einordnung:**
- **Trend (Tag/Woche):** Tag: uneinheitlich; Abgeschlossene Wochen: aufwärts
- **Marktstruktur:** Swings: gemischt; 20-Tage-Grenze: Durchbruch unten
- **Momentum (RSI/MACD):** RSI14 37.3 (über 70 = überkauft, nicht automatisch Verkauf); MACD-Histogramm zunehmend negativ
- **Volumen (relativ/OBV):** Volumen: 2.57× gegenüber 20 Tagen; 10-Tage-OBV: fallend oder gleich; Volumendaten sind börsenspezifisch, kein globales Krypto-Gesamtvolumen
- **Volatilität (ATR/Bollinger):** ATR14: 2.53% des Kurses; Bollinger-Bandbreite: 6.60%; Volatilität bestimmt Risiko/Positionsgröße, nicht die Kursrichtung
- **Marktphase (ADX):** ADX14 18.0: SEITWAERTS/UNSICHER; DI-Richtung: ABWAERTS; ADX allein zeigt Trendstärke, keinen zukünftigen Gewinn
- **Unterstützung/Widerstand:** 60-Tage-Widerstand 77520.9000 EUR, Distanz 11.40%; 60-Tage-Unterstützung 64927.2000 EUR, Abstand 7.18%; Historische Niveaus sind keine garantierten Stop- oder Umkehrpunkte
- **Einstiegsgeometrie (ATR/Risiko):** Nur Szenario: Einstieg Schlusskurs 69587.6000, Abstand Stop 2×ATR; Historischer 60-Tage-Widerstand 77520.9000 (kein Kursziel); Indikatives Chance-Risiko-Verhältnis: 2.25; Schlusskurs-Stop/ATR schützt nicht vor Kurslücken, Spreads und Slippage
- **Relative Stärke zu BTC:** 30-Tage-Mehr-/Minderrendite zu BTC: +0.00 Prozentpunkte; 60-Tage-Korrelation zu BTC: 1.00; BTC ist der Vergleichsmaßstab, kein unabhängiger Kaufsignalgeber
- **Orderbuch/Spread:** Kein L2-Snapshot angefordert; keine Liquiditätsaussage möglich
- **Risikokontrolle:** Kein aktuelles Orderbuch: tatsächliche Ausführbarkeit nicht geprüft

### ETH/EUR · ABWARTEN

**Letzter Kurstag:** 2026-10-29

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
| Datenqualität | OK | kerzen: 719,00, letzter_tag: 2026-10-29 |
| Trend (Tag/Woche) | NEUTRAL | kurs: 2011,34, ema20: 2146,53, sma50: 2235,28, sma200: 1876,63 |
| Marktstruktur | NEGATIV | hoch_20: 2299,93, tief_20: 2037,54, hoch_60: 2466,25, tief_60: 2036,02 |
| Momentum (RSI/MACD) | NEGATIV | rsi14: 31,83, macd_histogramm: -9,76, macd_histogramm_vortag: -5,79 |
| Volumen (relativ/OBV) | POSITIV | volumen_faktor_20: 1,66, obv_10_tage_steigend: True, tageskurs_gestiegen: False |
| Volatilität (ATR/Bollinger) | NEUTRAL | atr14: 78,32, atr14_prozent: 3,89, bollinger_breite_prozent: 11,20, risikostufe: NORMAL |
| Marktphase (ADX) | NEUTRAL | adx14: 28,55, plus_di14: 14,30, minus_di14: 29,92, phase: STARKER_TREND |
| Unterstützung/Widerstand | NEUTRAL | unterstuetzung: 2036,02, widerstand: 2466,25, abstand_widerstand_prozent: 22,62, abstand_unterstuetzung_prozent: -1,21 |
| Einstiegsgeometrie (ATR/Risiko) | NEUTRAL | indikative_einstiegsbasis: 2011,34, theoretischer_2atr_stop: 1854,69, 60t_widerstand: 2466,25, 60t_unterstuetzung: 2036,02 |
| Relative Stärke zu BTC | NEGATIV | rendite_30_tage_prozent: -14,80, btc_30_tage_prozent: -5,65, relative_starke_pp: -9,15, korrelation_60_tage: 0,93 |
| Orderbuch/Spread | NICHT_GEMESSEN | — |
| Risikokontrolle | OK | kaufkandidat_erlaubt: True, atr_prozent: 3,89 |

**Einordnung:**
- **Trend (Tag/Woche):** Tag: uneinheitlich; Abgeschlossene Wochen: uneinheitlich
- **Marktstruktur:** Swings: tiefere Hochs/Tiefs; 20-Tage-Grenze: Durchbruch unten
- **Momentum (RSI/MACD):** RSI14 31.8 (über 70 = überkauft, nicht automatisch Verkauf); MACD-Histogramm zunehmend negativ
- **Volumen (relativ/OBV):** Volumen: 1.66× gegenüber 20 Tagen; 10-Tage-OBV: steigend; Volumendaten sind börsenspezifisch, kein globales Krypto-Gesamtvolumen
- **Volatilität (ATR/Bollinger):** ATR14: 3.89% des Kurses; Bollinger-Bandbreite: 11.20%; Volatilität bestimmt Risiko/Positionsgröße, nicht die Kursrichtung
- **Marktphase (ADX):** ADX14 28.6: STARKER_TREND; DI-Richtung: ABWAERTS; ADX allein zeigt Trendstärke, keinen zukünftigen Gewinn
- **Unterstützung/Widerstand:** 60-Tage-Widerstand 2466.2500 EUR, Distanz 22.62%; 60-Tage-Unterstützung 2036.0200 EUR, Abstand -1.21%; Historische Niveaus sind keine garantierten Stop- oder Umkehrpunkte
- **Einstiegsgeometrie (ATR/Risiko):** Nur Szenario: Einstieg Schlusskurs 2011.3400, Abstand Stop 2×ATR; Historischer 60-Tage-Widerstand 2466.2500 (kein Kursziel); Indikatives Chance-Risiko-Verhältnis: 2.90; Schlusskurs-Stop/ATR schützt nicht vor Kurslücken, Spreads und Slippage
- **Relative Stärke zu BTC:** 30-Tage-Mehr-/Minderrendite zu BTC: -9.15 Prozentpunkte; 60-Tage-Korrelation zu BTC: 0.93; BTC ist der Vergleichsmaßstab, kein unabhängiger Kaufsignalgeber
- **Orderbuch/Spread:** Kein L2-Snapshot angefordert; keine Liquiditätsaussage möglich
- **Risikokontrolle:** Kein aktuelles Orderbuch: tatsächliche Ausführbarkeit nicht geprüft

### SOL/EUR · ABWARTEN

**Letzter Kurstag:** 2026-10-29

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
| Datenqualität | OK | kerzen: 719,00, letzter_tag: 2026-10-29 |
| Trend (Tag/Woche) | NEUTRAL | kurs: 85,30, ema20: 93,02, sma50: 96,59, sma200: 77,14 |
| Marktstruktur | NEGATIV | hoch_20: 101,06, tief_20: 88,06, hoch_60: 109,90, tief_60: 82,90 |
| Momentum (RSI/MACD) | NEGATIV | rsi14: 29,81, macd_histogramm: -0,59, macd_histogramm_vortag: -0,32 |
| Volumen (relativ/OBV) | NEGATIV | volumen_faktor_20: 1,67, obv_10_tage_steigend: False, tageskurs_gestiegen: False |
| Volatilität (ATR/Bollinger) | NEUTRAL | atr14: 3,54, atr14_prozent: 4,16, bollinger_breite_prozent: 12,87, risikostufe: NORMAL |
| Marktphase (ADX) | NEUTRAL | adx14: 28,84, plus_di14: 13,29, minus_di14: 30,57, phase: STARKER_TREND |
| Unterstützung/Widerstand | NEUTRAL | unterstuetzung: 82,90, widerstand: 109,90, abstand_widerstand_prozent: 28,84, abstand_unterstuetzung_prozent: 2,90 |
| Einstiegsgeometrie (ATR/Risiko) | NEUTRAL | indikative_einstiegsbasis: 85,30, theoretischer_2atr_stop: 78,21, 60t_widerstand: 109,90, 60t_unterstuetzung: 82,90 |
| Relative Stärke zu BTC | NEGATIV | rendite_30_tage_prozent: -18,78, btc_30_tage_prozent: -5,65, relative_starke_pp: -13,13, korrelation_60_tage: 0,86 |
| Orderbuch/Spread | NICHT_GEMESSEN | — |
| Risikokontrolle | OK | kaufkandidat_erlaubt: True, atr_prozent: 4,16 |

**Einordnung:**
- **Trend (Tag/Woche):** Tag: uneinheitlich; Abgeschlossene Wochen: uneinheitlich
- **Marktstruktur:** Swings: tiefere Hochs/Tiefs; 20-Tage-Grenze: Durchbruch unten
- **Momentum (RSI/MACD):** RSI14 29.8 (über 70 = überkauft, nicht automatisch Verkauf); MACD-Histogramm zunehmend negativ
- **Volumen (relativ/OBV):** Volumen: 1.67× gegenüber 20 Tagen; 10-Tage-OBV: fallend oder gleich; Volumendaten sind börsenspezifisch, kein globales Krypto-Gesamtvolumen
- **Volatilität (ATR/Bollinger):** ATR14: 4.16% des Kurses; Bollinger-Bandbreite: 12.87%; Volatilität bestimmt Risiko/Positionsgröße, nicht die Kursrichtung
- **Marktphase (ADX):** ADX14 28.8: STARKER_TREND; DI-Richtung: ABWAERTS; ADX allein zeigt Trendstärke, keinen zukünftigen Gewinn
- **Unterstützung/Widerstand:** 60-Tage-Widerstand 109.9000 EUR, Distanz 28.84%; 60-Tage-Unterstützung 82.9000 EUR, Abstand 2.90%; Historische Niveaus sind keine garantierten Stop- oder Umkehrpunkte
- **Einstiegsgeometrie (ATR/Risiko):** Nur Szenario: Einstieg Schlusskurs 85.3000, Abstand Stop 2×ATR; Historischer 60-Tage-Widerstand 109.9000 (kein Kursziel); Indikatives Chance-Risiko-Verhältnis: 3.47; Schlusskurs-Stop/ATR schützt nicht vor Kurslücken, Spreads und Slippage
- **Relative Stärke zu BTC:** 30-Tage-Mehr-/Minderrendite zu BTC: -13.13 Prozentpunkte; 60-Tage-Korrelation zu BTC: 0.86; BTC ist der Vergleichsmaßstab, kein unabhängiger Kaufsignalgeber
- **Orderbuch/Spread:** Kein L2-Snapshot angefordert; keine Liquiditätsaussage möglich
- **Risikokontrolle:** Kein aktuelles Orderbuch: tatsächliche Ausführbarkeit nicht geprüft

### NEAR/EUR · ABWARTEN

**Letzter Kurstag:** 2026-10-29

**Master-Begründung:** Kaufprüfung: 3 von 9 Bedingungen nicht erfüllt; Fehlt: Momentum positiv; Fehlt: Volumensignal mindestens neutral; Fehlt: OBV steigend; Orderbuch/Spread nicht geprüft (historische Tagesanalyse); Widerspruch: Trend positiv, Momentum negativ

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
| Datenqualität | OK | kerzen: 719,00, letzter_tag: 2026-10-29 |
| Trend (Tag/Woche) | POSITIV | kurs: 3,63, ema20: 4,21, sma50: 3,93, sma200: 2,18 |
| Marktstruktur | NEUTRAL | hoch_20: 5,35, tief_20: 3,80, hoch_60: 5,35, tief_60: 1,55 |
| Momentum (RSI/MACD) | NEGATIV | rsi14: 40,81, macd_histogramm: -0,11, macd_histogramm_vortag: -0,08 |
| Volumen (relativ/OBV) | NEGATIV | volumen_faktor_20: 1,39, obv_10_tage_steigend: False, tageskurs_gestiegen: False |
| Volatilität (ATR/Bollinger) | RISIKO | atr14: 0,38, atr14_prozent: 10,39, bollinger_breite_prozent: 30,55, risikostufe: HOCH |
| Marktphase (ADX) | NEUTRAL | adx14: 24,58, plus_di14: 14,56, minus_di14: 24,46, phase: TRENDPHASE |
| Unterstützung/Widerstand | NEUTRAL | unterstuetzung: 1,55, widerstand: 5,35, abstand_widerstand_prozent: 47,58, abstand_unterstuetzung_prozent: 134,48 |
| Einstiegsgeometrie (ATR/Risiko) | NEUTRAL | indikative_einstiegsbasis: 3,63, theoretischer_2atr_stop: 2,87, 60t_widerstand: 5,35, 60t_unterstuetzung: 1,55 |
| Relative Stärke zu BTC | NEGATIV | rendite_30_tage_prozent: -15,79, btc_30_tage_prozent: -5,65, relative_starke_pp: -10,14, korrelation_60_tage: 0,45 |
| Orderbuch/Spread | NICHT_GEMESSEN | — |
| Risikokontrolle | OK | kaufkandidat_erlaubt: True, atr_prozent: 10,39 |

**Einordnung:**
- **Trend (Tag/Woche):** Tag: uneinheitlich; Abgeschlossene Wochen: aufwärts
- **Marktstruktur:** Swings: höhere Hochs/Tiefs; 20-Tage-Grenze: Durchbruch unten
- **Momentum (RSI/MACD):** RSI14 40.8 (über 70 = überkauft, nicht automatisch Verkauf); MACD-Histogramm zunehmend negativ
- **Volumen (relativ/OBV):** Volumen: 1.39× gegenüber 20 Tagen; 10-Tage-OBV: fallend oder gleich; Volumendaten sind börsenspezifisch, kein globales Krypto-Gesamtvolumen
- **Volatilität (ATR/Bollinger):** ATR14: 10.39% des Kurses; Bollinger-Bandbreite: 30.55%; Volatilität bestimmt Risiko/Positionsgröße, nicht die Kursrichtung
- **Marktphase (ADX):** ADX14 24.6: TRENDPHASE; DI-Richtung: ABWAERTS; ADX allein zeigt Trendstärke, keinen zukünftigen Gewinn
- **Unterstützung/Widerstand:** 60-Tage-Widerstand 5.3500 EUR, Distanz 47.58%; 60-Tage-Unterstützung 1.5460 EUR, Abstand 134.48%; Historische Niveaus sind keine garantierten Stop- oder Umkehrpunkte
- **Einstiegsgeometrie (ATR/Risiko):** Nur Szenario: Einstieg Schlusskurs 3.6251, Abstand Stop 2×ATR; Historischer 60-Tage-Widerstand 5.3500 (kein Kursziel); Indikatives Chance-Risiko-Verhältnis: 2.29; Schlusskurs-Stop/ATR schützt nicht vor Kurslücken, Spreads und Slippage
- **Relative Stärke zu BTC:** 30-Tage-Mehr-/Minderrendite zu BTC: -10.14 Prozentpunkte; 60-Tage-Korrelation zu BTC: 0.45; BTC ist der Vergleichsmaßstab, kein unabhängiger Kaufsignalgeber
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
