"""Manually authorized CI orchestration. Backup: read-only export. Recovery: no CF access.

CLI never emits exception text, subprocess output, SQL, table hashes or identifiers.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import signal
import shutil
import subprocess
import sys
import tempfile
from urllib.request import Request, urlopen
import encrypted_d1 as core
import backup_preflight

REPO = 'MueschKi/krypto-master-network'
WORKFLOW = '.github/workflows/cloudflare-d1-backup.yml'
ARTIFACT = 'kmn-encrypted-d1'


def quiet(command, *, environment=None, timeout=300):
    # Stop npx AND its descendants before temp cleanup on interruption.
    # Output is discarded, never printed or attached as an artifact.
    with subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                          env=environment, start_new_session=True) as process:
        try:
            process.wait(timeout=timeout)
        except BaseException:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
            raise core.BackupError('SUBPROCESS_ABORTED') from None
        core.require(process.returncode == 0, 'SUBPROCESS_FAILED')
    return b''



@core.staged('ENV_CONTEXT')
def context():
    core.require(os.getenv('GITHUB_EVENT_NAME') == 'workflow_dispatch' and os.getenv('GITHUB_REF') == 'refs/heads/main' and os.getenv('GITHUB_REPOSITORY') == REPO,
                 'MAIN_ONLY')
    run_id, commit = os.getenv('GITHUB_RUN_ID', ''), os.getenv('GITHUB_SHA', '')
    core.require(bool(re.fullmatch('[1-9][0-9]*', run_id)) and bool(re.fullmatch('[0-9a-f]{40}', commit)), 'ORIGIN_INVALID')
    return {'repository': REPO, 'run_id': run_id, 'commit': commit}


def remote_verify(binding):
    # REST GET verifies exact identity without Wrangler list's broader permissions.
    backup_preflight.verify(binding)


def export_sql(binding, scratch):
    remote_verify(binding)
    config = Path(scratch)/'wrangler.export.toml'
    core.write_new(config, ('name = "kmn-backup-only"\naccount_id = "'+binding['account_id']+'"\n'
        '[[d1_databases]]\nbinding = "DB"\ndatabase_name = "kmn"\ndatabase_id = "'+binding['database_id']+'"\n').encode())
    source = Path(scratch)/'export.sql'
    environment = dict(os.environ)
    environment.pop('D1_BACKUP_PASSPHRASE', None)
    environment['WRANGLER_SEND_METRICS'] = 'false'
    environment['WRANGLER_LOG_PATH'] = str(Path(scratch)/'wrangler-private.log')
    with core.at_stage('WRANGLER_EXPORT'):
        quiet(['npx', '--no-install', 'wrangler', 'd1', 'export', 'kmn', '--remote',
               '--skip-confirmation', '--config', str(config), '--output', str(source)], environment=environment, timeout=900)
    with core.at_stage('EXPORT_EMPTY'):
        core.require(source.is_file() and source.stat().st_size > 0, 'EXPORT_EMPTY')
    os.chmod(source, 0o600)
    remote_verify(binding)
    return source


def github_get(suffix):
    token = os.getenv('GH_TOKEN', '')
    core.require(bool(token), 'GITHUB_TOKEN_MISSING')
    request = Request('https://api.github.com/repos/'+REPO+suffix,
                      headers={'Authorization':'Bearer '+token, 'Accept':'application/vnd.github+json'})
    with urlopen(request, timeout=30) as response:
        core.require(response.status == 200, 'SOURCE_RUN_UNAVAILABLE')
        return json.loads(response.read(2_000_000))


def source_run(run_id):
    core.require(bool(re.fullmatch('[1-9][0-9]*', run_id)), 'SOURCE_RUN_INVALID')
    run = github_get('/actions/runs/'+run_id)
    core.require(run.get('id') == int(run_id) and run.get('conclusion') == 'success'
                 and run.get('event') == 'workflow_dispatch' and run.get('head_branch') == 'main'
                 and run.get('repository', {}).get('full_name') == REPO
                 and run.get('path', '').split('@')[0] == WORKFLOW, 'SOURCE_RUN_UNTRUSTED')
    created = datetime.fromisoformat(run['created_at'].replace('Z', '+00:00'))
    age = (datetime.now(timezone.utc)-created).total_seconds()
    core.require(0 <= age < 7*86400, 'SOURCE_RUN_EXPIRED')
    artifacts = github_get('/actions/runs/'+run_id+'/artifacts?per_page=100')
    matches = [a for a in artifacts.get('artifacts', []) if a.get('name') == ARTIFACT]
    core.require(len(matches) == 1 and not matches[0].get('expired', True)
                 and 0 < matches[0].get('size_in_bytes', 0) <= core.MAX_CIPHERTEXT+100000, 'ARTIFACT_UNAVAILABLE')
    core.require(bool(re.fullmatch('[0-9a-f]{40}', run.get('head_sha', ''))), 'SOURCE_COMMIT_INVALID')
    return {'repository': REPO, 'run_id': run_id, 'commit': run['head_sha']}


def backup(binding, origin, secret, publish_dir, scratch):
    source = export_sql(binding, scratch)
    cipher, _ = core.pack(source, scratch, binding, origin, secret)
    with tempfile.TemporaryDirectory(dir=scratch, prefix='verify-') as verify:
        core.recover(cipher, core.storage_snapshot.digest(cipher), verify, binding, origin, secret)
    # Publishing happens ONLY after authenticated decryption and both restores.
    core.publish(cipher, publish_dir)


def recovery(binding, secret, run_id, scratch):
    origin = source_run(run_id)
    download = Path(scratch)/'download'
    download.mkdir(mode=0o700)
    environment = dict(os.environ)
    for key in ('CLOUDFLARE_API_TOKEN', 'D1_BACKUP_PASSPHRASE'):
        environment.pop(key, None)
    quiet(['gh', 'run', 'download', run_id, '--repo', REPO, '--name', ARTIFACT, '--dir', str(download)], environment=environment)
    core.require({p.name for p in download.iterdir()} == {'backup.tar.gz.gpg', 'ciphertext.sha256'}, 'ARTIFACT_FILES_INVALID')
    checksum = (download/'ciphertext.sha256').read_text().strip()
    core.recover(download/'backup.tar.gz.gpg', checksum, scratch, binding, origin, secret)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=('diagnose', 'backup', 'recovery'))
    parser.add_argument('--publish-dir', type=Path)
    parser.add_argument('--source-run-id', default='')
    args = parser.parse_args(argv)
    os.umask(0o077)
    origin = context()
    binding = core.identity(os.getenv('CLOUDFLARE_ACCOUNT_ID', ''), os.getenv('KMN_D1_DATABASE_ID', ''))
    if args.operation == 'diagnose':
        core.require(os.getenv('BACKUP_CONFIRMATION') == 'DIAGNOSE_EXISTING_KMN', 'CONSENT_MISSING')
        backup_preflight.credentials()
        with tempfile.TemporaryDirectory(dir=os.getenv('RUNNER_TEMP'), prefix='kmn-private-') as scratch:
            backup_preflight.tools_available(scratch)
            backup_preflight.token_status()
            remote_verify(binding)
        print('Diagnose verified. GET metadata only. No export or deployment approval.')
        return
    secret = os.getenv('D1_BACKUP_PASSPHRASE', '')
    with core.at_stage('SECRET_FORMAT'):
        core.require(len(secret) >= 32 and '\n' not in secret and '\r' not in secret, 'KEY_MISSING_OR_INVALID')
    core.require(shutil.which('gpg') is not None, 'GPG_MISSING')
    confirmation = os.getenv('BACKUP_CONFIRMATION', '')
    core.require(confirmation == ('EXPORT_EXISTING_KMN' if args.operation == 'backup' else 'OFFLINE_RECOVERY_ONLY'), 'CONSENT_MISSING')
    if args.operation == 'backup':
        core.require(os.getenv('MAINTENANCE_CONFIRMATION') == 'OWNER_CONFIRMED_MAINTENANCE', 'MAINTENANCE_MISSING')
        core.require(args.publish_dir is not None and not args.publish_dir.exists(), 'PUBLISH_TARGET_INVALID')
    with tempfile.TemporaryDirectory(dir=os.getenv('RUNNER_TEMP'), prefix='kmn-private-') as scratch:
        if args.operation == 'backup':
            backup(binding, origin, secret, args.publish_dir, scratch)
        else:
            recovery(binding, secret, args.source_run_id, scratch)
    print('Encrypted backup and offline recovery verified.' if args.operation == 'backup' else 'Offline recovery verified. No Cloudflare write or restore.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # No raw exception, SQL, API response, path, passphrase or table row in CI.
        print(core.safe_failure(error), file=sys.stderr)
        sys.exit(1)
