"""ATR, bands, and risk regime; not a price-direction vote."""
from net_core import Finding, moving_avg, latest, true_range


def analyze(symbol, df, context=None):
    close = df['close']
    tr = true_range(df)
    atr = latest(tr.rolling(14, min_periods=14).mean())
    price = latest(close)
    atr_pct = 100 * atr / price
    mid = latest(moving_avg(close, 20))
    std = latest(close.rolling(20).std())
    width = 100 * 4 * std / mid
    risk = 'HOCH' if atr_pct > 8 else 'ERHOEHT' if atr_pct > 5 else 'NORMAL'
    return Finding('Volatilität (ATR/Bollinger)', 'RISIKO' if risk != 'NORMAL' else 'NEUTRAL', 0,
                   {'atr14':round(atr,4),'atr14_prozent':round(atr_pct,2),
                    'bollinger_breite_prozent':round(width,2),'risikostufe':risk},
                   [f'ATR14: {atr_pct:.2f}% des Kurses',
                    f'Bollinger-Bandbreite: {width:.2f}%',
                    'Volatilität bestimmt Risiko/Positionsgröße, nicht die Kursrichtung'])
