"""Executable counterexamples, not a simulated production backup implementation.

Only synthetic SQLite sources; no Cloudflare requests, credentials or writers.
"""
from contextlib import ExitStack, redirect_stdout
import io
import os
from pathlib import Path
import sqlite3
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_d1_backup import ci, core, fixture, BINDING, ORIGIN, KEY, SCRIPTS


class ReadBackupRefusalTests(unittest.TestCase):
    def test_even_full_consent_cannot_bypass_refusal_or_touch_any_resource(self):
        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ, {
                'BACKUP_CONFIRMATION': 'BACKUP_READ_ONLY_KMN',
                'MAINTENANCE_CONFIRMATION': 'OWNER_CONFIRMED_MAINTENANCE',
                'D1_BACKUP_PASSPHRASE': KEY, 'RUNNER_TEMP': tmp,
            }, clear=True))
            blocked = [stack.enter_context(patch.object(module, name)) for module, name in (
                (ci, 'context'), (core, 'identity'), (ci, 'remote_verify'),
                (ci, 'urlopen'), (ci.d1_read_probe, 'run'),
                (ci.backup_preflight, 'verify'), (ci, 'quiet'),
                (ci, 'backup'), (ci, 'export_sql'), (ci, 'recovery'),
                (core, 'pack'), (core, 'recover'), (core, 'publish'),
                (ci.tempfile, 'TemporaryDirectory'),
            )]
            output = stack.enter_context(redirect_stdout(io.StringIO()))
            with self.assertRaises(core.BackupError) as caught:
                ci.main(['backup-readonly', '--publish-dir', tmp+'/artifact'])
            self.assertEqual(core.safe_failure(caught.exception),
                             'FAILED stage=D1_READ_CONSISTENCY_UNPROVEN')
            self.assertEqual(output.getvalue(), '')
            for call in blocked:
                call.assert_not_called()
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_cli_nonzero_no_success_no_artifact_with_or_without_consent(self):
        for consent in ('', 'BACKUP_READ_ONLY_KMN', 'EXPORT_EXISTING_KMN'):
            with tempfile.TemporaryDirectory() as tmp:
                result = subprocess.run(
                    [sys.executable, str(SCRIPTS/'d1_backup_ci.py'), 'backup-readonly',
                     '--publish-dir', tmp+'/artifact'],
                    env={'PATH': os.defpath, 'RUNNER_TEMP': tmp,
                         'BACKUP_CONFIRMATION': consent, 'D1_BACKUP_PASSPHRASE': KEY},
                    capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, '')
                self.assertEqual(result.stderr, 'FAILED stage=D1_READ_CONSISTENCY_UNPROVEN\n')
                self.assertEqual(list(Path(tmp).iterdir()), [])


class ReadBackupCounterexamples(unittest.TestCase):
    def test_equal_boundary_scans_and_keyset_counts_can_hide_impossible_snapshot(self):
        with sqlite3.connect(':memory:') as source:
            source.executescript('CREATE TABLE t(id INTEGER PRIMARY KEY,v TEXT);'
                                 "INSERT INTO t VALUES(1,'A'),(2,'A');")
            scan = lambda: source.execute('SELECT * FROM t ORDER BY id').fetchall()
            before = scan()
            page1 = source.execute('SELECT * FROM t ORDER BY id LIMIT 1').fetchall()
            # One atomic writer transaction: the source is AA, then BB, then AA.
            source.execute("UPDATE t SET v='B'")
            source.commit()
            page2 = source.execute('SELECT * FROM t WHERE id>? ORDER BY id LIMIT 1',
                                   (page1[-1][0],)).fetchall()
            source.execute("UPDATE t SET v='A'")
            source.commit()
            self.assertEqual(before, scan())
            extract = page1 + page2
            self.assertEqual([row[0] for row in extract], [1, 2])
            self.assertEqual(len(extract), len(before))
            self.assertEqual(extract, [(1, 'A'), (2, 'B')])
            # No source state ever contained this perfectly paginated result.
            self.assertNotIn(extract, [before, [(1, 'B'), (2, 'B')]])

    def test_sqlite_type_encoding_traps_are_source_observable(self):
        with sqlite3.connect(':memory:') as source:
            nul = "quote'\n\x00🔒"
            # quote() silently loses the suffix at NUL; hex(TEXT bytes) retains it.
            quoted, encoded = source.execute('SELECT quote(?),hex(CAST(? AS BLOB))',
                                             (nul, nul)).fetchone()
            self.assertNotIn('🔒', quoted)
            self.assertEqual(bytes.fromhex(encoded).decode('utf-8'), nul)
            for integer in (-2**63, 2**63-1):
                typed = source.execute('SELECT typeof(?),CAST(? AS TEXT)',
                                       (integer, integer)).fetchone()
                self.assertEqual(typed, ('integer', str(integer)))
            self.assertNotEqual(int(float(2**63-1)), 2**63-1)
            # SQLite quote(REAL) is not a general bit-preserving wire codec.
            value = -0.0
            literal = source.execute('SELECT quote(?)', (value,)).fetchone()[0]
            restored = source.execute('SELECT '+literal).fetchone()[0]
            self.assertNotEqual(struct.pack('>d', value), struct.pack('>d', restored))

    def test_aes256_and_independent_restores_cannot_prove_an_already_lossy_extract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sql = fixture(root)
            source_path = root/'source.sqlite'
            core.import_sql(sql, source_path)
            original = 'before\x00after🔒'
            with sqlite3.connect(source_path) as source:
                source.execute('UPDATE account_snapshots SET payload=?', (original,))
                source.commit()
                # Deliberately broken extractor; not used in production.
                sql.write_text('\n'.join(source.iterdump()))
                self.assertEqual(source.execute('SELECT payload FROM account_snapshots').fetchone()[0], original)
            scratch = root/'pack'; scratch.mkdir()
            cipher, proof = core.pack(sql, scratch, BINDING, ORIGIN, KEY)
            restore = root/'restore'; restore.mkdir()
            self.assertEqual(core.recover(cipher, core.storage_snapshot.digest(cipher),
                                          restore, BINDING, ORIGIN, KEY), proof)
            for name in ('sql-restored.sqlite', 'snapshot-restored.sqlite'):
                with sqlite3.connect(restore/name) as restored:
                    self.assertEqual(restored.execute('SELECT payload FROM account_snapshots').fetchone()[0], 'before')
            self.assertEqual(core.summary(restore/'sql-restored.sqlite'),
                             core.summary(restore/'snapshot-restored.sqlite'))
            self.assertNotEqual(core.summary(source_path), proof['summary'])
