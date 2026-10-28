"""Potential trade geometry: NOT executable entry levels or guaranteed price targets."""
from net_core import Finding, latest, true_range


def analyze(symbol, df, context=None):
    price = latest(df['close'])
    atr = latest(true_range(df).rolling(14,min_periods=14).mean())
    previous_res = latest(df['high'].iloc[-61:-1].max())
    previous_sup = latest(df['low'].iloc[-61:-1].min())
    # Hypothetical setup; price can gap through a stop, 2 ATR is not a binding loss cap.
    theoretical_stop = price - 2 * atr
    risk_distance = price - theoretical_stop
    upside = previous_res - price
    rr = upside / risk_distance if risk_distance > 0 else None
    if upside <= 0:
        situation = 'AUSBRUCH/KEIN_ZIEL_AUS_HISTORISCHEM_WIDERSTAND'
    elif rr >= 2:
        situation = 'THEORETISCH_GUENSTIG'
    elif rr >= 1.5:
        situation = 'THEORETISCH_AKZEPTABEL'
    else:
        situation = 'UNGÜNSTIGER_ABSTAND_ZUM_WIDERSTAND'
    return Finding('Einstiegsgeometrie (ATR/Risiko)', 'NEUTRAL', 0,
                   {'indikative_einstiegsbasis':round(price,4),
                    'theoretischer_2atr_stop':round(theoretical_stop,4),
                    '60t_widerstand':round(previous_res,4),
                    '60t_unterstuetzung':round(previous_sup,4),
                    'indikatives_crv_zum_widerstand':round(rr,2) if rr is not None and upside>0 else None,
                    'bewertung':situation},
                   [f'Nur Szenario: Einstieg Schlusskurs {price:.4f}, Abstand Stop 2×ATR',
                    f'Historischer 60-Tage-Widerstand {previous_res:.4f} (kein Kursziel)',
                    f'Indikatives Chance-Risiko-Verhältnis: {rr:.2f}' if rr is not None and upside>0 else 'Kein sinnvoller R/R-Wert aus altem Widerstand',
                    'Schlusskurs-Stop/ATR schützt nicht vor Kurslücken, Spreads und Slippage'])
