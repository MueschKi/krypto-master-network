"""Public daily Kraken spot prices. No API key, no private trading endpoints."""
from __future__ import annotations

from datetime import datetime, timezone
import pandas as pd

SYMBOLS = ["BTC/EUR", "ETH/EUR", "SOL/EUR", "NEAR/EUR"]
DAY_MS = 86_400_000


def exchange():
    try:
        import ccxt
    except ImportError as exc:
        raise RuntimeError("Bitte 'pip install -r requirements.txt' ausführen.") from exc
    return ccxt.kraken({"enableRateLimit": True, "timeout": 20000})


def get_daily(exchange_obj=None) -> tuple[dict[str, pd.DataFrame], object]:
    ex = exchange_obj or exchange()
    ex.load_markets()
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    result = {}
    for symbol in SYMBOLS:
        if symbol not in ex.markets or not ex.markets[symbol].get("active", True):
            raise RuntimeError(f"Markt nicht verfügbar: {symbol}")
        raw = ex.fetch_ohlcv(symbol, timeframe="1d", limit=720)
        if not raw:
            raise RuntimeError(f"Keine Kursdaten von Kraken für {symbol}")
        data = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
        # Kraken also returns the incomplete current candle. Never use it in signals.
        data = data[data["timestamp"] + DAY_MS <= now_ms].copy()
        data.index = pd.to_datetime(data["timestamp"], unit="ms", utc=True)
        data = data[["open", "high", "low", "close", "volume"]].astype(float)
        data = data[~data.index.duplicated(keep="last")].sort_index()
        if len(data) < 250:
            raise RuntimeError(f"Nicht genug abgeschlossene Tageskerzen für {symbol}: {len(data)}")
        result[symbol] = data
    return result, ex


def aligned(data: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    dates = sorted(set.intersection(*(set(d.index) for d in data.values())))
    if len(dates) < 250:
        raise RuntimeError("Zu wenige gemeinsame tägliche Kerzen für alle Märkte")
    return {sym: df.loc[dates].copy() for sym, df in data.items()}


def synthetic_demo() -> dict[str, pd.DataFrame]:
    """Deterministic invented prices to verify execution offline, NOT market data."""
    import numpy as np
    rng = np.random.default_rng(42)
    idx = pd.date_range("2023-01-01", periods=620, freq="D", tz="UTC")
    out = {}
    for n, s in enumerate(SYMBOLS):
        returns = rng.normal(0.0002, 0.025 + 0.003 * n, len(idx))
        values = (100 + n * 30) * np.exp(np.cumsum(returns))
        opens = values * (1 + rng.normal(0, .004, len(idx)))
        high = np.maximum(opens, values) * 1.015
        low = np.minimum(opens, values) * 0.985
        vol = rng.lognormal(4, .7, len(idx))
        out[s] = pd.DataFrame({"open": opens, "high": high, "low": low,
                               "close": values, "volume": vol}, index=idx)
    return out
