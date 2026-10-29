"""Issue #6: fail-closed accounts, raw daily data and historical ATR parity."""
from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
from market import SYMBOLS, aligned, get_daily, synthetic_demo
from net_data_bot import analyze
from research_master import _research_step
from test_trailing_v14 import q, r
from trade_engine import fresh_account, run_paper, validate_state
from trailing_engine import run_trailing_paper
from trading import initialize_account, load_state, load_trailing_state


class AccountSafetyTests(unittest.TestCase):
    def test_missing_corrupt_and_explicit_exclusive_init(self):
        for trailing, loader in ((False, load_state), (True, load_trailing_state)):
            with self.subTest(trailing=trailing), tempfile.TemporaryDirectory() as tmp:
                p = Path(tmp)/'account.json'
                with self.assertRaises(FileNotFoundError): loader(p)
                self.assertFalse(p.exists())
                initialize_account(p, trailing=trailing)
                self.assertEqual(loader(p)['cash_eur'], 1000)
                original = p.read_bytes()
                with self.assertRaises(FileExistsError): initialize_account(p, trailing=trailing)
                self.assertEqual(p.read_bytes(), original)
                for broken in ('{bad', 'null', '{"version":"broken"}'):
                    p.write_text(broken)
                    with self.assertRaises((ValueError, TypeError)): loader(p)
                    self.assertEqual(p.read_text(), broken)

    def test_normal_paper_missing_account_stops_before_network_or_writes(self):
        import os
        import trading
        for missing in ('master_paper_state.json', 'master_trailing_state.json'):
            with tempfile.TemporaryDirectory() as tmp:
                old_cwd = Path.cwd()
                try:
                    os.chdir(tmp)
                    initialize_account(Path('daten/master_paper_state.json'))
                    initialize_account(Path('daten/master_trailing_state.json'), trailing=True)
                    Path('daten', missing).unlink()
                    before = {str(p):p.read_bytes() for p in Path('.').rglob('*') if p.is_file()}
                    with patch('sys.argv', ['trading.py', 'paper']), patch.object(trading, 'get_daily') as network:
                        with self.assertRaises(FileNotFoundError): trading.main()
                        network.assert_not_called()
                    self.assertEqual(before, {str(p):p.read_bytes() for p in Path('.').rglob('*') if p.is_file()})
                finally:
                    os.chdir(old_cwd)

    def test_production_strategy_and_parameters_unchanged(self):
        import hashlib
        source = Path('trade_engine.py').read_text()
        strategy = source[:source.index('def validate_state')] + source[source.index('def equity'):]
        self.assertEqual(hashlib.sha256(strategy.encode()).hexdigest(), 'e9a7330d5d5e59738f359585bc3fb00149b8a252dcb5b92cf63931c2c26fa2af')

    def test_existing_accounts_accepted(self):
        load_state(); load_trailing_state()

    def test_invalid_balances_history_and_risk(self):
        state, _ = run_paper(fresh_account(), r(), q())
        for key, value in [('initial_eur', 0), ('highest_equity_eur', 999),
                           ('last_equity_eur', float('nan')), ('cash_eur', True),
                           ('halt_new_buys', 'false'), ('last_processed_day', '2026-02-30')]:
            bad = deepcopy(state); bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): validate_state(bad)
        for mutate in (lambda s: s['equity_history'].append(s['equity_history'][0]),
                       lambda s: s['equity_history'][0].update(cash_eur=900),
                       lambda s: s.update(last_processed_day='2026-10-28')):
            bad = deepcopy(state); mutate(bad)
            with self.assertRaises(ValueError): validate_state(bad)
        bought, _ = run_paper(fresh_account(), r(actions={'BTC/EUR':'BEOBACHTEN: KAUFKANDIDAT'}), q())
        bought['trades'].append(deepcopy(bought['trades'][0]))
        with self.assertRaises(ValueError): validate_state(bought)

    def test_trailing_plausibility(self):
        state, _ = run_trailing_paper(fresh_account(), r(actions={'BTC/EUR':'BEOBACHTEN: KAUFKANDIDAT'}), q())
        for value in (0, float('inf'), 10000):
            bad = deepcopy(state); bad['positions']['BTC/EUR']['trailing_stop_eur'] = value
            with self.assertRaises(ValueError): validate_state(bad)


