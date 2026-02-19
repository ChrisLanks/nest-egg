"""
Base provider interface for market data.

This allows swapping between Yahoo Finance, Alpha Vantage, Finnhub, etc.
without changing the application code.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import date
from decimal import Decimal
from pydantic import BaseModel


class QuoteData(BaseModel):
    """Standardized quote data across all providers."""

    symbol: str
    price: Decimal
    name: Optional[str] = None
    currency: str = "USD"
    exchange: Optional[str] = None
    volume: Optional[int] = None
    market_cap: Optional[Decimal] = None
    change: Optional[Decimal] = None  # Price change
    change_percent: Optional[Decimal] = None  # Percentage change
    previous_close: Optional[Decimal] = None
    open: Optional[Decimal] = None
    high: Optional[Decimal] = None
    low: Optional[Decimal] = None
    year_high: Optional[Decimal] = None
    year_low: Optional[Decimal] = None
    dividend_yield: Optional[Decimal] = None
    pe_ratio: Optional[Decimal] = None


class HistoricalPrice(BaseModel):
    """Single historical price point."""

    date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    adjusted_close: Optional[Decimal] = None


class SearchResult(BaseModel):
    """Stock/security search result."""

    symbol: str
    name: str
    type: str  # stock, etf, mutual_fund, crypto, etc.
    exchange: Optional[str] = None
    currency: Optional[str] = None


class HoldingMetadata(BaseModel):
    """Classification metadata for a holding, used to enrich asset allocation data."""

    symbol: str
    name: Optional[str] = None
    asset_type: Optional[str] = None   # 'stock', 'etf', 'mutual_fund', 'crypto', 'other'
    asset_class: Optional[str] = None  # 'domestic', 'international'
    market_cap: Optional[str] = None   # 'large', 'mid', 'small' (equities only)
    sector: Optional[str] = None       # e.g. 'Technology', 'Healthcare'
    industry: Optional[str] = None     # e.g. 'Software', 'Biotechnology'
    country: Optional[str] = None      # e.g. 'United States', 'Germany'


class MarketDataProvider(ABC):
    """
    Abstract base class for market data providers.

    Implementations: YahooFinanceProvider, AlphaVantageProvider, FinnhubProvider
    """

    @abstractmethod
    async def get_quote(self, symbol: str) -> QuoteData:
        """
        Get current quote for a symbol.

        Args:
            symbol: Ticker symbol (e.g., "AAPL", "BTC-USD")

        Returns:
            QuoteData with current price and details

        Raises:
            ValueError: If symbol not found
            Exception: If API error
        """

    @abstractmethod
    async def get_quotes_batch(self, symbols: List[str]) -> Dict[str, QuoteData]:
        """
        Get quotes for multiple symbols efficiently.

        Args:
            symbols: List of ticker symbols

        Returns:
            Dict mapping symbol to QuoteData
        """

    @abstractmethod
    async def get_historical_prices(
        self, symbol: str, start_date: date, end_date: date, interval: str = "1d"
    ) -> List[HistoricalPrice]:
        """
        Get historical price data.

        Args:
            symbol: Ticker symbol
            start_date: Start date
            end_date: End date
            interval: Time interval (1d, 1wk, 1mo)

        Returns:
            List of HistoricalPrice objects
        """

    @abstractmethod
    async def search_symbol(self, query: str) -> List[SearchResult]:
        """
        Search for stocks/securities by name or symbol.

        Args:
            query: Search query (company name or partial symbol)

        Returns:
            List of SearchResult objects
        """

    @abstractmethod
    def supports_realtime(self) -> bool:
        """Whether this provider supports real-time data."""

    @abstractmethod
    def get_rate_limits(self) -> Dict[str, int]:
        """
        Get rate limit information.

        Returns:
            Dict with 'calls_per_minute', 'calls_per_day', etc.
        """

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get human-readable provider name."""

    async def get_holding_metadata(self, symbol: str) -> HoldingMetadata:
        """
        Get classification metadata for a holding (sector, asset type, market cap, etc.).

        Default implementation returns an empty metadata object. Providers that support
        this data should override this method.

        Args:
            symbol: Ticker symbol (e.g., "AAPL", "VTI")

        Returns:
            HoldingMetadata with classification fields populated where available.
        """
        return HoldingMetadata(symbol=symbol)
