"""ATR is magnitude, not market direction; threshold is a heuristic veto."""
import pandas as pd


def analyse(data):
    prev = data.close.shift(1)
    tr = pd.concat([data.high-data.low, (data.high-prev).abs(),
                    (data.low-prev).abs()], axis=1).max(axis=1)
    atr = float(tr.ewm(alpha=1/14, adjust=False).mean().iloc[-1])
    ratio = atr / float(data.close.iloc[-1])
    return {'signal': 'BLOCKIERT' if ratio > .1 else 'NEUTRAL',
            'indicators': {'atr14': atr, 'atr14_fraction': ratio},
            'reason': 'ATR14 / Schluss > 10 % blockiert (heuristisches Volatilitätslimit); sonst richtungsneutral.'}
