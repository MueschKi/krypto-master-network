"""Causal trend specialist; never reads future rows."""
def analyse(data):
    close = data.close
    values = {f'ema{n}': float(close.ewm(span=n, adjust=False).mean().iloc[-1])
              for n in (20, 50, 200)}
    a, b, c = values.values()
    signal = 'POSITIV' if close.iloc[-1] > a > b > c else (
        'NEGATIV' if close.iloc[-1] < a < b < c else 'NEUTRAL')
    return {'signal': signal, 'indicators': values,
            'reason': 'POSITIV: Schluss > EMA20 > EMA50 > EMA200; NEGATIV: umgekehrt; sonst NEUTRAL.'}
