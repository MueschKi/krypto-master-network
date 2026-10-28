"""Market data quality specialist. Determines whether downstream analysis may run."""
from __future__ import annotations
import pandas as pd
import numpy as np
from net_core import Finding


def analyze(symbol: str, df: pd.DataFrame, reference_day=None) -> Finding:
    fail = []
    must = {'open', 'high', 'low', 'close', 'volume'}
    if not must.issubset(df.columns):
        return Finding('Datenqualität', 'BLOCKIERT', -2, {}, ['OHLCV-Spalten fehlen'])
    if len(df) < 260:
        fail.append(f'Nur {len(df)} Tage, mindestens 260 benötigt')
    if df.empty or not isinstance(df.index, pd.DatetimeIndex) or df.index.tz is None:
        fail.append('Ungültiger oder zeitlich nicht zugeordneter Kursindex')
        return Finding('Datenqualität', 'BLOCKIERT', -2, {'kerzen': len(df)}, fail)
    if df.index.has_duplicates or not df.index.is_monotonic_increasing:
        fail.append('Zeitreihe nicht eindeutig bzw. nicht chronologisch')
    d = df[['open','high','low','close','volume']].to_numpy(dtype=float)
    if not np.isfinite(d).all():
        fail.append('Fehlende oder unendliche Kurswerte')
    if (d[:, :4] <= 0).any() or (d[:, 4] < 0).any():
        fail.append('Nicht plausible Kurs- oder Volumenwerte')
    if (d[:, 1] < d[:, [0, 2, 3]].max(axis=1)).any() or (d[:, 2] > d[:, [0, 1, 3]].min(axis=1)).any():
        fail.append('High/Low inkonsistent')
    if len(df) > 1:
        gaps = (df.index[1:] - df.index[:-1]).days
        if (gaps > 2).any() or (gaps < 1).any():
            fail.append('Lücken oder doppelte Tagesabstände in den Daten')
    if reference_day is not None:
        last = df.index[-1].date()
        if (reference_day - last).days > 2 or last > reference_day:
            fail.append(f'Letzter abgeschlossener Kurstag {last}: veraltete / zukünftige Daten')
    if fail:
        return Finding('Datenqualität', 'BLOCKIERT', -2, {'kerzen': len(df), 'letzter_tag': df.index[-1].date().isoformat()}, fail)
    return Finding('Datenqualität', 'OK', 0, {'kerzen': len(df), 'letzter_tag': df.index[-1].date().isoformat()},
                   ['Abgeschlossene Tageskerzen plausibel; keine Echtzeitgarantie'])
