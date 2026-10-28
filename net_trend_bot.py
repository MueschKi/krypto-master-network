"""Independent 1-day / completed 1-week trend specialist."""
import pandas as pd
from net_core import assessment, moving_avg, latest


def analyze(symbol, df, context=None):
    close = df['close']
    ema20, sma50, sma200 = (latest(moving_avg(close, 20, ema=True)),
                            latest(moving_avg(close, 50)), latest(moving_avg(close, 200)))
    price = latest(close)
    daily_up = price > ema20 > sma50 and price > sma200
    daily_down = price < ema20 < sma50 and price < sma200
    # Calendar weeks end on Sunday. Latest partial week MUST be excluded.
    weekly = close.resample('W-SUN').last()
    if df.index[-1].weekday() != 6:
        weekly = weekly.iloc[:-1]
    w8 = latest(moving_avg(weekly, 8, ema=True))
    w20 = latest(moving_avg(weekly, 20))
    weekly_price = latest(weekly)
    weekly_up = w8 is not None and w20 is not None and weekly_price > w8 > w20
    weekly_down = w8 is not None and w20 is not None and weekly_price < w8 < w20
    score = (1 if daily_up else -1 if daily_down else 0) + (1 if weekly_up else -1 if weekly_down else 0)
    return assessment('Trend (Tag/Woche)', score,
                      {'kurs':price,'ema20':ema20,'sma50':sma50,'sma200':sma200,
                       'wochen_ema8':w8,'wochen_sma20':w20,
                       'tag_aufwaerts':daily_up,'woche_aufwaerts':weekly_up},
                      [f'Tag: {"Aufwärtstrend" if daily_up else "Abwärtstrend" if daily_down else "uneinheitlich"}',
                       f'Abgeschlossene Wochen: {"aufwärts" if weekly_up else "abwärts" if weekly_down else "uneinheitlich"}'])
