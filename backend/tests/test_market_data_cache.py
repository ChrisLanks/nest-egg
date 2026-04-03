"""
Tests for the Redis-backed market data cache layer.

1. CachedMarketDataProvider returns cached quote on HIT
2. CachedMarketDataProvider calls provider on MISS and stores result
3. Batch quotes: partial cache hit fetches only missing symbols
4. Batch quotes: full cache hit makes no provider call
5. get_holding_metadata returns cached metadata on HIT
6. get_holding_metadata calls provider on MISS and caches
7. search_symbol is always a pass-through (no caching)
8. Cache failures are transparent — provider is called on error
9. Historical prices are cached and returned on HIT
10. Provider name and rate limits are delegated to inner provider
"""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.market_data.base_provider import (
    HistoricalPrice,
    HoldingMetadata,
    QuoteData,
    SearchResult,
)
from app.services.market_data.cache import CachedMarketDataProvider


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_quote(symbol: str, price: float = 100.0) -> QuoteData:
    return QuoteData(symbol=symbol, price=Decimal(str(price)), currency="USD")


def _make_metadata(symbol: str) -> HoldingMetadata:
    return HoldingMetadata(symbol=symbol, sector="Technology", asset_type="stock")


def _make_historical(symbol: str) -> HistoricalPrice:
    return HistoricalPrice(
        date=date(2026, 1, 2),
        open=Decimal("100"),
        high=Decimal("105"),
        low=Decimal("99"),
        close=Decimal("103"),
        volume=1000,
    )


def _mock_provider() -> MagicMock:
    provider = MagicMock()
    provider.get_quote = AsyncMock()
    provider.get_quotes_batch = AsyncMock()
    provider.get_holding_metadata = AsyncMock()
    provider.get_historical_prices = AsyncMock()
    provider.search_symbol = AsyncMock()
    provider.supports_realtime = MagicMock(return_value=False)
    provider.get_rate_limits = MagicMock(return_value={"calls_per_minute": 60})
    provider.get_provider_name = MagicMock(return_value="mock_provider")
    return provider


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("app.services.market_data.cache.redis_cache")
async def test_get_quote_cache_hit(mock_redis):
    """Cached quote is returned without calling the provider."""
    quote = _make_quote("AAPL", 150.0)
    mock_redis.get = AsyncMock(return_value=quote.model_dump())

    provider = _mock_provider()
    cached = CachedMarketDataProvider(provider)

    result = await cached.get_quote("AAPL")

    assert result.symbol == "AAPL"
    assert result.price == Decimal("150.0")
    provider.get_quote.assert_not_called()


@pytest.mark.asyncio
@patch("app.services.market_data.cache.redis_cache")
async def test_get_quote_cache_miss(mock_redis):
    """On miss, provider is called and result is cached."""
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.setex = AsyncMock(return_value=True)

    quote = _make_quote("AAPL", 150.0)
    provider = _mock_provider()
    provider.get_quote.return_value = quote

    cached = CachedMarketDataProvider(provider)
    result = await cached.get_quote("AAPL")

    assert result.symbol == "AAPL"
    provider.get_quote.assert_called_once_with("AAPL")
    mock_redis.setex.assert_called_once()


@pytest.mark.asyncio
@patch("app.services.market_data.cache.redis_cache")
async def test_batch_partial_cache_hit(mock_redis):
    """Batch: cached symbols are used, only missing symbols hit the provider."""
    aapl_data = _make_quote("AAPL", 150.0).model_dump()

    async def _get(key):
        if "AAPL" in key:
            return aapl_data
        return None

    mock_redis.get = AsyncMock(side_effect=_get)
    mock_redis.setex = AsyncMock(return_value=True)

    msft_quote = _make_quote("MSFT", 300.0)
    provider = _mock_provider()
    provider.get_quotes_batch.return_value = {"MSFT": msft_quote}

    cached = CachedMarketDataProvider(provider)
    result = await cached.get_quotes_batch(["AAPL", "MSFT"])

    assert "AAPL" in result
    assert "MSFT" in result
    # Provider should only be called for MSFT
    provider.get_quotes_batch.assert_called_once_with(["MSFT"])


