"""Offline regression tests for D1 EU jurisdiction verification and bootstrap safety.

No network, Cloudflare credentials, database or Worker required.
"""
import contextlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest import TestCase, mock

SOURCE = Path(__file__).resolve().parent / "cloudflare/scripts/setup_d1_ci.py"
spec = importlib.util.spec_from_file_location("setup_d1_ci", SOURCE)
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)

DB_UUID = "ad2a8b4c-1111-4222-8333-123456789abc"
ACCOUNT_ID = "0123456789abcdef0123456789abcdef"
TOKEN = "test-secret-must-never-be-logged"


class D1SetupSafetyTests(TestCase):
    def _details(self, jurisdiction="eu", name="kmn", identifier=DB_UUID, success=True):
        return json.dumps({"success": success, "result": {
            "name": name, "uuid": identifier, "jurisdiction": jurisdiction,
        }}).encode("utf-8")

    def _verify(self, payload):
        fake_response = SimpleNamespace(status=200, read=lambda limit: payload)
        with (mock.patch.dict(os.environ, {
                  "CLOUDFLARE_ACCOUNT_ID": ACCOUNT_ID,
                  "CLOUDFLARE_API_TOKEN": TOKEN,
              }),
              mock.patch.object(setup, "urlopen",
                                return_value=contextlib.nullcontext(fake_response)) as urlopen):
            setup.require_eu_jurisdiction(DB_UUID)
        return urlopen

    def test_eu_existing_database_accepted_only_when_verified(self):
        urlopen = self._verify(self._details())
        request = urlopen.call_args.args[0]
        self.assertEqual(
            request.full_url,
            f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/d1/database/{DB_UUID}",
        )
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 20)

    def test_wrong_missing_and_null_jurisdiction_fail_closed(self):
        for jurisdiction in ("us", "weur", None, ""):
            with self.subTest(jurisdiction=jurisdiction):
                with self.assertRaisesRegex(RuntimeError, "nicht nachweislich eu"):
                    self._verify(self._details(jurisdiction=jurisdiction))

    def test_unknown_name_and_uuid_mismatch_refused(self):
        for payload in (
            self._details(name="other"),
            self._details(identifier="11111111-1111-4111-8111-111111111111"),
        ):
            with self.assertRaises(RuntimeError):
                self._verify(payload)

    def test_unparsable_or_unsuccessful_d1_info_refused(self):
        for payload in (b'{"result": []}', b'not json', self._details(success=False)):
            with self.assertRaises(RuntimeError):
                self._verify(payload)

    def test_cloudflare_permission_error_is_sanitized(self):
        from urllib.error import HTTPError
        with (mock.patch.dict(os.environ, {
                  "CLOUDFLARE_ACCOUNT_ID": ACCOUNT_ID,
                  "CLOUDFLARE_API_TOKEN": TOKEN,
              }),
              mock.patch.object(setup, "urlopen",
                                side_effect=HTTPError("secret-url", 403, "secret-detail", {}, None))):
            with self.assertRaisesRegex(RuntimeError, "HTTP 403") as caught:
                setup.require_eu_jurisdiction(DB_UUID)
        self.assertNotIn("secret-url", str(caught.exception))
        self.assertNotIn(TOKEN, str(caught.exception))

    def test_duplicate_named_databases_refused(self):
        duplicate = json.dumps([
            {"name": "kmn", "uuid": DB_UUID},
            {"name": "kmn", "uuid": DB_UUID},
        ])
        with mock.patch.object(setup, "wrangler", return_value=duplicate):
            with self.assertRaisesRegex(RuntimeError, "Mehr als eine"):
                setup.find_database()

    def test_bootstrap_exactly_one_eu_create(self):
        with (mock.patch.object(setup, "ensure_credentials"),
              mock.patch.object(setup, "find_database", side_effect=[None, DB_UUID]),
              mock.patch.object(setup, "wrangler", return_value="") as cli,
              mock.patch.object(setup, "require_eu_jurisdiction") as jurisdiction,
              mock.patch("sys.argv", ["setup_d1_ci.py", "bootstrap"])):
            setup.main()
        cli.assert_called_once_with("d1", "create", "kmn", "--jurisdiction", "eu")
        jurisdiction.assert_called_once_with(DB_UUID)

    def test_existing_db_requires_eu_verification_without_create(self):
        with (mock.patch.object(setup, "ensure_credentials"),
              mock.patch.object(setup, "find_database", return_value=DB_UUID),
              mock.patch.object(setup, "wrangler") as cli,
              mock.patch.object(setup, "require_eu_jurisdiction") as jurisdiction,
              mock.patch("sys.argv", ["setup_d1_ci.py", "bootstrap"])):
            setup.main()
        cli.assert_not_called()
        jurisdiction.assert_called_once_with(DB_UUID)

    def test_failed_eu_verification_never_writes_deploy_config(self):
        with tempfile.TemporaryDirectory() as temp:
            with (mock.patch.object(setup, "ensure_credentials"),
                  mock.patch.object(setup, "find_database", return_value=DB_UUID),
                  mock.patch.object(setup, "require_eu_jurisdiction",
                                    side_effect=RuntimeError("unknown")),
                  mock.patch("sys.argv", ["setup_d1_ci.py", "resolve"])):
                with self.assertRaisesRegex(RuntimeError, "unknown"):
                    setup.main()
            self.assertFalse((Path(temp) / "wrangler.deploy.toml").exists())

    def test_workflow_requires_free_for_bootstrap_and_blocks_deployment(self):
        workflow = (Path(__file__).resolve().parent /
                    ".github/workflows/cloudflare-manual-deploy.yml").read_text()
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn('FREE_CONFIRMATION" != "FREE"', workflow)
        self.assertIn('Deployment blocked pending current-data recovery gate', workflow)
        self.assertNotIn('wrangler d1 migrations apply', workflow)
        self.assertNotIn('npx wrangler deploy --config', workflow)
        self.assertNotIn("\n  push:", workflow)
        self.assertNotIn("\n  schedule:", workflow)


if __name__ == "__main__":
    import unittest
    unittest.main()
