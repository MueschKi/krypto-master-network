"""Exchange boundary. Public order book only. No credential or private endpoint access.

Live trading is intentionally NOT implemented. There is no flag to activate it.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite


@dataclass(frozen=True)
class Quote:
    symbol: str
    bid: float
    ask: float
    observed_utc: str

    def validate(self, max_spread_pct: float = 0.50) -> None:
        if (not isfinite(self.bid) or not isfinite(self.ask) or self.bid <= 0
                or self.ask <= 0 or self.bid >= self.ask):
            raise ValueError(f'Ungültige öffentliche Geld-/Briefkurse: {self.symbol}')
        if (self.ask - self.bid) / ((self.ask + self.bid) / 2) * 100 > max_spread_pct:
            raise ValueError(f'Spread über {max_spread_pct:.2f}%: {self.symbol}')

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2


class PublicKrakenQuotes:
    """Uses only public spot order-book reads; never places orders."""
    def __init__(self, exchange):
        self.exchange = exchange

    def fetch(self, symbols: list[str]) -> dict[str, Quote]:
        result = {}
        for symbol in symbols:
            book = self.exchange.fetch_order_book(symbol, limit=5)
            bids, asks = book.get('bids') or [], book.get('asks') or []
            if not bids or not asks:
                raise RuntimeError(f'Kein vollständiges Orderbuch: {symbol}')
            stamp = book.get('timestamp')
            if stamp is not None:
                age_ms = int(datetime.now(timezone.utc).timestamp() * 1000) - int(stamp)
                if age_ms > 5 * 60 * 1000 or age_ms < -60_000:
                    raise RuntimeError(f'Orderbuch mit veraltetem oder zukünftigem Zeitstempel: {symbol}')
            if float(bids[0][1]) <= 0 or float(asks[0][1]) <= 0:
                raise ValueError(f'Leeres bestes Angebot: {symbol}')
            bid, ask = float(bids[0][0]), float(asks[0][0])
            quote = Quote(symbol, bid, ask, datetime.now(timezone.utc).isoformat(timespec='seconds'))
            quote.validate()
            result[symbol] = quote
        return result


class LiveExchangeAdapter:
    """Reserved interface. No code path can unlock real orders in this package."""
    def __init__(self, *args, **kwargs):
        raise PermissionError('ECHTGELD-GESPERRT: Kein Live-Adapter installiert.')

    def place_order(self, *args, **kwargs):
        raise PermissionError('ECHTGELD-GESPERRT: Es werden niemals reale Orders versendet.')
