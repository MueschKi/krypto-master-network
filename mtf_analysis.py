"""Read-only Multi-Timeframe CLI. Demo has no network and writes only demo artifacts."""
import argparse
import json
from pathlib import Path
from mtf_data import SYMBOLS, TIMEFRAMES, fetch_all, synthetic, utc_now_ms, iso
from net_timeframe_bot import analyse, summarize

DEMO_NOW_MS = 1793232000000  # 2026-10-29 00:00:00 UTC
LIMITS = ('Reine Beobachtung, keine Orders und keine Übergabe an Paper-Engines. '
          'Keine Prognosewahrscheinlichkeiten. Kraken liefert maximal ca. 720 Kerzen: '
          '15m ca. 7,5 Tage, 1h ca. 30 Tage, 4h ca. 120 Tage, 1d ca. 720 Tage; '
          'die laufende Kerze wird entfernt. EMA startet am ersten vorhandenen Schlusskurs; '
          'RSI/ATR verwenden rekursive Wilder-Glättung ab erstem Wert. Mindestens 250 '
          'abgeschlossene Kerzen, begrenzter Warm-up besonders für EMA200. '
          'Alle Zeiten UTC; Fenster enden unterschiedlich. Kein Resampling oder Auffüllen. '
          'Fehlende zuletzt erwartete Kerzen blockieren auch bei Börsenverzögerungen. '
          'Überlappende Zeitfenster sind keine unabhängigen Beweise. '
          'Keine historischen Intraday-Daten außerhalb des Kraken-Limits und kein Backtest.')


def build_report(raw, now_ms, mode):
    assets = []
    for symbol in SYMBOLS:
        frames = {tf: analyse(raw.get((symbol, tf)), tf, now_ms) for tf in TIMEFRAMES}
        assets.append({'symbol': symbol, 'timeframes': frames, 'summary': summarize(frames)})
    return {'schema_version': '1.5', 'mode': mode, 'snapshot_utc': iso(now_ms),
            'source': 'synthetisch (keine Marktdaten)' if mode == 'demo' else 'Kraken public spot EUR',
            'classification': 'BLOCKIERT' if any(a['summary']['classification'] == 'BLOCKIERT'
                                                for a in assets) else 'OK',
            'methodological_limits': LIMITS, 'assets': assets}


def render(report):
    lines = ['# Krypto Master Network v1.5 – Zeitfenster', '',
             f"Modus: **{report['mode']}** · Quelle: {report['source']}",
             f"Snapshot: {report['snapshot_utc']} · Datenfreigabe: **{report['classification']}**", '',
             'Nur Beobachtung. Keine Handelssignale für die bestehenden Konten.', '']
    for asset in report['assets']:
        summary = asset['summary']
        lines += [f"## {asset['symbol']} – {summary['classification']}", '', *summary['reasons'], '',
                  '| Fenster | Einstufung | Datenqualität | Letzter Kerzenschluss UTC |',
                  '|---|---|---|---|']
        for tf, frame in asset['timeframes'].items():
            dq = frame['quality']
            lines.append(f"| {tf} | {frame['classification']} | {dq['status']} | {dq['latest_close_utc'] or '—'} |")
        for tf, frame in asset['timeframes'].items():
            dq = frame['quality']
            lines += ['', f'### {tf}', '',
                      f"Kerzenstart: {dq['latest_open_utc'] or '—'}; Schluss: {dq['latest_close_utc'] or '—'}.",
                      f"Datenqualität: {dq['reason']}; {dq['closed_count']} abgeschlossene, "
                      f"{dq['excluded_unclosed']} nicht abgeschlossene ausgeschlossen.", *frame['reasons'][1:]]
            for name, agent in frame['agents'].items():
                values = ', '.join(f'{k}={v:.6g}' for k, v in agent['indicators'].items())
                lines += [f"- {name}: **{agent['signal']}** – {values}. {agent['reason']}"]
    return '\n'.join(lines + ['', '## Methodische Grenzen', '', report['methodological_limits'], ''])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('demo', 'analyse'))
    args = parser.parse_args(argv)
    # Freeze before retrieval: later responses may never move the analysis cutoff.
    now_ms = DEMO_NOW_MS if args.mode == 'demo' else utc_now_ms()
    raw = synthetic(now_ms) if args.mode == 'demo' else fetch_all()
    report = build_report(raw, now_ms, args.mode)
    md = Path('DEMO_ZEITFENSTER.md' if args.mode == 'demo' else 'ZEITFENSTER.md')
    js = Path('DEMO_ZEITFENSTER.json' if args.mode == 'demo' else 'daten/zeitfenster_analysen.json')
    encoded = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    js.parent.mkdir(parents=True, exist_ok=True)
    js.write_text(encoded, encoding='utf-8')
    md.write_text(render(report), encoding='utf-8')
    print(f"MTF {args.mode}: {report['classification']}; {md}, {js}. Nur Beobachtung.")
    # A blocked report is an explicit result, persisted by Actions for inspection.
    return report


if __name__ == '__main__':
    main()
