"""Regression tests for independent agent protocol and non-trading master."""
import unittest
from datetime import date
import numpy as np
from market import aligned, synthetic_demo, SYMBOLS
from net_core import assessment, rsi, Finding
from net_master import run_all, generate_markdown, review
import net_data_bot, net_liquidity_bot


class NetworkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=aligned(synthetic_demo())

    def test_all_agents(self):
        data=run_all(self.data,reference_day=None)
        self.assertEqual(len(data['assets']),4)
        for a in data['assets']:
            self.assertEqual(len(a['agents']),12)
            self.assertIn(a['action'],['ABWARTEN','BEOBACHTEN: KAUFKANDIDAT','SCHWACHER MARKT','RISIKOSPERRE'])
            self.assertNotIn('TRADE', a['action'])

    def test_json_is_serializable(self):
        import json
        report=run_all(self.data)
        s=json.dumps(report,allow_nan=False)
        self.assertIn('RESEARCH_ONLY_NO_TRADES',s)

    def test_markdown(self):
        report=run_all(self.data)
        report_md=generate_markdown(report)
        for symbol in SYMBOLS:
            self.assertIn(symbol,report_md)
        self.assertIn('keine',report_md.lower())

    def test_old_data_is_blocked(self):
        d=self.data[SYMBOLS[0]]
        q=net_data_bot.analyze(SYMBOLS[0],d,reference_day=date(2026,10,28))
        self.assertEqual(q.signal,'BLOCKIERT')

    def test_missing_candles_block(self):
        d=self.data[SYMBOLS[0]].iloc[-100:]
        self.assertEqual(net_data_bot.analyze(SYMBOLS[0],d).signal,'BLOCKIERT')

    def test_modified_corrupted_ohlcv_blocks(self):
        d=self.data[SYMBOLS[0]].copy()
        d.iloc[-1,d.columns.get_loc('high')]=d.iloc[-1]['close']*0.8
        self.assertEqual(net_data_bot.analyze(SYMBOLS[0],d).signal,'BLOCKIERT')

    def test_no_liquidity_data_is_not_falsely_positive(self):
        r=net_liquidity_bot.analyze('BTC/EUR',enabled=False)
        self.assertEqual(r.signal,'NICHT_GEMESSEN')

    def test_data_gate_means_no_other_agents(self):
        d=self.data['BTC/EUR'].iloc[-90:]
        out=review('BTC/EUR',d,self.data)
        self.assertEqual(out['action'],'DATENSPERRE')
        self.assertEqual(set(out['agents']),{'daten'})

    def test_scores_range(self):
        for a in run_all(self.data)['assets']:
            self.assertTrue(all(-2<=x<=2 for x in a['scores'].values()))

    def test_no_order_calls_from_default_analysis(self):
        class FakeExchange:
            def fetch_order_book(self,*args,**kwargs):
                raise AssertionError('should not call orderbook')
        report=run_all(self.data,ex=FakeExchange(),orderbook=False)
        self.assertEqual(len(report['assets']),4)

    def test_wilder_rsi_for_constant_price_is_50(self):
        import pandas as pd
        close=pd.Series([100.] * 50)
        self.assertAlmostEqual(float(rsi(close).iloc[-1]),50)


    def test_orderbook_good_and_risky_spread(self):
        class Book:
            def fetch_order_book(self, *args, **kwargs):
                return {'bids': [[100.0, 1.0]], 'asks': [[101.0, 1.0]]}
        result=net_liquidity_bot.analyze('BTC/EUR',ex=Book(),enabled=True)
        self.assertEqual(result.signal,'RISIKO')
        self.assertGreater(result.facts['spread_prozent'],0.5)

    def test_hard_risk_veto_at_high_atr(self):
        import net_risk_bot
        fs={'daten':Finding('Datenqualität','OK',0,{},[]),
            'volatilitaet': Finding('Volatilität','RISIKO',0,{'atr14_prozent':15.},[]),
            'liquiditaet': Finding('Orderbuch','NICHT_GEMESSEN',0,{},[])}
        result=net_risk_bot.analyze('SOL/EUR',fs)
        self.assertEqual(result.signal,'BLOCKIERT')

    def test_weekly_signal_ignores_unfinished_week(self):
        import net_trend_bot
        d=self.data['BTC/EUR'].copy()
        # current last candle is a weekday; modifying this daily candle may affect
        # daily evidence but cannot alter the completed weekly moving averages.
        self.assertNotEqual(d.index[-1].weekday(),6)
        w=net_trend_bot.analyze('BTC/EUR',d).facts['wochen_ema8']
        d.loc[d.index[-1], 'close'] *= 1.01
        w2=net_trend_bot.analyze('BTC/EUR',d).facts['wochen_ema8']
        self.assertEqual(w,w2)

    def test_research_only_no_portfolio_changes(self):
        import tempfile
        from pathlib import Path
        from net_master import save_report
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)
            save_report(run_all(self.data),out)
            self.assertTrue((out/'NETZWERK.md').exists())
            self.assertTrue((out/'daten/netzwerk_analysen.json').exists())
            self.assertFalse((out/'daten/paper_portfolio.json').exists())
            self.assertFalse((out/'daten/trend_portfolio.json').exists())
            self.assertFalse((out/'daten/opt_trend_portfolio.json').exists())

if __name__=='__main__':
    unittest.main()
