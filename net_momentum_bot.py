"""Independent RSI and MACD momentum specialist."""
from net_core import assessment, moving_avg, latest, rsi


def analyze(symbol, df, context=None):
    close = df['close']
    r = latest(rsi(close, 14))
    macd = moving_avg(close, 12, ema=True) - moving_avg(close, 26, ema=True)
    macd_sig = moving_avg(macd, 9, ema=True)
    hist = latest(macd - macd_sig)
    hist_prev = latest((macd - macd_sig).iloc[:-1])
    rsi_score = 1 if 50 < r < 70 else -1 if r < 40 else 0
    macd_score = 1 if hist > 0 and hist > hist_prev else -1 if hist < 0 and hist < hist_prev else 0
    return assessment('Momentum (RSI/MACD)', rsi_score + macd_score,
                      {'rsi14':r, 'macd_histogramm':hist,
                       'macd_histogramm_vortag':hist_prev},
                      [f'RSI14 {r:.1f} (über 70 = überkauft, nicht automatisch Verkauf)',
                       f'MACD-Histogramm {"zunehmend positiv" if macd_score > 0 else "zunehmend negativ" if macd_score < 0 else "ohne eindeutigen Schub"}'])
