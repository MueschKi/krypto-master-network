"""Backtest safety tests: look-ahead, account separation, quote/cost assumptions."""
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from market import aligned, synthetic_demo, SYMBOLS
from net_master import run_all
from backtest_master import open_quotes, replay, save, render, drawdown, WARMUP
from trade_engine import fresh_account
from trade_broker import LiveExchangeAdapter


class MasterBacktestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=aligned(synthetic_demo())

    def test_master_has_explainable_gates(self):
        r=run_all(self.data)
        for item in r['assets']:
            self.assertEqual(len(item['gates']),9)
            self.assertEqual(set(item['failed_gates']),
                             {k for k,ok in item['gates'].items() if not ok})
            if item['action']=='BEOBACHTEN: KAUFKANDIDAT':
                self.assertFalse(item['failed_gates'])
            if item['action']=='ABWARTEN':
                self.assertTrue(item['failed_gates'])
                self.assertTrue(any('Fehlt' in r for r in item['reasons']))

    def test_next_open_only(self):
        q=open_quotes(self.data,301)
        day=SYMBOLS[0]
        orig=q[day].mid
        manipulated={s:df.copy() for s,df in self.data.items()}
        manipulated[day].iloc[301,manipulated[day].columns.get_loc('close')]*=50
        manipulated[day].iloc[301,manipulated[day].columns.get_loc('high')]*=50
        self.assertEqual(open_quotes(manipulated,301)[day].mid,orig)

    def test_open_quotes_reject_invalid_values(self):
        invalid={s:df.copy() for s,df in self.data.items()}
        invalid[SYMBOLS[0]].iloc[301,invalid[SYMBOLS[0]].columns.get_loc('open')]=0
        with self.assertRaises(ValueError): open_quotes(invalid,301)
        with self.assertRaises(ValueError): open_quotes(self.data,301,spread=.01)

    def test_history_minimum(self):
        with self.assertRaises(ValueError): replay({s:df.iloc[:250] for s,df in self.data.items()})
        with self.assertRaises(ValueError): replay(self.data,max_signals=0)

    def test_short_replay_does_not_mutate_data(self):
        before={s:len(df) for s,df in self.data.items()}
        result=replay(self.data,max_signals=4)
        self.assertEqual(len(result['curve']),4)
        self.assertEqual(result['state']['last_processed_day'],result['curve'][-1]['signal_day_utc'])
        self.assertEqual(before,{s:len(df) for s,df in self.data.items()})
        self.assertGreater(result['curve'][0]['fill_day_utc'],result['curve'][0]['signal_day_utc'])
        self.assertEqual(sum(result['counts'].values()),16)

    def test_output_files_no_account_write(self):
        result=replay(self.data,max_signals=3)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            path=root/'daten/master_paper_state.json'
            path.parent.mkdir()
            path.write_text('{"keep_me":"unchanged"}',encoding='utf-8')
            save(result, root, source='TESTKURSE')
            self.assertEqual(path.read_text(),'{"keep_me":"unchanged"}')
            self.assertTrue((root/'BACKTEST_MASTER.md').exists())
            self.assertTrue((root/'daten/master_backtest_kurve.csv').exists())
            self.assertTrue((root/'daten/master_backtest_trades.csv').exists())
            self.assertIn('KÜNSTLICHE',render(result,source='KÜNSTLICHE'))

    def test_drawdown_known_example(self):
        self.assertAlmostEqual(drawdown([1000,1100,990,1200]),10)

    def test_no_live_trading_adapter(self):
        with self.assertRaises(PermissionError): LiveExchangeAdapter()


if __name__=='__main__':
    unittest.main()
