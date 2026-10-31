"""Synthetic offline-only diagnostic UI regression tests."""
from contextlib import redirect_stdout
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent / "cloudflare/scripts"))
import d1_offline_diagnostic as d
import encrypted_d1 as core


class OfflineDiagnosticTests(unittest.TestCase):
    def test_missing_node_exits_without_cloudflare(self):
        with patch.object(d.shutil, "which", return_value=None), redirect_stdout(io.StringIO()) as output:
            self.assertEqual(d.diagnose(), 1)
        self.assertIn("FAILED OFFLINE_WRANGLER NODE_MISSING", output.getvalue())

    def test_synthetic_stage_is_bounded_and_no_raw_errors(self):
        fake_error = core.BackupError("PRIVATE_SECRET_CANARY", stage="GPG_ENCRYPT")
        with patch.object(d.shutil, "which", return_value="/usr/bin/fake"), \
             patch.object(d.preparation, "contract"), \
             patch.object(d.preparation, "synthetic_sql", side_effect=fake_error), \
             patch.object(d.preparation, "ROOT", Path("/tmp/fake-kmn")), \
             patch.object(d.Path, "is_file", return_value=True), \
             redirect_stdout(io.StringIO()) as output:
            self.assertEqual(d.diagnose(), 1)
        self.assertIn("FAILED OFFLINE_GPG_ENCRYPT UNCLASSIFIED", output.getvalue())
        self.assertNotIn("PRIVATE_SECRET_CANARY", output.getvalue())

    def test_synthetic_sqlite_stages_are_safe_and_do_not_log_sql(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            safe = d.preparation.synthetic_sql(root)
            self.assertEqual(
                d.explain_synthetic_sql_import(safe, root),
                "FAILED OFFLINE_SQL_IMPORT CORE_IMPORT_DIFFERENCE")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "synthetic.sql"
            source.write_text("PRAGMA writable_schema=ON; -- PRIVATE_CANARY")
            output = d.explain_synthetic_sql_import(source, root)
            self.assertIn("STEP=SCRIPT_EXEC", output)
            self.assertIn("CODE=SQLITE_AUTH", output)
            self.assertNotIn("PRIVATE_CANARY", output)

    def test_diagnostic_handles_sqlite_build_without_extension_api(self):
        import sqlite3
        import tempfile
        real_connect = sqlite3.connect

        class MissingExtensionAPI:
            def __init__(self, *args, **kwargs):
                self.db = real_connect(*args, **kwargs)

            def __getattr__(self, name):
                if name == 'enable_load_extension':
                    raise AttributeError(name)
                return getattr(self.db, name)

            def __enter__(self):
                self.db.__enter__()
                return self

            def __exit__(self, *args):
                return self.db.__exit__(*args)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = d.preparation.synthetic_sql(root)
            with patch.object(d.sqlite3, 'connect', side_effect=MissingExtensionAPI):
                self.assertEqual(
                    d.explain_synthetic_sql_import(source, root),
                    'FAILED OFFLINE_SQL_IMPORT CORE_IMPORT_DIFFERENCE')

    def test_absent_gpg_is_diagnostic_not_crash(self):
        def which(name):
            return None if name == "gpg" else "/usr/bin/synthetic"
        with patch.object(d.shutil, "which", side_effect=which), \
             patch.object(d.preparation, "contract"), \
             patch.object(d.Path, "is_file", return_value=True), \
             redirect_stdout(io.StringIO()) as output:
            self.assertEqual(d.diagnose(), 1)
        self.assertIn("FAILED OFFLINE_GPG GPG_MISSING", output.getvalue())


if __name__ == "__main__":
    unittest.main()
