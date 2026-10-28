"""Distance to prior 60-day support and resistance, without look-ahead."""
from net_core import assessment, latest


def analyze(symbol, df, context=None):
    price = latest(df['close'])
    resistance = latest(df['high'].iloc[-61:-1].max())
    support = latest(df['low'].iloc[-61:-1].min())
    dist_res = 100 * (resistance / price - 1)
    dist_sup = 100 * (price / support - 1)
    near_res = 0 <= dist_res < 1.5
    near_sup = 0 <= dist_sup < 1.5
    breakout = dist_res < 0
    score = 1 if breakout else -1 if near_res else 0
    return assessment('Unterstützung/Widerstand', score,
                      {'unterstuetzung':support,'widerstand':resistance,
                       'abstand_widerstand_prozent':dist_res,
                       'abstand_unterstuetzung_prozent':dist_sup,
                       'nahe_widerstand':near_res,'nahe_unterstuetzung':near_sup},
                      [f'60-Tage-Widerstand {resistance:.4f} EUR, Distanz {dist_res:.2f}%',
                       f'60-Tage-Unterstützung {support:.4f} EUR, Abstand {dist_sup:.2f}%',
                       'Historische Niveaus sind keine garantierten Stop- oder Umkehrpunkte'])
