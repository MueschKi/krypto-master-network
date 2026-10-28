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

STATE_FILE = Path('daten/master_paper_state.json')


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
        atomic_text(Path('DEMO_TRADING.md'), render(test_state, report))
        print('DEMO: künstliche Kurse, nur DEMO_TRADING.md; kein Zugriff auf Demokonto oder Börse.')
        return

    data, exchange = get_daily()
    data = aligned(data)
    report = run_all(data, reference_day=datetime.now(timezone.utc).date())
    if args.modus == 'analyse':
        save_report(report)
        print('Nur Analyse – keine Trades ausgeführt. NETZWERK.md erzeugt.')
        return

    # Paper mode: verify all signals & real public quotes BEFORE changing state.
    state = load_state()
    day = report['assets'][0]['date']
    if state.get('last_processed_day') and day <= state['last_processed_day']:
        save_report(report)
        atomic_text(Path('TRADING_STATUS.md'), render(state, report, duplicate=True))
        print(f'Börsentag {day} schon verarbeitet. Keine doppelten Trades.')
        return
    if any(a['action']=='DATENSPERRE' for a in report['assets']):
        raise RuntimeError('Master-Datensperre: PAPER-Lauf ohne Ausführung abgebrochen')
    quotes = PublicKrakenQuotes(exchange).fetch([a['symbol'] for a in report['assets']])
    next_state, changed = run_paper(state, report, quotes)
    if not changed:
        raise RuntimeError('Unbeabsichtigter Duplikatstatus')
    # State is canonical; reports can be regenerated on rerun if report creation fails.
    atomic_text(STATE_FILE, json.dumps(next_state, indent=2, ensure_ascii=False, allow_nan=False))
    save_report(report)
    atomic_text(Path('TRADING_STATUS.md'), render(next_state, report))
    print(f'MASTER PAPER {day}: {len(next_state["trades"])-len(state["trades"])} virtuelle Ausführungen; '
          f'Depotwert {next_state["last_equity_eur"]:.2f} EUR. KEINE Echtgeldorders.')


if __name__ == '__main__':
    main()
