"""Market regime agent: ADX14 for trend strength, directional index only descriptive."""
import numpy as np
import pandas as pd
from net_core import Finding, latest, true_range


def analyze(symbol, df, context=None):
    n=14
    high, low = df['high'], df['low']
    up, down = high.diff(), -low.diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0),up,0.),index=df.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0),down,0.),index=df.index)
    # Wilder's smoothed directional movement and true range.
    tr = true_range(df)
    alpha = 1 / n
    atr = tr.ewm(alpha=alpha,adjust=False,min_periods=n).mean().replace(0,np.nan)
    plus_di = 100 * plus_dm.ewm(alpha=alpha,adjust=False,min_periods=n).mean()/atr
    minus_di = 100 * minus_dm.ewm(alpha=alpha,adjust=False,min_periods=n).mean()/atr
    dx = (100 * (plus_di - minus_di).abs()/(plus_di + minus_di).replace(0,np.nan))
    adx = latest(dx.ewm(alpha=alpha,adjust=False,min_periods=n).mean())
    plus,minus=latest(plus_di),latest(minus_di)
    regime = 'STARKER_TREND' if adx >= 25 else 'TRENDPHASE' if adx >= 20 else 'SEITWAERTS/UNSICHER'
    direction='AUFWAERTS' if plus > minus else 'ABWAERTS' if minus > plus else 'UNBESTIMMT'
    return Finding('Marktphase (ADX)', 'NEUTRAL', 0,
                   {'adx14':round(adx,2),'plus_di14':round(plus,2),'minus_di14':round(minus,2),
                    'phase':regime,'richtung':direction},
                   [f'ADX14 {adx:.1f}: {regime}',f'DI-Richtung: {direction}',
                    'ADX allein zeigt Trendstärke, keinen zukünftigen Gewinn'])
