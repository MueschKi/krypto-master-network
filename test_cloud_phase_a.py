"""Read-only snapshot regression: original bytes/history survive export."""
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent

class CloudPhaseATests(unittest.TestCase):
    def test_account_export_preserves_every_source_byte_and_history(self):
        paths = [ROOT/'daten'/name for name in ('master_paper_state.json','master_trailing_state.json')]
        before = [p.read_bytes() for p in paths]
        spec = importlib.util.spec_from_file_location('account_snapshot', ROOT/'cloudflare/scripts/account_snapshot.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sql = module.snapshot_sql()
        self.assertEqual([p.read_bytes() for p in paths], before)
        for raw in before:
            self.assertIn(hashlib.sha256(raw).hexdigest(), sql)
            self.assertIn(json.dumps(json.loads(raw),ensure_ascii=False,allow_nan=False).replace("'", "''"), sql)
        self.assertEqual(sql.count('INSERT INTO account_snapshots'), 2)
        self.assertNotIn('UPDATE', sql)
        self.assertNotIn('DELETE', sql)
