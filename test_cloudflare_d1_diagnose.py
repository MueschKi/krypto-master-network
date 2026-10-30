"""Offline tests: diagnostics must never mutate Cloudflare or print tokens."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
from unittest import TestCase, mock

SOURCE = Path(__file__).resolve().parent / "cloudflare/scripts/diagnose_d1_ci.py"
spec = importlib.util.spec_from_file_location("diagnose_d1_ci", SOURCE)
diagnose = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnose)

ACCOUNT = "0123456789abcdef0123456789abcdef"
TOKEN = "a-SECRET-token-never-display"


class CloudflareD1DiagnosticTests(TestCase):
    def run_case(self, api_results, wrangler=None):
        out = io.StringIO()
        env = {"CLOUDFLARE_ACCOUNT_ID": ACCOUNT, "CLOUDFLARE_API_TOKEN": TOKEN}
        with (mock.patch.dict(os.environ, env, clear=True),
              mock.patch.object(diagnose, "api_get", side_effect=api_results) as api,
              mock.patch.object(diagnose.subprocess, "run", return_value=wrangler) as cli,
              contextlib.redirect_stdout(out)):
            outcome = diagnose.diagnose()
        transcript = out.getvalue()
        self.assertNotIn(TOKEN, transcript)
        self.assertNotIn(ACCOUNT, transcript)
        self.assertNotIn("private-error", transcript)
        return outcome, transcript, api, cli

    def test_missing_credentials_fail_without_api_calls(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "CLOUDFLARE_ACCOUNT_ID"):
                diagnose.credentials()

    def test_token_invalid_never_reads_d1(self):
        outcome, stdout, api, cli = self.run_case([
            (403, {"success": False, "errors": [{"code": 9109, "message": "private-error"}]})
        ])
        self.assertEqual(outcome, 1)
        self.assertEqual(api.call_count, 1)
        cli.assert_not_called()
        self.assertIn("Code 9109", stdout)

    def test_token_active_but_d1_forbidden_is_distinguished(self):
        outcome, stdout, api, cli = self.run_case([
            (200, {"success": True, "result": {"status": "active"}}),
            (403, {"success": False, "errors": [{"code": 10000, "message": "private-error"}]})
        ])
        self.assertEqual(outcome, 2)
        self.assertEqual(api.call_count, 2)
        cli.assert_not_called()
        self.assertIn("D1: Datenbankliste nicht lesbar", stdout)
        self.assertIn("10000", stdout)

    def test_rest_ok_wrangler_failure_is_distinguished(self):
        outcome, stdout, api, cli = self.run_case([
            (200, {"success": True, "result": {"status": "active"}}),
            (200, {"success": True, "result": []}),
        ], subprocess.CompletedProcess(args=["wrangler"], returncode=1, stdout="", stderr="private-error"))
        self.assertEqual(outcome, 3)
        self.assertIn("WRANGLER: D1-Liste fehlgeschlagen", stdout)
        cli.assert_called_once()

    def test_both_rest_and_wrangler_ok(self):
        outcome, stdout, api, cli = self.run_case([
            (200, {"success": True, "result": {"status": "active"}}),
            (200, {"success": True, "result": []}),
        ], subprocess.CompletedProcess(args=["wrangler"], returncode=0, stdout=json.dumps([]), stderr=""))
        self.assertEqual(outcome, 0)
        self.assertIn("DIAGNOSE OK", stdout)
        self.assertEqual(cli.call_args.args[0], ["npx", "wrangler", "d1", "list", "--json"])

    def test_untrusted_errors_print_numeric_codes_only(self):
        self.assertEqual(
            diagnose.error_codes({"errors": [
                {"code": "10000", "message": "private-error"},
                {"code": "secret", "message": "private-error"},
                {"code": 9109},
            ]}),
            "10000,9109",
        )

    def test_workflow_dispatched_diagnose_has_no_resource_mutations(self):
        text = (Path(__file__).resolve().parent /
                ".github/workflows/cloudflare-manual-deploy.yml").read_text()
        self.assertIn("          - diagnose", text)
        self.assertIn("if: inputs.operation == 'diagnose'", text)
        self.assertIn("python scripts/diagnose_d1_ci.py", text)
        self.assertNotIn("\n  push:", text)
        self.assertNotIn("\n  schedule:", text)


if __name__ == "__main__":
    import unittest
    unittest.main()
