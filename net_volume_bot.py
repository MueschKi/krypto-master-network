"""Volume confirmation using relative OHLCV volume and on-balance volume."""
import numpy as np
from net_core import assessment, latest


def analyze(symbol, df, context=None):
    close = df['close']
    volume = df['volume']
    v_mean = float(volume.iloc[-21:-1].mean())
    v_rel = float(volume.iloc[-1]/v_mean) if v_mean > 0 else 0.0
    movement = np.sign(close.diff().fillna(0))
    obv = (movement * volume).cumsum()
    obv_positive = float(obv.iloc[-1] - obv.iloc[-11]) > 0
    price_up = close.iloc[-1] > close.iloc[-2]
    confirmed_up = v_rel >= 1.2 and price_up and obv_positive
    confirmed_down = v_rel >= 1.2 and not price_up and not obv_positive
    score = 2 if confirmed_up else -2 if confirmed_down else (1 if obv_positive else -1)
    return assessment('Volumen (relativ/OBV)', score,
                      {'volumen_faktor_20':v_rel,'obv_10_tage_steigend':obv_positive,
                       'tageskurs_gestiegen':bool(price_up)},
                      [f'Volumen: {v_rel:.2f}× gegenüber 20 Tagen',
                       f'10-Tage-OBV: {"steigend" if obv_positive else "fallend oder gleich"}',
                       'Volumendaten sind börsenspezifisch, kein globales Krypto-Gesamtvolumen'])
