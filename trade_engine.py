"""Deterministic spot-only Paper Trading engine. EUR cash, no margin or shorting.

All modifications happen in memory; the caller commits state atomically only after
successful validation of the entire multi-coin run.
"""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
from math import isfinite

from trade_broker import Quote

START_EUR = 1000.0
FEE_RATE = 0.004
SLIPPAGE_RATE = 0.001
MAX_COIN_WEIGHT = 0.12
MAX_EXPOSURE = 0.45
MIN_ORDER_EUR = 15.0
CASH_RESERVE_EUR = 300.0
STOP_FRACTION = 0.07
HALT_DRAWDOWN = 0.12
ALLOWED = {'BTC/EUR', 'ETH/EUR', 'SOL/EUR', 'NEAR/EUR'}


def fresh_account() -> dict:
    return {'version': '1.1', 'currency': 'EUR', 'initial_eur': START_EUR,
            'cash_eur': START_EUR, 'positions': {}, 'trades': [],
            'last_processed_day': None, 'highest_equity_eur': START_EUR,
            'last_equity_eur': START_EUR, 'halt_new_buys': False,
            'equity_history': [], 'decisions': [], 'quote_snapshot': {}}


def validate_state(s: dict) -> None:
    if s.get('version') != '1.1' or s.get('currency') != 'EUR':
        raise ValueError('Unbekanntes Kontodatenformat: niemals automatisch zurücksetzen')
    cash = s.get('cash_eur')
    if not isinstance(cash, (int, float)) or not isfinite(cash) or cash < -1e-6:
        raise ValueError('Ungültiges Kontoguthaben')
    if not isinstance(s.get('trades'), list) or not isinstance(s.get('positions'), dict):
        raise ValueError('Beschädigtes Demokonto')
    for symbol, p in s['positions'].items():
        if symbol not in ALLOWED or any(not isfinite(float(p[k])) or float(p[k]) <= 0
                                     for k in ('qty', 'entry_price_eur', 'cost_basis_eur')):
            raise ValueError('Ungültiger Coin-Bestand')


def equity(s: dict, quotes: dict[str, Quote]) -> float:
    return float(s['cash_eur']) + sum(float(p['qty']) * quotes[sym].mid
                                    for sym, p in s['positions'].items())


def trade(s: dict, symbol: str, side: str, quote: Quote, amount_eur: float,
          day: str, reason: str):
    if side == 'BUY':
        # amount_eur is inclusive of fee; cash never goes negative.
        notional = amount_eur / (1 + FEE_RATE)
        fee = notional * FEE_RATE
        fill = quote.ask * (1 + SLIPPAGE_RATE)
        qty = notional / fill
        s['cash_eur'] -= amount_eur
        s['positions'][symbol] = {'qty': qty, 'entry_price_eur': fill,
                                  'cost_basis_eur': amount_eur, 'entry_day': day}
        gross = notional
        slippage = qty * (fill - quote.ask)
        realized = None
    else:
        p = s['positions'].pop(symbol)
        qty = float(p['qty'])
        fill = quote.bid * (1 - SLIPPAGE_RATE)
        gross = qty * fill
        fee = gross * FEE_RATE
        received = gross - fee
        realized = received - float(p['cost_basis_eur'])
        slippage = qty * (quote.bid - fill)
        s['cash_eur'] += received
    s['trades'].append({'day': day, 'timestamp_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                        'symbol': symbol, 'side': side, 'qty': round(qty, 10),
                        'fill_price_eur': round(fill, 9), 'gross_eur': round(gross, 6),
                        'fee_eur': round(fee, 6), 'slippage_eur': round(slippage, 6),
                        'realized_pnl_eur': round(realized, 6) if realized is not None else None,
                        'reason': reason, 'type': 'SIMULATION_ONLY'})


