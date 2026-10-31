"""Offline authenticated GnuPG backup and independently verified SQLite recovery.

No network, remote SQL or deletion API. Plaintext stays in a caller-owned private
TemporaryDirectory. Only publish() may copy ciphertext into an artifact directory.
"""
from __future__ import annotations
from contextlib import contextmanager
from functools import wraps
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import tarfile
import tempfile
import uuid
import storage_snapshot

MAX_FILE = 1_500_000_000
MAX_ARCHIVE = 3_000_000_000
MAX_CIPHERTEXT = 100_000_000
MEMBERS = {'export.sql', 'snapshot.sqlite', 'snapshot.sqlite.sha256.json', 'proof.json'}
MIGRATIONS = ('0001_observation.sql', '0002_review_guards.sql', '0003_storage_guard.sql')


STAGES = frozenset("D1_READ_CONSISTENCY_UNPROVEN D1_READ_PROBE ENV_CONTEXT SECRET_FORMAT D1_LIST D1_DETAIL_EU WRANGLER_EXPORT EXPORT_EMPTY SQL_IMPORT SCHEMA_MISMATCH GPG_ENCRYPT GPG_DECRYPT RESTORE_PARITY ARTIFACT_LIMIT ARTIFACT_UPLOAD".split())


EXPORT_CLASSES = frozenset('UNKNOWN AUTH_DENIED API_ERROR DOWNLOAD_AUTH_DENIED DOWNLOAD_NOT_FOUND DOWNLOAD_RATE_LIMIT DOWNLOAD_SERVER_ERROR DOWNLOAD_HTTP_ERROR CLI_SYNTAX CONFIG_INVALID SPAWN_FAILED TIMEOUT OUTPUT_LIMIT INTERRUPTED'.split())


PROBE_CLASSES = frozenset('UNKNOWN AUTH_DENIED RATE_LIMIT API_UNAVAILABLE HTTP_ERROR NETWORK_ERROR TIMEOUT RESPONSE_LIMIT RESPONSE_INVALID RESULT_INVALID'.split())


class BackupError(Exception):
    """Internal detail is never rendered by the CLI; only validated fields are."""
    def __init__(self, code, *, stage=None, http=None, cf_codes=(), failure_class=None, exit_code=None):
        super().__init__(code)
        self.stage = stage if stage in STAGES else None
        self.failure_class = failure_class if failure_class in EXPORT_CLASSES | PROBE_CLASSES else 'UNKNOWN'
        self.exit_code = exit_code if type(exit_code) is int and -255 <= exit_code <= 255 else None
        self.http = http if type(http) is int and 100 <= http <= 599 else None
        self.cf_codes = tuple(sorted({c for c in cf_codes if type(c) is int and 0 <= c <= 99999999}))[:20]


def safe_failure(error):
    stage = error.stage if isinstance(error, BackupError) and error.stage in STAGES else 'ENV_CONTEXT'
    result = 'FAILED stage=' + stage
    if stage == 'WRANGLER_EXPORT':
        kind = error.failure_class if error.failure_class in EXPORT_CLASSES else 'UNKNOWN'
        result += ' class=' + kind
        if type(error.exit_code) is int and -255 <= error.exit_code <= 255:
            result += ' EXIT=' + str(error.exit_code)
        if kind.startswith('DOWNLOAD_') and error.http is not None:
            result += ' HTTP=' + str(error.http)
        if kind in ('API_ERROR', 'AUTH_DENIED') and error.cf_codes:
            result += ' CF=' + ','.join(map(str, error.cf_codes))
        return result
    if stage == 'D1_READ_PROBE':
        kind = error.failure_class if error.failure_class in PROBE_CLASSES else 'UNKNOWN'
        result += ' class=' + kind
    if isinstance(error, BackupError) and error.http is not None and stage in ('ENV_CONTEXT', 'D1_LIST', 'D1_DETAIL_EU', 'D1_READ_PROBE'):
        result += ' HTTP=' + str(error.http)
        if error.cf_codes:
            result += ' CF=' + ','.join(map(str, error.cf_codes))
    return result


