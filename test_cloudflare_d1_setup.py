"""Offline regression tests for the Cloudflare D1 bootstrap safety gate.

No network, Cloudflare credentials, DB or Worker required.
"""
import importlib.util
import json
from pathlib import Path
import tempfile
from unittest import TestCase, mock

SOURCE = Path(__file__).resolve().parent / "cloudflare/scripts/setup_d1_ci.py"
spec = importlib.util.spec_from_file_location("setup_d1_ci", SOURCE)
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)

DB_UUID = "ad2a8b4c-1111-4222-8333-123456789abc"


class D1SetupSafetyTests(TestCase):
    def _details(self, jurisdiction="eu", name="kmn", identifier=DB_UUID):
        return json.dumps({"result": {
            "name": name,
            "uuid": identifier,
            "jurisdiction": jurisdiction,
        }})

    def test_eu_existing_database_accepted_only_when_verified(self):
        with mock.patch.object(setup, "wrangler", return_value=self._details()) as cli:
            setup.require_eu_jurisdiction(DB_UUID)
        cli.assert_called_once_with("d1", "info", "kmn", "--json", capture=True)

    def test_wrong_missing_and_null_jurisdiction_fail_closed(self):
        for jurisdiction in ("us", "weur", None, ""):
            with self.subTest(jurisdiction=jurisdiction):
                with mock.patch.object(setup, "wrangler", return_value=self._details(jurisdiction)):
                    with self.assertRaisesRegex(RuntimeError, "nicht nachweislich eu"):
                        setup.require_eu_jurisdiction(DB_UUID)

    def test_unknown_name_and_uuid_mismatch_refused(self):
        for details in (self._details(name="other"), self._details(identifier="11111111-1111-4111-8111-111111111111")):
            with mock.patch.object(setup, "wrangler", return_value=details):
                with self.assertRaises(RuntimeError):
                    setup.require_eu_jurisdiction(DB_UUID)

    def test_unparsable_d1_info_refused(self):
        with mock.patch.object(setup, "wrangler", return_value='{"result": []}'):
            with self.assertRaises(RuntimeError):
                setup.require_eu_jurisdiction(DB_UUID)

    def test_duplicate_named_databases_refused(self):
        duplicate = json.dumps([{"name": "kmn", "uuid": DB_UUID}, {"name": "kmn", "uuid": DB_UUID}])
        with mock.patch.object(setup, "wrangler", return_value=duplicate):
            with self.assertRaisesRegex(RuntimeError, "Mehr als eine"):
                setup.find_database()

    def test_bootstrap_exactly_one_eu_create(self):
        with (mock.patch.object(setup, "ensure_credentials"),
              mock.patch.object(setup, "find_database", side_effect=[None, DB_UUID]) as find,
              mock.patch.object(setup, "wrangler", return_value="") as cli,
              mock.patch.object(setup, "require_eu_jurisdiction") as jurisdiction,
              mock.patch("sys.argv", ["setup_d1_ci.py", "bootstrap"])):
            setup.main()
        find.assert_called()
        cli.assert_called_once_with("d1", "create", "kmn", "--jurisdiction", "eu")
        jurisdiction.assert_called_once_with(DB_UUID)

    def test_existing_db_requires_eu_verification_and_no_create(self):
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
            config = Path(temp) / "wrangler.toml"
            config.write_text('database_id = "00000000-0000-0000-0000-000000000000"')
            with (mock.patch.object(setup, "ensure_credentials"),
                  mock.patch.object(setup, "find_database", return_value=DB_UUID),
                  mock.patch.object(setup, "require_eu_jurisdiction", side_effect=RuntimeError("unknown")),
                  mock.patch("sys.argv", ["setup_d1_ci.py", "resolve"])):
                # EU validation must abort before touching configuration files.
                with self.assertRaisesRegex(RuntimeError, "unknown"):
                    setup.main()
            self.assertFalse((Path(temp) / "wrangler.deploy.toml").exists())

    def test_workflow_requires_explicit_free_and_deploy_confirmations(self):
        workflow = (Path(__file__).resolve().parent /
                    ".github/workflows/cloudflare-manual-deploy.yml").read_text()
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn('FREE_CONFIRMATION" != "FREE"', workflow)
        self.assertIn('DEPLOY_CONFIRMATION" != "DEPLOY_READ_ONLY"', workflow)
        self.assertNotIn("\n  push:", workflow)
        self.assertNotIn("\n  schedule:", workflow)


if __name__ == "__main__":
    import unittest
    unittest.main()
