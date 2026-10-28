"""Standalone, strictly simulated 2.5x ATR trailing-exit paper engine.

Inputs: a prior day's fully closed OHLCV analysis and a subsequent *public* bid/ask
snapshot. Exit trigger uses close vs the stop saved at the END of the PRIOR run;
new stop is raised after the trigger check and is never lowered. No exchange
orders, no secret keys, no account access beyond a caller-supplied dict.

The production 7%% engine remains in trade_engine.py and is NOT modified.
"""
from __future__ import annotations
from copy import deepcopy
from math import isfinite

from trade_engine import (ALLOWED, MAX_EXPOSURE, MAX_COIN_WEIGHT, MIN_ORDER_EUR,
                          CASH_RESERVE_EUR, HALT_DRAWDOWN, equity, trade,
                          validate_state)
from trade_broker import Quote

ATR_FACTOR = 2.5
POLICY_NAME = 'atr_trailing_2_5_close'


def _positive_number(v, name):
    try:
        n = float(v)
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f'Ungültig: {name}') from None
    if not isfinite(n) or n <= 0:
        raise ValueError(f'Ungültig: {name}')
    return n


def _validate_trailing_positions(state):
    validate_state(state)
    for symbol, p in state['positions'].items():
        # Fail closed: do not silently initialize a missing stop on existing positions.
        stop = _positive_number(p.get('trailing_stop_eur'), f'{symbol}: Stopp fehlt')
        peak = _positive_number(p.get('trailing_peak_close'), f'{symbol}: Hoch fehlt')
        if stop >= peak:
            raise ValueError(f'{symbol}: Trailing-Stopp über/equal Höchstkurs')
    if state.get('exit_policy') not in (None, POLICY_NAME):
        raise ValueError('Fremde Exit-Strategie im Trailing-Konto')