@contextmanager
def at_stage(stage):
    if stage not in STAGES:
        raise BackupError('ENV_CONTEXT', stage='ENV_CONTEXT')
    try:
        yield
    except BackupError as exc:
        if exc.stage is None:
            exc.stage = stage
        raise
    except Exception:
        raise BackupError(stage, stage=stage) from None


def staged(stage):
    def decorate(function):
        @wraps(function)
        def call(*args, **kwargs):
            with at_stage(stage):
                return function(*args, **kwargs)
        return call
    return decorate


def require(condition, code):
    if not condition:
        raise BackupError(code)


@staged('SECRET_FORMAT')
def identity(account, database):
    require(bool(re.fullmatch('[0-9a-f]{32}', account or '')), 'ACCOUNT_INVALID')
    try:
        canonical = str(uuid.UUID(database))
    except (ValueError, TypeError, AttributeError):
        raise BackupError('DATABASE_INVALID') from None
    require(canonical == database and canonical != str(uuid.UUID(int=0)), 'DATABASE_INVALID')
    return {'account_id': account, 'database_id': canonical, 'name': 'kmn', 'jurisdiction': 'eu'}


def write_new(path, data):
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as stream:
        stream.write(data)


@staged('SQL_IMPORT')
def import_sql(source, destination):
    """Only a NEW local SQLite file. SQLite cannot attach/read/write other files."""
    source, destination = Path(source), Path(destination)
    require(source.is_file() and not source.is_symlink() and 0 < source.stat().st_size <= MAX_FILE, 'EXPORT_EMPTY_OR_OVERSIZE')
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(fd)
    try:
        with sqlite3.connect(destination) as db:
            # Some supported Python/SQLite builds omit the Python API for
            # loadable extensions entirely. In those builds there is nothing
            # to disable through this API. Keep the SQL authorizer denylist
            # for load_extension/readfile/writefile in either case.
            disable_extension = getattr(db, 'enable_load_extension', None)
            if disable_extension is not None:
                disable_extension(False)
            db.execute('PRAGMA max_page_count=366210')  # <= 1.5 GB at 4096 bytes/page
            db.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, 8_000_000)
            def authorize(action, first, second, *_):
                if action in (sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH, sqlite3.SQLITE_CREATE_VTABLE):
                    return sqlite3.SQLITE_DENY
                if action == sqlite3.SQLITE_PRAGMA and first.lower() not in ('foreign_keys', 'defer_foreign_keys'):
                    return sqlite3.SQLITE_DENY
                if action == sqlite3.SQLITE_FUNCTION and str(second).lower() in ('load_extension', 'readfile', 'writefile'):
                    return sqlite3.SQLITE_DENY
                return sqlite3.SQLITE_OK
            db.set_authorizer(authorize)
            db.executescript(source.read_text(encoding='utf-8'))
            db.set_authorizer(None)
            storage_snapshot.integrity(db)
    except Exception:
        destination.unlink(missing_ok=True)
        raise BackupError('LOCAL_IMPORT_FAILED') from None


def _quoted(name):
    return '"' + name.replace('"', '""') + '"'


