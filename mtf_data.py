"""Isolated public OHLCV reader and fail-closed quality gate; no trading imports."""
from datetime import datetime, timezone
import numpy as np
import pandas as pd

SYMBOLS = ('BTC/EUR', 'ETH/EUR', 'SOL/EUR', 'NEAR/EUR')
TIMEFRAMES = {'1d': 86400000, '4h': 14400000, '1h': 3600000, '15m': 900000}
COLUMNS = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
MIN_CANDLES = 250


def utc_now_ms():
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def iso(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat()


def quality(raw, timeframe, now_ms):
    """Never sort, deduplicate, fill gaps or substitute prices. UTC fixed grid."""
    duration = TIMEFRAMES[timeframe]
    facts = {'status': 'BLOCKIERT', 'reason': '', 'closed_count': 0,
             'excluded_unclosed': 0, 'latest_open_utc': None, 'latest_close_utc': None}
    try:
        if raw is None or len(raw) == 0:
            raise ValueError('KEINE_DATEN: keine OHLCV-Kerzen')
        data = pd.DataFrame(raw, columns=COLUMNS).astype(float)
        if not np.isfinite(data.timestamp).all():
            raise ValueError('Ungültige Zeitstempel')
        if (data.timestamp < 0).any() or (data.timestamp % duration != 0).any():
            raise ValueError('Zeitstempel außerhalb des UTC-Zeitrasters')
        if (data.timestamp.diff().dropna() <= 0).any():
            raise ValueError('Doppelte oder unsortierte Zeitstempel')
        # Exclude every candle whose close is later than the frozen snapshot.
        closed = data[data.timestamp + duration <= now_ms].copy()
        facts['excluded_unclosed'] = len(data) - len(closed)
        facts['closed_count'] = len(closed)
        if not closed.empty:
            facts.update(latest_open_utc=iso(closed.timestamp.iloc[-1]),
                         latest_close_utc=iso(closed.timestamp.iloc[-1] + duration))
        if len(closed) < MIN_CANDLES:
            raise ValueError(f'Zu wenig abgeschlossene Kerzen: {len(closed)} < {MIN_CANDLES}')
        if not np.isfinite(closed.to_numpy()).all():
            raise ValueError('NaN/inf in abgeschlossenen OHLCV-Daten')
        if (closed.timestamp.diff().dropna() != duration).any():
            raise ValueError('Datenlücke in abgeschlossenen Kerzen')
        if closed.timestamp.iloc[-1] != (now_ms // duration - 1) * duration:
            raise ValueError('Neueste abgeschlossene Kerze fehlt / Daten veraltet')
        if ((closed[['open', 'high', 'low', 'close']] <= 0).any().any()
                or (closed.volume < 0).any()
                or (closed.high < closed[['open', 'close', 'low']].max(axis=1)).any()
                or (closed.low > closed[['open', 'close', 'high']].min(axis=1)).any()):
            raise ValueError('Unplausible OHLCV-Werte')
        facts.update(status='OK', reason='Lückenlos, plausibel, aktuell und vollständig abgeschlossen')
        return closed.reset_index(drop=True), facts
    except (ValueError, TypeError, OverflowError) as exc:
        facts['reason'] = str(exc)
        return None, facts


def public_exchange():
    import ccxt
    return ccxt.kraken({'enableRateLimit': True, 'timeout': 20000})


def fetch_all(exchange_obj=None):
    """One market load + at most 16 sequential bounded OHLCV requests, no retries."""
    out = {}
    try:
        ex = exchange_obj if exchange_obj is not None else public_exchange()
        ex.load_markets()
    except Exception as exc:
        return {(s, tf): {'error': f'Marktliste: {type(exc).__name__}: {exc}'}
                for s in SYMBOLS for tf in TIMEFRAMES}
    for symbol in SYMBOLS:
        for tf in TIMEFRAMES:
            try:
                if symbol not in ex.markets or not ex.markets[symbol].get('active', True):
                    raise ValueError('Markt fehlt oder ist inaktiv')
                out[symbol, tf] = ex.fetch_ohlcv(symbol, timeframe=tf, limit=720)
            except Exception as exc:
                out[symbol, tf] = {'error': f'{type(exc).__name__}: {exc}'}
    return out


def synthetic(now_ms):
    """Fixed seed and UTC grid; never creates an exchange."""
    rng = np.random.default_rng(150)
    result = {}
    for n, symbol in enumerate(SYMBOLS):
        for tf, duration in TIMEFRAMES.items():
            timestamps = (now_ms // duration - np.arange(620, 0, -1)) * duration
            closes = (100 + 30*n) * np.exp(np.cumsum(rng.normal(.0003, .01, 620)))
            opens = np.r_[closes[0], closes[:-1]]
            result[symbol, tf] = np.column_stack((timestamps, opens,
                np.maximum(opens, closes)*1.005, np.minimum(opens, closes)*.995,
                closes, rng.uniform(1, 100, 620))).tolist()
    return result
