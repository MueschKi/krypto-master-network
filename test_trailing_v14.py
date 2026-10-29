"""v1.4: independent accounts, trailing-stop monotonicity and safety regression."""
from __future__ import annotations
import json
import os
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from trade_engine import fresh_account, run_paper, STOP_FRACTION
from trailing_engine import run_trailing_paper
from compare_report import render_comparison, render_trailing
from trade_broker import Quote, LiveExchangeAdapter
from trading import load_trailing_state

SYMBOLS=('BTC/EUR','ETH/EUR','NEAR/EUR','SOL/EUR')

def q(day='2026-10-27',price=100):
    return {s:Quote(s, price-0.04,price+0.04,day) for s in SYMBOLS}

def r(day='2026-10-27', actions=None, closes=None, atrs=None):
    actions=actions or {}; closes=closes or {}; atrs=atrs or {}
    return {'assets':[{'symbol':s,'date':day,'action':actions.get(s,'ABWARTEN'),
                        'agents':{'daten':{'signal':'OK'},'risiko':{'signal':'OK'},
                                  'setup':{'facts':{'indikative_einstiegsbasis':closes.get(s,100.)}},
                                  'volatilitaet':{'facts':{'atr14':atrs.get(s,5.0)}}}}
                       for s in SYMBOLS]}

