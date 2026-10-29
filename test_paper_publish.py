"""Real two-clone races against a local bare remote; no GitHub writes."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import paper_publish as ops
from trade_engine import fresh_account, run_paper
from test_trading import report, quotes


class PaperPublishTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.remote, self.repo, self.peer = (root/n for n in ('remote.git','repo','peer'))
        ops.git(root, 'init', '--bare', '--initial-branch=main', str(self.remote))
        ops.git(root, 'clone', str(self.remote), str(self.repo))
        self.configure(self.repo)
        (self.repo/'daten').mkdir()
        for p in ops.ACCOUNTS:
            s = fresh_account()
            if 'trailing' in p: s['exit_policy'] = 'atr_trailing_2_5_close'
            (self.repo/p).write_text(json.dumps(s))
        for p in ops.REPORTS: (self.repo/p).write_text('old report')
        (self.repo/'ZEITFENSTER.md').write_text('old MTF')
        self.commit(self.repo)
        ops.git(self.repo, 'push', 'origin', 'main')
        ops.git(root, 'clone', str(self.remote), str(self.peer)); self.configure(self.peer)
        # Create output without committing it: HEAD must still describe input state.
        for p in ops.ACCOUNTS:
            s, _ = run_paper(fresh_account(), report(), quotes())
            if 'trailing' in p: s['exit_policy'] = 'atr_trailing_2_5_close'
            (self.repo/p).write_text(json.dumps(s))
        for p in ops.REPORTS: (self.repo/p).write_text('new report')
        (self.repo/'unrelated').write_text('private unstaged file')
        self.before = ops.git(self.repo, 'status', '--porcelain').stdout

    def configure(self, repo):
        ops.git(repo, 'config', 'user.name', 'Test')
        ops.git(repo, 'config', 'user.email', 'test@example.invalid')

    def commit(self, repo):
        ops.git(repo, 'add', '.'); ops.git(repo, 'commit', '-m', 'test')

    def head(self): return ops.git(self.repo,'ls-remote','origin','refs/heads/main').stdout.split()[0]

    def race(self, path):
        real = ops.git; pushes = []
        def racing(cwd, *args, **kwargs):
            if args[0] == 'push':
                pushes.append(args)
                if len(pushes) == 1:
                    if path in ops.ACCOUNTS:
                        state = json.loads((self.repo/path).read_text())
                        (self.peer/path).write_text(json.dumps(state))
                    else: (self.peer/path).write_text('concurrent MTF')
                    self.commit(self.peer)
                    real(self.peer,'push','origin','main')
            return real(cwd,*args,**kwargs)
        return patch('paper_publish.git',side_effect=racing), pushes

    def test_parallel_mtf_retained_and_only_allowlist_committed(self):
        race, pushes = self.race('ZEITFENSTER.md')
        with race: self.assertTrue(ops.publish(self.repo,self.repo))
        self.assertEqual(len(pushes),2)
        head = self.head()
        self.assertEqual(ops.git(self.repo,'show',f'{head}:ZEITFENSTER.md').stdout,'concurrent MTF')
        changed = ops.git(self.repo,'diff-tree','--no-commit-id','--name-only','-r',head).stdout.splitlines()
        self.assertEqual(set(changed),set(ops.PATHS))
        self.assertEqual(ops.git(self.repo,'status','--porcelain').stdout,self.before)

    def test_parallel_either_account_aborts_without_double_booking(self):
        race, pushes = self.race(ops.ACCOUNTS[1])
        with race, self.assertRaisesRegex(RuntimeError,'Konflikt'): ops.publish(self.repo,self.repo)
        self.assertEqual(len(pushes),1)
        saved = json.loads(ops.git(self.repo,'show',f'{self.head()}:{ops.ACCOUNTS[1]}').stdout)
        self.assertEqual(len(saved['equity_history']),1)

    def test_account_changed_before_first_fetch_also_aborts(self):
        path = ops.ACCOUNTS[0]
        (self.peer/path).write_text((self.repo/path).read_text())
        self.commit(self.peer); ops.git(self.peer,'push','origin','main')
        head = self.head()
        with self.assertRaisesRegex(RuntimeError,'Konflikt'): ops.publish(self.repo,self.repo)
        self.assertEqual(self.head(),head)

    def test_denied_push_bounded_and_no_data_lost(self):
        hook = self.remote/'hooks/pre-receive'; hook.write_text('#!/bin/sh\nexit 1\n'); hook.chmod(0o755)
        real = ops.git; pushes = []
        def tracked(cwd,*args,**kw):
            if args[0]=='push': pushes.append(args)
            return real(cwd,*args,**kw)
        with patch('paper_publish.git',side_effect=tracked), self.assertRaisesRegex(RuntimeError,'FAILURE'):
            ops.publish(self.repo,self.repo)
        self.assertEqual(len(pushes),3)
        self.assertEqual(ops.git(self.repo,'status','--porcelain').stdout,self.before)

    def test_analysis_never_publishes_accounts(self):
        self.assertTrue(ops.publish(self.repo,self.repo,mode='analyse'))
        head = self.head()
        saved = json.loads(ops.git(self.repo,'show',f'{head}:{ops.ACCOUNTS[0]}').stdout)
        self.assertIsNone(saved['last_processed_day'])
        changed = ops.git(self.repo,'diff-tree','--no-commit-id','--name-only','-r',head).stdout.splitlines()
        self.assertEqual(set(changed),set(ops.REPORTS[-2:]))

    def test_cli_reports_failure(self):
        with patch('sys.argv',['paper_publish.py','--branch','main']), patch.object(ops,'publish',side_effect=RuntimeError('denied')):
            self.assertEqual(ops.main(),1)

    def test_missing_output_aborts_before_push(self):
        (self.repo/ops.ACCOUNTS[0]).unlink()
        head = self.head()
        with self.assertRaises(FileNotFoundError): ops.publish(self.repo,self.repo)
        self.assertEqual(head,self.head())
