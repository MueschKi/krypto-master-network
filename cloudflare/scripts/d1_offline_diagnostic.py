"""Offline-only Codespaces diagnostics. Safe fixed status codes, no secrets.

This program never contacts Cloudflare, loads OAuth tokens, or reads the real D1.
Use the VS Code task; no terminal copy/paste required.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import sqlite3
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



def explain_synthetic_sql_import(source: Path, scratch: Path):
    """Replay the import's local SQLite operations, never dump SQL or exception text.

    This function receives only synthetic_sql() output from this diagnostic task.
    Stages mirror core.import_sql(), not Cloudflare or any external database.
    """
    current = "OPEN"
    db = None
    try:
        destination = scratch / "diagnostic-import.sqlite"
        # Same exclusive-create SQLite destination behavior as production import.
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(fd)
        db = sqlite3.connect(destination)
        current = "DISABLE_EXTENSION"
        # Mirror encrypted_d1.import_sql on builds without the extension API.
        disable_extension = getattr(db, "enable_load_extension", None)
        if disable_extension is not None:
            disable_extension(False)
        current = "PAGE_LIMIT"
        db.execute("PRAGMA max_page_count=366210")
        current = "SQL_LIMIT"
        db.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, 8_000_000)

        def authorize(action, first, second, *_):
            if action in (sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH,
                          sqlite3.SQLITE_CREATE_VTABLE):
                return sqlite3.SQLITE_DENY
            if (action == sqlite3.SQLITE_PRAGMA
                    and (first or "").lower() not in ("foreign_keys", "defer_foreign_keys")):
                return sqlite3.SQLITE_DENY
            if (action == sqlite3.SQLITE_FUNCTION
                    and str(second).lower() in ("load_extension", "readfile", "writefile")):
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK

        current = "SET_AUTHORIZER"
        db.set_authorizer(authorize)
        current = "SCRIPT_EXEC"
        db.executescript(source.read_text(encoding="utf-8"))
        db.set_authorizer(None)
        current = "INTEGRITY_CHECK"
        integrity = db.execute("PRAGMA integrity_check").fetchall()
        if integrity != [("ok",)]:
            return "FAILED OFFLINE_SQL_IMPORT INTEGRITY_CHECK_NOT_OK"
        current = "FOREIGN_KEY_CHECK"
        foreign = db.execute("PRAGMA foreign_key_check").fetchall()
        if foreign:
            return "FAILED OFFLINE_SQL_IMPORT FOREIGN_KEYS_INVALID"
        return "FAILED OFFLINE_SQL_IMPORT CORE_IMPORT_DIFFERENCE"
    except Exception as exc:
        # SQLite error names are published by SQLite, not copied from exceptions
        # or SQL. Never print str(exc), tracebacks or synthetic row payloads.
        allowed = {
            "SQLITE_AUTH", "SQLITE_ERROR", "SQLITE_READONLY", "SQLITE_CANTOPEN",
            "SQLITE_NOMEM", "SQLITE_IOERR", "SQLITE_CORRUPT", "SQLITE_NOTADB",
            "SQLITE_FULL", "SQLITE_BUSY", "SQLITE_LOCKED", "SQLITE_CONSTRAINT",
            "SQLITE_MISUSE",
        }
        sqlite_code = getattr(exc, "sqlite_errorname", None)
        suffix = sqlite_code if sqlite_code in allowed else type(exc).__name__ if type(exc).__name__ in (
            "AttributeError", "PermissionError", "FileNotFoundError", "UnicodeDecodeError") else "UNKNOWN"
        return "FAILED OFFLINE_SQL_IMPORT STEP=" + current + " CODE=" + suffix
    finally:
        if db is not None:
            try:
                db.set_authorizer(None)
                db.close()
            except Exception:
                pass

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
            try:
                core.import_sql(source, scratch / "preflight-import.sqlite")
            except core.BackupError:
                print(explain_synthetic_sql_import(source, scratch))
                return 1
            print("OK SYNTHETIC_SQL_IMPORT")
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
