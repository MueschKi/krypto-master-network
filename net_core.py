"""Common, transparent output protocol for independent analysis agents.

No exchange order APIs, no account access, and no invented AI probabilities.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import math
import numpy as np
import pandas as pd


@dataclass
class Finding:
    agent: str
    signal: str  # POSITIV | NEGATIV | NEUTRAL | RISIKO | BLOCKIERT
    score: int  # -2 to +2, NON-probabilistic heuristic diagnostic
    facts: dict
    reasons: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def latest(value, default=None):
    try:
        out = float(value.iloc[-1] if hasattr(value, 'iloc') else value)
        return out if math.isfinite(out) else default
    except (TypeError, ValueError, IndexError, AttributeError):
        return default


def clean(v, digits=4):
    """JSON-safe numeric values; never convert missing data to false certainty."""
    if v is None:
        return None
    if isinstance(v, (np.integer, int)) and not isinstance(v, bool):
        return int(v)
    if isinstance(v, (np.floating, float)):
        v = float(v)
        return round(v, digits) if math.isfinite(v) else None
    return v


def moving_avg(s, n, ema=False):
    s = pd.to_numeric(s, errors='coerce')
    return s.ewm(span=n, adjust=False, min_periods=n).mean() if ema else s.rolling(n, min_periods=n).mean()


def assessment(agent, score, facts, reasons):
    score = max(-2, min(2, int(score)))
    label = 'POSITIV' if score > 0 else ('NEGATIV' if score < 0 else 'NEUTRAL')
    return Finding(agent, label, score, {k: clean(v) for k, v in facts.items()}, reasons)


def rsi(close: pd.Series, n=14):
    delta = close.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    # Wilder RSI: exponential smoothing with alpha=1/n.
    up_avg = up.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    down_avg = down.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    ratio = up_avg / down_avg.replace(0, np.nan)
    value = 100 - 100 / (1 + ratio)
    value = value.mask((down_avg == 0) & (up_avg > 0), 100)
    value = value.mask((down_avg == 0) & (up_avg == 0), 50)
    return value


def true_range(df):
    prior = df['close'].shift(1)
    return pd.concat([df['high'] - df['low'], (df['high'] - prior).abs(),
                      (df['low'] - prior).abs()], axis=1).max(axis=1)
