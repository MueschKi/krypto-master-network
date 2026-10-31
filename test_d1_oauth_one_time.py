"""Only local synthetic tests. No device login, network calls or real D1 access."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parent / "cloudflare/scripts"))

import d1_oauth_one_time as once
import d1_oauth_prepare as prepared
import encrypted_d1 as core


class FakeTTY(io.StringIO):
    def isatty(self):
        return True


class OAuthOnceTests(unittest.TestCase):
    def test_no_run_without_explicit_flag(self):
        with patch.object(once.sys, "argv", ["script"]), patch.object(once, "perform") as perform:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(once.main(), 2)
            perform.assert_not_called()

    def test_oauth_environment_excludes_inherited_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"CLOUDFLARE_API_TOKEN": "TOKEN_CANARY",
                                         "GH_TOKEN": "GH_CANARY",
                                         "GITHUB_TOKEN": "GH_CANARY",
                                         "NODE_OPTIONS": "INJECTION_CANARY"}):
                environment = once.isolated_environment(Path(tmp))
            self.assertNotIn("CLOUDFLARE_API_TOKEN", environment)
            self.assertNotIn("GITHUB_TOKEN", environment)
            self.assertNotIn("GH_TOKEN", environment)
            self.assertNotIn("NODE_OPTIONS", environment)
            self.assertEqual(environment["WRANGLER_SEND_METRICS"], "false")
            self.assertEqual(os.readlink(environment["WRANGLER_LOG_PATH"]), os.devnull)

    def test_oauth_type_refuses_api_token_and_malformed_json(self):
        for data in (b'{"type":"api_token","token":"CLOUDFLARE_CANARY"}',
                     b'{"type":"oauth","token":"not_oauth"}', b'not json', b''):
            with patch.object(once, "command", return_value=data):
                with self.assertRaises(once.Refused) as rejected:
                    once.oauth_token({})
                self.assertEqual(rejected.exception.stage, "AUTH_TYPE_INVALID")
        token = "cfoat_" + "A" * 40
        with patch.object(once, "command", return_value=json.dumps(
                {"type": "oauth", "token": token}).encode()):
            self.assertEqual(once.oauth_token({}), token)

    def test_exact_cloudflare_identity_and_eu_required(self):
        good = {"success": True, "errors": [], "result": {
            "uuid": once.DATABASE, "name": "kmn", "jurisdiction": "eu"}}
        class Response:
            status = 200
            def __init__(self, data):
                self.data = json.dumps(data).encode()
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, limit): return self.data[:limit]
        class Opener:
            def __init__(self, data): self.data = data
            def open(self, request, timeout):
                self.url = request.full_url
                self.method = request.get_method()
                return Response(self.data)
        with patch.object(once, "build_opener", return_value=Opener(good)):
            binding = once.identity("synthetic_OAUTH_TOKEN_NEVER_PRINT")
            self.assertEqual(binding["database_id"], once.DATABASE)
            self.assertEqual(binding["jurisdiction"], "eu")
        for changes in ({"jurisdiction":"auto"}, {"uuid":"wrong"}, {"name":"other"}):
            bad = json.loads(json.dumps(good))
            bad["result"].update(changes)
            with patch.object(once, "build_opener", return_value=Opener(bad)):
                with self.assertRaises(once.Refused):
                    once.identity("synthetic_OAUTH_TOKEN_NEVER_PRINT")

    def test_second_consent_missing_does_not_export_and_logs_out(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scratch = root / "scratch"
            scratch.mkdir()
            package = scratch / "node_modules/wrangler/package.json"
            package.parent.mkdir(parents=True)
            package.write_text('{"version":"4.156.0"}')
            with contextlib.ExitStack() as stack:
                stack.enter_context(patch.object(once, "CLOUDFLARE_DIR", scratch))
                stack.enter_context(patch.dict(os.environ, {"CODESPACES":"true"}))
                stack.enter_context(patch.object(once.sys, "stdin", FakeTTY()))
                output = stack.enter_context(contextlib.redirect_stdout(FakeTTY()))
                stack.enter_context(patch.object(once, "OUTPUT", root / "encrypted"))
                stack.enter_context(patch.object(prepared, "contract"))
                stack.enter_context(patch.object(once, "source_commit", return_value="a" * 40))
                stack.enter_context(patch.object(once, "oauth_token", return_value="cfoat_" + "A" * 40))
                stack.enter_context(patch.object(once, "identity", return_value=core.identity(once.ACCOUNT, once.DATABASE)))
                command = stack.enter_context(patch.object(once, "command", return_value=b""))
                stack.enter_context(patch.object(once, "consent", side_effect=[
                    None, None, once.Refused("OWNER_CONSENT_MISSING")]))
                export = stack.enter_context(patch.object(once.export_diag, "run"))
                with self.assertRaises(once.Refused):
                    once.perform(scratch, {})
                export.assert_not_called()
                self.assertEqual(sum("logout" in str(c.args) for c in command.call_args_list), 1)
                self.assertFalse((root/"encrypted").exists())
                self.assertNotIn("cfoat_", output.getvalue())

    def test_synthetic_native_export_runs_real_aes_and_four_restore_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scratch = root / "scratch"
            scratch.mkdir()
            package = scratch / "node_modules/wrangler/package.json"
            package.parent.mkdir(parents=True)
            package.write_text('{"version":"4.156.0"}')
            with contextlib.ExitStack() as stack:
                stack.enter_context(patch.object(once, "CLOUDFLARE_DIR", scratch))
                stack.enter_context(patch.dict(os.environ, {"CODESPACES":"true"}))
                stack.enter_context(patch.object(once.sys, "stdin", FakeTTY()))
                output = stack.enter_context(contextlib.redirect_stdout(FakeTTY()))
                stack.enter_context(patch.object(once, "OUTPUT", root / "encrypted"))
                stack.enter_context(patch.object(prepared, "contract"))
                stack.enter_context(patch.object(once, "source_commit", return_value="a" * 40))
                stack.enter_context(patch.object(once, "oauth_token", return_value="cfoat_" + "B" * 40))
                binding = core.identity(once.ACCOUNT, once.DATABASE)
                identity = stack.enter_context(patch.object(once, "identity", return_value=binding))
                command = stack.enter_context(patch.object(once, "command", return_value=b""))
                consent = stack.enter_context(patch.object(once, "consent"))
                stack.enter_context(patch.object(once, "key_from_operator", return_value="S"*48))
                def write_fake_native_export(argv, **kwargs):
                    self.assertEqual(argv[3:6], ["d1", "export", "kmn"])
                    self.assertIn("--remote", argv)
                    self.assertNotIn("CLOUDFLARE_API_TOKEN", kwargs["environment"])
                    prepared.synthetic_sql(scratch)
                export = stack.enter_context(patch.object(once.export_diag, "run", side_effect=write_fake_native_export))
                self.assertTrue(once.perform(scratch, {}))
                self.assertEqual(consent.call_count, 3)
                self.assertEqual(identity.call_count, 2)
                self.assertEqual(export.call_count, 1)
                self.assertEqual(sum("logout" in str(c.args) for c in command.call_args_list), 1)
                self.assertTrue((root/"encrypted"/"backup.tar.gz.gpg").is_file())
                self.assertTrue((root/"encrypted"/"ciphertext.sha256").is_file())
                stdout = output.getvalue()
                self.assertIn("VERIFIED", stdout)
                self.assertNotIn("cfoat_", stdout)
                self.assertNotIn("S"*48, stdout)


if __name__ == "__main__":
    unittest.main()
