"""Offline SQLite backup/restore only; no network, SQL deletion or Cloudflare CLI.

Use on a protected local SQLite copy of an approved D1 export. Snapshot and
restore destinations must not exist. SHA-256 is an integrity check, not a signature.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def integrity(db):
    if db.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
        raise ValueError('SQLite integrity check failed')
    if db.execute('PRAGMA foreign_key_check').fetchall():
        raise ValueError('SQLite foreign key check failed')


def copy_database(source, destination):
    source, destination = Path(source), Path(destination)
    if source.is_symlink() or not source.is_file():
        raise ValueError('Source must be a regular local database')
    # O_EXCL prevents overwrite, including symlink destinations.
    fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    try:
        with sqlite3.connect(source.resolve().as_uri() + '?mode=ro', uri=True) as src:
            integrity(src)
            with sqlite3.connect(destination) as dst:
                src.backup(dst)
                integrity(dst)
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def backup(source, destination):
    destination = Path(destination)
    manifest = destination.with_suffix(destination.suffix + '.sha256.json')
    if manifest.exists() or manifest.is_symlink():
        raise FileExistsError('Manifest already exists')
    copy_database(source, destination)
    data = {'format': 1, 'sha256': digest(destination), 'bytes': destination.stat().st_size}
    fd = os.open(manifest, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(data, stream, sort_keys=True)
    return data


def restore(snapshot, destination):
    snapshot = Path(snapshot)
    manifest = json.loads(snapshot.with_suffix(snapshot.suffix + '.sha256.json').read_text())
    if manifest.get('format') != 1 or digest(snapshot) != manifest.get('sha256'):
        raise ValueError('Snapshot hash mismatch')
    copy_database(snapshot, destination)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('backup', 'restore'))
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    (backup if args.operation == 'backup' else restore)(args.source, args.destination)
    print('Offline snapshot operation verified; no remote changes.')
