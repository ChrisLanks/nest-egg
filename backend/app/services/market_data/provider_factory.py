"""
Provider factory for market data.

Centralizes provider selection logic with automatic failover.
"""

import logging
from typing import List, Optional

from app.config import settings

from .base_provider import MarketDataProvider
from .cache import CachedMarketDataProvider
from .yahoo_finance_provider import YahooFinanceProvider

logger = logging.getLogger(__name__)


class MarketDataProviderFactory:
    """Factory for creating market data providers with failover support."""

    _instance: Optional[MarketDataProvider] = None

    @classmethod
    def _create_raw_provider(cls, provider_name: str) -> MarketDataProvider:
        """Create a raw (unwrapped) provider by name.

        Raises ValueError if the provider is unsupported or unavailable.
        """
        provider_name = provider_name.lower()

        if provider_name == "yahoo_finance":
            return YahooFinanceProvider()
        elif provider_name == "alpha_vantage":
            try:
                from .alpha_vantage_provider import AlphaVantageProvider

                return AlphaVantageProvider()
            except ImportError:
                raise ValueError(
                    "Alpha Vantage provider is not yet implemented. "
                    "Configure ALPHA_VANTAGE_API_KEY and add the provider module."
                )
        elif provider_name == "finnhub":
            try:
                from .finnhub_provider import FinnhubProvider

                return FinnhubProvider()
            except ImportError:
                raise ValueError(
                    "Finnhub provider is not yet implemented. "
                    "Configure FINNHUB_API_KEY and add the provider module."
                )
        elif provider_name == "coingecko":
            from .coingecko_provider import CoinGeckoProvider

            api_key = settings.COINGECKO_API_KEY
            return CoinGeckoProvider(api_key=api_key)
        else:
            raise ValueError(
                f"Unsupported market data provider: {provider_name}. "
                f"Supported: yahoo_finance, alpha_vantage, finnhub, coingecko"
            )

    @classmethod
    def get_provider_chain(cls) -> List[str]:
        """Return the ordered list of provider names (primary + fallbacks)."""
        chain = [settings.MARKET_DATA_PROVIDER]
        fallbacks = settings.MARKET_DATA_FALLBACK_PROVIDERS.strip()
        if fallbacks:
            chain.extend(
                name.strip()
                for name in fallbacks.split(",")
                if name.strip() and name.strip() != settings.MARKET_DATA_PROVIDER
            )
        return chain

    @classmethod
    def get_provider(cls, provider_name: Optional[str] = None) -> MarketDataProvider:
        """
        Get market data provider instance.

        Args:
            provider_name: Override provider (yahoo_finance, alpha_vantage, finnhub, coingecko)
                          If None, uses environment variable MARKET_DATA_PROVIDER

        Returns:
            MarketDataProvider instance (wrapped with cache + circuit breaker)

        Raises:
            ValueError: If provider not supported or not installed
        """
        # Use cached instance if no override
        if provider_name is None and cls._instance is not None:
            return cls._instance

        # Determine which provider to use
        if provider_name is None:
            provider_name = settings.MARKET_DATA_PROVIDER

        provider = cls._create_raw_provider(provider_name)

        # Wrap with Redis caching layer (includes circuit breaker)
        provider = CachedMarketDataProvider(provider)
        logger.info(f"Using market data provider: {provider.get_provider_name()} (cached)")

        # Cache instance if no override
        if cls._instance is None:
            cls._instance = provider

        return provider

    @classmethod
    async def get_quote_with_failover(cls, symbol: str):
        """Try primary provider, then fallbacks on failure.

        This is used for critical single-quote fetches where availability
        matters more than consistency (e.g. user-triggered refresh).
        """
        from .base_provider import QuoteData

        chain = cls.get_provider_chain()
        last_error: Optional[Exception] = None

        for name in chain:
            try:
                provider = cls.get_provider(name)
                return await provider.get_quote(symbol)
            except Exception as exc:
                logger.warning(
                    "Provider %s failed for %s: %s — trying next", name, symbol, exc
                )
                last_error = exc
                # Reset cached instance so next iteration creates a new provider
                cls._instance = None

        raise ValueError(
            f"All providers exhausted for {symbol}. Last error: {last_error}"
        )


def get_market_data_provider(provider_name: Optional[str] = None) -> MarketDataProvider:
    """
    Convenience function to get market data provider.

    Args:
        provider_name: Optional provider override

    Returns:
        MarketDataProvider instance
    """
    return MarketDataProviderFactory.get_provider(provider_name)
