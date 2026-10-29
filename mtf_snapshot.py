"""Operational MTF wrapper: fresh artifacts and allowlisted, fast-forward publication.

No trading imports or account writes. Publication uses a disposable Git checkout,
so concurrent Paper commits and a dirty caller checkout are never staged/reset.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from mtf_analysis import build_report, render
from mtf_data import SYMBOLS, TIMEFRAMES, utc_now_ms

PATHS = ('ZEITFENSTER.md', 'daten/zeitfenster_analysen.json')


def timestamp(report):
    value = datetime.fromisoformat(report['snapshot_utc'])
    if value.tzinfo is None or value.utcoffset().total_seconds() != 0:
        raise ValueError('Snapshot benötigt UTC-Zeitstempel')
    return value


def load_bundle(directory):
    root = Path(directory)
    report = json.loads((root / PATHS[1]).read_text(encoding='utf-8'))
    timestamp(report)
    if report['mode'] != 'analyse' or report['classification'] not in ('OK', 'BLOCKIERT'):
        raise ValueError('Kein produktiver Analysebericht')
    if (root / PATHS[0]).read_text(encoding='utf-8') != render(report):
        raise ValueError('Markdown und JSON gehören nicht zum selben Snapshot')
    return report


def write_bundle(directory, report):
    root = Path(directory)
    (root / 'daten').mkdir(parents=True, exist_ok=True)
    (root / PATHS[1]).write_text(json.dumps(report, ensure_ascii=False, indent=2,
                                         allow_nan=False) + '\n', encoding='utf-8')
    (root / PATHS[0]).write_text(render(report), encoding='utf-8')


def run_snapshot(directory):
    """Discard tracked old reports before execution; never upload them as fresh."""
    start = utc_now_ms()
    for path in PATHS:
        Path(path).unlink(missing_ok=True)
    failure = None
    try:
        subprocess.run([sys.executable, 'mtf_analysis.py', 'analyse'], check=True, timeout=900)
        report = load_bundle('.')
        if not start <= timestamp(report).timestamp() * 1000 <= utc_now_ms():
            raise ValueError('Bericht stammt nicht aus diesem Lauf')
    except (subprocess.SubprocessError, OSError, ValueError, KeyError, TypeError) as exc:
        failure = f'{type(exc).__name__}: {exc}'
        raw = {(s, tf): {'error': 'MTF-Ausführungsfehler: ' + failure}
               for s in SYMBOLS for tf in TIMEFRAMES}
        report = build_report(raw, start, 'analyse')
    write_bundle(directory, report)
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a', encoding='utf-8') as stream:
            stream.write(f"## MTF-Betriebsdiagnose\n\nTrigger: `{os.environ.get('GITHUB_EVENT_NAME', 'lokal')}`. "
                         'Nur ein tatsächlich beobachtetes `schedule`-Event belegt einen Cron-Start.\n\n')
            if failure:
                stream.write('**Ausführung fehlgeschlagen; BLOCKIERT-Diagnose, kein gültiger Marktsnapshot.**\n\n')
            stream.write(render(report))
    if failure:
        raise RuntimeError(failure)
    return report


def git(cwd, *args, check=True):
    return subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', *args], cwd=cwd,
                          text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          check=check)


def publish(directory, repository='.', attempts=3):
    """Fetch/rebuild on latest main, never merge, force-push or stage caller files.

    A changed report pair since our initial fetch is a conflict unless it is
    already as new/newer. Unrelated remote commits are retained on each retry.
    """
    bundle = {path: (Path(directory) / path).read_bytes() for path in PATHS}
    incoming = load_bundle(directory)
    incoming_time = timestamp(incoming)
    if incoming_time > datetime.now(timezone.utc):
        raise ValueError('Snapshot liegt in der Zukunft')
    # Checkout credentials stay in the caller repo's local Git config. Use that
    # repo for fetch/push; the temporary checkout only builds the commit tree.
    initial = None
    with tempfile.TemporaryDirectory(prefix='mtf-publish-') as tmp:
        try:
            for _ in range(attempts):
                git(repository, 'fetch', 'origin', 'refs/heads/main')
                head = git(repository, 'rev-parse', 'FETCH_HEAD').stdout.strip()
                current = {}
                for path in PATHS:
                    result = git(repository, 'show', f'{head}:{path}', check=False)
                    if result.returncode and git(repository, 'cat-file', '-e', f'{head}:{path}', check=False).returncode == 0:
                        raise RuntimeError('Remote-Bericht nicht lesbar')
                    current[path] = result.stdout if result.returncode == 0 else None
                if (current[PATHS[0]] is None) != (current[PATHS[1]] is None):
                    raise ValueError('Remote-Berichtspaar unvollständig')
                if current[PATHS[1]] is not None:
                    remote_report = json.loads(current[PATHS[1]])
                    if timestamp(remote_report) >= incoming_time:
                        print('Kein Push: Remote-Snapshot ist gleich alt oder neuer.')
                        return False
                if initial is not None and current != initial:
                    raise RuntimeError('Konflikt: Remote-MTF-Berichte während Veröffentlichung geändert')
                initial = current
                work = Path(tmp) / 'checkout'
                if work.exists():
                    git(repository, 'worktree', 'remove', '--force', str(work))
                git(repository, 'worktree', 'add', '--detach', str(work), head)
                for path, data in bundle.items():
                    target = work / path
                    if target.is_symlink() or target.parent.is_symlink():
                        raise ValueError('Symlinks im Berichtspfad sind nicht erlaubt')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
                git(work, 'add', '--', *PATHS)
                changed = git(work, 'diff', '--cached', '--name-only').stdout.splitlines()
                if not changed:
                    return False
                if not set(changed) <= set(PATHS):
                    raise RuntimeError('Unerlaubte Dateien im Commit')
                git(work, '-c', 'user.name=github-actions[bot]',
                    '-c', 'user.email=41898282+github-actions[bot]@users.noreply.github.com',
                    'commit', '-m', 'MTF: Beobachtungssnapshot aktualisiert')
                commit = git(work, 'rev-parse', 'HEAD').stdout.strip()
                result = git(repository, 'push', 'origin', f'{commit}:refs/heads/main', check=False)
                if result.returncode == 0:
                    print('MTF-Berichte auf main gespeichert.')
                    return True
                print(result.stderr, file=sys.stderr)
            raise RuntimeError('MTF-Push nach drei Versuchen fehlgeschlagen; Artifact bleibt erhalten')
        finally:
            work = Path(tmp) / 'checkout'
            if work.exists():
                git(repository, 'worktree', 'remove', '--force', str(work), check=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('run', 'publish'))
    parser.add_argument('directory')
    args = parser.parse_args()
    try:
        (run_snapshot if args.action == 'run' else publish)(args.directory)
    except Exception as exc:
        message = f'MTF {args.action} fehlgeschlagen: {type(exc).__name__}: {exc}'
        print(message, file=sys.stderr)
        if os.environ.get('GITHUB_STEP_SUMMARY'):
            with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as stream:
                stream.write('\n\n**MTF-Schritt fehlgeschlagen. Details im Job-Log; vorhandenes Artifact bleibt erhalten.**\n')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
