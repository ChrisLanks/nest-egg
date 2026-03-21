"""Unit tests for CoinGecko market data provider."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.market_data.base_provider import (
    HistoricalPrice,
    HoldingMetadata,
    QuoteData,
    SearchResult,
)
from app.services.market_data.coingecko_provider import (
    CoinGeckoProvider,
    _coingecko_id_to_symbol,
    _symbol_to_coingecko_id,
)

# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


class TestSymbolToCoingeckoId:
    """Tests for _symbol_to_coingecko_id helper."""

    def test_direct_mapping_btc_usd(self):
        assert _symbol_to_coingecko_id("BTC-USD") == "bitcoin"

    def test_direct_mapping_eth_usd(self):
        assert _symbol_to_coingecko_id("ETH-USD") == "ethereum"

    def test_case_insensitive(self):
        assert _symbol_to_coingecko_id("btc-usd") == "bitcoin"

    def test_bare_ticker_appends_usd(self):
        """BTC should try BTC-USD and find bitcoin."""
        assert _symbol_to_coingecko_id("BTC") == "bitcoin"

    def test_bare_ticker_eth(self):
        assert _symbol_to_coingecko_id("ETH") == "ethereum"

    def test_unknown_symbol_lowercase_passthrough(self):
        assert _symbol_to_coingecko_id("NEWCOIN") == "newcoin"

    def test_already_coingecko_id(self):
        assert _symbol_to_coingecko_id("bitcoin") == "bitcoin"

    def test_unknown_mixed_case_passthrough(self):
        assert _symbol_to_coingecko_id("SomeToken") == "sometoken"


class TestCoingeckoIdToSymbol:
    """Tests for _coingecko_id_to_symbol helper."""

    def test_known_id_bitcoin(self):
        assert _coingecko_id_to_symbol("bitcoin") == "BTC-USD"

    def test_known_id_ethereum(self):
        assert _coingecko_id_to_symbol("ethereum") == "ETH-USD"

    def test_unknown_id_generates_symbol(self):
        assert _coingecko_id_to_symbol("some-unknown-coin") == "SOME-UNKNOWN-COIN-USD"


# ---------------------------------------------------------------------------
# Provider class tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCoinGeckoProviderInit:
    """Tests for CoinGeckoProvider initialization."""

    def test_init_without_api_key(self):
        provider = CoinGeckoProvider()
        assert provider._api_key is None
        assert provider.provider_name == "CoinGecko"
        assert provider._client is None

    def test_init_with_api_key(self):
        provider = CoinGeckoProvider(api_key="test-key-123")  # pragma: allowlist secret
        assert provider._api_key == "test-key-123"  # pragma: allowlist secret

    def test_get_provider_name(self):
        provider = CoinGeckoProvider()
        assert provider.get_provider_name() == "CoinGecko"

    def test_supports_realtime_returns_false(self):
        provider = CoinGeckoProvider()
        assert provider.supports_realtime() is False

    def test_rate_limits_without_key(self):
        provider = CoinGeckoProvider()
        limits = provider.get_rate_limits()
        assert limits["calls_per_minute"] == 10
        assert "note" in limits

    def test_rate_limits_with_key(self):
        provider = CoinGeckoProvider(api_key="some-key")
        limits = provider.get_rate_limits()
        assert limits["calls_per_minute"] == 500
        assert "Free API key tier" in limits["note"]


@pytest.mark.unit
@pytest.mark.asyncio
class TestCoinGeckoProviderGetQuote:
    """Tests for CoinGeckoProvider.get_quote."""

    async def test_get_quote_success(self):
        provider = CoinGeckoProvider()
        mock_response = {
            "bitcoin": {
                "usd": 65000.50,
                "usd_market_cap": 1300000000000,
                "usd_24h_change": 2.5,
                "usd_24h_vol": 25000000000,
            }
        }
        provider._request = AsyncMock(return_value=mock_response)

        quote = await provider.get_quote("BTC-USD")

        assert isinstance(quote, QuoteData)
        assert quote.symbol == "BTC-USD"
        assert quote.price == Decimal("65000.50")
        assert quote.market_cap == Decimal("1300000000000")
        assert quote.change_percent == Decimal("2.5")
        assert quote.volume == 25000000000
        assert quote.currency == "USD"
        # change = price * change_percent / 100
        expected_change = Decimal("65000.50") * Decimal("2.5") / Decimal("100")
        assert quote.change == expected_change

    async def test_get_quote_no_price_data(self):
        """Should raise ValueError when coin data is missing."""
        provider = CoinGeckoProvider()
        provider._request = AsyncMock(return_value={})

        with pytest.raises(ValueError, match="No price data"):
            await provider.get_quote("BTC-USD")

    async def test_get_quote_coin_missing_usd(self):
        """Should raise ValueError when usd field is missing."""
        provider = CoinGeckoProvider()
        provider._request = AsyncMock(return_value={"bitcoin": {}})

        with pytest.raises(ValueError, match="No price data"):
            await provider.get_quote("BTC-USD")

    async def test_get_quote_with_none_optional_fields(self):
        """Should handle None values for market_cap, change, volume."""
        provider = CoinGeckoProvider()
        mock_response = {
            "bitcoin": {
                "usd": 65000.0,
                "usd_market_cap": None,
                "usd_24h_change": None,
                "usd_24h_vol": None,
            }
        }
        provider._request = AsyncMock(return_value=mock_response)

        quote = await provider.get_quote("BTC-USD")

        assert quote.price == Decimal("65000.0")
        assert quote.market_cap is None
        assert quote.change_percent is None
        assert quote.change is None
        assert quote.volume is None

    async def test_get_quote_bare_ticker(self):
        """Should work with bare ticker like BTC."""
        provider = CoinGeckoProvider()
        mock_response = {
            "bitcoin": {
                "usd": 65000.0,
                "usd_market_cap": 1300000000000,
                "usd_24h_change": 2.5,
                "usd_24h_vol": 25000000000,
            }
        }
        provider._request = AsyncMock(return_value=mock_response)

        quote = await provider.get_quote("BTC")
        assert quote.symbol == "BTC"
        assert quote.price == Decimal("65000.0")

    async def test_get_quote_timeout(self):
        """Should raise ValueError on timeout."""
        provider = CoinGeckoProvider()
        provider._request = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        with pytest.raises(ValueError, match="timeout"):
            await provider.get_quote("BTC-USD")

    async def test_get_quote_http_error(self):
        """Should raise ValueError on HTTP error."""
        provider = CoinGeckoProvider()
        mock_request = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 500
        error = httpx.HTTPStatusError("Server Error", request=mock_request, response=mock_response)
        provider._request = AsyncMock(side_effect=error)

        with pytest.raises(ValueError, match="CoinGecko API error"):
            await provider.get_quote("BTC-USD")

    async def test_get_quote_invalid_symbol(self):
        """Should raise ValueError for symbols with injection characters."""
        provider = CoinGeckoProvider()

        with pytest.raises(ValueError):
            await provider.get_quote("BTC;DROP TABLE")

    async def test_get_quote_generic_exception(self):
        """Should wrap generic exceptions in ValueError."""
        provider = CoinGeckoProvider()
        provider._request = AsyncMock(side_effect=RuntimeError("something broke"))

        with pytest.raises(ValueError, match="Failed to fetch quote"):
            await provider.get_quote("BTC-USD")


@pytest.mark.unit
@pytest.mark.asyncio
class TestCoinGeckoProviderGetQuotesBatch:
    """Tests for CoinGeckoProvider.get_quotes_batch."""

    async def test_batch_success(self):
        provider = CoinGeckoProvider()
        mock_response = {
            "bitcoin": {
                "usd": 65000.0,
                "usd_market_cap": 1300000000000,
                "usd_24h_change": 2.5,
                "usd_24h_vol": 25000000000,
            },
            "ethereum": {
                "usd": 3500.0,
                "usd_market_cap": 420000000000,
                "usd_24h_change": -1.2,
                "usd_24h_vol": 15000000000,
            },
        }
        provider._request = AsyncMock(return_value=mock_response)

        quotes = await provider.get_quotes_batch(["BTC-USD", "ETH-USD"])

        assert len(quotes) == 2
        assert "BTC-USD" in quotes
        assert "ETH-USD" in quotes
        assert quotes["BTC-USD"].price == Decimal("65000.0")
        assert quotes["ETH-USD"].price == Decimal("3500.0")

    async def test_batch_partial_data(self):
        """Should skip symbols with no price data in response."""
        provider = CoinGeckoProvider()
        mock_response = {
            "bitcoin": {
                "usd": 65000.0,
                "usd_market_cap": 1300000000000,
                "usd_24h_change": 2.5,
                "usd_24h_vol": 25000000000,
            },
            # ethereum missing from response
        }
        provider._request = AsyncMock(return_value=mock_response)

        quotes = await provider.get_quotes_batch(["BTC-USD", "ETH-USD"])

        assert len(quotes) == 1
        assert "BTC-USD" in quotes

    async def test_batch_fallback_on_failure(self):
        """Should fall back to individual fetches on batch failure."""
        provider = CoinGeckoProvider()

        # First call (batch) fails, individual calls succeed
        single_quote = QuoteData(
            symbol="BTC-USD",
            price=Decimal("65000.0"),
            currency="USD",
        )
        provider._request = AsyncMock(side_effect=ValueError("batch failed"))
        provider.get_quote = AsyncMock(return_value=single_quote)

        quotes = await provider.get_quotes_batch(["BTC-USD"])

        assert len(quotes) == 1
        assert quotes["BTC-USD"].price == Decimal("65000.0")
        provider.get_quote.assert_called_once_with("BTC-USD")

    async def test_batch_fallback_individual_also_fails(self):
        """Should skip symbols that fail even in fallback."""
        provider = CoinGeckoProvider()
        provider._request = AsyncMock(side_effect=ValueError("batch failed"))
        provider.get_quote = AsyncMock(side_effect=ValueError("also failed"))

        quotes = await provider.get_quotes_batch(["BTC-USD"])

        assert len(quotes) == 0

    async def test_batch_empty_symbols(self):
        """Should return empty dict for invalid symbols list."""
        provider = CoinGeckoProvider()

        # All symbols fail validation
        quotes = await provider.get_quotes_batch([";;;", "|||"])
        assert quotes == {}

    async def test_batch_skips_invalid_symbols(self):
        """Should skip symbols that fail validation, process the rest."""
        provider = CoinGeckoProvider()
        mock_response = {
            "bitcoin": {
                "usd": 65000.0,
                "usd_market_cap": 1300000000000,
                "usd_24h_change": 2.5,
                "usd_24h_vol": 25000000000,
            },
        }
        provider._request = AsyncMock(return_value=mock_response)

        quotes = await provider.get_quotes_batch(["BTC-USD", ";;;INVALID"])

        assert len(quotes) == 1
        assert "BTC-USD" in quotes


@pytest.mark.unit
@pytest.mark.asyncio
class TestCoinGeckoProviderGetHistoricalPrices:
    """Tests for CoinGeckoProvider.get_historical_prices."""

    async def test_historical_prices_success(self):
        provider = CoinGeckoProvider()
        mock_response = {
            "prices": [
                [1709251200000, 63000.0],  # 2024-03-01
                [1709337600000, 64000.0],  # 2024-03-02
                [1709424000000, 65000.0],  # 2024-03-03
            ]
        }
        provider._request = AsyncMock(return_value=mock_response)

        prices = await provider.get_historical_prices(
            "BTC-USD",
            start_date=date(2024, 3, 1),
            end_date=date(2024, 3, 3),
        )

        assert len(prices) == 3
        assert all(isinstance(p, HistoricalPrice) for p in prices)
        assert prices[0].close == Decimal("63000.0")
        assert prices[-1].close == Decimal("65000.0")
        # Volume is 0 since market_chart doesn't provide per-point volume
        assert prices[0].volume == 0

    async def test_historical_prices_empty(self):
        """Should return empty list when no prices returned."""
        provider = CoinGeckoProvider()
        provider._request = AsyncMock(return_value={"prices": []})

        prices = await provider.get_historical_prices(
            "BTC-USD",
            start_date=date(2024, 3, 1),
            end_date=date(2024, 3, 3),
        )

        assert prices == []

    async def test_historical_prices_filters_by_date_range(self):
        """Should only include prices within the specified date range."""
        provider = CoinGeckoProvider()
        mock_response = {
            "prices": [
                [1709164800000, 62000.0],  # 2024-02-29 - before range
                [1709251200000, 63000.0],  # 2024-03-01 - in range
                [1709337600000, 64000.0],  # 2024-03-02 - in range
                [1709510400000, 66000.0],  # 2024-03-04 - after range
            ]
        }
        provider._request = AsyncMock(return_value=mock_response)

        prices = await provider.get_historical_prices(
            "BTC-USD",
            start_date=date(2024, 3, 1),
            end_date=date(2024, 3, 2),
        )

        assert len(prices) == 2

    async def test_historical_prices_zero_days(self):
        """Should use days=1 when end_date equals start_date."""
        provider = CoinGeckoProvider()
        provider._request = AsyncMock(return_value={"prices": []})

        await provider.get_historical_prices(
            "BTC-USD",
            start_date=date(2024, 3, 1),
            end_date=date(2024, 3, 1),
        )

        call_kwargs = provider._request.call_args
        assert call_kwargs[1]["params"]["days"] == "1"

    async def test_historical_prices_timeout(self):
        provider = CoinGeckoProvider()
        provider._request = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        with pytest.raises(ValueError, match="timeout"):
            await provider.get_historical_prices(
                "BTC-USD",
                start_date=date(2024, 3, 1),
                end_date=date(2024, 3, 3),
            )

    async def test_historical_prices_invalid_symbol(self):
        provider = CoinGeckoProvider()

        with pytest.raises(ValueError):
            await provider.get_historical_prices(
                ";;;",
                start_date=date(2024, 3, 1),
                end_date=date(2024, 3, 3),
            )

    async def test_historical_prices_generic_exception(self):
        provider = CoinGeckoProvider()
        provider._request = AsyncMock(side_effect=RuntimeError("network error"))

        with pytest.raises(ValueError, match="Failed to fetch historical data"):
            await provider.get_historical_prices(
                "BTC-USD",
                start_date=date(2024, 3, 1),
                end_date=date(2024, 3, 3),
            )

    async def test_historical_prices_multiple_points_same_day(self):
        """Multiple price points on the same day should produce one HistoricalPrice."""
        provider = CoinGeckoProvider()
        # Two points on 2024-03-01 (different times)
        mock_response = {
            "prices": [
                [1709251200000, 63000.0],  # 2024-03-01 00:00
                [1709294400000, 63500.0],  # 2024-03-01 12:00
            ]
        }
        provider._request = AsyncMock(return_value=mock_response)

        prices = await provider.get_historical_prices(
            "BTC-USD",
            start_date=date(2024, 3, 1),
            end_date=date(2024, 3, 1),
        )

        assert len(prices) == 1
        assert prices[0].open == Decimal("63000.0")
        assert prices[0].close == Decimal("63500.0")
        assert prices[0].high == Decimal("63500.0")
        assert prices[0].low == Decimal("63000.0")


@pytest.mark.unit
@pytest.mark.asyncio
class TestCoinGeckoProviderSearchSymbol:
    """Tests for CoinGeckoProvider.search_symbol."""

    async def test_search_success(self):
        provider = CoinGeckoProvider()
        mock_response = {
            "coins": [
                {"id": "bitcoin", "name": "Bitcoin", "symbol": "btc"},
                {"id": "ethereum", "name": "Ethereum", "symbol": "eth"},
            ]
        }
        provider._request = AsyncMock(return_value=mock_response)

        results = await provider.search_symbol("bit")

        assert len(results) == 2
        assert all(isinstance(r, SearchResult) for r in results)
        assert results[0].symbol == "BTC-USD"
        assert results[0].name == "Bitcoin"
        assert results[0].type == "crypto"
        assert results[0].exchange == "CoinGecko"
        assert results[1].symbol == "ETH-USD"

    async def test_search_empty_results(self):
        provider = CoinGeckoProvider()
        provider._request = AsyncMock(return_value={"coins": []})

        results = await provider.search_symbol("zzzznonexistent")

        assert results == []

    async def test_search_returns_empty_on_error(self):
        """Should return empty list on error, not raise."""
        provider = CoinGeckoProvider()
        provider._request = AsyncMock(side_effect=ValueError("API error"))

        results = await provider.search_symbol("bitcoin")

        assert results == []

    async def test_search_limits_to_20_results(self):
        """Should return at most 20 results."""
        provider = CoinGeckoProvider()
        coins = [{"id": f"coin-{i}", "name": f"Coin {i}", "symbol": f"C{i}"} for i in range(30)]
        provider._request = AsyncMock(return_value={"coins": coins})

        results = await provider.search_symbol("coin")

        assert len(results) == 20

    async def test_search_unknown_coin_symbol_generation(self):
        """Unknown CoinGecko IDs should generate uppercase-USD symbols."""
        provider = CoinGeckoProvider()
        mock_response = {
            "coins": [
                {"id": "some-new-coin", "name": "Some New Coin", "symbol": "snc"},
            ]
        }
        provider._request = AsyncMock(return_value=mock_response)

        results = await provider.search_symbol("some")

        assert results[0].symbol == "SOME-NEW-COIN-USD"


@pytest.mark.unit
@pytest.mark.asyncio
class TestCoinGeckoProviderGetHoldingMetadata:
    """Tests for CoinGeckoProvider.get_holding_metadata."""

    async def test_metadata_large_cap(self):
        provider = CoinGeckoProvider()
        mock_response = {
            "name": "Bitcoin",
            "categories": ["Cryptocurrency"],
            "market_data": {"market_cap": {"usd": 1300000000000}},
        }
        provider._request = AsyncMock(return_value=mock_response)

        meta = await provider.get_holding_metadata("BTC-USD")

        assert isinstance(meta, HoldingMetadata)
        assert meta.symbol == "BTC-USD"
        assert meta.name == "Bitcoin"
        assert meta.asset_type == "crypto"
        assert meta.market_cap == "large"
        assert meta.sector == "Cryptocurrency"

    async def test_metadata_mid_cap(self):
        provider = CoinGeckoProvider()
        mock_response = {
            "name": "MidCoin",
            "categories": ["DeFi"],
            "market_data": {"market_cap": {"usd": 5000000000}},
        }
        provider._request = AsyncMock(return_value=mock_response)

        meta = await provider.get_holding_metadata("BTC-USD")

        assert meta.market_cap == "mid"

    async def test_metadata_small_cap(self):
        provider = CoinGeckoProvider()
        mock_response = {
            "name": "SmallCoin",
            "categories": ["Meme"],
            "market_data": {"market_cap": {"usd": 500000000}},
        }
        provider._request = AsyncMock(return_value=mock_response)

        meta = await provider.get_holding_metadata("BTC-USD")

        assert meta.market_cap == "small"

    async def test_metadata_no_market_cap(self):
        provider = CoinGeckoProvider()
        mock_response = {
            "name": "NoCap",
            "categories": [],
            "market_data": {"market_cap": {}},
        }
        provider._request = AsyncMock(return_value=mock_response)

        meta = await provider.get_holding_metadata("BTC-USD")

        assert meta.market_cap is None
        assert meta.sector is None

    async def test_metadata_request_failure_returns_default(self):
        """Should return bare metadata on API error, not raise."""
        provider = CoinGeckoProvider()
        provider._request = AsyncMock(side_effect=ValueError("API down"))

        meta = await provider.get_holding_metadata("BTC-USD")

        assert meta.symbol == "BTC-USD"
        assert meta.name is None
        assert meta.market_cap is None

    async def test_metadata_invalid_symbol_returns_default(self):
        """Should return bare metadata for invalid symbols."""
        provider = CoinGeckoProvider()

        meta = await provider.get_holding_metadata(";;;INVALID")

        assert meta.symbol == ";;;INVALID"
        assert meta.name is None

    async def test_metadata_boundary_large_cap(self):
        """Exactly 10B should be large cap."""
        provider = CoinGeckoProvider()
        mock_response = {
            "name": "BoundaryCoin",
            "categories": ["Crypto"],
            "market_data": {"market_cap": {"usd": 10000000000}},
        }
        provider._request = AsyncMock(return_value=mock_response)

        meta = await provider.get_holding_metadata("BTC-USD")

        assert meta.market_cap == "large"

    async def test_metadata_boundary_mid_cap(self):
        """Exactly 2B should be mid cap."""
        provider = CoinGeckoProvider()
        mock_response = {
            "name": "MidBoundary",
            "categories": ["Crypto"],
            "market_data": {"market_cap": {"usd": 2000000000}},
        }
        provider._request = AsyncMock(return_value=mock_response)

        meta = await provider.get_holding_metadata("BTC-USD")

        assert meta.market_cap == "mid"


@pytest.mark.unit
@pytest.mark.asyncio
class TestCoinGeckoProviderRequest:
    """Tests for CoinGeckoProvider._request retry logic."""

    async def test_request_success(self):
        provider = CoinGeckoProvider()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "ok"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        provider._get_client = AsyncMock(return_value=mock_client)

        result = await provider._request("GET", "/test")

        assert result == {"data": "ok"}

    async def test_request_retry_on_429(self):
        """Should retry on 429 and succeed on subsequent attempt."""
        provider = CoinGeckoProvider()

        rate_limited_resp = MagicMock()
        rate_limited_resp.status_code = 429
        rate_limited_resp.headers = {"Retry-After": "1"}

        success_resp = MagicMock()
        success_resp.status_code = 200
        success_resp.json.return_value = {"data": "ok"}
        success_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=[rate_limited_resp, success_resp])
        provider._get_client = AsyncMock(return_value=mock_client)

        with patch(
            "app.services.market_data.coingecko_provider.asyncio.sleep", new_callable=AsyncMock
        ):
            result = await provider._request("GET", "/test")

        assert result == {"data": "ok"}
        assert mock_client.request.call_count == 2

    async def test_request_exhausted_retries_on_429(self):
        """Should raise ValueError after exhausting retries on 429."""
        provider = CoinGeckoProvider()

        rate_limited_resp = MagicMock()
        rate_limited_resp.status_code = 429
        rate_limited_resp.headers = {"Retry-After": "1"}

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=rate_limited_resp)
        provider._get_client = AsyncMock(return_value=mock_client)

        with patch(
            "app.services.market_data.coingecko_provider.asyncio.sleep", new_callable=AsyncMock
        ):
            with pytest.raises(ValueError, match="rate limit exceeded"):
                await provider._request("GET", "/test")

        # Initial attempt + 2 retries = 3
        assert mock_client.request.call_count == 3

    async def test_request_caps_retry_after_at_30(self):
        """Should cap Retry-After at 30 seconds."""
        provider = CoinGeckoProvider()

        rate_limited_resp = MagicMock()
        rate_limited_resp.status_code = 429
        rate_limited_resp.headers = {"Retry-After": "120"}

        success_resp = MagicMock()
        success_resp.status_code = 200
        success_resp.json.return_value = {"ok": True}
        success_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=[rate_limited_resp, success_resp])
        provider._get_client = AsyncMock(return_value=mock_client)

        with patch(
            "app.services.market_data.coingecko_provider.asyncio.sleep",
            new_callable=AsyncMock,
        ) as mock_sleep:
            await provider._request("GET", "/test")

        mock_sleep.assert_called_once_with(30)

    async def test_request_raises_on_http_error(self):
        """Should call raise_for_status for non-429 errors."""
        provider = CoinGeckoProvider()

        error_resp = MagicMock()
        error_resp.status_code = 500
        mock_request = MagicMock()
        error_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=mock_request, response=error_resp
        )

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=error_resp)
        provider._get_client = AsyncMock(return_value=mock_client)

        with pytest.raises(httpx.HTTPStatusError):
            await provider._request("GET", "/test")

    async def test_request_default_retry_after(self):
        """Should default to 5s when Retry-After header is missing."""
        provider = CoinGeckoProvider()

        rate_limited_resp = MagicMock()
        rate_limited_resp.status_code = 429
        rate_limited_resp.headers = {}  # No Retry-After

        success_resp = MagicMock()
        success_resp.status_code = 200
        success_resp.json.return_value = {"ok": True}
        success_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=[rate_limited_resp, success_resp])
        provider._get_client = AsyncMock(return_value=mock_client)

        with patch(
            "app.services.market_data.coingecko_provider.asyncio.sleep",
            new_callable=AsyncMock,
        ) as mock_sleep:
            await provider._request("GET", "/test")

        mock_sleep.assert_called_once_with(5)


@pytest.mark.unit
@pytest.mark.asyncio
class TestCoinGeckoProviderClose:
    """Tests for CoinGeckoProvider.close."""

    async def test_close_with_open_client(self):
        provider = CoinGeckoProvider()
        mock_client = AsyncMock()
        mock_client.is_closed = False
        mock_client.aclose = AsyncMock()
        provider._client = mock_client

        await provider.close()

        mock_client.aclose.assert_called_once()

    async def test_close_with_no_client(self):
        """Should not raise when no client exists."""
        provider = CoinGeckoProvider()
        provider._client = None

        await provider.close()  # Should not raise

    async def test_close_with_already_closed_client(self):
        """Should not call aclose on an already closed client."""
        provider = CoinGeckoProvider()
        mock_client = AsyncMock()
        mock_client.is_closed = True
        provider._client = mock_client

        await provider.close()

        mock_client.aclose.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
class TestCoinGeckoProviderGetClient:
    """Tests for CoinGeckoProvider._get_client lazy initialization."""

    async def test_creates_client_on_first_call(self):
        provider = CoinGeckoProvider()
        assert provider._client is None

        client = await provider._get_client()

        assert client is not None
        assert isinstance(client, httpx.AsyncClient)
        await provider.close()

    async def test_creates_client_with_api_key_header(self):
        provider = CoinGeckoProvider(api_key="test-key")

        client = await provider._get_client()

        assert client.headers.get("x-cg-demo-api-key") == "test-key"
        await provider.close()

    async def test_reuses_existing_client(self):
        provider = CoinGeckoProvider()

        client1 = await provider._get_client()
        client2 = await provider._get_client()

        assert client1 is client2
        await provider.close()

    async def test_recreates_closed_client(self):
        provider = CoinGeckoProvider()

        client1 = await provider._get_client()
        await client1.aclose()

        client2 = await provider._get_client()

        assert client1 is not client2
        assert not client2.is_closed
        await provider.close()
