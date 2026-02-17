"""
Provider factory for market data.

Centralizes provider selection logic.
"""

import os
from typing import Optional
import logging

from .base_provider import MarketDataProvider
from .yahoo_finance_provider import YahooFinanceProvider

logger = logging.getLogger(__name__)


class MarketDataProviderFactory:
    """Factory for creating market data providers."""

    _instance: Optional[MarketDataProvider] = None

    @classmethod
    def get_provider(cls, provider_name: Optional[str] = None) -> MarketDataProvider:
        """
        Get market data provider instance.

        Args:
            provider_name: Override provider (yahoo_finance, alpha_vantage, finnhub)
                          If None, uses environment variable MARKET_DATA_PROVIDER

        Returns:
            MarketDataProvider instance

        Raises:
            ValueError: If provider not supported
        """
        # Use cached instance if no override
        if provider_name is None and cls._instance is not None:
            return cls._instance

        # Determine which provider to use
        if provider_name is None:
            provider_name = os.getenv('MARKET_DATA_PROVIDER', 'yahoo_finance')

        provider_name = provider_name.lower()

        # Create provider instance
        if provider_name == 'yahoo_finance':
            provider = YahooFinanceProvider()
        elif provider_name == 'alpha_vantage':
            # Import only if needed
            from .alpha_vantage_provider import AlphaVantageProvider
            provider = AlphaVantageProvider()
        elif provider_name == 'finnhub':
            # Import only if needed
            from .finnhub_provider import FinnhubProvider
            provider = FinnhubProvider()
        else:
            raise ValueError(
                f"Unsupported market data provider: {provider_name}. "
                f"Supported: yahoo_finance, alpha_vantage, finnhub"
            )

        logger.info(f"Using market data provider: {provider.get_provider_name()}")

        # Cache instance if no override
        if cls._instance is None:
            cls._instance = provider

        return provider


def get_market_data_provider(provider_name: Optional[str] = None) -> MarketDataProvider:
    """
    Convenience function to get market data provider.

    Args:
        provider_name: Optional provider override

    Returns:
        MarketDataProvider instance
    """
    return MarketDataProviderFactory.get_provider(provider_name)
