"""Offline-only Codespaces diagnostics. Safe fixed status codes, no secrets.

This program never contacts Cloudflare, loads OAuth tokens, or reads the real D1.
Use the VS Code task; no terminal copy/paste required.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import sys
import tempfile

import d1_oauth_prepare as preparation
import encrypted_d1 as core

SAFE_CODES = frozenset({
    "GPG_MISSING", "KEY_MISSING_OR_INVALID", "LOCAL_IMPORT_FAILED",
    "REQUIRED_HISTORY_EMPTY", "SNAPSHOT_PARITY_FAILED", "CIPHERTEXT_TOO_LARGE",
    "ENCRYPT_FAILED", "DECRYPT_FAILED", "AUTHENTICATION_FAILED",
    "MIGRATION_HISTORY_MISSING", "MIGRATION_HISTORY_UNEXPECTED",
    "TABLE_SET_UNEXPECTED", "TABLE_SCHEMA_UNEXPECTED",
    "RESTORE_PARITY_FAILED", "OAUTH_CONTRACT_REVIEW_REQUIRED",
})
SAFE_STAGES = frozenset({
    "ENV_CONTEXT", "SECRET_FORMAT", "SQL_IMPORT", "SCHEMA_MISMATCH",
    "GPG_ENCRYPT", "GPG_DECRYPT", "RESTORE_PARITY", "ARTIFACT_LIMIT",
    "ARTIFACT_UPLOAD",
})


def status(stage, code):
    print("FAILED OFFLINE_" + stage + " " + code)
    return 1


def diagnose():
    if sys.version_info < (3, 11):
        return status("PYTHON", "PYTHON_TOO_OLD")
    print("OK PYTHON")

    if shutil.which("node") is None:
        return status("WRANGLER", "NODE_MISSING")
    if not (preparation.ROOT / "cloudflare/node_modules/wrangler/package.json").is_file():
        return status("WRANGLER", "NPM_INSTALL_MISSING")
    try:
        preparation.contract()
    except Exception:
        return status("WRANGLER", "CONTRACT_FAILED")
    print("OK WRANGLER_CONTRACT")

    if shutil.which("gpg") is None:
        return status("GPG", "GPG_MISSING")
    if shutil.which("gpgconf") is None:
        return status("GPG", "GPGCONF_MISSING")
    print("OK GPG_TOOLS_PRESENT")

    try:
        with tempfile.TemporaryDirectory(prefix="kmn-diagnostic-test-") as temporary:
            scratch = Path(temporary)
            os.chmod(scratch, 0o700)
            source = preparation.synthetic_sql(scratch)
            print("OK SYNTHETIC_SQL_GENERATED")
            binding = core.identity("a"*32, "12345678-1234-4234-8234-123456789abc")
            origin = {"repository": "synthetic/offline", "run_id": "synthetic",
                      "commit": "b"*40}
            import secrets
            preparation.verified_package(source, scratch, binding, origin,
                                        secrets.token_urlsafe(48), scratch / "ciphertext-only")
    except core.BackupError as exc:
        stage = exc.stage if exc.stage in SAFE_STAGES else "UNKNOWN"
        code = str(exc) if str(exc) in SAFE_CODES else "UNCLASSIFIED"
        return status(stage, code)
    except Exception:
        return status("SYNTHETIC", "UNCLASSIFIED")
    print("VERIFIED SYNTHETIC AES256_AND_INDEPENDENT_RECOVERY")
    return 0


if __name__ == "__main__":
    sys.exit(diagnose())
