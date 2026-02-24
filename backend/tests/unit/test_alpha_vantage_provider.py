"""Tests for Alpha Vantage market data provider."""

import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_timeseries():
    """Create a mock Alpha Vantage TimeSeries."""
    with patch("app.services.market_data.alpha_vantage_provider.TimeSeries") as mock_cls:
        ts = MagicMock()
        mock_cls.return_value = ts
        yield ts


@pytest.fixture
def provider(mock_timeseries, monkeypatch):
    """Create an AlphaVantageProvider with mocked TimeSeries."""
    monkeypatch.setattr("app.config.settings.ALPHA_VANTAGE_API_KEY", "test-key")
    from app.services.market_data.alpha_vantage_provider import AlphaVantageProvider

    p = AlphaVantageProvider()
    p._ts = mock_timeseries
    return p


class TestAlphaVantageProvider:
    """Test suite for Alpha Vantage market data provider."""

    def test_init_requires_api_key(self, monkeypatch):
        """Should raise ValueError if API key not configured."""
        monkeypatch.setattr("app.config.settings.ALPHA_VANTAGE_API_KEY", None)
        from app.services.market_data.alpha_vantage_provider import AlphaVantageProvider

        with pytest.raises(ValueError, match="ALPHA_VANTAGE_API_KEY"):
            AlphaVantageProvider()

    @pytest.mark.asyncio
    async def test_get_quote_success(self, provider, mock_timeseries):
        """Should return QuoteData from Alpha Vantage Global Quote."""
        mock_timeseries.get_quote_endpoint.return_value = (
            {
                "01. symbol": "AAPL",
                "02. open": "184.50",
                "03. high": "186.00",
                "04. low": "184.00",
                "05. price": "185.50",
                "06. volume": "50000000",
                "07. latest trading day": "2023-11-15",
                "08. previous close": "183.00",
                "09. change": "2.50",
                "10. change percent": "1.3661%",
            },
            None,  # meta_data
        )

        result = await provider.get_quote("AAPL")

        assert result.symbol == "AAPL"
        assert result.price == Decimal("185.50")
        assert result.open == Decimal("184.50")
        assert result.high == Decimal("186.00")
        assert result.low == Decimal("184.00")
        assert result.volume == 50000000
        assert result.previous_close == Decimal("183.00")
        assert result.change == Decimal("2.50")
        assert result.change_percent == Decimal("1.3661")

    @pytest.mark.asyncio
    async def test_get_quote_no_data(self, provider, mock_timeseries):
        """Should raise ValueError when no data returned."""
        mock_timeseries.get_quote_endpoint.return_value = ({}, None)

        with pytest.raises(ValueError, match="No price data"):
            await provider.get_quote("INVALID")

    @pytest.mark.asyncio
    async def test_get_quote_no_price_field(self, provider, mock_timeseries):
        """Should raise ValueError when price field is missing."""
        mock_timeseries.get_quote_endpoint.return_value = (
            {"01. symbol": "XYZ"},
            None,
        )

        with pytest.raises(ValueError, match="No price data"):
            await provider.get_quote("XYZ")

    @pytest.mark.asyncio
    async def test_get_quote_invalid_symbol(self, provider):
        """Should reject invalid symbols."""
        with pytest.raises(ValueError):
            await provider.get_quote("DROP TABLE")

    @pytest.mark.asyncio
    async def test_get_quotes_batch(self, provider, mock_timeseries):
        """Should fetch multiple quotes sequentially."""
        mock_timeseries.get_quote_endpoint.side_effect = [
            (
                {
                    "01. symbol": "AAPL",
                    "05. price": "185.50",
                    "10. change percent": "1.37%",
                },
                None,
            ),
            (
                {
                    "01. symbol": "GOOGL",
                    "05. price": "142.00",
                    "10. change percent": "0.71%",
                },
                None,
            ),
        ]

        result = await provider.get_quotes_batch(["AAPL", "GOOGL"])

        assert len(result) == 2
        assert result["AAPL"].price == Decimal("185.50")
        assert result["GOOGL"].price == Decimal("142.00")

    @pytest.mark.asyncio
    async def test_get_quotes_batch_partial_failure(self, provider, mock_timeseries):
        """Should return successful quotes even if some fail."""
        mock_timeseries.get_quote_endpoint.side_effect = [
            ({"01. symbol": "AAPL", "05. price": "185.50"}, None),
            ({}, None),  # No data for second symbol
        ]

        result = await provider.get_quotes_batch(["AAPL", "INVALID"])

        assert len(result) == 1
        assert "AAPL" in result

    @pytest.mark.asyncio
    async def test_get_historical_prices_daily(self, provider, mock_timeseries):
        """Should return historical prices from daily endpoint."""
        mock_timeseries.get_daily.return_value = (
            {
                "2023-11-15": {
                    "1. open": "184.50",
                    "2. high": "186.00",
                    "3. low": "184.00",
                    "4. close": "185.50",
                    "5. volume": "50000000",
                },
                "2023-11-14": {
                    "1. open": "183.00",
                    "2. high": "184.50",
                    "3. low": "182.50",
                    "4. close": "183.75",
                    "5. volume": "45000000",
                },
                "2023-10-01": {  # Outside date range
                    "1. open": "170.00",
                    "2. high": "171.00",
                    "3. low": "169.00",
                    "4. close": "170.50",
                    "5. volume": "40000000",
                },
            },
            None,
        )

        result = await provider.get_historical_prices(
            "AAPL", date(2023, 11, 1), date(2023, 11, 30)
        )

        # Should only include dates within range
        assert len(result) == 2
        assert result[0].date == date(2023, 11, 14)
        assert result[0].close == Decimal("183.75")
        assert result[1].date == date(2023, 11, 15)
        assert result[1].close == Decimal("185.50")

    @pytest.mark.asyncio
    async def test_get_historical_prices_weekly(self, provider, mock_timeseries):
        """Should use weekly endpoint for 1wk interval."""
        mock_timeseries.get_weekly.return_value = (
            {
                "2023-11-17": {
                    "1. open": "184.50",
                    "2. high": "187.00",
                    "3. low": "183.00",
                    "4. close": "186.00",
                    "5. volume": "250000000",
                },
            },
            None,
        )

        result = await provider.get_historical_prices(
            "AAPL", date(2023, 11, 1), date(2023, 11, 30), interval="1wk"
        )

        assert len(result) == 1
        mock_timeseries.get_weekly.assert_called_once_with("AAPL")

    @pytest.mark.asyncio
    async def test_get_historical_prices_monthly(self, provider, mock_timeseries):
        """Should use monthly endpoint for 1mo interval."""
        mock_timeseries.get_monthly.return_value = (
            {
                "2023-11-30": {
                    "1. open": "184.50",
                    "2. high": "190.00",
                    "3. low": "180.00",
                    "4. close": "189.00",
                    "5. volume": "1000000000",
                },
            },
            None,
        )

        result = await provider.get_historical_prices(
            "AAPL", date(2023, 11, 1), date(2023, 11, 30), interval="1mo"
        )

        assert len(result) == 1
        mock_timeseries.get_monthly.assert_called_once_with("AAPL")

    @pytest.mark.asyncio
    async def test_get_historical_prices_no_data(self, provider, mock_timeseries):
        """Should raise ValueError when no data returned."""
        mock_timeseries.get_daily.return_value = ({}, None)

        with pytest.raises(ValueError, match="No historical data"):
            await provider.get_historical_prices(
                "INVALID", date(2023, 1, 1), date(2023, 12, 31)
            )

    @pytest.mark.asyncio
    async def test_search_symbol(self, provider, mock_timeseries):
        """Should return search results from symbol search."""
        mock_timeseries.get_symbol_search.return_value = (
            [
                {
                    "1. symbol": "AAPL",
                    "2. name": "Apple Inc.",
                    "3. type": "Equity",
                    "4. region": "United States",
                    "8. currency": "USD",
                },
                {
                    "1. symbol": "APLE",
                    "2. name": "Apple Hospitality REIT Inc",
                    "3. type": "ETF",
                    "4. region": "United States",
                    "8. currency": "USD",
                },
            ],
            None,
        )

        result = await provider.search_symbol("apple")

        assert len(result) == 2
        assert result[0].symbol == "AAPL"
        assert result[0].name == "Apple Inc."
        assert result[0].type == "stock"
        assert result[1].type == "etf"
        assert result[0].currency == "USD"

    @pytest.mark.asyncio
    async def test_search_symbol_empty(self, provider, mock_timeseries):
        """Should return empty list for no matches."""
        mock_timeseries.get_symbol_search.return_value = ([], None)

        result = await provider.search_symbol("ZZZZZ")

        assert result == []

    @pytest.mark.asyncio
    async def test_search_symbol_api_error(self, provider, mock_timeseries):
        """Should return empty list on API error."""
        mock_timeseries.get_symbol_search.side_effect = Exception("API error")

        result = await provider.search_symbol("AAPL")

        assert result == []

    def test_supports_realtime(self, provider):
        """Alpha Vantage free tier does not support real-time."""
        assert provider.supports_realtime() is False

    def test_get_rate_limits(self, provider):
        """Should report conservative rate limits."""
        limits = provider.get_rate_limits()
        assert limits["calls_per_minute"] == 5
        assert limits["calls_per_day"] == 25

    def test_get_provider_name(self, provider):
        """Should return Alpha Vantage."""
        assert provider.get_provider_name() == "Alpha Vantage"
