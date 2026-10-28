"""Mobile reports for the isolated fixed-stop / trailing-stop paper portfolios."""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
from math import isfinite
from trade_report import render as legacy_render, money


def _closed(state):
    trades=[t for t in state['trades'] if t['side']=='SELL']
    return len(trades), sum(float(t['realized_pnl_eur'])>0 for t in trades), sum(float(t['realized_pnl_eur']) for t in trades)


def _dd(history, initial=1000.0):
    peak=float(initial); maxdd=0.0
    for r in history:
        val=float(r['equity_eur'])
        if not isfinite(val) or val<=0:
            raise ValueError('Ungültiger Portfoliopunkt')
        peak=max(peak,val)
        maxdd=max(maxdd, 100*(1-val/peak))
    return maxdd


def render_trailing(state:dict, report:dict, duplicate=False) -> str:
    text=legacy_render(state,report,duplicate=duplicate)
    text=text.replace('# Krypto Master Network – Trading-Dashboard',
                      '# Krypto Master Network – ATR-Trailing-Demokonto')
    text=text.replace('## Master-Demokonto', '## ATR-Trailing-Demokonto (2,5× ATR14)')
    text=text.replace('Transaktionsbuch im Demokontostand `daten/master_paper_state.json`.',
                      'Transaktionsbuch im separaten `daten/master_trailing_state.json`.')
    lines=['', '## Nachgezogene Stopps', '',
           '| Coin | Höchster gespeicherter Schlusskurs | Aktueller ATR-Stopp |',
           '|:--|--:|--:|']
    if state['positions']:
        for sym,p in sorted(state['positions'].items()):
            lines.append(f'| {sym} | {money(p["trailing_peak_close"])} | {money(p["trailing_stop_eur"])} |')
    else:
        lines.append('| Keine offenen Positionen | — | — |')
    lines += ['', 'Der Stopp wird **erst nach erfolgreicher Tagesverarbeitung** neu berechnet und '
              'ist **kein börsenseitig gesetzter Stop-Auftrag**. Eine Kurslücke kann deutlich '
              'größere Verluste verursachen.', '']
    return text + '\n' + '\n'.join(lines)


def render_comparison(fixed:dict, trailing:dict) -> str:
    now=datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M UTC')
    accs=[('Master 7%-Stopp',fixed),('Master ATR-Trailing 2,5x',trailing)]
    lines=['# Krypto Master Network – Vergleich zweier Paper-Konten','',
           '**KEIN ECHTGELD. Keine Gewinngarantie. Unterschiedliche Konto-Starttermine beachten.**','',
           f'Erstellt: {now}', '',
           '## Aktuelle Depotwerte', '',
           '| Strategie | Börsentag | Depotwert | Seit Konto-Start | Trades | Geschlossene (Gewinner) | Max. beob. Rückgang |',
           '|:--|:--|--:|--:|--:|--:|--:|']
    for label,s in accs:
        initial=float(s['initial_eur'])
        n,w,pnl=_closed(s)
        lines.append(f'| {label} | {s["last_processed_day"] or "—"} | '
                     f'{money(s["last_equity_eur"])} | '
                     f'{100*(s["last_equity_eur"]/initial-1):+.2f} % | '
                     f'{len(s["trades"])} | {n} ({w}) | {_dd(s["equity_history"],initial):.2f} % |')
    lines.extend(['', '## Gemeinsamer Beobachtungszeitraum', ''])
    fixed_hist={x['day']:float(x['equity_eur']) for x in fixed['equity_history']}
    trail_hist={x['day']:float(x['equity_eur']) for x in trailing['equity_history']}
    shared=sorted(set(fixed_hist)&set(trail_hist))
    if len(shared)>=2:
        first,last=shared[0],shared[-1]
        lines.extend([f'Gemeinsame Bewertungstage: **{len(shared)}** ({first} bis {last}).', '',
                      '| Strategie | Veränderung zwischen erster und letzter gemeinsamer Bewertung |',
                      '|:--|--:|',
                      f'| Master 7%-Stopp | {(fixed_hist[last]/fixed_hist[first]-1)*100:+.2f} % |',
                      f'| Master ATR-Trailing | {(trail_hist[last]/trail_hist[first]-1)*100:+.2f} % |',
                      '', 'Die erste gemeinsame Bewertung enthält gegebenenfalls bereits frühere Trades; '
                      'dies ist deshalb **kein kontrolliertes Experiment mit identischem Anfangsportfolio**.'])
    else:
        lines.append('Noch **zu wenige gemeinsame Bewertungstage** für einen Vergleich der Entwicklung. ' 
                     'Beide Konten sammeln unabhängig Daten.')
    lines += ['', '## Überprüfungen', '',
              '- Der ursprüngliche Master und der Trailing-Bot haben **getrennte Kontodateien**.',
              '- Neue Trailing-Stopps werden nur aus abgeschlossenen Tagesdaten nachgezogen; **niemals abgesenkt**.',
              '- Käufe/Verkäufe sind Simulationen mit öffentlichen Kraken-Quoten und angenommenen Kosten.',
              '- Die Ausführung erfolgt nur bei einem erfolgreichen GitHub-Lauf, nicht ständig.',
              '- Frühere historische +8,63 % mit ATR-Trailing wurden auf bereits bekannten Daten ermittelt; '
              '**dieser laufende Vergleich soll neue Daten liefern**.', '',
              'Details: [`TRADING_STATUS.md`](TRADING_STATUS.md) und '
              '[`TRAILING_STATUS.md`](TRAILING_STATUS.md).', '']
    return '\n'.join(lines)