@staged('SCHEMA_MISMATCH')
def summary(path):
    with sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True) as db:
        storage_snapshot.integrity(db)
        names = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        require('d1_migrations' in names, 'MIGRATION_HISTORY_MISSING')
        history = tuple(row[0] for row in db.execute('SELECT name FROM d1_migrations ORDER BY name'))
        require(history in (MIGRATIONS[:2], MIGRATIONS), 'MIGRATION_HISTORY_UNEXPECTED')
        with sqlite3.connect(':memory:') as expected:
            for name in history:
                expected.executescript((Path(__file__).parent.parent/'migrations'/name).read_text())
            tables = {row[0] for row in expected.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            require(set(names) == tables | {'d1_migrations'}, 'TABLE_SET_UNEXPECTED')
            for table in tables:
                actual_cols = db.execute('PRAGMA table_info(' + _quoted(table) + ')').fetchall()
                expected_cols = expected.execute('PRAGMA table_info(' + _quoted(table) + ')').fetchall()
                require(actual_cols == expected_cols, 'TABLE_SCHEMA_UNEXPECTED')
        result = {}
        for table in names:
            columns = db.execute('PRAGMA table_info(' + _quoted(table) + ')').fetchall()
            order = ','.join(str(i+1) for i in range(len(columns)))
            h, count = hashlib.sha256(), 0
            for row in db.execute('SELECT * FROM ' + _quoted(table) + ' ORDER BY ' + order):
                typed = [[type(v).__name__, v.hex() if isinstance(v, bytes) else v] for v in row]
                h.update(json.dumps(typed, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode()+b'\n')
                count += 1
            result[table] = {'rows': count, 'sha256': h.hexdigest()}
        schema = list(db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"))
        return {'migrations': list(history), 'tables': result,
                'schema_sha256': hashlib.sha256(json.dumps(schema, separators=(',', ':')).encode()).hexdigest()}


def gpg(source, destination, secret, scratch, decrypt=False):
    with at_stage('SECRET_FORMAT'):
        require(isinstance(secret, str) and len(secret) >= 32 and '\n' not in secret and '\r' not in secret, 'KEY_MISSING_OR_INVALID')
    with at_stage('GPG_DECRYPT' if decrypt else 'GPG_ENCRYPT'):
        return _gpg(source, destination, secret, scratch, decrypt)


def _gpg(source, destination, secret, scratch, decrypt=False):
    require(isinstance(secret, str) and len(secret) >= 32 and '\n' not in secret and '\r' not in secret, 'KEY_MISSING_OR_INVALID')
    require(shutil.which('gpg') is not None, 'GPG_MISSING')
    # Never put the passphrase in argv, output, a key file, or the child environment.
    # GPG and its agent need no Cloudflare/GitHub/OAuth credentials or Node hooks.
    # Explicit --homedir below also avoids inherited user keyring configuration.
    environment = {k: v for k, v in os.environ.items()
                   if k in ('PATH', 'SystemRoot', 'LANG', 'LC_ALL', 'LC_CTYPE')}
    home = Path(scratch)/('gpg-decrypt' if decrypt else 'gpg-encrypt')
    home.mkdir(mode=0o700, exist_ok=True)
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(fd)
    command = ['gpg', '--no-options', '--homedir', str(home), '--batch', '--yes', '--no-tty', '--no-symkey-cache',
               '--pinentry-mode', 'loopback', '--passphrase-fd', '0', '--status-fd', '1', '--output', str(destination)]
    command += ['--decrypt', str(source)] if decrypt else [
        '--symmetric', '--cipher-algo', 'AES256', '--force-mdc', '--s2k-mode', '3',
        '--s2k-digest-algo', 'SHA512', '--s2k-count', '65011712', '--compress-algo', 'none', str(source)]
    try:
        proc = subprocess.run(command, input=(secret+'\n').encode(), stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, env=environment, timeout=300)
        require(proc.returncode == 0, 'DECRYPT_FAILED' if decrypt else 'ENCRYPT_FAILED')
        if decrypt:
            require(b'[GNUPG:] GOODMDC' in proc.stdout and b'[GNUPG:] DECRYPTION_OKAY' in proc.stdout, 'AUTHENTICATION_FAILED')
        require(Path(destination).stat().st_size > 0, 'CIPHERTEXT_EMPTY')
    except Exception:
        Path(destination).unlink(missing_ok=True)
        raise BackupError('DECRYPT_FAILED' if decrypt else 'ENCRYPT_FAILED', stage='GPG_DECRYPT' if decrypt else 'GPG_ENCRYPT') from None
    finally:
        try:
            subprocess.run(['gpgconf', '--homedir', str(home), '--kill', 'gpg-agent'],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment, timeout=10)
        except Exception:
            pass
        shutil.rmtree(home, ignore_errors=True)


@staged('RESTORE_PARITY')
def pack(source_sql, scratch, binding, origin, secret):
    scratch = Path(scratch)
    imported = scratch/'imported.sqlite'
    import_sql(source_sql, imported)
    baseline = summary(imported)
    require(all(baseline['tables'][t]['rows'] > 0 for t in ('analyses', 'jobs', 'runs')), 'REQUIRED_HISTORY_EMPTY')
    snapshot = scratch/'snapshot.sqlite'
    storage_snapshot.backup(imported, snapshot)
    require(summary(snapshot) == baseline, 'SNAPSHOT_PARITY_FAILED')
    proof = {'format': 1, 'binding': binding, 'origin': origin, 'summary': baseline,
             'sql_sha256': storage_snapshot.digest(source_sql), 'snapshot_sha256': storage_snapshot.digest(snapshot)}
    write_new(scratch/'proof.json', json.dumps(proof, sort_keys=True).encode())
    archive = scratch/'bundle.tar.gz'
    with tarfile.open(archive, 'x:gz') as tar:
        for name in sorted(MEMBERS):
            path = Path(source_sql) if name == 'export.sql' else scratch/name
            tar.add(path, arcname=name, recursive=False)
    os.chmod(archive, 0o600)
    cipher = scratch/'backup.tar.gz.gpg'
    gpg(archive, cipher, secret, scratch)
    with at_stage('ARTIFACT_LIMIT'):
        require(cipher.stat().st_size <= MAX_CIPHERTEXT, 'CIPHERTEXT_TOO_LARGE')
    return cipher, proof


@staged('RESTORE_PARITY')
def recover(cipher, cipher_hash, scratch, binding, origin, secret):
    with at_stage('ARTIFACT_LIMIT'):
        require(Path(cipher).is_file() and not Path(cipher).is_symlink() and 0 < Path(cipher).stat().st_size <= MAX_CIPHERTEXT, 'CIPHERTEXT_INVALID')
    require(bool(re.fullmatch('[0-9a-f]{64}', cipher_hash)), 'CIPHERTEXT_HASH_INVALID')
    require(storage_snapshot.digest(cipher) == cipher_hash, 'CIPHERTEXT_HASH_MISMATCH')
    scratch = Path(scratch)
    archive = scratch/'decrypted.tar.gz'
    gpg(cipher, archive, secret, scratch, decrypt=True)
    require(archive.stat().st_size <= MAX_ARCHIVE, 'ARCHIVE_TOO_LARGE')
    seen, total = set(), 0
    with tarfile.open(archive, 'r|gz') as tar:
        for member in tar:
            require(member.name in MEMBERS and member.name not in seen and member.isfile(), 'ARCHIVE_MEMBERS_INVALID')
            total += member.size
            require(0 < member.size <= MAX_FILE and total <= MAX_ARCHIVE, 'ARCHIVE_SIZE_INVALID')
            if member.name.endswith('.json'):
                require(member.size <= 2_000_000, 'MANIFEST_TOO_LARGE')
            seen.add(member.name)
            with tar.extractfile(member) as content:
                # No extractall: names/links never control a path or permissions.
                write_new(scratch/member.name, content.read())
    require(seen == MEMBERS, 'ARCHIVE_MEMBERS_INVALID')
    proof = json.loads((scratch/'proof.json').read_text())
    require(proof.get('format') == 1 and proof.get('binding') == binding and proof.get('origin') == origin, 'PROVENANCE_MISMATCH')
    require(storage_snapshot.digest(scratch/'export.sql') == proof['sql_sha256'], 'SQL_HASH_MISMATCH')
    require(storage_snapshot.digest(scratch/'snapshot.sqlite') == proof['snapshot_sha256'], 'SNAPSHOT_HASH_MISMATCH')
    # Independent SQL import AND the existing snapshot recovery implementation.
    import_sql(scratch/'export.sql', scratch/'sql-restored.sqlite')
    storage_snapshot.restore(scratch/'snapshot.sqlite', scratch/'snapshot-restored.sqlite')
    require(summary(scratch/'sql-restored.sqlite') == proof['summary'] == summary(scratch/'snapshot-restored.sqlite'), 'RESTORE_PARITY_FAILED')
    return proof


@staged('ARTIFACT_UPLOAD')
def publish(cipher, directory):
    # Caller uploads only these two explicit files after a successful recovery.
    directory = Path(directory)
    directory.mkdir(mode=0o700)
    try:
        write_new(directory/'backup.tar.gz.gpg', Path(cipher).read_bytes())
        write_new(directory/'ciphertext.sha256', (storage_snapshot.digest(cipher)+'\n').encode())
    except Exception:
        shutil.rmtree(directory)
        raise