class TrailingV14Tests(unittest.TestCase):
    def test_both_can_buy_separate_accounts(self):
        report=r(actions={'BTC/EUR':'BEOBACHTEN: KAUFKANDIDAT'})
        baseline=fresh_account()
        original=deepcopy(baseline)
        fixed,fc=run_paper(baseline,report,q())
        trailing,tc=run_trailing_paper(baseline,report,q())
        self.assertTrue(fc and tc)
        self.assertEqual(baseline,original)
        self.assertEqual(fixed['positions']['BTC/EUR'].get('trailing_stop_eur'),None)
        self.assertGreater(trailing['positions']['BTC/EUR']['trailing_stop_eur'],0)
        self.assertEqual(fixed['last_processed_day'],trailing['last_processed_day'])
        self.assertLessEqual(1000-trailing['cash_eur'],450.000001)
        self.assertEqual(len(trailing['trades']),1)
        self.assertEqual(trailing['trades'][0]['type'],'SIMULATION_ONLY')

    def test_no_duplicate(self):
        a,_=run_trailing_paper(fresh_account(),r(actions={'BTC/EUR':'BEOBACHTEN: KAUFKANDIDAT'}),q())
        b,changed=run_trailing_paper(a,r(actions={'BTC/EUR':'BEOBACHTEN: KAUFKANDIDAT'}),q())
        self.assertFalse(changed)
        self.assertEqual(a,b)

    def test_stop_never_lowers_and_sells_on_next_closed_day(self):
        a,_=run_trailing_paper(fresh_account(),r(actions={'BTC/EUR':'BEOBACHTEN: KAUFKANDIDAT'}),q())
        stop=a['positions']['BTC/EUR']['trailing_stop_eur']
        b,_=run_trailing_paper(a,r('2026-10-28',closes={'BTC/EUR':115},atrs={'BTC/EUR':2.}),q('2026-10-28',115))
        raised=b['positions']['BTC/EUR']['trailing_stop_eur']
        self.assertGreater(raised,stop)
        self.assertGreater(b['positions']['BTC/EUR']['trailing_peak_close'],100)
        c,_=run_trailing_paper(b,r('2026-10-29',closes={'BTC/EUR':111},atrs={'BTC/EUR':15.}),q('2026-10-29',110))
        self.assertEqual(c['positions']['BTC/EUR']['trailing_stop_eur'],raised)
        d,_=run_trailing_paper(c,r('2026-10-30',closes={'BTC/EUR':105}),q('2026-10-30',105))
        self.assertNotIn('BTC/EUR',d['positions'])
        self.assertEqual([t['side'] for t in d['trades']],['BUY','SELL'])
        self.assertIn('ATR-Trailing',d['trades'][-1]['reason'])

    def test_stop_vs_fixed_differ(self):
        r1=r(actions={'BTC/EUR':'BEOBACHTEN: KAUFKANDIDAT'},atrs={'BTC/EUR':10.0})
        f,_=run_paper(fresh_account(),r1,q())
        t,_=run_trailing_paper(fresh_account(),r1,q())
        r2=r('2026-10-28',closes={'BTC/EUR':92.5},atrs={'BTC/EUR':10.0})
        f,_=run_paper(f,r2,q('2026-10-28',92.5))
        t,_=run_trailing_paper(t,r2,q('2026-10-28',92.5))
        self.assertNotIn('BTC/EUR',f['positions'])
        self.assertIn('BTC/EUR',t['positions'])

    def test_bad_atr_blocks_without_state_mutation(self):
        base=fresh_account()
        for atr in (0,-2,float('nan'),float('inf')):
            with self.subTest(atr=atr),self.assertRaises(ValueError):
                run_trailing_paper(base,r(atrs={'BTC/EUR':atr}),q())
        self.assertEqual(base['cash_eur'],1000)

    def test_state_corruption_not_reset(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'trail.json';path.write_text('{bad',encoding='utf8')
            with self.assertRaises(json.JSONDecodeError):load_trailing_state(path)
            path.write_text(json.dumps(fresh_account()),encoding='utf8')
            with self.assertRaises(ValueError):load_trailing_state(path)

    def test_missing_existing_trailing_metadata_blocks(self):
        base,_=run_paper(fresh_account(),r(actions={'BTC/EUR':'BEOBACHTEN: KAUFKANDIDAT'}),q())
        with self.assertRaises(ValueError):run_trailing_paper(base,r('2026-10-28'),q('2026-10-28'))

    def test_risk_veto_and_bad_quote(self):
        bad=r(actions={'BTC/EUR':'BEOBACHTEN: KAUFKANDIDAT'})
        bad['assets'][0]['agents']['risiko']['signal']='RISIKO'
        a,_=run_trailing_paper(fresh_account(),bad,q())
        self.assertEqual(len(a['trades']),0)
        bad_quotes=q(); del bad_quotes['ETH/EUR']
        with self.assertRaises(ValueError):run_trailing_paper(fresh_account(),r(),bad_quotes)

    def test_drawdown_halt_allows_sell(self):
        base=fresh_account();base['highest_equity_eur']=1200
        a,_=run_trailing_paper(base,r(actions={'BTC/EUR':'BEOBACHTEN: KAUFKANDIDAT'}),q())
        self.assertTrue(a['halt_new_buys'])
        self.assertEqual(a['trades'],[])
        b,_=run_trailing_paper(fresh_account(),r(actions={'BTC/EUR':'BEOBACHTEN: KAUFKANDIDAT'}),q())
        b['halt_new_buys']=True
        c,_=run_trailing_paper(b,r('2026-10-28',actions={'BTC/EUR':'SCHWACHER MARKT'}),q('2026-10-28'))
        self.assertEqual(c['trades'][-1]['side'],'SELL')

    def test_report_and_no_live_adapter(self):
        base=fresh_account()
        a,_=run_trailing_paper(base,r(),q())
        report=render_comparison(a,a)
        self.assertIn('Gemeinsamer Beobachtungszeitraum',report)
        self.assertIn('ATR-Trailing-Demokonto',render_trailing(a,r()))
        with self.assertRaises(PermissionError):LiveExchangeAdapter.place_order(None,'BTC/EUR','buy',1)

    def test_introducing_trailing_does_not_touch_processed_fixed_account(self):
        import trading
        with tempfile.TemporaryDirectory() as d:
            orig=os.getcwd()
            os.chdir(d)
            try:
                Path('daten').mkdir()
                rep=r(actions={'BTC/EUR':'BEOBACHTEN: KAUFKANDIDAT'})
                old,_=run_paper(fresh_account(),rep,q())
                trading.initialize_account(Path('daten/master_trailing_state.json'), trailing=True)
                old_text=json.dumps(old,indent=2,ensure_ascii=False)
                Path('daten/master_paper_state.json').write_text(old_text,encoding='utf8')
                with patch('sys.argv',['trading.py','paper']), \
                     patch.object(trading,'get_daily',return_value=({},object())), \
                     patch.object(trading,'aligned',side_effect=lambda x:x), \
                     patch.object(trading,'run_all',return_value=rep), \
                     patch.object(trading,'generate_markdown',return_value='TEST REPORT'), \
                     patch.object(trading.PublicKrakenQuotes,'fetch',return_value=q()):
                    trading.main()
                self.assertEqual(Path('daten/master_paper_state.json').read_text(encoding='utf8'),old_text)
                trailing=json.loads(Path('daten/master_trailing_state.json').read_text(encoding='utf8'))
                self.assertEqual(len(trailing['trades']),1)
            finally:
                os.chdir(orig)

    def test_trading_paper_integration_both_states_and_replay(self):
        import trading
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            orig=os.getcwd()
            os.chdir(d)
            try:
                trading.initialize_account(Path('daten/master_paper_state.json'))
                trading.initialize_account(Path('daten/master_trailing_state.json'), trailing=True)
                rep=r(actions={'BTC/EUR':'BEOBACHTEN: KAUFKANDIDAT'})
                with patch('sys.argv',['trading.py','paper']), \
                     patch.object(trading,'get_daily',return_value=({},object())), \
                     patch.object(trading,'aligned',side_effect=lambda x:x), \
                     patch.object(trading,'run_all',return_value=rep), \
                     patch.object(trading,'generate_markdown',return_value='TEST REPORT'), \
                     patch.object(trading.PublicKrakenQuotes,'fetch',return_value=q()):
                    trading.main()
                    base=Path('daten/master_paper_state.json')
                    trail=Path('daten/master_trailing_state.json')
                    self.assertTrue(base.exists() and trail.exists())
                    self.assertEqual(len(json.loads(base.read_text())['trades']),1)
                    self.assertEqual(len(json.loads(trail.read_text())['trades']),1)
                    trading.main()
                    self.assertEqual(len(json.loads(base.read_text())['trades']),1)
                    self.assertEqual(len(json.loads(trail.read_text())['trades']),1)
                    self.assertTrue(Path('VERGLEICH_MASTER.md').exists())
            finally:os.chdir(orig)

if __name__=='__main__':unittest.main()
