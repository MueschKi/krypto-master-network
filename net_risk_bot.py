"""Hard veto for stale data, anomalous risk, unreliable volume, wide order book."""
from net_core import Finding


def analyze(symbol, findings):
    data = findings['daten']
    vol = findings.get('volatilitaet')
    liq = findings.get('liquiditaet')
    blocks = []
    alerts = []
    if data.signal != 'OK':
        blocks += data.reasons
    atr = vol.facts.get('atr14_prozent') if vol else None
    if atr is None or atr >= 12:
        blocks.append('ATR zu hoch oder unbekannt (>=12 %): kein Kaufkandidat')
    elif atr >= 8:
        alerts.append('Hohe Volatilität: im Paper Trading besonders vorsichtig')
    if liq and liq.facts.get('spread_prozent') is not None and liq.facts['spread_prozent'] > 0.5:
        blocks.append('Spread >0,5 % im Zeitpunkt-Snapshot')
    if liq is None or liq.signal == 'NICHT_GEMESSEN':
        alerts.append('Kein aktuelles Orderbuch: tatsächliche Ausführbarkeit nicht geprüft')
    return Finding('Risikokontrolle', 'BLOCKIERT' if blocks else 'OK',
                   -2 if blocks else 0, {'kaufkandidat_erlaubt':not bool(blocks), 'atr_prozent':atr},
                   blocks or (alerts or ['Keine harten Analysetore verletzt']))
