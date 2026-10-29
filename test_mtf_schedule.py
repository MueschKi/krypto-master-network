"""Operational regressions using real local Git remotes, no network or accounts."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import mtf_snapshot as ops
from mtf_analysis import build_report

NOW = 1793232000000


@contextmanager
def cd(path):
    previous = Path.cwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(previous)


class SnapshotTests(unittest.TestCase):
    def test_workflow_routing_and_artifact_before_push(self):
        new = Path('.github/workflows/mtf-schedule.yml').read_text()
        old = Path('.github/workflows/master-paper.yml').read_text()
        self.assertIn("cron: '37 0,4,8,12,16,20 * * *'", new)
        self.assertIn('workflow_dispatch:', new)
        self.assertIn('python -m unittest discover -q', new)
        self.assertIn('retention-days: 7', new)
        self.assertIn('if-no-files-found: error', new)
        self.assertIn("always() && steps.analyse.outcome != 'skipped'", new)
        self.assertLess(new.index('actions/upload-artifact'), new.index('mtf_snapshot.py publish'))
        self.assertIn("github.ref == 'refs/heads/main'", new)
        self.assertIn('group: mtf-snapshot-main', new)
        self.assertIn("&& 'mtf-snapshot-main'", old)
        self.assertNotIn('trading.py', new)
        self.assertNotIn('secrets.', new)
        self.assertIn("cron: '17 4 * * *'", old)
        self.assertIn("cron: '47 6 * * *'", old)
        self.assertIn("github.event.inputs.modus || 'paper'", old)
        # Everything in the Paper mode execution and staging stays identical.
        expected = {'            paper|analyse)': '263691eedd4c04cb5d2cdb3f48abaf45ecc3c2c31b59b93e9e3db7c4b460a02f', '            demo|analyse|paper)': '4658a830acb065c1ed70c2ba799126021f1b2e3006ce84f7cfcd6251e6564a25'}
        for start, digest in expected.items():
            self.assertEqual(hashlib.sha256(old.split(start)[1].split(';;')[0].encode()).hexdigest(), digest)

    def test_run_discards_stale_report_and_diagnoses_crash(self):
        with tempfile.TemporaryDirectory() as tmp, cd(tmp):
            ops.write_bundle('.', build_report({}, NOW - 1000, 'analyse'))
            def crash(*args, **kwargs):
                self.assertFalse(Path(ops.PATHS[0]).exists())
                self.assertFalse(Path(ops.PATHS[1]).exists())
                raise subprocess.CalledProcessError(1, 'analyse')
            with patch('mtf_snapshot.subprocess.run', side_effect=crash), \
                 patch('mtf_snapshot.utc_now_ms', return_value=NOW), \
                 patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': str(Path(tmp)/'summary')}):
                with self.assertRaises(RuntimeError):
                    ops.run_snapshot('artifact')
            report = ops.load_bundle('artifact')
            self.assertEqual(report['classification'], 'BLOCKIERT')
            self.assertEqual(ops.timestamp(report).timestamp()*1000, NOW)
            self.assertIn('Ausführungsfehler', Path('artifact/ZEITFENSTER.md').read_text())
            self.assertIn('fehlgeschlagen', Path('summary').read_text())

    def test_missing_kraken_data_is_fresh_blocked_result(self):
        with tempfile.TemporaryDirectory() as tmp, cd(tmp):
            def analyse(*args, **kwargs):
                ops.write_bundle('.', build_report({}, NOW, 'analyse'))
            with patch('mtf_snapshot.subprocess.run', side_effect=analyse), \
                 patch('mtf_snapshot.utc_now_ms', return_value=NOW), \
                 patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': str(Path(tmp)/'summary')}):
                result = ops.run_snapshot('artifact')
            self.assertEqual(result['classification'], 'BLOCKIERT')
            self.assertEqual(result, ops.load_bundle('artifact'))
            self.assertEqual({str(p.relative_to('artifact')) for p in Path('artifact').rglob('*') if p.is_file()}, set(ops.PATHS))

    def test_stale_or_mismatched_output_never_becomes_fresh(self):
        with tempfile.TemporaryDirectory() as tmp, cd(tmp):
            def stale(*args, **kwargs):
                ops.write_bundle('.', build_report({}, NOW-1000, 'analyse'))
            with patch('mtf_snapshot.subprocess.run', side_effect=stale), \
                 patch('mtf_snapshot.utc_now_ms', return_value=NOW):
                with self.assertRaises(RuntimeError):
                    ops.run_snapshot('artifact')
            self.assertEqual(ops.load_bundle('artifact')['classification'], 'BLOCKIERT')
            Path('artifact/ZEITFENSTER.md').write_text('alter Bericht')
            with self.assertRaises(ValueError):
                ops.load_bundle('artifact')


class PublishTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.remote, self.repo, self.peer = (root/x for x in ('remote.git', 'repo', 'peer'))
        ops.git(root, 'init', '--bare', '--initial-branch=main', str(self.remote))
        ops.git(root, 'clone', str(self.remote), str(self.repo))
        for repo in (self.repo,):
            ops.git(repo, 'config', 'user.name', 'Test')
            ops.git(repo, 'config', 'user.email', 'test@example.invalid')
        (self.repo/'account').write_bytes(b'protected account\n')
        self.commit(self.repo, 'base')
        ops.git(self.repo, 'push', 'origin', 'main')
        ops.git(root, 'clone', str(self.remote), str(self.peer))
        ops.git(self.peer, 'config', 'user.name', 'Test')
        ops.git(self.peer, 'config', 'user.email', 'test@example.invalid')
        self.bundle = root/'bundle'
        ops.write_bundle(self.bundle, build_report({}, NOW, 'analyse'))

    def commit(self, repo, message):
        ops.git(repo, 'add', '.')
        ops.git(repo, 'commit', '-m', message)

    def remote_head(self):
        return ops.git(self.repo, 'ls-remote', 'origin', 'refs/heads/main').stdout.split()[0]

    def test_only_allowlisted_paths_and_dirty_checkout_untouched(self):
        (self.repo/'account').write_bytes(b'local uncommitted account\n')
        (self.bundle/'evil').write_text('must never be staged')
        self.assertTrue(ops.publish(self.bundle, self.repo))
        head = self.remote_head()
        changed = ops.git(self.repo, 'diff-tree', '--no-commit-id', '--name-only', '-r', head).stdout.splitlines()
        self.assertEqual(set(changed), set(ops.PATHS))
        self.assertEqual(ops.git(self.repo, 'show', f'{head}:account').stdout, 'protected account\n')
        self.assertEqual((self.repo/'account').read_bytes(), b'local uncommitted account\n')
        self.assertFalse(ops.publish(self.bundle, self.repo))

    def test_newer_remote_and_invalid_timestamp_fail_closed(self):
        ops.write_bundle(self.peer, build_report({}, NOW+1000, 'analyse'))
        self.commit(self.peer, 'newer report')
        ops.git(self.peer, 'push', 'origin', 'main')
        head = self.remote_head()
        self.assertFalse(ops.publish(self.bundle, self.repo))
        self.assertEqual(head, self.remote_head())
        path = self.peer/ops.PATHS[1]
        report = json.loads(path.read_text()); report['snapshot_utc'] = 'invalid'
        path.write_text(json.dumps(report))
        self.commit(self.peer, 'corrupt report')
        ops.git(self.peer, 'push', 'origin', 'main')
        with self.assertRaises(ValueError):
            ops.publish(self.bundle, self.repo)

    def race(self, change):
        real_git = ops.git
        pushes = []
        def racing(cwd, *args, **kwargs):
            if args[0] == 'push':
                pushes.append(args)
                if len(pushes) == 1:
                    change()
                    real_git(self.peer, 'push', 'origin', 'main')
            return real_git(cwd, *args, **kwargs)
        return patch('mtf_snapshot.git', side_effect=racing), pushes

    def test_parallel_paper_update_retained_with_retry(self):
        def change():
            (self.peer/'account').write_text('remote Paper update\n')
            self.commit(self.peer, 'Paper update')
        race, pushes = self.race(change)
        with race:
            self.assertTrue(ops.publish(self.bundle, self.repo))
        self.assertEqual(len(pushes), 2)
        self.assertEqual(ops.git(self.repo, 'show', f'{self.remote_head()}:account').stdout, 'remote Paper update\n')

    def test_parallel_newer_mtf_never_overwritten(self):
        def change():
            ops.write_bundle(self.peer, build_report({}, NOW+1000, 'analyse'))
            self.commit(self.peer, 'newer MTF')
        race, pushes = self.race(change)
        with race:
            self.assertFalse(ops.publish(self.bundle, self.repo))
        self.assertEqual(len(pushes), 1)

    def test_conflicting_remote_reports_abort(self):
        def change():
            ops.write_bundle(self.peer, build_report({}, NOW-1000, 'analyse'))
            self.commit(self.peer, 'conflicting MTF')
        race, pushes = self.race(change)
        with race, self.assertRaisesRegex(RuntimeError, 'Konflikt'):
            ops.publish(self.bundle, self.repo)
        self.assertEqual(len(pushes), 1)

    def test_push_denied_bounded_and_artifact_preserved(self):
        hook = self.remote/'hooks'/'pre-receive'
        hook.write_text('#!/bin/sh\nexit 1\n'); hook.chmod(0o755)
        before = {p: (self.bundle/p).read_bytes() for p in ops.PATHS}
        real = ops.git
        pushes = []
        def track(cwd, *args, **kwargs):
            if args[0] == 'push':
                pushes.append(args)
            return real(cwd, *args, **kwargs)
        with patch('mtf_snapshot.git', side_effect=track), self.assertRaises(RuntimeError):
            ops.publish(self.bundle, self.repo)
        self.assertEqual(len(pushes), 3)
        self.assertEqual(before, {p: (self.bundle/p).read_bytes() for p in ops.PATHS})


if __name__ == '__main__':
    unittest.main()
