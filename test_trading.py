"""Regression tests: safety, accounting, replay and fail-closed execution."""
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from trade_broker import Quote, LiveExchangeAdapter, PublicKrakenQuotes
from trade_engine import fresh_account, run_paper, equity, validate_state
from trading import atomic_text, load_state

SYMS = ['BTC/EUR','ETH/EUR','NEAR/EUR','SOL/EUR']
DAY = '2026-10-27'


def quotes(day=DAY):
    return {s: Quote(s, 100.0, 100.1, day) for s in SYMS}


def report(actions=None, prices=None):
    actions = actions or {}
    prices = prices or {}
    return {'assets': [{'symbol':s, 'date':DAY, 'action':actions.get(s, 'ABWARTEN'),
                        'agents': {'daten': {'signal':'OK'},
                                   'risiko': {'signal':'OK'},
                                   'setup':{'facts':{'indikative_einstiegsbasis':prices.get(s, 100.)}}}}
                       for s in SYMS]}


class TradingTests(unittest.TestCase):
    def test_initial(self):
        self.assertEqual(fresh_account()['cash_eur'], 1000)

    def test_buy_fee_and_idempotency(self):
        a, changed = run_paper(fresh_account(), report({'BTC/EUR':'BEOBACHTEN: KAUFKANDIDAT'}), quotes())
        self.assertTrue(changed)
        self.assertEqual(len(a['trades']),1)
        self.assertEqual(a['trades'][0]['type'],'SIMULATION_ONLY')
        self.assertLess(equity(a,quotes()),1000)
        self.assertAlmostEqual(a['cash_eur'],880,places=2)
        b, changed = run_paper(a,report({'BTC/EUR':'BEOBACHTEN: KAUFKANDIDAT'}),quotes())
        self.assertFalse(changed)
        self.assertEqual(a,b)

    def test_sell_following_day_when_market_weak(self):
        s, _ = run_paper(fresh_account(), report({'BTC/EUR':'BEOBACHTEN: KAUFKANDIDAT'}), quotes())
        r = report({'BTC/EUR':'SCHWACHER MARKT'})
        for a in r['assets']:a['date']='2026-10-28'
        b, _ = run_paper(s,r,quotes())
        self.assertFalse(b['positions'])
        self.assertEqual([x['side'] for x in b['trades']], ['BUY','SELL'])
        self.assertLess(b['trades'][1]['realized_pnl_eur'],0)

    def test_stop_sells_even_when_other_buy_blocked(self):
        s, _ = run_paper(fresh_account(), report({'BTC/EUR':'BEOBACHTEN: KAUFKANDIDAT'}), quotes())
        r = report({'ETH/EUR':'BEOBACHTEN: KAUFKANDIDAT'}, {'BTC/EUR':90})
        for a in r['assets']:a['date']='2026-10-28'
        s['halt_new_buys'] = True
        b, _ = run_paper(s,r,quotes())
        self.assertFalse(b['positions'])
        self.assertEqual(len(b['trades']),2)

    def test_no_buy_when_risk_veto(self):
        r=report({'ETH/EUR':'BEOBACHTEN: KAUFKANDIDAT'})
        r['assets'][1]['agents']['risiko']['signal']='BLOCKIERT'
        a,_=run_paper(fresh_account(),r,quotes())
        self.assertEqual(len(a['trades']),0)

    def test_invalid_data_blocks_all(self):
        r=report({'BTC/EUR':'BEOBACHTEN: KAUFKANDIDAT'})
        r['assets'][0]['action']='DATENSPERRE'
        with self.assertRaises(ValueError):run_paper(fresh_account(),r,quotes())

    def test_bad_quote_blocks_all(self):
        q=quotes()
        q['NEAR/EUR']=Quote('NEAR/EUR',99,101,DAY)
        with self.assertRaises(ValueError):run_paper(fresh_account(),report(),q)
        del q['NEAR/EUR']
        with self.assertRaises(ValueError):run_paper(fresh_account(),report(),q)

    def test_misaligned_dates_block(self):
        r=report(); r['assets'][0]['date']='2026-10-26'
        with self.assertRaises(ValueError):run_paper(fresh_account(),r,quotes())

    def test_sticky_drawdown(self):
        s=fresh_account();s['highest_equity_eur']=1200
        a,_=run_paper(s,report({'BTC/EUR':'BEOBACHTEN: KAUFKANDIDAT'}),quotes())
        self.assertTrue(a['halt_new_buys'])
        self.assertEqual(len(a['trades']),0)

    def test_real_adapter_unconditionally_locked(self):
        with self.assertRaises(PermissionError):LiveExchangeAdapter(apiKey='fake')
        with self.assertRaises(PermissionError):LiveExchangeAdapter.place_order(None,'BTC/EUR','buy',1)

    def test_public_quotes_no_private_calls(self):
        class FakeEx:
            def fetch_order_book(self,symbol,limit=5):
                return {'bids': [[99,1]], 'asks': [[99.1,1]]}
            def create_order(self,*args,**kwargs):
                raise AssertionError('real order requested')
        data=PublicKrakenQuotes(FakeEx()).fetch(SYMS)
        self.assertEqual(len(data),4)

    def test_invalid_state_never_reset(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'state.json';p.write_text('{invalid',encoding='utf8')
            with self.assertRaises(json.JSONDecodeError):load_state(p)
            atomic_text(p,'{"version":"broken"}')
            with self.assertRaises(ValueError):load_state(p)

    def test_atomic_file_write(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'daten/status.md'
            atomic_text(p,'first')
            atomic_text(p,'second')
            self.assertEqual(p.read_text(), 'second')

    def test_no_leverage_or_negative_cash(self):
        a,_=run_paper(fresh_account(),report({s:'BEOBACHTEN: KAUFKANDIDAT' for s in SYMS}),quotes())
        self.assertGreaterEqual(a['cash_eur'],300)
        self.assertLessEqual(1000-a['cash_eur'],450+1e-6)
        self.assertLessEqual(len(a['trades']),4)


if __name__=='__main__': unittest.main()
