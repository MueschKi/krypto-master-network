"""Historical *diagnostic* replay of the unchanged master and the paper engine.

NOT live trading, not an optimized strategy, and not an untouched out-of-sample
experiment. Each day's signal only sees candles up to that day's CLOSE. The
simulated execution uses the NEXT day's OPEN with a fixed hypothetical spread.
No historical order book is available from the current Kraken OHLC endpoint.
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path

from market import SYMBOLS, aligned, get_daily, synthetic_demo
from net_master import run_all
from trade_broker import Quote
from trade_engine import (
    START_EUR, FEE_RATE, SLIPPAGE_RATE, fresh_account, run_paper,
)

# NOT historical observations: sensitivity assumption at the NEXT open.
ASSUMED_TOTAL_SPREAD = 0.0015  # 0.15%, bid/ask symmetric around next open
WARMUP = 260


def open_quotes(data, next_index: int, spread: float = ASSUMED_TOTAL_SPREAD) -> dict[str, Quote]:
    """Proxy quote using exclusively NEXT bar OPEN. Never next high/low/close."""
    if not isfinite(spread) or not 0 < spread < .005:
        raise ValueError('Unsupported artificial spread (needs <0.5%)')
    result = {}
    for symbol, df in data.items():
        opening = float(df['open'].iloc[next_index])
        if not isfinite(opening) or opening <= 0:
            raise ValueError(f'Invalid historical opening: {symbol}')
        stamp = df.index[next_index].isoformat()
        q = Quote(symbol, opening * (1 - spread/2),
                  opening * (1 + spread/2), stamp)
        q.validate()
        result[symbol] = q
    return result


def drawdown(values):
    peak = START_EUR
    worst = 0.0
    for item in values:
        peak = max(peak, float(item))
        worst = max(worst, 1 - float(item)/peak)
    return worst * 100


def _passive_start(quotes):
    # 45% exposure, equal four holdings, leaves 55% EUR; charges entry costs.
    stake = START_EUR * .45 / len(SYMBOLS)
    qty = {s: (stake / (1 + FEE_RATE)) /
               (quotes[s].ask * (1 + SLIPPAGE_RATE)) for s in SYMBOLS}
    return START_EUR - stake * len(SYMBOLS), qty


def replay(data, warmup=WARMUP, max_signals=None, strategy_override=None):
    """Replay with identical paper engine; state not persisted or touched.

    strategy_override exists only for synthetic unit tests; real backtest always
    uses the unmodified net_master rules. No future candles in analysis frames.
    """
    data = aligned(data)
    dates = data[SYMBOLS[0]].index
    if warmup < 260 or len(dates) < warmup + 2:
        raise ValueError('Not enough daily history for an honest replay')
    start = warmup - 1
    if max_signals is not None:
        if max_signals < 1:
            raise ValueError('max_signals must be positive')
        start = max(start, len(dates) - 1 - max_signals)
    state = fresh_account()
    counter = Counter()
    gate_failures = Counter()
    coin_actions = Counter()
    executions = Counter()
    blocked_days = 0
    cash_passive = None
    qty_passive = None
    curve = []
    for i in range(start, len(dates) - 1):
        history = {sym: df.iloc[:i+1] for sym, df in data.items()}
        reports = run_all(history, orderbook=False, reference_day=None)
        if strategy_override:
            reports = strategy_override(reports, i)
        for a in reports['assets']:
            counter[a['action']] += 1
            coin_actions[(a['symbol'], a['action'])] += 1
            gate_failures.update(a.get('failed_gates', []))
        next_quotes = open_quotes(data, i+1)
        if qty_passive is None:
            cash_passive, qty_passive = _passive_start(next_quotes)
        state, changed = run_paper(state, reports, next_quotes)
        if not changed:
            raise AssertionError('Backtest attempted duplicate day')
        executions.update((d['decision'], d['reason']) for d in state['decisions'])
        blocked_days += int(state['halt_new_buys'])
        passive_value = cash_passive + sum(qty_passive[s] * next_quotes[s].mid for s in SYMBOLS)
        curve.append({
            'signal_day_utc': dates[i].date().isoformat(),
            'fill_day_utc': dates[i+1].date().isoformat(),
            'master_eur': round(float(state['last_equity_eur']), 6),
            'passiv_eur': round(float(passive_value), 6),
            'cash_eur': round(float(state['cash_eur']), 6),
            'positions': len(state['positions']),
            'halt_new_buys': bool(state['halt_new_buys']),
        })
    return {'state':state, 'curve':curve, 'counts':counter, 'gates':gate_failures,
            'coin_actions': coin_actions, 'execution_counts': executions,
            'blocked_days':blocked_days, 'source_candles':len(dates),
            'source_start':dates[0].date().isoformat(),
            'source_end':dates[-1].date().isoformat(),
            'warmup':warmup, 'spread_rate':ASSUMED_TOTAL_SPREAD}


def _periods(rows, chunks=3):
    out = []
    n = len(rows)
    for k in range(chunks):
        part = rows[(n*k)//chunks:(n*(k+1))//chunks]
        if not part:
            continue
        prev = START_EUR if k == 0 else rows[(n*k)//chunks - 1]['master_eur']
        prev_passive = START_EUR if k == 0 else rows[(n*k)//chunks - 1]['passiv_eur']
        end = part[-1]
        out.append((part[0]['signal_day_utc'], end['fill_day_utc'],
                    (end['master_eur']/prev-1)*100,
                    (end['passiv_eur']/prev_passive-1)*100,
                    max(0.0, drawdown([prev] + [r['master_eur'] for r in part]))))
    return out


def euros(value):
    return f'{value:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.') + ' €'


def render(result, source='ECHTE KRAKEN-TAGESKURSE'):
    state, curve = result['state'], result['curve']
    trades = state['trades']
    closed = [t for t in trades if t['side'] == 'SELL']
    winning = sum(t['realized_pnl_eur'] > 0 for t in closed)
    initial = START_EUR
    last = curve[-1]
    master = last['master_eur']; passive = last['passiv_eur']
    fee = sum(float(t['fee_eur']) for t in trades)
    slip = sum(float(t['slippage_eur']) for t in trades)
    buys = sum(t['side']=='BUY' for t in trades)
    sells = len(closed)
    now = datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M UTC')
    lines = [
        '# Krypto Master Network – Historischer Master-Backtest v1.2', '',
        '**NUR HISTORISCHE SIMULATION. KEINE ECHTGELD-ORDERS. KEINE GEWINNPROGNOSE.**', '',
        f'Erstellt: {now}  ',
        f'Datenquelle: **{source}**  ',
        f'Kursdaten: {result["source_start"]} bis {result["source_end"]} ({result["source_candles"]} Tageskerzen je Coin)  ',
        f'Signalzeitraum: **{curve[0]["signal_day_utc"]} bis {curve[-1]["signal_day_utc"]}**  ',
        f'Ausführungszeitraum: **{curve[0]["fill_day_utc"]} bis {curve[-1]["fill_day_utc"]}**  ',
        f'Handelstage im historischen Replay: **{len(curve)}**; zuvor mindestens {result["warmup"]} Kerzen für Indikatoren.', '',
        '## Kontovergleich', '',
        '| Strategie | Endwert | Nettorendite | Max. Drawdown | Ausführungen |',
        '|:--|--:|--:|--:|--:|',
        f'| **Master v1.1 – unveränderte Kaufregeln** | {euros(master)} | {(master/initial-1)*100:+.2f} % | '
        f'{drawdown([r["master_eur"] for r in curve]):.2f} % | {len(trades)} |',
        f'| Passiv 11,25 % je Coin, 55 % EUR | {euros(passive)} | {(passive/initial-1)*100:+.2f} % | '
        f'{drawdown([r["passiv_eur"] for r in curve]):.2f} % | 4 Käufe |',
        f'| EUR-Bargeld ohne Zinsen | {euros(initial)} | +0,00 % | 0,00 % | 0 |', '',
        '## Handelsstatistik', '',
        f'- **Virtuelle Ausführungen:** {len(trades)} ({buys} Käufe / {sells} Verkäufe).',
        f'- **Geschlossene Trades:** {sells}; davon profitabel: {winning}'
        + (f' ({100*winning/sells:.1f} %)' if sells else ' (Trefferquote nicht bestimmbar)'),
        f'- **Realisierte Gewinne/Verluste:** {euros(sum(t["realized_pnl_eur"] for t in closed))}',
        f'- **Gebühren aller Master-Ausführungen:** {euros(fee)}; **modellierte Slippage:** {euros(slip)} (bereits in Kontowerten enthalten).',
        f'- **Positionen am Testende:** {len(state["positions"])}; EUR-Rest: {euros(state["cash_eur"])}.',
        f'- **Neue Käufe am Ende gesperrt:** {"JA" if state["halt_new_buys"] else "NEIN"}.', '',
        '## Warum hat der Master nicht gekauft?', '',
        'Hier zählen wir jede einzelne Prüfung pro Coin und Signal-Tag. Die Bedingungen sind **nicht unabhängig**:', '',
        '| Kaufbedingung, die nicht erfüllt wurde | Coin-Tage |', '|:--|--:|',
    ]
    for label, count in result['gates'].most_common():
        lines.append(f'| {label} | {count} |')
    lines += ['', '### Einstufungen des Masters', '',
              '| Entscheidung | Coin-Tage |', '|:--|--:|']
    for action, count in result['counts'].most_common():
        lines.append(f'| {action} | {count} |')
    lines += ['', '### Tatsächliche Paper-Engine-Entscheidungen', '',
              f'- **Tage mit aktiver Kauf-Drawdown-Sperre:** {result["blocked_days"]} von {len(curve)}.',
              '| Ausführungsentscheidung / Grund | Coin-Tage |', '|:--|--:|']
    for (decision, reason), count in result['execution_counts'].most_common():
        lines.append(f'| {decision}: {reason} | {count} |')
    lines += ['', '### Käufe und Verkäufe pro Coin', '',
              '| Coin | Käufe | Verkäufe | Realisiert |', '|:--|--:|--:|--:|']
    for symbol in SYMBOLS:
        ts=[t for t in trades if t['symbol']==symbol]
        lines.append(f'| {symbol} | {sum(t["side"]=="BUY" for t in ts)} | '
                     f'{sum(t["side"]=="SELL" for t in ts)} | '
                     f'{euros(sum(t["realized_pnl_eur"] for t in ts if t["side"]=="SELL"))} |')
    lines += ['', '## Drei zeitlich aufeinanderfolgende Abschnitte', '',
              '**Ein durchgehendes Konto**: Teilrenditen verwenden den Kontowert am Beginn des Abschnitts.', '',
              '| Abschnitt (Signalbeginn bis Ausführung) | Master | Passiv | Max. Teilrückgang Master |',
              '|:--|--:|--:|--:|']
    for b,e,m,p,d in _periods(curve):
        lines.append(f'| {b} – {e} | {m:+.2f} % | {p:+.2f} % | {d:.2f} % |')
    lines += ['', '## Wichtige methodische Grenzen', '',
              '- **Kein echter historischer Spread:** Das Replay setzt einen fiktiven konstanten Bid/Ask-Gesamtspread von '
              f'{result["spread_rate"]*100:.2f} % an (zusätzlich {FEE_RATE*100:.1f} % Gebühr und '
              f'{SLIPPAGE_RATE*100:.1f} % Slippage je Ausführung). Die echten vergangenen Orderbücher fehlen.',
              '- Analysen verwenden nur bis zum jeweiligen Tagesschluss bekannte OHLCV-Daten; '
              'simulierte Ausführungen nutzen frühestens den **Open des Folgetages**.',
              '- Eine Stop-Regel ist **kein echter Stop-Auftrag**. Stop-Signale werden nur täglich geprüft; '
              'Sprünge, Gaps, Spreads, Verzögerungen und Teilfüllungen sind nicht realistisch rekonstruiert.',
              '- Der Drawdown wird aus den Modellwerten an den simulierten Ausführungszeitpunkten berechnet; '
              'intraday auftretende Verluste können höher gewesen sein.',
              '- Das Master-Regelwerk war bereits auf Grundlage früherer Backtests entwickelt worden. '
              '**Diese Historie ist kein unabhängiger Out-of-Sample-Nachweis.** Keine automatische Optimierung in diesem Modul.',
              '- Die Kraken-OHLC-Historie ist begrenzt. Weitere Marktphasen und echte neue Paper-Trades '
              'sind notwendig, bevor man von einem belastbaren Handelsvorteil sprechen kann.',
              '- Die historische Simulation nutzt nicht das echte Orderbuch und misst keine Live-Latenz oder Börsenrestriktionen.',
              '- **Der Backtest verändert `daten/master_paper_state.json` und das reale Paper-Demokonto NICHT.**', '',
              'Maschinenlesbar: `daten/master_backtest_kurve.csv` und `daten/master_backtest_trades.csv`.', '']
    return '\n'.join(lines)


def write_csv(path: Path, rows: list, fieldnames: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as fh:
        writer=csv.DictWriter(fh, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def save(result, root=Path('.'), source='ECHTE KRAKEN-TAGESKURSE'):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    (root/'BACKTEST_MASTER.md').write_text(render(result, source), encoding='utf-8')
    write_csv(root/'daten/master_backtest_kurve.csv', result['curve'],
              ['signal_day_utc','fill_day_utc','master_eur','passiv_eur','cash_eur',
               'positions','halt_new_buys'])
    write_csv(root/'daten/master_backtest_trades.csv', result['state']['trades'],
              ['day','symbol','side','qty','fill_price_eur','gross_eur',
               'fee_eur','slippage_eur','realized_pnl_eur','reason','type'])


def main():
    ap=argparse.ArgumentParser(description='Rein historischer Master-Netzwerk-Test; keine echten Trades')
    ap.add_argument('modus',choices=['historisch','demo'])
    args=ap.parse_args()
    if args.modus=='demo':
        # Short and deterministic, avoids real network; no paper-account writes.
        data=aligned(synthetic_demo())
        outcome=replay(data,max_signals=8)
        text=render(outcome,'KÜNSTLICHE KURSE – NUR SOFTWARETEST')
        Path('DEMO_MASTER_BACKTEST.md').write_text(text, encoding='utf-8')
        print('DEMO: 8 synthetische Tage getestet, kein Zugriff auf laufendes Demokonto.')
        return
    data,_ = get_daily()
    result=replay(data)
    save(result)
    ending=result['state']['last_equity_eur']
    print(f'MASTER-BACKTEST: {len(result["curve"])} Signal-Tage, '
          f'{len(result["state"]["trades"])} virtuelle Ausführungen, '
          f'Endwert {ending:.2f} EUR; Bericht BACKTEST_MASTER.md')
    print('Paper-Konto wurde nicht verändert. Kein Echtgeldhandel möglich.')


if __name__=='__main__':
    main()
