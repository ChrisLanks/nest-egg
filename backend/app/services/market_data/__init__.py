"""
Market data service - Provider-agnostic price data.

Supports multiple providers:
- Yahoo Finance (FREE, default)
- Alpha Vantage (FREE tier: 500 calls/day)
- Finnhub (FREE tier: 60 calls/min)
- More can be added easily!
"""

from .base_provider import (
    MarketDataProvider,
    QuoteData,
    HistoricalPrice,
    SearchResult,
)
from .yahoo_finance_provider import YahooFinanceProvider
from .provider_factory import get_market_data_provider

__all__ = [
    "MarketDataProvider",
    "QuoteData",
    "HistoricalPrice",
    "SearchResult",
    "YahooFinanceProvider",
    "get_market_data_provider",
]
