"""Master integrates analysis in transparent, non-ML, fail-closed conditions.

The master emits research watchlist decisions only and NEVER places orders.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json

from net_core import Finding
import net_data_bot, net_trend_bot, net_structure_bot, net_momentum_bot
import net_volume_bot, net_volatility_bot, net_levels_bot, net_relative_bot
import net_liquidity_bot, net_risk_bot, net_regime_bot, net_setup_bot


SPECIALISTS = ('daten', 'trend', 'struktur', 'momentum', 'volumen',
               'volatilitaet', 'marktphase', 'niveaus', 'setup', 'relativ', 'liquiditaet', 'risiko')


def review(symbol, df, data, ex=None, orderbook=False, reference_day=None):
    facts = {'daten': net_data_bot.analyze(symbol, df, reference_day=reference_day)}
    if facts['daten'].signal != 'OK':
        return {'symbol':symbol, 'action':'DATENSPERRE', 'reasons':facts['daten'].reasons,
                'date': df.index[-1].date().isoformat() if len(df) else None,
                'agents': {k:v.to_dict() for k,v in facts.items()}, 'scores':{}}
    facts.update({
        'trend': net_trend_bot.analyze(symbol, df),
        'struktur': net_structure_bot.analyze(symbol, df),
        'momentum': net_momentum_bot.analyze(symbol, df),
        'volumen': net_volume_bot.analyze(symbol, df),
        'volatilitaet': net_volatility_bot.analyze(symbol, df),
        'marktphase': net_regime_bot.analyze(symbol, df),
        'niveaus': net_levels_bot.analyze(symbol, df),
        'setup': net_setup_bot.analyze(symbol, df),
        'relativ': net_relative_bot.analyze(symbol, df, data),
        'liquiditaet': net_liquidity_bot.analyze(symbol, ex=ex, enabled=orderbook),
    })
    facts['risiko'] = net_risk_bot.analyze(symbol, facts)
    reasons = []
    trend, momentum, structure, volume = (facts[x].score for x in ('trend','momentum','struktur','volumen'))
    risk_clear = facts['risiko'].signal == 'OK'
    near_resistance = facts['niveaus'].facts['nahe_widerstand']
    # Confluence: 4 different technical evidence types; correlations exist!
    # Informational classification, NOT an executable trade recommendation.
    vol_confirmed = (volume >= 0 and facts['volumen'].facts['volumen_faktor_20'] >= 0.8
                     and facts['volumen'].facts['obv_10_tage_steigend'])
    setup = facts['setup'].facts
    # Invalid setup geometry can block a watchlist candidate, except explicit breakouts.
    setup_ok = setup['bewertung'] in ('THEORETISCH_GUENSTIG','THEORETISCH_AKZEPTABEL',
                                     'AUSBRUCH/KEIN_ZIEL_AUS_HISTORISCHEM_WIDERSTAND')
    confluence = (trend >= 1 and momentum >= 1 and structure >= 0 and vol_confirmed
                  and setup_ok and not near_resistance)
    if not risk_clear:
        action = 'RISIKOSPERRE'
        reasons += facts['risiko'].reasons
    elif confluence:
        action = 'BEOBACHTEN: KAUFKANDIDAT'
        reasons += ['Trend/Momentum positiv, Preisstruktur nicht negativ, Volumen/Setup bestehen Mindestprüfung',
                    'Keine Order; Einstieg, Liquidität und Positionsrisiko separat prüfen']
    elif trend <= -1 and momentum <= -1:
        action = 'SCHWACHER MARKT'
        reasons += ['Trend und Momentum negativ; keine Kaufsuche']
    else:
        action = 'ABWARTEN'
        reasons += ['Nicht alle technischen Kriterien für einen Kaufkandidaten erfüllt']
    if facts['liquiditaet'].signal == 'NICHT_GEMESSEN':
        reasons += ['Orderbuch/Spread nicht geprüft (historische Tagesanalyse)']
    if trend > 0 and momentum < 0:
        reasons += ['Widerspruch: Trend positiv, Momentum negativ']
    if trend < 0 and momentum > 0:
        reasons += ['Widerspruch: Trend negativ, Momentum positiv']
    return {'symbol': symbol, 'action':action, 'reasons':reasons,
            'date':df.index[-1].date().isoformat(),
            'agents':{k:v.to_dict() for k,v in facts.items()},
            'scores':{x:facts[x].score for x in ('trend','struktur','momentum','volumen','niveaus','relativ')}}


def run_all(data, ex=None, orderbook=False, reference_day=None):
    from market import aligned, SYMBOLS
    data = aligned(data)
    reports = [review(sym, data[sym], data, ex=ex,
                      orderbook=orderbook, reference_day=reference_day)
               for sym in SYMBOLS]
    return {'network_version':'1.0', 'created_utc':datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'basis':'Nur abgeschlossene Kraken-Tageskerzen (optional separater Live-Orderbuch-Snapshot)',
            'mode':'RESEARCH_ONLY_NO_TRADES', 'assets':reports}


def german(x):
    return f'{x:.2f}'.replace('.', ',') if x is not None else 'n.v.'


def generate_markdown(report:dict):
    lines = [
        '# Krypto Master Network – Zentrale Profi-Analyse', '',
        '**Dieser Bericht enthält nur Analysen. Virtuelle Master-Orders stehen separat in `TRADING_STATUS.md`. Echtgeldhandel ist gesperrt.**', '',
        f'Erstellt (UTC): {report["created_utc"]}  ',
        f'Datenquelle: {report["basis"]}  ',
        'Die Master-Einstufungen sind heuristische Beobachtungssignale, keine statistischen Wahrscheinlichkeiten.', '',
        '## Master-Übersicht', '',
        '| Coin | Trend | Struktur | Momentum | Volumen | ATR | Master |',
        '|:--|:--|:--|:--|:--|--:|:--|'
    ]
    for asset in report['assets']:
        a = asset['agents']
        if asset['action']=='DATENSPERRE':
            lines.append(f'| {asset["symbol"]} | — | — | — | — | — | DATENSPERRE |')
            continue
        def letter(k):
            c=a[k]
            return f'{c["signal"]} ({c["score"]:+d})'
        atr=a['volatilitaet']['facts']['atr14_prozent']
        lines.append(f'| {asset["symbol"]} | {letter("trend")} | {letter("struktur")} | '
                     f'{letter("momentum")} | {letter("volumen")} | {german(atr)} % | {asset["action"]} |')
    lines.extend(['', '## Einzelberichte der Spezialisten', ''])
    for asset in report['assets']:
        lines += [f'### {asset["symbol"]} · {asset["action"]}', '',
                  f'**Letzter Kurstag:** {asset["date"]}', '']
        lines += ['**Master-Begründung:** ' + '; '.join(asset['reasons']), '']
        lines += ['| Spezialist | Signal | Fakten |', '|:--|:--|:--|']
        for key in SPECIALISTS:
            if key not in asset['agents']:
                continue
            v=asset['agents'][key]
            # Limit the summary to key, bounded evidence; all metrics remain in JSON.
            metrics=list(v['facts'].items())[:4]
            info=', '.join(f'{k}: {german(q) if isinstance(q,(int,float)) and not isinstance(q,bool) else q}' for k,q in metrics)
            lines.append(f'| {v["agent"]} | {v["signal"]} | {info or "—"} |')
        lines += ['', '**Einordnung:**']
        for k in ('trend','struktur','momentum','volumen','volatilitaet','marktphase','niveaus','setup','relativ','liquiditaet','risiko'):
            v=asset['agents'].get(k)
            if v:
                lines.append(f'- **{v["agent"]}:** '+ '; '.join(v['reasons']))
        lines.append('')
    lines += ['## Regeln und Grenzen', '',
              '- Analyse-Bots sind unabhängige Module, aber ihre Kursdaten und Indikatoren sind statistisch abhängig.',
              '- Der Master nutzt feste Bestätigungsbedingungen, keine beliebige Stimmenmehrheit.',
              '- ATR = Schwankungsmaß, RSI/MACD = Momentum, EMA/SMA = Trend; keine Garantie für Gewinne.',
              '- Ein einmaliger Orderbuch-Snapshot sagt nichts über langfristigen Orderfluss oder Spoofing aus.',
              '- Die Master-Analyse führt selbst keine Orders aus; die separate Trading-Engine verwaltet ein neues, unabhängiges Demokonto. Bestehende KI-/Trend-/Opt-Trend-Depots bleiben unverändert.',
              '- Für echten Handel fehlen u.a. Ausführungsmodell, robuste OOS-Tests und individuelles Risikobudget.', '',
              'Maschinenlesbare Einzelwerte: `daten/netzwerk_analysen.json`.', '']
    return '\n'.join(lines)


def save_report(report, output_root: Path):
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root/'daten').mkdir(exist_ok=True)
    (output_root/'NETZWERK.md').write_text(generate_markdown(report), encoding='utf-8')
    (output_root/'daten'/'netzwerk_analysen.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False),encoding='utf-8')
