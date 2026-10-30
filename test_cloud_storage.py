"""Offline 30-day SQLite model; never touches production files or Cloudflare.

Exercises actual additive schema, immutable-candle trigger, full indexes, backup
and recovery. Size includes SQLite pages/indexes, not just JSON payload lengths.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('storage_snapshot', ROOT/'cloudflare/scripts/storage_snapshot.py')
snapshot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(snapshot)


def schema(db):
    for migration in sorted((ROOT/'cloudflare/migrations').glob('*.sql')):
        db.executescript(migration.read_text())


def audit_digest(db):
    h = hashlib.sha256()
    for table in ('analyses', 'runs', 'coverage_gaps', 'candle_batches', 'account_snapshots', 'account_bundles'):
        for row in db.execute(f'SELECT * FROM {table} ORDER BY 1,2,3'):
            h.update(json.dumps(row, separators=(',', ':')).encode())
    return h.hexdigest()


class StorageRecoveryTests(unittest.TestCase):
    def test_30_days_full_mtf_storage_budget_and_offline_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root/'source.sqlite'
            db = sqlite3.connect(path)
            schema(db)
            # Canary evidence must survive normalization, simulated cache retention,
            # and restore. No real account files are opened by this test.
            db.execute("INSERT INTO candle_batches VALUES('legacy','15m',0,0,'[]')")
            db.execute("INSERT INTO coverage_gaps VALUES('legacy','15m',0,900000,1,0)")
            sizes, events = [], 0
            units = [('15m', 900000), ('1h', 3600000), ('4h', 14400000), ('1d', 86400000)]
            # Stable closed prices: 720-bar windows overlap deterministically.
            # Two-kilobyte analysis payload allowance models actual signal JSON;
            # this is a synthetic model, not a live D1 growth measurement.
            payload = json.dumps({'quality': {'status': 'OK'}, 'padding': 'x'*2000})
            for day in range(30):
                for symbol in ('BTC/EUR', 'ETH/EUR', 'SOL/EUR', 'NEAR/EUR'):
                    for tf, duration in units:
                        for offset in range(0, 86400000, duration):
                            close = 1800000000000 // 86400000 * 86400000 + day*86400000 + offset
                            rows = [[close-(720-i)*duration, 100, 101, 99, 100, 10] for i in range(720)]
                            db.execute('''INSERT INTO raw_candles
                                SELECT ?,?,json_extract(value,'$[0]'),value FROM json_each(?) WHERE 1
                                ON CONFLICT(symbol,timeframe,open_utc) DO NOTHING''',
                                (symbol,tf,json.dumps(rows,separators=(',', ':'))))
                            db.execute('INSERT INTO analyses VALUES(?,?,?,?,?,?)', (symbol,tf,close,close,str(events),payload))
                            db.execute("INSERT INTO runs(id,scheduled,started,finished,status,symbol,timeframe,candle_close) VALUES(?,?,?,?,'OK',?,?,?)",
                                       (str(events),close,close,close,symbol,tf,close))
                            db.execute("INSERT INTO jobs VALUES(?,?,?,?,?,'OK',1)", (symbol,tf,close,str(events),close))
                            events += 1
                db.commit()
                sizes.append(db.execute('PRAGMA page_count').fetchone()[0]*db.execute('PRAGMA page_size').fetchone()[0])
            self.assertEqual(events, 508*30)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM raw_candles').fetchone()[0],16*720+events-16)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM analyses').fetchone()[0],events)
            self.assertLess(sizes[-1], 100_000_000)
            self.assertEqual(path.stat().st_size,sizes[-1])
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            before = audit_digest(db)
            snap = root/'backup.sqlite'
            manifest = snapshot.backup(path,snap)
            self.assertEqual(manifest['sha256'],snapshot.digest(snap))
            self.assertEqual(snap.stat().st_mode & 0o777,0o600)
            # ONLY a disposable local DB: proves UI evidence remains available
            # if cache retention is separately authorized in the future.
            db.execute('DELETE FROM raw_candles WHERE open_utc < (SELECT MAX(open_utc) FROM raw_candles)-86400000')
            db.commit()
            self.assertEqual(audit_digest(db),before)
            restored = root/'restored.sqlite'
            snapshot.restore(snap,restored)
            with sqlite3.connect(restored) as recovery:
                self.assertEqual(audit_digest(recovery),before)
                self.assertEqual(recovery.execute('SELECT COUNT(*) FROM raw_candles').fetchone()[0],16*720+events-16)
                self.assertEqual(recovery.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            # Both hash failure and overwrite fail without altering target data.
            with self.assertRaises(FileExistsError): snapshot.restore(snap,restored)
            with snap.open('ab') as out: out.write(b'corrupt')
            with self.assertRaises(ValueError): snapshot.restore(snap,root/'invalid.sqlite')
            self.assertFalse((root/'invalid.sqlite').exists())
            print(json.dumps({'model':'30d-720-bars', 'events':events,'sqlite_bytes':sizes[-1],
                              'raw_rows':16*720+events-16, 'daily_growth_last':sizes[-1]-sizes[-2]}))
            db.close()

    def test_crash_rollback_and_additive_legacy_compatibility(self):
        db = sqlite3.connect(':memory:')
        schema(db)
        db.execute("INSERT INTO candle_batches VALUES('BTC/EUR','15m',0,0,'legacy')")
        db.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            with db:
                db.execute("INSERT INTO raw_candles VALUES('BTC/EUR','15m',0,'[0,1,2,1,1,1]')")
                db.execute('INSERT INTO storage_guard(id) VALUES(2)')
        self.assertEqual(db.execute('SELECT COUNT(*) FROM raw_candles').fetchone()[0],0)
        self.assertEqual(db.execute('SELECT payload FROM candle_batches').fetchone()[0],'legacy')
        db.close()