class DailySafetyTests(unittest.TestCase):
    def setUp(self): self.data = synthetic_demo()

    def test_single_missing_day_rejected_before_alignment(self):
        broken = deepcopy(self.data)
        broken[SYMBOLS[0]] = broken[SYMBOLS[0]].drop(broken[SYMBOLS[0]].index[300])
        self.assertEqual(analyze(SYMBOLS[0], broken[SYMBOLS[0]]).signal, 'BLOCKIERT')
        with self.assertRaises(ValueError): aligned(broken)
        self.assertEqual(len(aligned(self.data)[SYMBOLS[0]]), 620)

    def test_current_closed_day_and_causal_replay(self):
        df = self.data[SYMBOLS[0]]
        day = df.index[-1].date()
        self.assertEqual(analyze('BTC/EUR', df, day + timedelta(days=1)).signal, 'OK')
        self.assertEqual(analyze('BTC/EUR', df, None).signal, 'OK')
        for reference in (day, day + timedelta(days=2), day + timedelta(days=3)):
            self.assertEqual(analyze('BTC/EUR', df, reference).signal, 'BLOCKIERT')

    def raw(self):
        df = self.data[SYMBOLS[0]]
        return [[int(i.timestamp()*1000), *row] for i, row in zip(df.index, df.to_numpy())]

    def fetch(self, rows):
        class Ex:
            markets = {s: {} for s in SYMBOLS}
            def load_markets(self): pass
            def fetch_ohlcv(self, *a, **kw): return rows
        return get_daily(Ex())[0]

    def test_raw_duplicates_unsorted_missing_and_off_grid(self):
        rows = self.raw()
        variants = [rows[:300]+rows[301:], rows[:300]+[rows[299]]+rows[300:],
                    [rows[1], rows[0]]+rows[2:]]
        off = deepcopy(rows); off[300][0] += 1000; variants.append(off)
        for bad in variants:
            with self.assertRaises(ValueError): self.fetch(bad)
        self.assertEqual(len(self.fetch(rows)[SYMBOLS[0]]), 620)

    def test_incomplete_today_excluded(self):
        today = pd.Timestamp.now(tz='UTC').normalize()
        rows = self.raw()
        start = today - pd.Timedelta(days=len(rows)-1)
        for i, row in enumerate(rows): row[0] = int((start+pd.Timedelta(days=i)).timestamp()*1000)
        result = self.fetch(rows)
        self.assertEqual(result[SYMBOLS[0]].index[-1], today-pd.Timedelta(days=1))


class ATRParityTests(unittest.TestCase):
    def test_gap_entry_peak_and_later_stop_match_production(self):
        prod = fresh_account(); research = fresh_account()
        steps = [r(actions={'BTC/EUR':'BEOBACHTEN: KAUFKANDIDAT'}, atrs={'BTC/EUR':2}),
                 r('2026-10-28', closes={'BTC/EUR':108}, atrs={'BTC/EUR':1}),
                 r('2026-10-29', closes={'BTC/EUR':106})]
        for idx, rep in enumerate(steps):
            quotes = q(price=110 if idx == 0 else 100)
            prod, _ = run_trailing_paper(prod, rep, quotes)
            research = _research_step(research, rep, quotes, 'ATR-Trailing 2,5x')
            for field in ('positions', 'cash_eur', 'last_equity_eur', 'equity_history', 'decisions'):
                self.assertEqual(prod[field], research[field])
            self.assertEqual([t['side'] for t in prod['trades']], [t['side'] for t in research['trades']])
            if idx == 0:
                p = research['positions']['BTC/EUR']
                self.assertEqual(p['trailing_peak_close'], p['entry_price_eur'])
            if idx == 1:
                self.assertAlmostEqual(research['positions']['BTC/EUR']['trailing_stop_eur'], 107.65004)
                # Old research peak=max(signal close=100, new close=108): 105.5.
                self.assertGreater(106, 105.5)
        self.assertEqual([t['side'] for t in research['trades']], ['BUY', 'SELL'])

    def test_nonpositive_atr_stop_fails_without_mutation(self):
        state = fresh_account(); before = deepcopy(state)
        rep = r(actions={'BTC/EUR':'BEOBACHTEN: KAUFKANDIDAT'}, atrs={'BTC/EUR':50})
        for execute in (lambda: run_trailing_paper(state, rep, q()),
                        lambda: _research_step(state, rep, q(), 'ATR-Trailing 2,5x')):
            with self.assertRaises(ValueError): execute()
            self.assertEqual(state, before)
