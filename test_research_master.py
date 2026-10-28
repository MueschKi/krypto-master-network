"""Safety and accounting tests for isolated v1.3 research."""
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
import pandas as pd

from market import synthetic_demo, aligned, SYMBOLS
from net_master import run_all
from backtest_master import open_quotes, replay
from trade_engine import fresh_account
from research_master import (
    analyze, _entry_diagnostics, _research_step, _roundtrip,
    modified_entries, render, save, VARIANTS,
)


class ResearchMasterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=aligned(synthetic_demo())

    def test_small_replay_has_parity_and_reconciliation(self):
        result=analyze(self.data,max_signals=12)
        original=result['variants']['Master unveraendert']
        self.assertEqual(original['curve'], [r['master_eur'] for r in result['baseline']['curve']])
        self.assertAlmostEqual(result['realized_eur']+result['unrealized_eur'],
                               original['curve'][-1]-1000,places=2)
        for v in VARIANTS:
            self.assertEqual(len(result['variants'][v]['curve']),12)
        self.assertIn('historische',render(result,'KÜNSTLICHE TESTDATEN').lower())

    def test_analysis_does_not_touch_paper_account(self):
        result=analyze(self.data,max_signals=5)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'daten').mkdir()
            account=root/'daten/master_paper_state.json'
            account.write_text('{"important":"not touched"}',encoding='utf-8')
            save(result,root,source='KÜNSTLICHE TESTDATEN')
            self.assertEqual(account.read_text(encoding='utf-8'),'{"important":"not touched"}')
            for p in ('DIAGNOSE_MASTER.md','daten/master_v13_trades.csv',
                      'daten/master_v13_entry.csv','daten/master_v13_kurven.csv'):
                self.assertTrue((root/p).is_file(),p)

    def test_no_buy_on_risk_block_even_without_volume_gates(self):
        rep=run_all({s:df.iloc[:300] for s,df in self.data.items()})
        r=deepcopy(rep)
        a=r['assets'][0]
        a['action']='ABWARTEN'
        a['gates']={
          'Trend positiv':True,'Momentum positiv':True,
          'Struktur mindestens neutral':True,'Volumensignal mindestens neutral':False,
          'Relatives Tagesvolumen mindestens 0,8':False,'OBV steigend':False,
          'Einstiegsszenario akzeptabel':True,'Nicht knapp unter Widerstand':True,
          'Risiko-Bot: freigegeben':False,
        }
        self.assertEqual(modified_entries(r)['assets'][0]['action'],'ABWARTEN')
        a['gates']['Risiko-Bot: freigegeben']=True
        a['agents']['risiko']['signal']='OK'
        self.assertEqual(modified_entries(r)['assets'][0]['action'],'BEOBACHTEN: KAUFKANDIDAT')
        self.assertEqual(rep['assets'][0]['action'],run_all({s:df.iloc[:300] for s,df in self.data.items()})['assets'][0]['action'])

    def test_trailing_stop_only_raises_and_uses_original_risk_budget(self):
        i=310
        report=run_all({s:df.iloc[:i+1] for s,df in self.data.items()})
        rep=deepcopy(report)
        a=next(a for a in rep['assets'] if a['symbol']=='BTC/EUR')
        a['action']='BEOBACHTEN: KAUFKANDIDAT'
        state=_research_step(fresh_account(),rep,open_quotes(self.data,i+1), 'ATR-Trailing 2,5x')
        self.assertIn('BTC/EUR',state['positions'])
        original=state['positions']['BTC/EUR']['research_stop_eur']
        rep2=deepcopy(rep)
        for a in rep2['assets']:
            a['date']=self.data[SYMBOLS[0]].index[i+1].date().isoformat()
        a=next(a for a in rep2['assets'] if a['symbol']=='BTC/EUR')
        a['action']='ABWARTEN'
        a['agents']['setup']['facts']['indikative_einstiegsbasis']=state['positions']['BTC/EUR']['entry_price_eur']*1.2
        a['agents']['volatilitaet']['facts']['atr14']=float(state['positions']['BTC/EUR']['entry_price_eur'])*0.01
        nextstate=_research_step(state,rep2,open_quotes(self.data,i+2), 'ATR-Trailing 2,5x')
        self.assertGreaterEqual(nextstate['positions']['BTC/EUR']['research_stop_eur'],original)
        self.assertLessEqual(sum(p['cost_basis_eur'] for p in nextstate['positions'].values()),450+1e-6)

    def test_mfe_excludes_fill_day_extremes(self):
        idx=pd.date_range('2026-01-01',periods=5,freq='D',tz='UTC')
        df=pd.DataFrame({'high':[100,1000,110,1000,100], 'low':[100,1,90,1,100]},index=idx)
        buy={'day':'2026-01-01','fill_price_eur':100}
        sell={'day':'2026-01-03','fill_price_eur':100,'realized_pnl_eur':-1,'reason':'Test Stopp'}
        out=_roundtrip(df,'BTC/EUR',buy,sell,1,3,False)
        self.assertAlmostEqual(out['mfe_pct_intraday_excl_fill_days'],10)
        self.assertAlmostEqual(out['mae_pct_intraday_excl_fill_days'],-10)

    def test_open_position_on_last_day_is_supported(self):
        idx=pd.date_range('2026-01-01',periods=3,freq='D',tz='UTC')
        df=pd.DataFrame({'high':[100,101,102],'low':[99,98,98]},index=idx)
        buy={'day':'2026-01-02','fill_price_eur':100}
        out=_roundtrip(df,'BTC/EUR',buy,None,2,2,True)
        self.assertTrue(out['open'])
        self.assertEqual(out['bars_held'],0)
        self.assertIsNone(out['mfe_pct_intraday_excl_fill_days'])

    def test_future_entry_diagnostics_not_used_for_signal(self):
        i=350
        report=run_all({s:df.iloc[:i+1] for s,df in self.data.items()})
        totals,found,rows=_entry_diagnostics(self.data,[(i,report)],horizon=7)
        changed={s:df.copy() for s,df in self.data.items()}
        for sym in SYMBOLS:
            changed[sym].iloc[i+8,changed[sym].columns.get_loc('open')]*=3
        _,found_changed,rows_changed=_entry_diagnostics(changed,[(i,report)],horizon=7)
        self.assertEqual(totals,CounterFromRows(rows))
        self.assertEqual([a['action'] for a in report['assets']],
                         [a['action'] for a in run_all({s:df.iloc[:i+1] for s,df in changed.items()})['assets']])
        self.assertEqual(len(rows),len(rows_changed))
        self.assertTrue(any(x['forward_7d_open_to_open_pct']!=y['forward_7d_open_to_open_pct'] for x,y in zip(rows,rows_changed)) if rows else True)


def CounterFromRows(rows):
    from collections import Counter
    c=Counter()
    for r in rows:
        for g in filter(None,r['failed_gates'].split(' | ')):c[g]+=1
    return c

if __name__=='__main__': unittest.main()
