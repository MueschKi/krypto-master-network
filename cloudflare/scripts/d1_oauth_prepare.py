"""Issue #28: offline preparation only. No login/export implementation or bypass.

A broader OAuth grant needs a separate owner decision and reviewed implementation.
The rehearsal never reads operator credentials, environment IDs, or private SQL.
"""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
import tempfile
import encrypted_d1 as core

ROOT = Path(__file__).resolve().parents[2]
BLOCKED = 'BLOCKED OAUTH_SCOPE_OWNER_APPROVAL_REQUIRED: d1:write + implicit offline_access; no login/export performed.'


def contract():
    # Allowlist, not inherited CF/GitHub credentials, Node injection or proxy secrets.
    environment = {k: os.environ[k] for k in ('PATH', 'SystemRoot') if k in os.environ}
    result = subprocess.run(['node', str(ROOT/'cloudflare/scripts/check_wrangler_oauth_contract.mjs')],
                            env=environment, capture_output=True, timeout=20)
    core.require(result.returncode == 0, 'OAUTH_CONTRACT_REVIEW_REQUIRED')


def verified_package(source, scratch, binding, origin, secret, publish):
    """Reusable offline tail: no publication until two fresh recovery passes succeed.

    origin is caller-supplied expected provenance, not remote authentication.
    No caller may use this function to bypass maintenance or OAuth authorization.
    """
    core.require(not Path(publish).exists(), 'PUBLISH_TARGET_INVALID')
    cipher, _ = core.pack(source, scratch, binding, origin, secret)
    digest = core.storage_snapshot.digest(cipher)
    for _ in range(2):
        with tempfile.TemporaryDirectory(dir=scratch, prefix='recovery-') as verify:
            core.recover(cipher, digest, verify, binding, origin, secret)
    core.publish(cipher, publish)


def synthetic_sql(scratch):
    with sqlite3.connect(':memory:') as db:
        for name in core.MIGRATIONS[:2]:
            db.executescript((ROOT/'cloudflare/migrations'/name).read_text())
        db.execute('CREATE TABLE d1_migrations(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,applied_at TEXT)')
        for name in core.MIGRATIONS[:2]:
            db.execute("INSERT INTO d1_migrations(name,applied_at) VALUES(?,'synthetic')", (name,))
        db.execute("INSERT INTO runs(id,scheduled,started,status) VALUES('synthetic',1,1,'OK')")
        db.execute("INSERT INTO jobs(symbol,timeframe,candle_close,owner,lease_until,status) VALUES('BTC/EUR','15m',1,'synthetic',2,'OK')")
        db.execute("INSERT INTO analyses VALUES('BTC/EUR','15m',1,1,'synthetic','{}')")
        source = Path(scratch)/'export.sql'
        core.write_new(source, ('\n'.join(db.iterdump())).encode())
        return source


def rehearse():
    # Ephemeral random test key, never a real password-manager secret.
    with tempfile.TemporaryDirectory(prefix='kmn-synthetic-') as directory:
        scratch = Path(directory)
        os.chmod(scratch, 0o700)
        binding = core.identity('a'*32, '12345678-1234-4234-8234-123456789abc')
        origin = {'repository': 'synthetic/offline', 'run_id': 'synthetic', 'commit': 'b'*40}
        verified_package(synthetic_sql(scratch), scratch, binding, origin,
                         secrets.token_urlsafe(48), scratch/'ciphertext-only')
    print('VERIFIED SYNTHETIC ONLY: AES-256 and two independent SQL/SQLite recovery passes; temporary files removed.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('prepare', 'rehearse', 'login', 'export'), default='prepare', nargs='?')
    args = parser.parse_args(argv)
    # Reject online modes before tools, credentials, filesystem or environment IDs.
    if args.operation in ('login', 'export'):
        print(BLOCKED)
        return 2
    os.umask(0o077)
    contract()
    if args.operation == 'rehearse':
        rehearse()
        return 0
    print('OFFLINE CONTRACT VERIFIED. Device login needs no callback port.')
    print('Codespaces can cost money: check included quota, zero spending budget and auto-stop before creating one.')
    print('Next: docs/D1_OAUTH_BACKUP_IPHONE.md. No production backup exists from this check.')
    print(BLOCKED)
    return 2


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (Exception, KeyboardInterrupt):
        print('FAILED OFFLINE_PREPARATION: no raw diagnostics; review tools/contract or local recovery.', file=sys.stderr)
        sys.exit(1)