@pytest.mark.asyncio
@patch("app.services.market_data.cache.redis_cache")
async def test_batch_full_cache_hit(mock_redis):
    """Batch: when all symbols are cached, provider is not called."""
    aapl_data = _make_quote("AAPL", 150.0).model_dump()
    msft_data = _make_quote("MSFT", 300.0).model_dump()

    async def _get(key):
        if "AAPL" in key:
            return aapl_data
        if "MSFT" in key:
            return msft_data
        return None

    mock_redis.get = AsyncMock(side_effect=_get)

    provider = _mock_provider()
    cached = CachedMarketDataProvider(provider)
    result = await cached.get_quotes_batch(["AAPL", "MSFT"])

    assert len(result) == 2
    provider.get_quotes_batch.assert_not_called()


@pytest.mark.asyncio
@patch("app.services.market_data.cache.redis_cache")
async def test_metadata_cache_hit(mock_redis):
    """Cached metadata is returned without calling the provider."""
    meta = _make_metadata("VTI")
    mock_redis.get = AsyncMock(return_value=meta.model_dump())

    provider = _mock_provider()
    cached = CachedMarketDataProvider(provider)
    result = await cached.get_holding_metadata("VTI")

    assert result.sector == "Technology"
    provider.get_holding_metadata.assert_not_called()


@pytest.mark.asyncio
@patch("app.services.market_data.cache.redis_cache")
async def test_metadata_cache_miss(mock_redis):
    """On miss, provider metadata is fetched and cached."""
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.setex = AsyncMock(return_value=True)

    meta = _make_metadata("VTI")
    provider = _mock_provider()
    provider.get_holding_metadata.return_value = meta

    cached = CachedMarketDataProvider(provider)
    result = await cached.get_holding_metadata("VTI")

    assert result.symbol == "VTI"
    provider.get_holding_metadata.assert_called_once_with("VTI")
    mock_redis.setex.assert_called_once()


@pytest.mark.asyncio
@patch("app.services.market_data.cache.redis_cache")
async def test_search_symbol_passthrough(mock_redis):
    """search_symbol always delegates to the provider (no caching)."""
    provider = _mock_provider()
    provider.search_symbol.return_value = [
        SearchResult(symbol="AAPL", name="Apple Inc.", type="stock")
    ]

    cached = CachedMarketDataProvider(provider)
    result = await cached.search_symbol("apple")

    assert len(result) == 1
    provider.search_symbol.assert_called_once_with("apple")


@pytest.mark.asyncio
@patch("app.services.market_data.cache.redis_cache")
async def test_cache_error_falls_through(mock_redis):
    """Redis failure is transparent — provider is called."""
    mock_redis.get = AsyncMock(side_effect=Exception("Redis down"))
    mock_redis.setex = AsyncMock(return_value=False)

    quote = _make_quote("AAPL", 150.0)
    provider = _mock_provider()
    provider.get_quote.return_value = quote

    cached = CachedMarketDataProvider(provider)
    result = await cached.get_quote("AAPL")

    assert result.symbol == "AAPL"
    provider.get_quote.assert_called_once()


@pytest.mark.asyncio
@patch("app.services.market_data.cache.redis_cache")
async def test_historical_cache_hit(mock_redis):
    """Cached historical prices are returned without provider call."""
    hp = _make_historical("AAPL")
    mock_redis.get = AsyncMock(return_value=[hp.model_dump()])

    provider = _mock_provider()
    cached = CachedMarketDataProvider(provider)
    result = await cached.get_historical_prices(
        "AAPL", date(2026, 1, 1), date(2026, 1, 31)
    )

    assert len(result) == 1
    provider.get_historical_prices.assert_not_called()


def test_provider_name_delegated():
    """get_provider_name and get_rate_limits delegate to inner provider."""
    provider = _mock_provider()
    cached = CachedMarketDataProvider(provider)

    assert cached.get_provider_name() == "mock_provider"
    assert cached.get_rate_limits() == {"calls_per_minute": 60}
    assert cached.supports_realtime() is False
