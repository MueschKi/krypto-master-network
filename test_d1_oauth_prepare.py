"""Synthetic-only preparation and fail-closed OAuth boundary tests."""
import contextlib
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent/'cloudflare/scripts'))
import d1_oauth_prepare as prep
import encrypted_d1 as core
from test_d1_backup import fixture, BINDING, ORIGIN, KEY


class OAuthPreparationTests(unittest.TestCase):
    def test_online_modes_refuse_before_any_subprocess_or_tempfile(self):
        for operation in ('login', 'export'):
            with patch.object(prep, 'contract') as contract, patch.object(prep, 'rehearse') as rehearsal:
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(prep.main([operation]), 2)
                self.assertIn('OAUTH_SCOPE_OWNER_APPROVAL_REQUIRED', output.getvalue())
                contract.assert_not_called()
                rehearsal.assert_not_called()

    def test_prepare_never_calls_rehearsal_and_keeps_policy_blocked(self):
        with patch.object(prep, 'contract'), patch.object(prep, 'rehearse') as rehearsal:
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(prep.main(['prepare']), 2)
            self.assertIn('can cost money', output.getvalue())
            rehearsal.assert_not_called()

    def test_contract_failure_has_no_fallback(self):
        with patch.object(prep.subprocess, 'run', return_value=type('Result', (), {'returncode': 1})()):
            with self.assertRaises(core.BackupError): prep.contract()

    def test_contract_child_does_not_inherit_credentials_or_node_injection(self):
        with patch.dict(os.environ, {'CLOUDFLARE_API_TOKEN': 'CANARY', 'NODE_OPTIONS': 'CANARY', 'GH_TOKEN': 'CANARY'}):
            with patch.object(prep.subprocess, 'run', return_value=type('Result', (), {'returncode': 0})()) as run:
                prep.contract()
            self.assertNotIn('CANARY', str(run.call_args))
            self.assertTrue(set(run.call_args.kwargs['env']) <= {'PATH', 'SystemRoot'})

    def test_missing_export_and_network_or_auth_failure_do_not_publish(self):
        # HTTP 403, network interruption and denied OAuth have no retry path here.
        for failure in (core.BackupError('HTTP_403'), ConnectionError('private signed URL'), KeyboardInterrupt()):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                with patch.object(core, 'pack', side_effect=failure), patch.object(core, 'publish') as publish:
                    with self.assertRaises(BaseException):
                        prep.verified_package(root/'missing.sql', root, BINDING, ORIGIN, KEY, root/'public')
                    publish.assert_not_called()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(core.BackupError):
                prep.verified_package(root/'missing.sql', root, BINDING, ORIGIN, KEY, root/'public')
            self.assertFalse((root/'public').exists())

    def test_recovery_failure_in_either_pass_prevents_publication(self):
        for pass_number in (1, 2):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                sql = fixture(root)
                with patch.object(core, 'recover', side_effect=[None]*(pass_number-1)+[core.BackupError('RESTORE_MISMATCH')]):
                    with self.assertRaises(core.BackupError):
                        prep.verified_package(sql, root, BINDING, ORIGIN, KEY, root/'public')
                self.assertFalse((root/'public').exists())

    def test_rehearsal_real_crypto_and_cleanup(self):
        paths = []
        original = tempfile.TemporaryDirectory
        def record(**kwargs):
            temporary = original(**kwargs)
            paths.append(Path(temporary.name))
            return temporary
        with patch.object(prep.tempfile, 'TemporaryDirectory', side_effect=record):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                prep.rehearse()
            self.assertIn('SYNTHETIC ONLY', output.getvalue())
            self.assertNotIn(KEY, output.getvalue())
        self.assertGreaterEqual(len(paths), 3)
        self.assertTrue(all(not p.exists() for p in paths))

    def test_gpg_children_do_not_receive_inherited_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root/'synthetic.txt'
            source.write_text('synthetic only')
            with patch.dict(os.environ, {'CLOUDFLARE_API_TOKEN': 'PRIVATE_CANARY',
                                         'GH_TOKEN': 'PRIVATE_CANARY',
                                         'D1_BACKUP_PASSPHRASE': 'PRIVATE_CANARY',
                                         'NODE_OPTIONS': 'PRIVATE_CANARY'}):
                with patch.object(core.subprocess, 'run', wraps=core.subprocess.run) as run:
                    core.gpg(source, root/'cipher.gpg', KEY, root)
                for call in run.call_args_list:
                    self.assertNotIn('PRIVATE_CANARY', str(call.kwargs['env']))
                    self.assertNotIn(KEY, str(call.args))

    def test_no_online_launch_task_or_automatic_setup(self):
        text = (prep.ROOT/'.vscode/tasks.json').read_text()
        self.assertNotIn('"login"', text)
        self.assertNotIn('"export"', text)
        self.assertNotIn('folderOpen', text)
        self.assertNotIn('postCreateCommand', text)


if __name__ == '__main__': unittest.main()
