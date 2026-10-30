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
fixture_root = Path(__file__).resolve().parents[1]/'tests/fixtures'
real = json.loads((fixture_root/'kraken-btc-eur-15m.json').read_text())
meta = json.loads((fixture_root/'kraken-btc-eur-15m.meta.json').read_text())
rows = [[float(r[0])*1000, *map(float, r[1:5]), float(r[6])] for r in real['result']['XXBTZEUR']][-720:]
cases.append(dict(symbol='BTC/EUR', timeframe='15m', name='real-Kraken-frozen', now=meta['snapshot_ms'], raw=rows, expected=analyse(rows,'15m',meta['snapshot_ms'])))
print(json.dumps(cases, allow_nan=False))

# Synthetic account pair ONLY: never load actual repository account data into fixtures.
import tempfile
from trade_engine import fresh_account
from account_snapshot import snapshot_sql
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    (root/'daten').mkdir()
    for filename in ('master_paper_state.json', 'master_trailing_state.json'):
        (root/'daten'/filename).write_text(json.dumps(fresh_account()))
    (Path(__file__).resolve().parents[1]/'tests/import.generated.json').write_text(json.dumps({'sql': snapshot_sql(root)}))
