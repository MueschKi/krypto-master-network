"""BTC market comparison / correlation; descriptive cross-asset risk context."""
from net_core import assessment


def analyze(symbol, df, context):
    btc = context.get('BTC/EUR')
    if btc is None:
        return assessment('Relative Stärke/BTC', 0, {}, ['BTC-Benchmark fehlt'])
    p = df['close']
    b = btc['close']
    asset_ret = float(p.iloc[-1] / p.iloc[-31] - 1)
    btc_ret = float(b.iloc[-1] / b.iloc[-31] - 1)
    relative = 100 * (asset_ret - btc_ret)
    corr = float(p.pct_change().iloc[-60:].corr(b.pct_change().iloc[-60:]))
    score = 0 if symbol == 'BTC/EUR' else (1 if relative > 3 else -1 if relative < -3 else 0)
    return assessment('Relative Stärke zu BTC', score,
                      {'rendite_30_tage_prozent':100 * asset_ret,
                       'btc_30_tage_prozent':100 * btc_ret,
                       'relative_starke_pp':relative,
                       'korrelation_60_tage':corr},
                      [f'30-Tage-Mehr-/Minderrendite zu BTC: {relative:+.2f} Prozentpunkte',
                       f'60-Tage-Korrelation zu BTC: {corr:.2f}',
                       'BTC ist der Vergleichsmaßstab, kein unabhängiger Kaufsignalgeber'])
