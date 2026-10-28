"""Optional public L2 order-book SNAPSHOT. Not evidence of lasting order flow."""
from net_core import Finding


def analyze(symbol, ex=None, enabled=False):
    if not enabled:
        return Finding('Orderbuch/Spread', 'NICHT_GEMESSEN', 0, {},
                       ['Kein L2-Snapshot angefordert; keine Liquiditätsaussage möglich'])
    if ex is None:
        return Finding('Orderbuch/Spread', 'NICHT_GEMESSEN', 0, {}, ['Börsenverbindung fehlt'])
    try:
        orderbook = ex.fetch_order_book(symbol, limit=20)
        bids = orderbook.get('bids') or []
        asks = orderbook.get('asks') or []
        if not bids or not asks:
            raise ValueError('Leeres Orderbuch')
        best_bid, best_ask = float(bids[0][0]), float(asks[0][0])
        if not 0 < best_bid < best_ask:
            raise ValueError('Ungültiger Bid/Ask-Snapshot')
        midpoint = (best_bid + best_ask) / 2
        spread = 100 * (best_ask - best_bid) / midpoint
        bid_notional = sum(float(px) * float(qty) for px, qty, *_ in bids[:10])
        ask_notional = sum(float(px) * float(qty) for px, qty, *_ in asks[:10])
        total = bid_notional + ask_notional
        imbalance = (bid_notional - ask_notional) / total if total else 0.0
        risk = spread > 0.5  # only an indicative alert, no exchange/order guarantee
        return Finding('Orderbuch/Spread', 'RISIKO' if risk else 'NEUTRAL', 0,
                       {'bid':best_bid,'ask':best_ask,'spread_prozent':round(spread,4),
                        'top10_imbalance':round(imbalance,3)},
                       [f'Aktueller einmaliger L2-Snapshot: Spread {spread:.3f}%',
                        'Orderbuch kann in Sekunden wechseln; keine Historie/Orderfluss-Analyse'])
    except Exception as exc:
        return Finding('Orderbuch/Spread', 'NICHT_GEMESSEN', 0, {},
                       [f'Snapshot fehlgeschlagen ({type(exc).__name__}); nicht als neutrales Orderbuch interpretieren'])
