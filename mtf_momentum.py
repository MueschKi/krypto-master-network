"""RSI14 (Wilder smoothing) and MACD12/26/9, causal EMA seed at first value."""
def analyse(data):
    close = data.close
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean().iloc[-1]
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean().iloc[-1]
    rsi = 50. if gain == loss == 0 else (100. if loss == 0 else float(100-100/(1+gain/loss)))
    macd = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    line = float(macd.iloc[-1])
    signal_line = float(macd.ewm(span=9, adjust=False).mean().iloc[-1])
    histogram = line - signal_line
    signal = 'POSITIV' if rsi > 50 and histogram > 0 else (
        'NEGATIV' if rsi < 50 and histogram < 0 else 'NEUTRAL')
    return {'signal': signal, 'indicators': {'rsi14': rsi, 'macd': line,
            'macd_signal': signal_line, 'macd_histogram': histogram},
            'reason': 'POSITIV: RSI > 50 und MACD-Histogramm > 0; NEGATIV: beide darunter; sonst NEUTRAL.'}
