"""Allowlisted paper transaction, rebuilt on fetched branch; no merges or force push."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from trade_engine import validate_state

ACCOUNTS = ('daten/master_paper_state.json', 'daten/master_trailing_state.json')
REPORTS = ('TRADING_STATUS.md', 'TRAILING_STATUS.md', 'VERGLEICH_MASTER.md',
           'NETZWERK.md', 'daten/netzwerk_analysen.json')
PATHS = ACCOUNTS + REPORTS


def git(cwd, *args, check=True):
    return subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', *args], cwd=cwd,
                          text=True, capture_output=True, check=check)


def blobs(repository, revision, paths):
    return {p: git(repository, 'rev-parse', f'{revision}:{p}').stdout.strip() for p in paths}


def publish(directory='.', repository='.', branch='main', attempts=3, mode='paper'):
    if mode not in ('paper', 'analyse') or not 1 <= attempts <= 5:
        raise ValueError('Ungültiger Publikationsmodus/Retry-Grenze')
    git(repository, 'check-ref-format', f'refs/heads/{branch}')
    base = git(repository, 'rev-parse', 'HEAD').stdout.strip()
    # Baseline is the checkout used for calculation, NOT the first fetched remote.
    expected = blobs(repository, base, ACCOUNTS)
    paths = PATHS if mode == 'paper' else REPORTS[-2:]
    bundle = {}
    for p in paths:
        source = Path(directory) / p
        if source.is_symlink() or source.parent.is_symlink():
            raise ValueError('Symlinks sind keine Paper-Ergebnisse')
        bundle[p] = source.read_bytes()
    if mode == 'paper':
        for p in ACCOUNTS:
            state = json.loads(bundle[p])
            validate_state(state)
            old = json.loads(git(repository, 'show', f'{base}:{p}').stdout)
            validate_state(old)
            if (state['trades'][:len(old['trades'])] != old['trades']
                    or state['equity_history'][:len(old['equity_history'])] != old['equity_history']
                    or state['initial_eur'] != old['initial_eur']
                    or state.get('exit_policy') != old.get('exit_policy')
                    or (old['last_processed_day'] and
                        (not state['last_processed_day'] or state['last_processed_day'] < old['last_processed_day']))):
                raise ValueError('Paper-Historie/Strategie darf nicht zurückgesetzt werden')
    with tempfile.TemporaryDirectory(prefix='paper-publish-') as tmp:
        work = Path(tmp) / 'checkout'
        try:
            for _ in range(attempts):
                git(repository, 'fetch', 'origin', f'refs/heads/{branch}')
                head = git(repository, 'rev-parse', 'FETCH_HEAD').stdout.strip()
                if blobs(repository, head, ACCOUNTS) != expected:
                    raise RuntimeError('Konflikt: Paper-Konto seit Berechnung verändert; neu laden und rechnen')
                # Never replay results over changed calculation code or competing reports.
                changed = git(repository, 'diff', '--name-only', base, head).stdout.splitlines()
                if any(p in paths or p.endswith('.py') or p == 'requirements.txt' for p in changed):
                    raise RuntimeError('Konflikt: Berechnungsgrundlage oder Paper-Bericht verändert')
                if work.exists():
                    git(repository, 'worktree', 'remove', '--force', str(work))
                git(repository, 'worktree', 'add', '--detach', str(work), head)
                for p, content in bundle.items():
                    target = work / p
                    if target.is_symlink() or target.parent.is_symlink():
                        raise ValueError('Symlinks im Paper-Zielpfad')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(content)
                git(work, 'add', '--', *paths)
                staged = git(work, 'diff', '--cached', '--name-only').stdout.splitlines()
                if not staged:
                    return False
                if not set(staged) <= set(paths):
                    raise RuntimeError('Unerlaubte Dateien im Paper-Commit')
                git(work, '-c', 'user.name=github-actions[bot]',
                    '-c', 'user.email=41898282+github-actions[bot]@users.noreply.github.com',
                    'commit', '-m', f'Master Network v1.5.2: {mode} aktualisiert')
                commit = git(work, 'rev-parse', 'HEAD').stdout.strip()
                result = git(repository, 'push', 'origin', f'{commit}:refs/heads/{branch}', check=False)
                if result.returncode == 0:
                    return True
                print(result.stderr, file=sys.stderr)
            raise RuntimeError(f'FAILURE: Paper-Push nach {attempts} Versuchen fehlgeschlagen')
        finally:
            if work.exists():
                git(repository, 'worktree', 'remove', '--force', str(work), check=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--branch', required=True)
    parser.add_argument('--mode', choices=('paper', 'analyse'), default='paper')
    args = parser.parse_args()
    try:
        publish(branch=args.branch, mode=args.mode)
    except Exception as exc:
        message = f'FAILURE: Paper-Publikation abgebrochen: {exc}'
        print(f'::error::{message}', file=sys.stderr)
        if os.environ.get('GITHUB_STEP_SUMMARY'):
            with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as stream:
                stream.write('\n\n**' + message + '**\n')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