def run_paper(state: dict, report: dict, quotes: dict[str, Quote]) -> tuple[dict, bool]:
    """Returns (new state, changed). All-or-none, no real broker access.

    Signals are generated from completed UTC daily candles. Paper fills use a
    subsequent PUBLIC order-book snapshot; fills are approximations.
    """
    validate_state(state)
    assets = report['assets']
    symbols = [a['symbol'] for a in assets]
    if set(symbols) != ALLOWED or len(symbols) != len(ALLOWED):
        raise ValueError('Unvollständiger oder unerwarteter Analyse-Satz')
    dates = {a.get('date') for a in assets}
    if len(dates) != 1 or None in dates:
        raise ValueError('Nicht synchronisierte Tagesdaten – keine Ausführungen')
    day = dates.pop()
    # Dates are ISO days, so lexical ordering is correct.
    prior = state.get('last_processed_day')
    if prior and day <= prior:
        return deepcopy(state), False
    if any(a['action'] == 'DATENSPERRE' or a['agents'].get('daten', {}).get('signal') != 'OK' for a in assets):
        raise ValueError('Datenqualitäts-Sperre – nichts ausführen')
    if set(quotes) != ALLOWED:
        raise ValueError('Fehlende öffentliche Orderbücher – kompletter Lauf gesperrt')
    for sym, q in quotes.items():
        if q.symbol != sym:
            raise ValueError('Quote-Symbol stimmt nicht überein')
        q.validate()
    s = deepcopy(state)
    portfolio_before = equity(s, quotes)
    if not isfinite(portfolio_before) or portfolio_before <= 0:
        raise ValueError('Ungültiger Portfoliowert')
    s['highest_equity_eur'] = max(float(s['highest_equity_eur']), portfolio_before)
    drawdown = 1 - portfolio_before / s['highest_equity_eur']
    if drawdown >= HALT_DRAWDOWN:
        s['halt_new_buys'] = True  # sticky until manual human review
    decisions = []
    # Sells first, so existing downside protection is not blocked by buy halt.
    for a in sorted(assets, key=lambda a: a['symbol']):
        sym = a['symbol']
        p = s['positions'].get(sym)
        if not p:
            continue
        last_close = float(a['agents']['setup']['facts']['indikative_einstiegsbasis'])
        if not isfinite(last_close) or last_close <= 0:
            raise ValueError('Invalid last close for stop assessment')
        stop = last_close <= float(p['entry_price_eur']) * (1 - STOP_FRACTION)
        reverse = a['action'] == 'SCHWACHER MARKT'
        if stop or reverse:
            reason = '7%-Tagesschluss-Stopp (keine garantierte Ausführung)' if stop else 'Master: schwacher Markt'
            trade(s, sym, 'SELL', quotes[sym], 0, day, reason)
            decisions.append({'symbol':sym, 'decision':'SELL', 'reason':reason})
        else:
            decisions.append({'symbol':sym, 'decision':'HOLD', 'reason':'Bestehende Position halten'})
    for a in sorted(assets, key=lambda a: a['symbol']):
        sym = a['symbol']
        if sym in s['positions'] or any(d['symbol']==sym for d in decisions):
            continue  # no re-entry on same daily candle after a sell
        if a['action'] != 'BEOBACHTEN: KAUFKANDIDAT':
            decisions.append({'symbol':sym, 'decision':'HOLD', 'reason':a['action']})
            continue
        if a['agents'].get('risiko',{}).get('signal') != 'OK':
            decisions.append({'symbol':sym, 'decision':'BLOCK', 'reason':'Risiko-Bot hat Veto'})
            continue
        if s['halt_new_buys']:
            decisions.append({'symbol':sym, 'decision':'BLOCK', 'reason':'Drawdown-Sperre'})
            continue
        current = equity(s, quotes)
        invested = current - s['cash_eur']
        deployed_cost = sum(float(p['cost_basis_eur']) for p in s['positions'].values())
        budget = min(current * MAX_COIN_WEIGHT,
                     current * MAX_EXPOSURE - invested,
                     float(s['initial_eur']) * MAX_EXPOSURE - deployed_cost,
                     s['cash_eur'] - CASH_RESERVE_EUR)
        if budget < MIN_ORDER_EUR:
            decisions.append({'symbol':sym, 'decision':'HOLD', 'reason':'Zu wenig freies Risikobudget'})
            continue
        trade(s, sym, 'BUY', quotes[sym], budget, day, 'Master-Kaufkandidat + Risiko-Freigabe')
        decisions.append({'symbol':sym, 'decision':'BUY', 'reason':f'Virtueller Einsatz {budget:.2f} EUR'})
    now_equity = equity(s, quotes)
    s['highest_equity_eur'] = max(float(s['highest_equity_eur']), now_equity)
    s['halt_new_buys'] = bool(s['halt_new_buys']) or (1 - now_equity / s['highest_equity_eur'] >= HALT_DRAWDOWN)
    s['last_equity_eur'] = now_equity
    s['last_processed_day'] = day
    s['decisions'] = decisions
    s['quote_snapshot'] = {sym: {'bid':q.bid, 'ask':q.ask, 'observed_utc':q.observed_utc}
                           for sym,q in quotes.items()}
    s['equity_history'].append({'day': day, 'equity_eur': round(now_equity, 6),
                                'cash_eur': round(s['cash_eur'], 6)})
    validate_state(s)
    return s, True
