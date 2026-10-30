"""Read existing accounts; emit SQL to stdout ONLY. Never writes source files."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from trade_engine import validate_state
from trailing_engine import _validate_trailing_positions
ROOT = Path(__file__).resolve().parents[2]
def snapshot_sql():
    statements = []
    for account, filename in [('master7','master_paper_state.json'), ('atr25','master_trailing_state.json')]:
        raw = (ROOT/'daten'/filename).read_bytes()
        data = json.loads(raw)
        validate_state(data)
        if account == 'atr25':
            _validate_trailing_positions(data)
        values = [account, datetime.now(timezone.utc).isoformat(), hashlib.sha256(raw).hexdigest(), json.dumps(data,ensure_ascii=False,allow_nan=False)]
        # INSERT only: importing twice must fail, never overwrite an existing snapshot.
        statements.append('INSERT INTO account_snapshots VALUES ('+', '.join("'"+v.replace("'", "''")+"'" for v in values)+');')
    return 'BEGIN TRANSACTION;\n'+'\n'.join(statements)+'\nCOMMIT;'
if __name__ == '__main__':
    print(snapshot_sql())
