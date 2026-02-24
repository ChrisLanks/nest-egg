"""Tests for Finnhub market data provider."""

import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_finnhub_client():
    """Create a mock Finnhub client."""
    with patch("app.services.market_data.finnhub_provider.finnhub.Client") as mock_cls:
        client = MagicMock()
        mock_cls.return_value = client
        yield client


@pytest.fixture
def provider(mock_finnhub_client, monkeypatch):
    """Create a FinnhubProvider with mocked client."""
    monkeypatch.setattr("app.config.settings.FINNHUB_API_KEY", "test-key")
    from app.services.market_data.finnhub_provider import FinnhubProvider

    p = FinnhubProvider()
    p._client = mock_finnhub_client
    return p


class TestFinnhubProvider:
    """Test suite for Finnhub market data provider."""

    def test_init_requires_api_key(self, monkeypatch):
        """Should raise ValueError if API key not configured."""
        monkeypatch.setattr("app.config.settings.FINNHUB_API_KEY", None)
        from app.services.market_data.finnhub_provider import FinnhubProvider

        with pytest.raises(ValueError, match="FINNHUB_API_KEY"):
            FinnhubProvider()

    @pytest.mark.asyncio
    async def test_get_quote_success(self, provider, mock_finnhub_client):
        """Should return QuoteData from Finnhub quote + profile."""
        mock_finnhub_client.quote.return_value = {
            "c": 185.50,  # current
            "h": 186.00,  # high
            "l": 184.00,  # low
            "o": 184.50,  # open
            "pc": 183.00,  # previous close
            "d": 2.50,  # change
            "dp": 1.37,  # change percent
            "t": 1700000000,
        }
        mock_finnhub_client.company_profile2.return_value = {
            "name": "Apple Inc.",
            "exchange": "NASDAQ",
            "currency": "USD",
            "marketCapitalization": 2850000,  # in millions
            "finnhubIndustry": "Technology",
            "country": "US",
        }

        result = await provider.get_quote("AAPL")

        assert result.symbol == "AAPL"
        assert result.price == Decimal("185.50")
        assert result.name == "Apple Inc."
        assert result.exchange == "NASDAQ"
        assert result.change == Decimal("2.50")
        assert result.change_percent == Decimal("1.37")
        assert result.previous_close == Decimal("183.00")
        assert result.high == Decimal("186.00")
        assert result.low == Decimal("184.00")
        assert result.market_cap == Decimal("2850000000000")  # millions * 1M

    @pytest.mark.asyncio
    async def test_get_quote_no_price_data(self, provider, mock_finnhub_client):
        """Should raise ValueError when no price data."""
        mock_finnhub_client.quote.return_value = {"c": 0, "h": 0, "l": 0, "o": 0}

        with pytest.raises(ValueError, match="No price data"):
            await provider.get_quote("INVALID")

    @pytest.mark.asyncio
    async def test_get_quote_without_profile(self, provider, mock_finnhub_client):
        """Should succeed even if company profile fails."""
        mock_finnhub_client.quote.return_value = {
            "c": 50.0,
            "h": 51.0,
            "l": 49.0,
            "o": 49.5,
            "pc": 49.0,
            "d": 1.0,
            "dp": 2.04,
        }
        mock_finnhub_client.company_profile2.side_effect = Exception("API error")

        result = await provider.get_quote("XYZ")

        assert result.symbol == "XYZ"
        assert result.price == Decimal("50.0")
        assert result.name is None  # Profile failed
        assert result.currency == "USD"  # Default

    @pytest.mark.asyncio
    async def test_get_quote_invalid_symbol(self, provider):
        """Should reject invalid symbols."""
        with pytest.raises(ValueError):
            await provider.get_quote("DROP TABLE")

    @pytest.mark.asyncio
    async def test_get_quotes_batch(self, provider, mock_finnhub_client):
        """Should fetch multiple quotes sequentially."""
        mock_finnhub_client.quote.side_effect = [
            {"c": 185.0, "h": 186.0, "l": 184.0, "o": 184.5, "pc": 183.0, "d": 2.0, "dp": 1.09},
            {"c": 142.0, "h": 143.0, "l": 141.0, "o": 141.5, "pc": 141.0, "d": 1.0, "dp": 0.71},
        ]
        mock_finnhub_client.company_profile2.return_value = {}

        result = await provider.get_quotes_batch(["AAPL", "GOOGL"])

        assert len(result) == 2
        assert "AAPL" in result
        assert "GOOGL" in result
        assert result["AAPL"].price == Decimal("185.0")

    @pytest.mark.asyncio
    async def test_get_quotes_batch_partial_failure(self, provider, mock_finnhub_client):
        """Should return successful quotes even if some fail."""
        mock_finnhub_client.quote.side_effect = [
            {"c": 185.0, "h": 186.0, "l": 184.0, "o": 184.5, "pc": 183.0, "d": 2.0, "dp": 1.09},
            {"c": 0},  # Invalid
        ]
        mock_finnhub_client.company_profile2.return_value = {}

        result = await provider.get_quotes_batch(["AAPL", "INVALID"])

        assert len(result) == 1
        assert "AAPL" in result

    @pytest.mark.asyncio
    async def test_get_historical_prices(self, provider, mock_finnhub_client):
        """Should return historical prices from stock candles."""
        mock_finnhub_client.stock_candles.return_value = {
            "s": "ok",
            "t": [1700000000, 1700086400],
            "o": [184.0, 185.0],
            "h": [186.0, 187.0],
            "l": [183.0, 184.0],
            "c": [185.0, 186.5],
            "v": [50000000, 45000000],
        }

        result = await provider.get_historical_prices(
            "AAPL", date(2023, 11, 1), date(2023, 11, 30)
        )

        assert len(result) == 2
        assert result[0].close == Decimal("185.0")
        assert result[0].volume == 50000000
        assert result[1].close == Decimal("186.5")

    @pytest.mark.asyncio
    async def test_get_historical_prices_no_data(self, provider, mock_finnhub_client):
        """Should raise ValueError when no candle data."""
        mock_finnhub_client.stock_candles.return_value = {"s": "no_data"}

        with pytest.raises(ValueError, match="No historical data"):
            await provider.get_historical_prices(
                "INVALID", date(2023, 1, 1), date(2023, 12, 31)
            )

    @pytest.mark.asyncio
    async def test_search_symbol(self, provider, mock_finnhub_client):
        """Should return search results from symbol lookup."""
        mock_finnhub_client.symbol_lookup.return_value = {
            "count": 2,
            "result": [
                {
                    "symbol": "AAPL",
                    "description": "Apple Inc.",
                    "type": "Common Stock",
                    "displaySymbol": "AAPL",
                },
                {
                    "symbol": "AAPD",
                    "description": "Direxion Daily AAPL Bear 1X Shares",
                    "type": "ETP",
                    "displaySymbol": "AAPD",
                },
            ],
        }

        result = await provider.search_symbol("AAPL")

        assert len(result) == 2
        assert result[0].symbol == "AAPL"
        assert result[0].name == "Apple Inc."
        assert result[0].type == "stock"
        assert result[1].type == "etf"

    @pytest.mark.asyncio
    async def test_search_symbol_empty_results(self, provider, mock_finnhub_client):
        """Should return empty list for no matches."""
        mock_finnhub_client.symbol_lookup.return_value = {"count": 0, "result": []}

        result = await provider.search_symbol("ZZZZZ")

        assert result == []

    @pytest.mark.asyncio
    async def test_search_symbol_api_error(self, provider, mock_finnhub_client):
        """Should return empty list on API error."""
        mock_finnhub_client.symbol_lookup.side_effect = Exception("API error")

        result = await provider.search_symbol("AAPL")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_holding_metadata(self, provider, mock_finnhub_client):
        """Should return holding metadata from company profile."""
        mock_finnhub_client.company_profile2.return_value = {
            "name": "Apple Inc.",
            "finnhubIndustry": "Technology",
            "country": "US",
            "marketCapitalization": 2850000,
        }

        result = await provider.get_holding_metadata("AAPL")

        assert result.symbol == "AAPL"
        assert result.name == "Apple Inc."
        assert result.sector == "Technology"
        assert result.market_cap == "large"
        assert result.asset_class == "domestic"

    @pytest.mark.asyncio
    async def test_get_holding_metadata_international(self, provider, mock_finnhub_client):
        """Should classify non-US stocks as international."""
        mock_finnhub_client.company_profile2.return_value = {
            "name": "Toyota Motor Corp",
            "country": "JP",
            "marketCapitalization": 250000,
        }

        result = await provider.get_holding_metadata("TM")

        assert result.asset_class == "international"
        assert result.market_cap == "large"

    def test_supports_realtime(self, provider):
        """Should support near-real-time data."""
        assert provider.supports_realtime() is True

    def test_get_rate_limits(self, provider):
        """Should report 60 calls per minute."""
        limits = provider.get_rate_limits()
        assert limits["calls_per_minute"] == 60

    def test_get_provider_name(self, provider):
        """Should return Finnhub."""
        assert provider.get_provider_name() == "Finnhub"
