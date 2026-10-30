"""Deterministic Python oracle; never accesses network/accounts."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mtf_data import synthetic, TIMEFRAMES
from net_timeframe_bot import analyse
NOW = 1793232000000
cases = []
for (symbol, tf), rows in synthetic(NOW).items():
    for name in ('seed150', 'flat', 'up', 'down', 'veto'):
        raw = rows if name == 'seed150' else [[r[0], 100 + (i*.1 if name == 'up' else -i*.1 if name == 'down' else 0), 150 if name == 'veto' else 101+(i*.1 if name == 'up' else -i*.1 if name == 'down' else 0), 50 if name == 'veto' else 99+(i*.1 if name == 'up' else -i*.1 if name == 'down' else 0), 100+(i*.1 if name == 'up' else -i*.1 if name == 'down' else 0), 10] for i,r in enumerate(rows)]
        cases.append(dict(symbol=symbol, timeframe=tf, name=name, now=NOW, raw=raw, expected=analyse(raw,tf,NOW)))
print(json.dumps(cases, allow_nan=False))
