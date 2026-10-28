"""One concise Markdown mobile dashboard; all values from persisted paper state."""
from __future__ import annotations
from datetime import datetime, timezone
from trade_engine import START_EUR, FEE_RATE, SLIPPAGE_RATE


def money(x):
    return f'{x:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.') + ' €'


def render(state: dict, report: dict | None = None, *, duplicate=False) -> str:
    initial = float(state['initial_eur'])
    equity = float(state['last_equity_eur'])
    pnl = equity - initial
    trades = state['trades']
    positions = state['positions']
    fees = sum(t['fee_eur'] for t in trades)
    slip = sum(t['slippage_eur'] for t in trades)
    now = datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M UTC')
    lines = [
        '# Krypto Master Network – Trading-Dashboard', '',
        '**NUR PAPER TRADING – ECHTGELD TECHNISCH GESPERRT.**', '',
        f'Aktualisierungszeit: {now}  ',
        f'Letzter verarbeiteter Börsentag: **{state["last_processed_day"] or "—"}**  ',
        f'Kontolauf: **{"bereits verarbeitet – keine Doppelbuchung" if duplicate else "reguläre Tagesverarbeitung"}**', '',
        '## Master-Demokonto', '',
        f'- **Depotwert:** {money(equity)}',
        f'- **Gewinn/Verlust seit Beginn:** {money(pnl)} ({100*pnl/initial:+.2f} %)',
        f'- **EUR-Reserve:** {money(state["cash_eur"])}',
        f'- **Wert der Coins:** {money(equity-state["cash_eur"])}',
        f'- **Ausführungen gesamt:** {len(trades)}',
        f'- **Gebühren:** {money(fees)}; **modellierte Zusatz-Slippage:** {money(slip)}',
        f'- **Neue Käufe blockiert (Drawdown):** {"JA" if state["halt_new_buys"] else "NEIN"}', '',
        '## Coin-Bestände', '',
        '| Coin | Menge | Wert nach letzter Quote |', '|:--|--:|--:|'
    ]
    if positions:
        for symbol, p in sorted(positions.items()):
            q = state['quote_snapshot'].get(symbol)
            value = p['qty']*((q['bid']+q['ask'])/2) if q else p['cost_basis_eur']
            lines.append(f'| {symbol} | {p["qty"]:.8f} | {money(value)} |')
    else:
        lines.append('| Keine offenen Positionen | — | — |')
    lines += ['', '## Master-Entscheidungen', '',
              '| Coin | Entscheidung | Begründung |', '|:--|:--|:--|']
    for d in state['decisions']:
        lines.append(f'| {d["symbol"]} | **{d["decision"]}** | {d["reason"]} |')
    if not state['decisions']:
        lines.append('| Noch keine Tagesauswertung | — | — |')
    lines += ['', '## Letzte simulierte Orders', '',
              '| Tag (UTC) | Coin | Aktion | Wert inkl. Kosten / netto | Grund |',
              '|:--|:--|:--|--:|:--|']
    for t in reversed(trades[-12:]):
        amount = t['gross_eur'] + t['fee_eur'] if t['side'] == 'BUY' else t['gross_eur'] - t['fee_eur']
        lines.append(f'| {t["day"]} | {t["symbol"]} | {t["side"]} | {money(amount)} | {t["reason"]} |')
    if not trades:
        lines.append('| Noch keine virtuellen Ausführungen | — | — | — | — |')
    lines += ['', '## Markt-Analysen', '',
              'Die ausführliche Bewertung der Spezial-Bots steht in [`NETZWERK.md`](NETZWERK.md).', '',
              '## Technische Hinweise', '',
              f'- Simulierte Orderfüllung: öffentliches Kraken-Orderbuch (Bid/Ask) + '
              f'{100*SLIPPAGE_RATE:.1f} % Zusatz-Slippage und {100*FEE_RATE:.1f} % Gebühren je Ausführung.',
              '- Kauf-/Stoppregeln verwenden abgeschlossene UTC-Tageskurse; '
              'Ausführung und Bewertung erfolgen zu später abgerufenen Geld-/Briefkursen.',
              '- Keine garantierten Stopps: bei Kurslücken, API-Problemen oder verzögerten GitHub-Läufen '
              'kann ein Stopp erst später geprüft werden.',
              '- Ein virtuelles Limit reduziert Risiken, verhindert aber keine Verluste.',
              '- Das System ist kein Hochfrequenz- oder 24/7-Orderüberwachungsdienst.',
              '- Die Renditeangaben sind nicht steuer- oder börsenspezifisch garantiert.',
              '', 'Transaktionsbuch im Demokontostand `daten/master_paper_state.json`.', '']
    return '\n'.join(lines)
