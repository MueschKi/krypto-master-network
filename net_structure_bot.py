"""Price action / market structure specialist. No fictitious liquidity levels."""
from net_core import assessment, latest


def analyze(symbol, df, context=None):
    close = df['close']
    # Levels prior to current candle, never based on the candle being assessed.
    high20 = latest(df['high'].iloc[-21:-1].max())
    low20 = latest(df['low'].iloc[-21:-1].min())
    high60 = latest(df['high'].iloc[-61:-1].max())
    low60 = latest(df['low'].iloc[-61:-1].min())
    price = latest(close)
    # Objective structure: compare two non-overlapping prior 20-day extrema.
    former_high = latest(df['high'].iloc[-41:-21].max())
    former_low = latest(df['low'].iloc[-41:-21].min())
    recent_high = high20
    recent_low = low20
    higher = recent_high > former_high and recent_low > former_low
    lower = recent_high < former_high and recent_low < former_low
    breakout = price > high20
    breakdown = price < low20
    score = (1 if higher else -1 if lower else 0) + (1 if breakout else -1 if breakdown else 0)
    return assessment('Marktstruktur', score,
                      {'hoch_20':high20,'tief_20':low20,'hoch_60':high60,'tief_60':low60,
                       'hoeher_hoch_und_tief':higher,'tiefer_hoch_und_tief':lower,
                       'ausbruch_20':breakout,'bruch_20':breakdown},
                      [f'Swings: {"höhere Hochs/Tiefs" if higher else "tiefere Hochs/Tiefs" if lower else "gemischt"}',
                       f'20-Tage-Grenze: {"Ausbruch oben" if breakout else "Durchbruch unten" if breakdown else "kein Ausbruch"}'])
