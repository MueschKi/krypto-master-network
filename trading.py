"""Master network entry point. Only analysis, paper, demo, tests. NO live orders.

Usage:
  python trading.py demo
  python trading.py analyse
  python trading.py paper
  python -m unittest -q test_netzwerk test_trading
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import tempfile
from datetime import datetime, timezone

from market import aligned, get_daily, synthetic_demo
from net_master import run_all, generate_markdown
from trade_broker import PublicKrakenQuotes, Quote
from trade_engine import fresh_account, run_paper, validate_state
from trade_report import render
from trailing_engine import run_trailing_paper
from compare_report import render_trailing, render_comparison

STATE_FILE = Path('daten/master_paper_state.json')
TRAILING_STATE_FILE = Path('daten/master_trailing_state.json')


def atomic_text(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix='.pending-', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def load_state(path: Path = STATE_FILE) -> dict:
    if not path.exists():
        return fresh_account()
    s = json.loads(path.read_text(encoding='utf-8'))
    validate_state(s)
    return s


def load_trailing_state(path: Path = TRAILING_STATE_FILE) -> dict:
    # A missing account is a NEW 1,000 EUR virtual account. A broken existing
    # account ALWAYS raises and is never reset.
    if not path.exists():
        return fresh_account()
    s = json.loads(path.read_text(encoding='utf-8'))
    validate_state(s)
    if s.get('exit_policy') != 'atr_trailing_2_5_close':
        raise ValueError('Falsche Strategie in gespeicherter Trailing-Kontodatei')
    return s


def save_report(report: dict):
    atomic_text(Path('NETZWERK.md'), generate_markdown(report))
    atomic_text(Path('daten/netzwerk_analysen.json'),
                json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False))


def main():
    parser = argparse.ArgumentParser(description='Krypto Master Network – nur Paper Trading')
    parser.add_argument('modus', choices=['demo', 'analyse', 'paper'])
    args = parser.parse_args()
    if args.modus == 'demo':
        data = aligned(synthetic_demo())
        report = run_all(data, reference_day=None)
        # Synthetic quote; demo NEVER reads or writes the real account file.
        quotes = {}
        for sym, frame in data.items():
            price = float(frame['close'].iloc[-1])
            quotes[sym] = Quote(sym, price * .9995, price * 1.0005,
                                datetime.now(timezone.utc).isoformat(timespec='seconds'))
        test_state, _ = run_paper(fresh_account(), report, quotes)
        trailing_state, _ = run_trailing_paper(fresh_account(), report, quotes)
        atomic_text(Path('DEMO_TRADING.md'),
                    render_comparison(test_state, trailing_state))
        print('DEMO: künstliche Kurse; beide Engines in getrennten Demo-Konten getestet. '
              'Keine echte Kontodatei verändert.')
        return

    data, exchange = get_daily()
    data = aligned(data)
    report = run_all(data, reference_day=datetime.now(timezone.utc).date())
    if args.modus == 'analyse':
        save_report(report)
        print('Nur Analyse – keine Trades ausgeführt. NETZWERK.md erzeugt.')
        return

    # Two separate paper accounts: original stays on fixed 7%-stop, while the
    # second account uses 2.5x ATR trailing. Decisions are calculated BEFORE
    # writing either account. GitHub commits all files only after job success.
    fixed = load_state()
    trailing = load_trailing_state()
    day = report['assets'][0]['date']
    fixed_due = not fixed.get('last_processed_day') or day > fixed['last_processed_day']
    trail_due = not trailing.get('last_processed_day') or day > trailing['last_processed_day']
    if fixed_due or trail_due:
        if any(a['action']=='DATENSPERRE' for a in report['assets']):
            raise RuntimeError('Master-Datensperre: PAPER-Lauf ohne Ausführung abgebrochen')
        quotes = PublicKrakenQuotes(exchange).fetch([a['symbol'] for a in report['assets']])
        # Compute both in memory. A failure in one engine prevents committing either.
        fixed_next, fixed_changed = (run_paper(fixed, report, quotes) if fixed_due
                                     else (fixed, False))
        trailing_next, trail_changed = (run_trailing_paper(trailing, report, quotes)
                                       if trail_due else (trailing, False))
        if fixed_due and not fixed_changed or trail_due and not trail_changed:
            raise RuntimeError('Unerwarteter nicht verarbeiteter Handelstag')
    else:
        fixed_next, trailing_next = fixed, trailing
        fixed_changed = trail_changed = False

    # Render all outputs before any writes, so broken state cannot partially save.
    fixed_md = render(fixed_next, report, duplicate=not fixed_changed)
    trailing_md = render_trailing(trailing_next, report, duplicate=not trail_changed)
    comparison_md = render_comparison(fixed_next, trailing_next)
    fixed_json = json.dumps(fixed_next, indent=2, ensure_ascii=False, allow_nan=False)
    trailing_json = json.dumps(trailing_next, indent=2, ensure_ascii=False, allow_nan=False)
    if fixed_changed:
        atomic_text(STATE_FILE, fixed_json)
    if trail_changed:
        atomic_text(TRAILING_STATE_FILE, trailing_json)
    save_report(report)
    atomic_text(Path('TRADING_STATUS.md'), fixed_md)
    atomic_text(Path('TRAILING_STATUS.md'), trailing_md)
    atomic_text(Path('VERGLEICH_MASTER.md'), comparison_md)
    print(f'MASTER PAPER {day}: Fix {len(fixed_next["trades"])-len(fixed["trades"])} Trades, '
          f'ATR-Trailing {len(trailing_next["trades"])-len(trailing["trades"])} Trades; '
          f'Kontostände {fixed_next["last_equity_eur"]:.2f} EUR und '
          f'{trailing_next["last_equity_eur"]:.2f} EUR. NUR Simulation.')


if __name__ == '__main__':
    main()
