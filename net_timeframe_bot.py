"""Independent observation agent; no connection to either paper engine."""
from mtf_data import quality, TIMEFRAMES
import mtf_trend
import mtf_momentum
import mtf_volatility


def analyse(raw, timeframe, now_ms):
    if isinstance(raw, dict) and 'error' in raw:
        raw_error = raw['error']
        data, dq = quality(None, timeframe, now_ms)
        dq['reason'] = raw_error
    else:
        data, dq = quality(raw, timeframe, now_ms)
    result = {'classification': 'BLOCKIERT', 'quality': dq, 'agents': {},
              'reasons': [dq['reason']]}
    if data is None:
        return result
    agents = {name: module.analyse(data) for name, module in
              [('trend', mtf_trend), ('momentum', mtf_momentum), ('volatility', mtf_volatility)]}
    t, m, v = (agents[n]['signal'] for n in ('trend', 'momentum', 'volatility'))
    result['classification'] = ('BLOCKIERT' if v == 'BLOCKIERT' else
                                t if t == m else 'NEUTRAL')
    result['agents'] = agents
    result['reasons'] += [f'Trend={t}, Momentum={m}, Volatilität={v}. '
                          'Trend und Momentum müssen übereinstimmen; Volatilitätsveto hat Vorrang.']
    result['internal_conflict'] = {t, m} == {'POSITIV', 'NEGATIV'}
    return result


def summarize(frames):
    signals = {tf: frames[tf]['classification'] for tf in TIMEFRAMES}
    blocked = [tf for tf, s in signals.items() if s == 'BLOCKIERT']
    positive = [tf for tf, s in signals.items() if s == 'POSITIV']
    negative = [tf for tf, s in signals.items() if s == 'NEGATIV']
    conflict = bool(positive and negative)
    classification = ('BLOCKIERT' if blocked else 'POSITIV' if len(positive) == 4
                      else 'NEGATIV' if len(negative) == 4 else 'NEUTRAL')
    return {'classification': classification, 'signals': signals, 'conflict': conflict,
            'reasons': [f'Positive Zeitfenster: {positive}; negative: {negative}; blockiert: {blocked}.',
                        'Widerspruch zwischen Zeitfenstern.' if conflict else 'Kein positiver/negativer Kreuzwiderspruch.',
                        'Gleichgewichtete Einstimmigkeit aller vier Fenster für POSITIV/NEGATIV; '
                        'sonst NEUTRAL. Jede Sperre blockiert die Gesamtauswertung. Keine Wahrscheinlichkeit.']}
