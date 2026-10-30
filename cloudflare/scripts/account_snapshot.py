"""Read and validate BOTH source accounts; emit ONE atomic D1-compatible INSERT.

No BEGIN/COMMIT, no remote calls, no source writes and no overwrite/upsert.
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from trade_engine import validate_state
from trailing_engine import _validate_trailing_positions
ROOT = Path(__file__).resolve().parents[2]

def snapshot_sql(root=ROOT):
    accounts = []
    for account, filename in [('master7', 'master_paper_state.json'), ('atr25', 'master_trailing_state.json')]:
        raw = (root/'daten'/filename).read_bytes()
        data = json.loads(raw)
        validate_state(data)
        if account == 'atr25':
            _validate_trailing_positions(data)
        accounts.append({'account': account, 'source_sha256': hashlib.sha256(raw).hexdigest(),
                         'payload': raw.decode('utf-8')})
    # Emit nothing unless validation of BOTH originals has succeeded.
    payload = json.dumps(accounts, ensure_ascii=False, allow_nan=False)
    values = ['paper-readonly-v1', datetime.now(timezone.utc).isoformat(),
              hashlib.sha256(payload.encode('utf-8')).hexdigest(), payload]
    return 'INSERT INTO account_bundles VALUES (' + ', '.join("'" + v.replace("'", "''") + "'" for v in values) + ');'

if __name__ == '__main__':
    print(snapshot_sql())
