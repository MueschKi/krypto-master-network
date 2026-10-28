"""v1.3: purely historical entry/exit research. NEVER reads or writes a live account.

The 1.2 master and its automatic paper execution are NOT changed. All variants
use the same historical OHLCV, master decisions, risk budgets, NEXT-bar opening
quotes and cost assumptions. All tested periods were previously inspected:
results are exploratory/in-sample, NOT validated performance forecasts.
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path

from backtest_master import WARMUP, drawdown, euros, open_quotes, replay
from market import SYMBOLS, aligned, get_daily, synthetic_demo
from trade_engine import (
    START_EUR, FEE_RATE, SLIPPAGE_RATE, MAX_COIN_WEIGHT, MAX_EXPOSURE,
    MIN_ORDER_EUR, CASH_RESERVE_EUR, HALT_DRAWDOWN, STOP_FRACTION,
    equity, fresh_account, run_paper, trade, validate_state,
)

ENTRY_OMITTED_GATES = frozenset({
    'Volumensignal mindestens neutral',
    'Relatives Tagesvolumen mindestens 0,8',
    'OBV steigend',
})
VARIANTS = ('Master unveraendert', 'ATR-Stopp 2x', 'ATR-Trailing 2,5x',
            'Ohne Volumen-Veto', 'EMA20/SMA50 (Master-Limits)')


def _get_atr(asset):
    v = float(asset['agents']['volatilitaet']['facts']['atr14'])
    if not isfinite(v) or v <= 0:
        raise ValueError('Ungueltiger ATR fuer Stoppsimulation')
    return v


def _get_close(asset):
    v = float(asset['agents']['setup']['facts']['indikative_einstiegsbasis'])
    if not isfinite(v) or v <= 0:
        raise ValueError('Ungueltiger Schlusskurs')
    return v


def modified_entries(report):
    """EXPLORATORY ABLATION. Never used in the running master paper mode."""
    r = deepcopy(report)
    for a in r['assets']:
        if a['action'] != 'ABWARTEN':
            continue
        gates = a.get('gates', {})
        if (len(gates) == 9 and
                all(ok for name, ok in gates.items() if name not in ENTRY_OMITTED_GATES)):
            a['action'] = 'BEOBACHTEN: KAUFKANDIDAT'
            a['reasons'].append('FORSCHUNG: Volumen-Veto hypothetisch ausgelassen')
    return r


def _research_step(state, report, quotes, variant):
    """Isolated simulated execution engine for alternate EXIT rules.

    This deliberately mirrors the checked v1.2 engine's risk, cash, position,
    and exit-on-weak-market logic. Parity with original on fixed 7%-exit is a
    mandatory assertion in historical runs and automated tests.
    """
    validate_state(state)
    s = deepcopy(state)
    day = report['assets'][0]['date']
    assert {a['date'] for a in report['assets']} == {day}
    assert set(quotes) == set(SYMBOLS)
    portfolio_before = equity(s, quotes)
    s['highest_equity_eur'] = max(float(s['highest_equity_eur']), portfolio_before)
    if 1 - portfolio_before / s['highest_equity_eur'] >= HALT_DRAWDOWN:
        s['halt_new_buys'] = True
    decisions = []
    for a in sorted(report['assets'], key=lambda a: a['symbol']):
        sym = a['symbol']
        p = s['positions'].get(sym)
        if not p:
            continue
        last_close = _get_close(a)
        entry = float(p['entry_price_eur'])
        if variant in ('Master unveraendert', 'Ohne Volumen-Veto'):
            stop = last_close <= entry * (1 - STOP_FRACTION)
        elif variant == 'ATR-Stopp 2x':
            stop = last_close <= float(p['research_stop_eur'])
        else:
            # The trailing threshold is computed using only earlier known closes.
            stop = last_close <= float(p['research_stop_eur'])
        reverse = a['action'] == 'SCHWACHER MARKT'
        if stop or reverse:
            reason = ('Master: schwacher Markt' if not stop else
                      ('7%-Tagesschluss-Stopp (keine garantierte Ausführung)'
                       if variant in ('Master unveraendert', 'Ohne Volumen-Veto')
                       else f'FORSCHUNG: {variant} Schlusskurs-Stopp'))
            trade(s, sym, 'SELL', quotes[sym], 0, day, reason)
            decisions.append({'symbol': sym, 'decision': 'SELL', 'reason': reason})
        else:
            if variant == 'ATR-Trailing 2,5x':
                # Update AFTER stop check. The bar is closed; the next day's
                # stop comparison is made to this newly known value.
                p['research_peak_close'] = max(float(p['research_peak_close']),last_close)
                p['research_stop_eur'] = max(float(p['research_stop_eur']),
                                            float(p['research_peak_close']) - 2.5*_get_atr(a))
            decisions.append({'symbol': sym, 'decision':'HOLD', 'reason':'Bestehende Position halten'})
    for a in sorted(report['assets'], key=lambda a: a['symbol']):
        sym = a['symbol']
        if sym in s['positions'] or any(d['symbol'] == sym for d in decisions):
            continue
        if a['action'] != 'BEOBACHTEN: KAUFKANDIDAT':
            decisions.append({'symbol':sym,'decision':'HOLD','reason':a['action']})
            continue
        if a['agents'].get('risiko', {}).get('signal') != 'OK':
            decisions.append({'symbol':sym,'decision':'BLOCK','reason':'Risiko-Bot hat Veto'})
            continue
        if s['halt_new_buys']:
            decisions.append({'symbol':sym,'decision':'BLOCK','reason':'Drawdown-Sperre'})
            continue
        current = equity(s, quotes)
        invested = current - s['cash_eur']
        deployed_cost = sum(float(p['cost_basis_eur']) for p in s['positions'].values())
        budget = min(current * MAX_COIN_WEIGHT,
                     current * MAX_EXPOSURE - invested,
                     float(s['initial_eur']) * MAX_EXPOSURE - deployed_cost,
                     s['cash_eur'] - CASH_RESERVE_EUR)
        if budget < MIN_ORDER_EUR:
            decisions.append({'symbol':sym,'decision':'HOLD','reason':'Zu wenig freies Risikobudget'})
            continue
        trade(s, sym, 'BUY', quotes[sym], budget, day,
              'Master-Kaufkandidat + Risiko-Freigabe')
        if variant in ('ATR-Stopp 2x', 'ATR-Trailing 2,5x'):
            p = s['positions'][sym]
            entry = float(p['entry_price_eur'])
            factor = 2.0 if variant == 'ATR-Stopp 2x' else 2.5
            p['research_stop_eur'] = max(0.000000001, entry - factor*_get_atr(a))
            if variant == 'ATR-Trailing 2,5x':
                p['research_peak_close'] = _get_close(a)
        decisions.append({'symbol':sym,'decision':'BUY','reason':f'Virtueller Einsatz {budget:.2f} EUR'})
    now_equity = equity(s, quotes)
    s['highest_equity_eur'] = max(float(s['highest_equity_eur']), now_equity)
    s['halt_new_buys'] = bool(s['halt_new_buys']) or (1 - now_equity/s['highest_equity_eur'] >= HALT_DRAWDOWN)
    s['last_equity_eur'] = now_equity
    s['last_processed_day'] = day
    s['decisions'] = decisions
    s['quote_snapshot'] = {sym:{'bid':q.bid,'ask':q.ask,'observed_utc':q.observed_utc}
                           for sym,q in quotes.items()}
    s['equity_history'].append({'day':day,'equity_eur':round(now_equity,6),
                                'cash_eur':round(s['cash_eur'],6)})
    validate_state(s)
    return s


def _trend_benchmark(report,data,i,indicator_cache):
    """CONTROL ONLY: EMA20/SMA50 decision with SAME master risk/cost/cash limits.

    Not an exact reproduction of the separate old v0.4 portfolio (which had
    different exposure sizing). This isolates entry rule differences.
    """
    r=deepcopy(report)
    for a in r['assets']:
        sym=a['symbol']
        if a['action']=='DATENSPERRE':continue
        close=float(data[sym]['close'].iloc[i])
        ema20=float(indicator_cache[sym]['ema20'].iloc[i])
        sma50=float(indicator_cache[sym]['sma50'].iloc[i])
        a['action']=('BEOBACHTEN: KAUFKANDIDAT' if close>sma50 and ema20>sma50
                     else 'SCHWACHER MARKT')
    return r


def _trade_diagnostics(baseline, data, timestamps):
    """MFE/MAE use only full daily bars STRICTLY BETWEEN entry and exit opens.
    Never used as a trigger: future prices are consulted ONLY for diagnostics.
    """
    dates = data[SYMBOLS[0]].index
    indices = {d.date().isoformat():i for i,d in enumerate(dates)}
    opened={}
    out=[]
    for t in baseline['state']['trades']:
        sym=t['symbol']; signal_day=t['day']
        fill_i=indices[signal_day]+1
        if t['side']=='BUY':
            if sym in opened: raise AssertionError('Overlapping buy positions')
            opened[sym] = (t,fill_i)
        else:
            if sym not in opened: raise AssertionError('Sell without opening buy')
            buy,buy_i = opened.pop(sym)
            out.append(_roundtrip(data[sym],sym,buy,t,buy_i,fill_i,False))
    # Open positions are NOT counted as completed winning trades.
    final_i = timestamps[-1] + 1
    for sym,(buy,buy_i) in opened.items():
        out.append(_roundtrip(data[sym],sym,buy,None,buy_i,final_i,True))
    return out


def _roundtrip(df,symbol,buy,sell,buy_i,last_i,is_open):
    entry=float(buy['fill_price_eur'])
    if last_i < buy_i or (last_i == buy_i and not is_open):
        raise AssertionError('Negative or zero completed holding duration')
    # Exclude entry day's and exit/valuation day's intraday extremes: their
    # order relative to an open fill is uncertain and may look ahead.
    section=df.iloc[buy_i+1:last_i]
    mfe=max(0.0,(float(section['high'].max())/entry-1)*100) if len(section) else None
    mae=min(0.0,(float(section['low'].min())/entry-1)*100) if len(section) else None
    pnl=float(sell['realized_pnl_eur']) if sell is not None else None
    return {'coin':symbol,'entry_signal_day':buy['day'],
            'entry_fill_day':df.index[buy_i].date().isoformat(),
            'exit_signal_day':sell['day'] if sell else '',
            'exit_fill_day':df.index[last_i].date().isoformat(),
            'bars_held':last_i-buy_i, 'open':is_open,
            'entry_price_eur':round(entry,8),
            'exit_price_eur':round(float(sell['fill_price_eur']),8) if sell else None,
            'net_realized_eur':pnl, 'exit_reason':sell['reason'] if sell else 'Offene Position',
            'mfe_pct_intraday_excl_fill_days':round(mfe,4) if mfe is not None else None,
            'mae_pct_intraday_excl_fill_days':round(mae,4) if mae is not None else None}


def _entry_diagnostics(data,snapshots,horizon=7,threshold=.03):
    """Descriptive NOT tradeable: forward movement after each blocked signal.
    Future data never affect decisions, only this retrospective diagnostic.
    """
    totals=Counter(); up=Counter(); rows=[]
    for i,report in snapshots:
        if i+1+horizon >= len(data[SYMBOLS[0]]): continue
        for a in report['assets']:
            if a['action']=='BEOBACHTEN: KAUFKANDIDAT': continue
            sym=a['symbol']; df=data[sym]
            entry=float(df['open'].iloc[i+1]); after=float(df['open'].iloc[i+1+horizon]);
            if entry<=0 or not isfinite(entry) or not isfinite(after):continue
            change=after/entry-1
            gates=a.get('failed_gates',[])
            for g in gates:
                totals[g]+=1;up[g]+=int(change>=threshold)
            rows.append({'coin':sym,'signal_day':df.index[i].date().isoformat(),
                         'master_action':a['action'],
                         'failed_gates':' | '.join(gates),
                         'forward_7d_open_to_open_pct':round(change*100,4)})
    return totals,up,rows


def _variant_results(data,snapshots,baseline):
    all_results={}
    indicator_cache={sym:{'ema20':df['close'].ewm(span=20,adjust=False).mean(),
                          'sma50':df['close'].rolling(50).mean()}
                     for sym,df in data.items()}
    base_equities=[r['master_eur'] for r in baseline['curve']]
    for variant in VARIANTS:
        state=fresh_account(); curve=[]
        for i,report in snapshots:
            quotes=open_quotes(data,i+1)
            new_report=(modified_entries(report) if variant=='Ohne Volumen-Veto' else
                        _trend_benchmark(report,data,i,indicator_cache)
                        if variant=='EMA20/SMA50 (Master-Limits)' else report)
            if variant in ('Master unveraendert','Ohne Volumen-Veto','EMA20/SMA50 (Master-Limits)'):
                state, changed=run_paper(state,new_report,quotes)
                if not changed:raise AssertionError('Duplicate backtest day')
            else:
                state=_research_step(state,new_report,quotes,variant)
            curve.append(round(float(state['last_equity_eur']),6))
        if variant=='Master unveraendert':
            if len(curve)!=len(base_equities) or any(abs(a-b)>0.00001 for a,b in zip(curve,base_equities)):
                raise AssertionError('Research baseline differs from production master replay')
        all_results[variant]={'state':state, 'curve':curve,
                              'return_pct':(curve[-1]/START_EUR-1)*100,
                              'max_drawdown_pct':drawdown(curve),
                              'executions':len(state['trades']),
                              'closed':sum(t['side']=='SELL' for t in state['trades'])}
    return all_results


def analyze(data,max_signals=None):
    data=aligned(data)
    snapshots=[]
    def capture(report,index):
        snapshots.append((index,report))
        return report
    baseline=replay(data,max_signals=max_signals,strategy_override=capture)
    variants=_variant_results(data,snapshots,baseline)
    roundtrips=_trade_diagnostics(baseline,data,[i for i,_ in snapshots])
    misses,followups,entry_rows=_entry_diagnostics(data,snapshots)
    state=baseline['state']
    last_quotes=open_quotes(data,snapshots[-1][0]+1)
    unrealized=sum(float(p['qty'])*last_quotes[s].mid-float(p['cost_basis_eur'])
                   for s,p in state['positions'].items())
    realized=sum(float(t['realized_pnl_eur']) for t in state['trades'] if t['side']=='SELL')
    reconciliation=realized+unrealized
    if abs(reconciliation-(float(state['last_equity_eur'])-START_EUR))>0.02:
        raise AssertionError('P&L components do not reconcile; inspect simulator')
    return {'baseline':baseline,'snapshots':snapshots,'variants':variants,
            'roundtrips':roundtrips,'entry_totals':misses,'entry_followups':followups,
            'entry_rows':entry_rows, 'realized_eur':realized, 'unrealized_eur':unrealized,
            'source_start':baseline['source_start'],'source_end':baseline['source_end'],
            'days':len(snapshots)}


def _fmt(x,suffix=''):
    return '—' if x is None else f'{x:+.2f}{suffix}'


def render(result,source='ECHTE KRAKEN-TAGESKURSE'):
    base=result['baseline']; variants=result['variants']; trips=result['roundtrips']
    completed=[t for t in trips if not t['open']]
    wins=[t for t in completed if t['net_realized_eur']>0]
    stop_trips=[t for t in completed if 'Stopp' in t['exit_reason']]
    now=datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M UTC')
    lines=[
        '# Krypto Master Network v1.3 – Entry-/Exit-Diagnose', '',
        '**NUR HISTORISCHE FORSCHUNG. KEINE ECHTGELD-ORDERS. KEINE AUTOMATISCHE STRATEGIEÄNDERUNG.**', '',
        f'Erstellt: {now}  ', f'Datenquelle: **{source}**  ',
        f'Verfügbarer Kurszeitraum: {result["source_start"]} bis {result["source_end"]}  ',
        f'Simulierte Signal-Tage: **{result["days"]}**. Mindestens {WARMUP} Vorlaufkerzen.', '',
        '## Gleiche historischen Preise und Handelskosten – Variantenvergleich', '',
        '| Variante | Endwert | Nettorendite | Max. Rückgang | Ausführungen | Geschlossene Trades |',
        '|:--|--:|--:|--:|--:|--:|',
    ]
    for name,v in variants.items():
        lines.append(f'| {name} | {euros(v["curve"][-1])} | {v["return_pct"]:+.2f} % | '
                     f'{v["max_drawdown_pct"]:.2f} % | {v["executions"]} | {v["closed"]} |')
    lines += ['',
      '**Methodik:** Identische Master-Signale, vier Coins, Startkapital 1.000 €, Risiko- und Cash-Obergrenzen. '
      'Simulierte Ausführung frühestens am nächsten Tages-Open, hypothetischer Gesamtspread 0,15 %, '
      f'Gebühren {100*FEE_RATE:.1f} % und Zusatz-Slippage {100*SLIPPAGE_RATE:.1f} % pro Ausführung.',
      'Alle Varianten verwenden dieselben **bereits bekannten historischen Testdaten**. '
      '**Ein höherer Wert ist kein unabhängiger Wirksamkeitsnachweis.**', '',
      '### Exakte Regeländerungen im Forschungstest', '',
      '- **Master unverändert:** Originale neun Entry-Gates und 7-%-Schlusskurs-Stopp.',
      '- **ATR-Stopp 2x:** gleiche Einstiegssignale, fester Einstiegskurs minus 2× ATR14 zum Kaufsignal; '
      'abgeschlossene Tagesschlusskurse lösen ggf. Verkauf zum nächsten Open aus.',
      '- **ATR-Trailing 2,5x:** gleiche Einstiegssignale, Anfangsstopp Einstieg minus 2,5× ATR14; '
      'Nachziehen anhand bisher abgeschlossener Schlusskurse, nie absenken.',
      '- **EMA20/SMA50 (Master-Limits):** einfache Trendfolge nach Kurs > SMA50 und EMA20 > SMA50; '
      'Verkauf bei Trendbruch, aber Positionslimits des Masters. **Keine exakte Reproduktion des alten separaten v0.4-Depots**.',
      '- **Ohne Volumen-Veto:** reine Entry-Ablation: drei Volumen-/OBV-Bedingungen entfallen, '
      'alle übrigen Gates sowie das Risiko-Veto bleiben; ursprünglicher 7-%-Stopp.',
      '- Keine Variable oder Parameter aus dem Vergleich wird in `trading.py`, `trade_engine.py` '
      'oder das echte Paper-Konto übernommen.', '',
      '## Original-Master: Gewinne und offene Positionen getrennt', '',
      f'- Realisierte abgeschlossene Trades: **{euros(result["realized_eur"])}**.',
      f'- Bewertung offener Positionen relativ zu ihren Kosten: **{euros(result["unrealized_eur"])}**.',
      f'- Zusammen ergibt das die Depotveränderung: **{euros(result["realized_eur"]+result["unrealized_eur"])}**.',
      f'- Gewinner unter geschlossenen Trades: **{len(wins)} von {len(completed)}**.',
      f'- Geschlossene Trades nach Schlusskurs-Stopp: **{len(stop_trips)}**.', '',
      '## Exit-Diagnose pro abgeschlossenem Trade', '',
      '| Coin | Einstieg (Open) | Ausstieg (Open) | Haltedauer (Bars) | Netto realisiert | MFE* | MAE* | Exit-Grund |',
      '|:--|:--|:--|--:|--:|--:|--:|:--|'
    ]
    for r in completed:
        lines.append(f'| {r["coin"]} | {r["entry_fill_day"]} | {r["exit_fill_day"]} | '
                     f'{r["bars_held"]} | {euros(r["net_realized_eur"])} | '
                     f'{_fmt(r["mfe_pct_intraday_excl_fill_days"]," %")} | '
                     f'{_fmt(r["mae_pct_intraday_excl_fill_days"]," %")} | {r["exit_reason"]} |')
    if not completed: lines.append('| Keine abgeschlossenen Trades | — | — | — | — | — | — | — |')
    lines += ['', '*MFE = größter zwischenzeitlicher Kursanstieg, MAE = stärkster Rückgang gegenüber dem Einstiegspreis. '
              'Reine Kursbewegungen **ohne Gebühren**; nur vollständige Tageskerzen zwischen Einstiegs- und Ausstiegs-Open, '
              'die beiden Fülltage werden bewusst ausgeschlossen. Bei kurzer Haltedauer können Werte fehlen. '
              'Diese Zukunftsdaten werden niemals für die Handelsentscheidung genutzt.', '',
              '## Entry-Diagnose: Was wurde rückblickend verpasst?', '',
              'Nach BLOCK/HOLD wird die **rein hypothetische** 7-Tage-Bewegung vom nächsten Open bis '
              'zum Open sieben Tage später ausgewertet. Ein Plus von mindestens 3 % ist kein realisierbarer '
              'Netto-Tradinggewinn. Überlappende Gates werden einzeln gezählt.', '',
              '| Nicht erfülltes Entry-Gate | Untersuchte Fälle | Danach mindestens +3 % | Anteil |',
              '|:--|--:|--:|--:|']
    for gate,total in result['entry_totals'].most_common():
        positives=result['entry_followups'][gate]
        lines.append(f'| {gate} | {total} | {positives} | {100*positives/total:.1f} % |')
    if not result['entry_totals']: lines.append('| Keine auswertbaren Fälle | — | — | — |')
    lines += ['', '## Interpretation und Sicherheitsgrenzen', '',
              '- **Selektionsbias:** Die Regeln und der historische Datenausschnitt waren bereits bekannt. '
              'Die Varianten sind Diagnoseexperimente, keine unberührten Out-of-sample-Ergebnisse.',
              '- Future-7d-Bewegungen und MFE/MAE dürfen ausschließlich **nachträglich** ausgewertet werden.',
              '- Gleichzeitige Signale, Korrelationscluster und überlappende 7-Tage-Fenster sind nicht unabhängig.',
              '- Historische Bid/Ask-Quotes und Intraday-Orderabfolge sind nicht verfügbar. '
              'Tages-Schlusskurs-Stopps bieten keinen garantierten Ausstiegspreis.',
              '- Die Forschung stellt keinen Echtgeld-Broker bereit und verändert das laufende Paper-Konto **nicht**.',
              '- Zuerst neue, bisher ungesehene Paper-Zeiträume und ggf. längere unabhängige Daten evaluieren.', '',
              'Maschinenlesbar: `daten/master_v13_trades.csv`, `daten/master_v13_entry.csv` '
              'und `daten/master_v13_kurven.csv`.', '']
    return '\n'.join(lines)


def _write_csv(path,records,headers):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=headers,extrasaction='ignore');w.writeheader();w.writerows(records)


def save(result,root=Path('.'),source='ECHTE KRAKEN-TAGESKURSE'):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    (root/'DIAGNOSE_MASTER.md').write_text(render(result,source),encoding='utf-8')
    _write_csv(root/'daten/master_v13_trades.csv',result['roundtrips'],[
        'coin','entry_signal_day','entry_fill_day','exit_signal_day','exit_fill_day','bars_held','open',
        'entry_price_eur','exit_price_eur','net_realized_eur','exit_reason',
        'mfe_pct_intraday_excl_fill_days','mae_pct_intraday_excl_fill_days'])
    _write_csv(root/'daten/master_v13_entry.csv',result['entry_rows'],[
        'coin','signal_day','master_action','failed_gates','forward_7d_open_to_open_pct'])
    rows=[]
    baseline=result['baseline']['curve']
    for j,r in enumerate(baseline):
        row={'signal_day_utc':r['signal_day_utc'],'fill_day_utc':r['fill_day_utc']}
        for variant,v in result['variants'].items():row[variant]=v['curve'][j]
        rows.append(row)
    _write_csv(root/'daten/master_v13_kurven.csv',rows,
               ['signal_day_utc','fill_day_utc']+list(VARIANTS))


def main():
    ap=argparse.ArgumentParser(description='Nur historische Forschung. KEINE Trades / keine Kontoänderung')
    ap.add_argument('modus',choices=['demo','historisch'])
    args=ap.parse_args()
    if args.modus=='demo':
        result=analyze(synthetic_demo(),max_signals=12)
        # Demo must not create publication files or overwrite user account.
        print('FORSCHUNGS-DEMO: 12 erfundene Signaltage erfolgreich; '
              'Produktion/Realkonto unverändert.')
        print('Variante Original:',result['variants']['Master unveraendert']['return_pct'])
    else:
        data,_=get_daily();result=analyze(data);save(result)
        print(f'MASTER-FORSCHUNG: {result["days"]} Tage, {len(result["roundtrips"])} '
              'Ein-/Ausstiegs-Fälle; DIAGNOSE_MASTER.md erstellt.')
        print('Paper-State unverändert. Echtgeldhandel technisch gesperrt.')


if __name__=='__main__':main()