def run_trailing_paper(state: dict, report: dict, quotes: dict[str, Quote]) -> tuple[dict, bool]:
    """Return (new_state, changed). Old state remains unchanged, ever."""
    _validate_trailing_positions(state)
    assets = report.get('assets', [])
    symbols = [a.get('symbol') for a in assets]
    if len(symbols) != len(ALLOWED) or set(symbols) != ALLOWED:
        raise ValueError('Analyse unvollständig oder doppelt')
    dates = {a.get('date') for a in assets}
    if len(dates) != 1 or None in dates:
        raise ValueError('Verschiedene oder fehlende Handelstage')
    day = dates.pop()
    if state.get('last_processed_day') and day <= state['last_processed_day']:
        return deepcopy(state), False
    for a in assets:
        if a.get('action') == 'DATENSPERRE' or a.get('agents', {}).get('daten', {}).get('signal') != 'OK':
            raise ValueError('Datenqualität nicht OK – kein Handel')
        _positive_number(a.get('agents', {}).get('setup', {}).get('facts', {}).get('indikative_einstiegsbasis'), 'Schlusskurs')
        _positive_number(a.get('agents', {}).get('volatilitaet', {}).get('facts', {}).get('atr14'), 'ATR14')
    if set(quotes) != ALLOWED:
        raise ValueError('Orderbuch fehlt – kein Handel')
    for sym, quote in quotes.items():
        if quote.symbol != sym:
            raise ValueError('Falsches Quote-Symbol')
        quote.validate()

    s = deepcopy(state)
    s['exit_policy'] = POLICY_NAME
    pre = equity(s, quotes)
    if not isfinite(pre) or pre <= 0:
        raise ValueError('Ungültiger Portfoliowert')
    s['highest_equity_eur'] = max(float(s['highest_equity_eur']), pre)
    if 1 - pre / s['highest_equity_eur'] >= HALT_DRAWDOWN:
        s['halt_new_buys'] = True

    decisions = []
    for a in sorted(assets, key=lambda item: item['symbol']):
        sym = a['symbol']
        p = s['positions'].get(sym)
        if p is None:
            continue
        close = float(a['agents']['setup']['facts']['indikative_einstiegsbasis'])
        # Old stop is known before this new candle. Closed candle triggers next snapshot fill.
        stop_before = float(p['trailing_stop_eur'])
        stop_hit = close <= stop_before
        weak = a['action'] == 'SCHWACHER MARKT'
        if stop_hit or weak:
            reason = (f'ATR-Trailing 2,5x: Close {close:.4f} <= Stopp {stop_before:.4f}; '
                      'spätere simulierte Ausführung' if stop_hit else 'Master: schwacher Markt')
            trade(s, sym, 'SELL', quotes[sym], 0, day, reason)
            decisions.append({'symbol': sym, 'decision': 'SELL', 'reason': reason})
        else:
            atr = float(a['agents']['volatilitaet']['facts']['atr14'])
            peak = max(float(p['trailing_peak_close']), close)
            candidate = peak - ATR_FACTOR * atr
            # Existing stop can NEVER be loosened and must stay below peak.
            p['trailing_peak_close'] = peak
            p['trailing_stop_eur'] = max(stop_before, candidate)
            decisions.append({'symbol': sym, 'decision': 'HOLD',
                              'reason': f'ATR-Trailing-Stopp {p["trailing_stop_eur"]:.4f}'})

    for a in sorted(assets, key=lambda item: item['symbol']):
        sym = a['symbol']
        if sym in s['positions'] or any(d['symbol'] == sym for d in decisions):
            continue  # no re-entry on same day after a sale
        if a['action'] != 'BEOBACHTEN: KAUFKANDIDAT':
            decisions.append({'symbol': sym, 'decision': 'HOLD', 'reason': a['action']})
            continue
        if a['agents'].get('risiko', {}).get('signal') != 'OK':
            decisions.append({'symbol': sym, 'decision': 'BLOCK', 'reason': 'Risiko-Veto'})
            continue
        if s['halt_new_buys']:
            decisions.append({'symbol': sym, 'decision': 'BLOCK', 'reason': 'Drawdown-Sperre'})
            continue
        current = equity(s, quotes)
        invested = current - float(s['cash_eur'])
        deployed_cost = sum(float(p['cost_basis_eur']) for p in s['positions'].values())
        budget = min(current * MAX_COIN_WEIGHT,
                     current * MAX_EXPOSURE - invested,
                     float(s['initial_eur']) * MAX_EXPOSURE - deployed_cost,
                     float(s['cash_eur']) - CASH_RESERVE_EUR)
        if not isfinite(budget) or budget < MIN_ORDER_EUR:
            decisions.append({'symbol': sym, 'decision': 'HOLD', 'reason': 'Risikobudget reicht nicht'})
            continue
        trade(s, sym, 'BUY', quotes[sym], budget, day,
              'Master-Kaufkandidat + Risiko-Freigabe; ATR-Trailing 2,5x')
        p = s['positions'][sym]
        entry = float(p['entry_price_eur'])
        close = float(a['agents']['setup']['facts']['indikative_einstiegsbasis'])
        atr = float(a['agents']['volatilitaet']['facts']['atr14'])
        stop = entry - ATR_FACTOR * atr
        # Fail closed instead of inventing an invalid tiny stop when ATR is huge.
        if stop <= 0:
            raise ValueError(f'{sym}: ATR-Stopp würde <= 0; kein Depot wird gebucht')
        p['trailing_stop_eur'] = stop
        p['trailing_peak_close'] = max(entry, close)
        decisions.append({'symbol': sym, 'decision':'BUY',
                          'reason': f'Virtueller Einsatz {budget:.2f} EUR; Start-Stopp {stop:.4f}'})

    now = equity(s, quotes)
    s['highest_equity_eur'] = max(float(s['highest_equity_eur']), now)
    if 1 - now/s['highest_equity_eur'] >= HALT_DRAWDOWN:
        s['halt_new_buys'] = True
    s['last_equity_eur'] = now
    s['last_processed_day'] = day
    s['decisions'] = decisions
    s['quote_snapshot'] = {sym: {'bid': q.bid, 'ask': q.ask, 'observed_utc': q.observed_utc}
                           for sym, q in quotes.items()}
    s['equity_history'].append({'day':day,'equity_eur':round(now,6),
                                'cash_eur':round(float(s['cash_eur']),6)})
    _validate_trailing_positions(s)
    return s, True
