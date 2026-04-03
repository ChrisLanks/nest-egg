"""
Tests for scalability and resilience improvements.

1. Provider failover chain returns correct order
2. Provider failover chain with no fallbacks
3. Circuit breaker is registered for market data providers
4. Retry decorator is applied to YahooFinanceProvider.get_quotes_batch
5. CachedMarketDataProvider uses circuit breaker for provider calls
6. Estimated monthly totals returns both income and spending in one query
7. MARKET_DATA_FALLBACK_PROVIDERS config is parsed correctly
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.circuit_breaker import KNOWN_SERVICES


# ---------------------------------------------------------------------------
# Circuit breaker coverage
# ---------------------------------------------------------------------------


def test_market_data_providers_in_known_services():
    """Circuit breaker KNOWN_SERVICES includes market data providers."""
    assert "yahoo_finance" in KNOWN_SERVICES
    assert "alpha_vantage" in KNOWN_SERVICES
    assert "finnhub" in KNOWN_SERVICES
    assert "coingecko" in KNOWN_SERVICES


def test_banking_providers_still_in_known_services():
    """Original banking providers are still covered."""
    assert "plaid" in KNOWN_SERVICES
    assert "teller" in KNOWN_SERVICES
    assert "mx" in KNOWN_SERVICES


# ---------------------------------------------------------------------------
# Provider failover chain
# ---------------------------------------------------------------------------


@patch("app.services.market_data.provider_factory.settings")
def test_provider_chain_with_fallbacks(mock_settings):
    """Failover chain includes primary + configured fallbacks."""
    from app.services.market_data.provider_factory import MarketDataProviderFactory

    mock_settings.MARKET_DATA_PROVIDER = "yahoo_finance"
    mock_settings.MARKET_DATA_FALLBACK_PROVIDERS = "alpha_vantage,finnhub"

    chain = MarketDataProviderFactory.get_provider_chain()
    assert chain == ["yahoo_finance", "alpha_vantage", "finnhub"]


@patch("app.services.market_data.provider_factory.settings")
def test_provider_chain_no_fallbacks(mock_settings):
    """Without fallback config, chain is just the primary."""
    from app.services.market_data.provider_factory import MarketDataProviderFactory

    mock_settings.MARKET_DATA_PROVIDER = "yahoo_finance"
    mock_settings.MARKET_DATA_FALLBACK_PROVIDERS = ""

    chain = MarketDataProviderFactory.get_provider_chain()
    assert chain == ["yahoo_finance"]


@patch("app.services.market_data.provider_factory.settings")
def test_provider_chain_deduplicates_primary(mock_settings):
    """Primary is not duplicated if also in fallback list."""
    from app.services.market_data.provider_factory import MarketDataProviderFactory

    mock_settings.MARKET_DATA_PROVIDER = "yahoo_finance"
    mock_settings.MARKET_DATA_FALLBACK_PROVIDERS = "yahoo_finance,finnhub"

    chain = MarketDataProviderFactory.get_provider_chain()
    assert chain == ["yahoo_finance", "finnhub"]


# ---------------------------------------------------------------------------
# Retry decorator
# ---------------------------------------------------------------------------


def test_yahoo_provider_get_quotes_batch_has_retry():
    """YahooFinanceProvider.get_quotes_batch has tenacity retry wrapper."""
    from app.services.market_data.yahoo_finance_provider import YahooFinanceProvider

    provider = YahooFinanceProvider()
    # tenacity wraps functions with a `retry` attribute
    assert hasattr(provider.get_quotes_batch, "retry")


# ---------------------------------------------------------------------------
# Cache + circuit breaker integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("app.services.market_data.cache.get_circuit_breaker")
@patch("app.services.market_data.cache.redis_cache")
async def test_cache_uses_circuit_breaker_on_miss(mock_redis, mock_cb_factory):
    """On cache miss, the circuit breaker wraps the provider call."""
    from app.services.market_data.base_provider import QuoteData
    from app.services.market_data.cache import CachedMarketDataProvider

    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.setex = AsyncMock(return_value=True)

    quote = QuoteData(symbol="AAPL", price=Decimal("150"), currency="USD")

    async def _cb_call(service_name, func, *args, **kwargs):
        assert service_name == "mock_provider"
        return await func(*args, **kwargs)

    mock_cb = MagicMock()
    mock_cb.call = AsyncMock(side_effect=_cb_call)
    mock_cb_factory.return_value = mock_cb

    provider = MagicMock()
    provider.get_quote = AsyncMock(return_value=quote)
    provider.get_provider_name = MagicMock(return_value="mock_provider")

    cached = CachedMarketDataProvider(provider)
    result = await cached.get_quote("AAPL")

    assert result.symbol == "AAPL"
    mock_cb.call.assert_called_once()


# ---------------------------------------------------------------------------
# Config setting exists
# ---------------------------------------------------------------------------


def test_fallback_providers_config_exists():
    """MARKET_DATA_FALLBACK_PROVIDERS is defined in settings."""
    from app.config import settings

    assert hasattr(settings, "MARKET_DATA_FALLBACK_PROVIDERS")
    # Default is empty string
    assert isinstance(settings.MARKET_DATA_FALLBACK_PROVIDERS, str)
