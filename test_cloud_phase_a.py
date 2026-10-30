"""Snapshot import regression: original bytes/history survive; pair is atomic."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from trade_engine import fresh_account

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('account_snapshot', ROOT/'cloudflare/scripts/account_snapshot.py')
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)

class CloudPhaseATests(unittest.TestCase):
    def database(self):
        db = sqlite3.connect(':memory:')
        for migration in sorted((ROOT/'cloudflare/migrations').glob('*.sql')):
            db.executescript(migration.read_text())
        return db

    def test_account_export_preserves_every_source_byte_and_history(self):
        paths = [ROOT/'daten'/name for name in ('master_paper_state.json','master_trailing_state.json')]
        before = [p.read_bytes() for p in paths]
        sql = exporter.snapshot_sql()
        self.assertEqual([p.read_bytes() for p in paths], before)
        self.assertEqual(sql.count('INSERT INTO account_bundles'), 1)
        for forbidden in ('BEGIN TRANSACTION', 'COMMIT;', 'UPDATE ', 'DELETE ', 'REPLACE '):
            self.assertNotIn(forbidden, sql)
        db = self.database()
        db.execute(sql)
        payload, checksum = db.execute('SELECT payload,bundle_sha256 FROM account_bundles').fetchone()
        self.assertEqual(hashlib.sha256(payload.encode()).hexdigest(), checksum)
        for raw, account in zip(before, json.loads(payload)):
            self.assertEqual(account['payload'].encode(), raw)
            self.assertEqual(account['source_sha256'], hashlib.sha256(raw).hexdigest())
        with self.assertRaises(sqlite3.IntegrityError):
            db.execute(sql)
        self.assertEqual(db.execute('SELECT payload FROM account_bundles').fetchone()[0], payload)

    def test_second_invalid_or_missing_account_emits_no_partial_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'daten').mkdir()
            (root/'daten/master_paper_state.json').write_text(json.dumps(fresh_account()))
            with self.assertRaises(FileNotFoundError):
                exporter.snapshot_sql(root)
            (root/'daten/master_trailing_state.json').write_text('{broken')
            with self.assertRaises(ValueError):
                exporter.snapshot_sql(root)
