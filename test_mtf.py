"""Frozen UTC boundaries, causal snapshots, quality veto and engine isolation."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from copy import deepcopy
from unittest.mock import patch
import numpy as np
from mtf_data import SYMBOLS, TIMEFRAMES, quality, synthetic, fetch_all
from mtf_analysis import DEMO_NOW_MS, build_report, main, render
from net_timeframe_bot import analyse, summarize

NOW = DEMO_NOW_MS
PROTECTED = ('market.py', 'net_master.py', 'trade_engine.py', 'trailing_engine.py',
             'trade_broker.py', 'trading.py', 'daten/master_paper_state.json',
             'daten/master_trailing_state.json', 'TRADING_STATUS.md',
             'TRAILING_STATUS.md', 'VERGLEICH_MASTER.md')


class MTFTests(unittest.TestCase):
    def setUp(self):
        self.raw = synthetic(NOW)

    def test_all_16_and_determinism(self):
        a = build_report(self.raw, NOW, 'demo')
        self.assertEqual(a, build_report(synthetic(NOW), NOW, 'demo'))
        self.assertEqual(a['classification'], 'OK')
        self.assertEqual(len(a['assets']), 4)
        for asset in a['assets']:
            self.assertEqual(set(asset['timeframes']), set(TIMEFRAMES))
            for frame in asset['timeframes'].values():
                self.assertEqual(frame['quality']['status'], 'OK')
                self.assertEqual(set(frame['agents']), {'trend', 'momentum', 'volatility'})
        json.dumps(a, allow_nan=False)
        self.assertIn('EMA200', render(a))

    def test_exact_close_and_one_ms_before_each_timeframe(self):
        for tf, duration in TIMEFRAMES.items():
            with self.subTest(tf=tf):
                rows = self.raw['BTC/EUR', tf]
                data, dq = quality(rows, tf, NOW)
                self.assertEqual(dq['status'], 'OK')
                self.assertEqual(data.timestamp.iloc[-1] + duration, NOW)
                before, dq = quality(rows, tf, NOW - 1)
                self.assertEqual(dq['status'], 'OK')
                self.assertEqual(len(before), len(data)-1)
                self.assertEqual(dq['excluded_unclosed'], 1)

    def test_future_prices_never_reach_indicators_or_snapshot(self):
        for tf, duration in TIMEFRAMES.items():
            rows = deepcopy(self.raw['BTC/EUR', tf])
            baseline = analyse(rows, tf, NOW)
            # Last candle starts NOW; a future row is also present.
            rows += [[NOW, 1e30, 1e31, 1e29, 1e30, 1e30],
                     [NOW+duration, 1, 2, .5, 1, 1]]
            changed = analyse(rows, tf, NOW)
            self.assertEqual(baseline['agents'], changed['agents'])
            self.assertEqual(baseline['classification'], changed['classification'])
            self.assertEqual(baseline['quality']['latest_close_utc'], changed['quality']['latest_close_utc'])

    def test_bad_data_blocks_every_timeframe(self):
        for tf in TIMEFRAMES:
            good = self.raw['BTC/EUR', tf]
            variants = [None, [], good[:200], good[:-1], good[:100]+good[101:],
                        good[:100]+[good[99]]+good[100:], list(reversed(good)), [[1, 2]]]
            for col, value in [(1, np.nan), (2, np.inf), (3, -1), (5, -1), (2, .01), (0, NOW+1)]:
                bad = deepcopy(good)
                bad[100][col] = value
                variants.append(bad)
            for bad in variants:
                with self.subTest(tf=tf):
                    result = analyse(bad, tf, NOW)
                    self.assertEqual(result['classification'], 'BLOCKIERT')
                    self.assertFalse(result['agents'])
                    self.assertTrue(result['quality']['reason'])

    def test_cross_signals_and_veto(self):
        for signals, expected, conflict in [(['POSITIV']*4, 'POSITIV', False),
                (['NEGATIV']*4, 'NEGATIV', False),
                (['POSITIV', 'NEGATIV', 'NEUTRAL', 'POSITIV'], 'NEUTRAL', True),
                (['POSITIV', 'BLOCKIERT', 'POSITIV', 'POSITIV'], 'BLOCKIERT', False)]:
            frames = {tf: {'classification': s} for tf, s in zip(TIMEFRAMES, signals)}
            result = summarize(frames)
            self.assertEqual(result['classification'], expected)
            self.assertEqual(result['conflict'], conflict)
        raw = deepcopy(self.raw)
        del raw['NEAR/EUR', '15m']
        self.assertEqual(build_report(raw, NOW, 'demo')['classification'], 'BLOCKIERT')

    def test_known_flat_and_directional_indicators(self):
        for slope, expected in [(0, 'NEUTRAL'), (.001, 'POSITIV'), (-.001, 'NEGATIV')]:
            rows = deepcopy(self.raw['BTC/EUR', '1d'])
            for i, row in enumerate(rows):
                price = 100 * np.exp(slope*i)
                row[1:] = [price, price*1.001, price*.999, price, 10]
            result = analyse(rows, '1d', NOW)
            self.assertEqual(result['agents']['trend']['signal'], expected)
            rsi = result['agents']['momentum']['indicators']['rsi14']
            self.assertAlmostEqual(rsi, 50 if slope == 0 else 100 if slope > 0 else 0)
        rows = deepcopy(self.raw['BTC/EUR', '1d'])
        for row in rows:
            row[2], row[3] = row[4]*2, row[4]*.5
        self.assertEqual(analyse(rows, '1d', NOW)['classification'], 'BLOCKIERT')

    def test_injected_public_reader_bounded_and_errors(self):
        class Exchange:
            markets = {s: {'active': True} for s in SYMBOLS}
            calls = []
            def load_markets(self):
                pass
            def fetch_ohlcv(self, symbol, timeframe, limit):
                self.calls.append((symbol, timeframe, limit))
                if symbol == 'NEAR/EUR':
                    raise RuntimeError('offline')
                return synthetic(NOW)[symbol, timeframe]
        ex = Exchange()
        report = build_report(fetch_all(ex), NOW, 'analyse')
        self.assertEqual(len(ex.calls), 16)
        self.assertTrue(all(c[2] == 720 for c in ex.calls))
        self.assertEqual(report['assets'][-1]['summary']['classification'], 'BLOCKIERT')
        self.assertEqual(report['assets'][0]['summary']['classification'] == 'BLOCKIERT', False)

    def test_exchange_initialization_failure_blocks_all(self):
        with patch('mtf_data.public_exchange', side_effect=RuntimeError('kein Zugriff')):
            report = build_report(fetch_all(), NOW, 'analyse')
        self.assertEqual(report['classification'], 'BLOCKIERT')
        for asset in report['assets']:
            for frame in asset['timeframes'].values():
                self.assertIn('kein Zugriff', frame['quality']['reason'])
                self.assertFalse(frame['agents'])

    def test_demo_no_network_and_only_demo_files(self):
        cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            try:
                os.chdir(tmp)
                with patch('mtf_data.public_exchange', side_effect=AssertionError('network')), \
                     patch('socket.socket', side_effect=AssertionError('network')):
                    first = main(['demo'])
                    content = Path('DEMO_ZEITFENSTER.json').read_bytes()
                    self.assertEqual(first, main(['demo']))
                    self.assertEqual(content, Path('DEMO_ZEITFENSTER.json').read_bytes())
                self.assertEqual({p.name for p in Path('.').iterdir()},
                                 {'DEMO_ZEITFENSTER.md', 'DEMO_ZEITFENSTER.json'})
            finally:
                os.chdir(cwd)

    def test_live_mode_writes_blocked_report_only(self):
        cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            try:
                os.chdir(tmp)
                with patch('mtf_analysis.fetch_all', return_value={}), \
                     patch('mtf_analysis.utc_now_ms', return_value=NOW):
                    report = main(['analyse'])
                self.assertEqual(report['classification'], 'BLOCKIERT')
                self.assertEqual(json.loads(Path('daten/zeitfenster_analysen.json').read_text()), report)
                self.assertEqual({str(p) for p in Path('.').rglob('*') if p.is_file()},
                                 {'ZEITFENSTER.md', 'daten/zeitfenster_analysen.json'})
            finally:
                os.chdir(cwd)

    def test_protected_files_byte_identical_to_base(self):
        # Pin baseline hashes in the fixture; independent of branch refs in CI.
        baseline = json.loads(Path('tests/mtf_protected_sha256.json').read_text())
        for path in baseline:
            self.assertEqual(hashlib.sha256(Path(path).read_bytes()).hexdigest(), baseline[path], path)

    def test_workflow_routes_and_schedule(self):
        workflow = Path('.github/workflows/master-paper.yml').read_text()
        self.assertIn("cron: '17 4 * * *'", workflow)
        self.assertIn("cron: '47 6 * * *'", workflow)
        self.assertIn("github.event.inputs.modus || 'paper'", workflow)
        self.assertIn('mtf-demo) python mtf_analysis.py demo', workflow)
        self.assertIn('mtf-analyse) python mtf_analysis.py analyse', workflow)
        section = workflow.split('            mtf-analyse)\n')[1].split(';;')[0]
        self.assertIn('python mtf_snapshot.py publish .', section)
        self.assertNotIn('state', section)


if __name__ == '__main__':
    unittest.main()
