"""Unit tests for Yahoo Finance provider."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
from datetime import date
import asyncio

from app.services.market_data.yahoo_finance_provider import YahooFinanceProvider
from app.services.market_data.base_provider import QuoteData
from app.services.market_data.security import SymbolValidationError


class TestYahooFinanceProvider:
    """Test suite for Yahoo Finance provider."""

    @pytest.fixture
    def provider(self):
        """Create provider instance for testing."""
        return YahooFinanceProvider()

    @pytest.mark.asyncio
    async def test_get_quote_valid_symbol(self, provider):
        """Should fetch quote for valid symbol."""
        # Mock yfinance Ticker
        mock_ticker = Mock()
        mock_ticker.info = {
            'symbol': 'AAPL',
            'currentPrice': 150.25,
            'longName': 'Apple Inc.',
            'currency': 'USD',
            'exchange': 'NASDAQ',
            'volume': 50000000,
            'marketCap': 2500000000000,
            'regularMarketChange': 2.50,
            'regularMarketChangePercent': 1.69,
            'previousClose': 147.75,
            'open': 148.00,
            'dayHigh': 151.00,
            'dayLow': 147.50,
            'fiftyTwoWeekHigh': 180.00,
            'fiftyTwoWeekLow': 120.00,
            'dividendYield': 0.005,
            'trailingPE': 25.5,
        }

        with patch('app.services.market_data.yahoo_finance_provider.yf.Ticker', return_value=mock_ticker):
            quote = await provider.get_quote("AAPL")

            assert quote.symbol == "AAPL"
            assert quote.price == Decimal("150.25")
            assert quote.name == "Apple Inc."
            assert quote.currency == "USD"

    @pytest.mark.asyncio
    async def test_get_quote_invalid_symbol_raises_error(self, provider):
        """Should raise ValueError for invalid symbol."""
        with pytest.raises(ValueError, match="Invalid symbol format"):
            await provider.get_quote("INVALID@#$")

    @pytest.mark.asyncio
    async def test_get_quote_with_timeout(self, provider):
        """Should timeout after configured timeout period."""
        # Mock a slow ticker that takes longer than timeout
        async def slow_ticker(*args, **kwargs):
            await asyncio.sleep(10)  # Sleep longer than 5 second timeout
            return Mock()

        with patch('app.services.market_data.yahoo_finance_provider.asyncio.to_thread', side_effect=slow_ticker):
            with pytest.raises(ValueError, match="timeout"):
                await provider.get_quote("AAPL")

    @pytest.mark.asyncio
    async def test_get_quote_no_price_data(self, provider):
        """Should raise error when no price data available."""
        mock_ticker = Mock()
        mock_ticker.info = {'symbol': 'AAPL'}  # No price data
        mock_ticker.history.return_value = MagicMock()
        mock_ticker.history.return_value.empty = True

        with patch('app.services.market_data.yahoo_finance_provider.yf.Ticker', return_value=mock_ticker):
            with pytest.raises(ValueError, match="No price data available"):
                await provider.get_quote("AAPL")

    @pytest.mark.asyncio
    async def test_get_quote_validates_response(self, provider):
        """Should validate response data before returning."""
        mock_ticker = Mock()
        mock_ticker.info = {
            'symbol': 'AAPL',
            'currentPrice': -100,  # Invalid negative price
        }

        with patch('app.services.market_data.yahoo_finance_provider.yf.Ticker', return_value=mock_ticker):
            with pytest.raises(ValueError):
                await provider.get_quote("AAPL")

    @pytest.mark.asyncio
    async def test_get_quotes_batch(self, provider):
        """Should fetch multiple quotes efficiently."""
        import pandas as pd

        # Mock batch download response
        mock_data = {
            'AAPL': pd.DataFrame({
                'Open': [148.0],
                'High': [151.0],
                'Low': [147.5],
                'Close': [150.25],
                'Volume': [50000000]
            }),
            'GOOGL': pd.DataFrame({
                'Open': [2800.0],
                'High': [2850.0],
                'Low': [2790.0],
                'Close': [2825.50],
                'Volume': [1000000]
            })
        }

        # Create a mock that simulates yf.download structure
        mock_download = MagicMock()
        mock_download.__getitem__ = lambda self, key: mock_data[key]

        with patch('app.services.market_data.yahoo_finance_provider.yf.download', return_value=mock_download):
            quotes = await provider.get_quotes_batch(["AAPL", "GOOGL"])

            assert "AAPL" in quotes
            assert "GOOGL" in quotes
            assert quotes["AAPL"].symbol == "AAPL"
            assert quotes["GOOGL"].symbol == "GOOGL"

    @pytest.mark.asyncio
    async def test_get_quotes_batch_falls_back_on_error(self, provider):
        """Should fall back to individual fetches if batch fails."""
        # Mock batch download to fail
        with patch('app.services.market_data.yahoo_finance_provider.yf.download', side_effect=Exception("Batch failed")):
            # Mock individual get_quote to succeed
            mock_quote = QuoteData(
                symbol="AAPL",
                price=Decimal("150.25")
            )

            with patch.object(provider, 'get_quote', return_value=mock_quote):
                quotes = await provider.get_quotes_batch(["AAPL"])

                assert "AAPL" in quotes
                assert quotes["AAPL"].symbol == "AAPL"

    @pytest.mark.asyncio
    async def test_get_historical_prices(self, provider):
        """Should fetch historical price data."""
        import pandas as pd

        mock_ticker = Mock()
        mock_ticker.history.return_value = pd.DataFrame({
            'Open': [145.0, 146.0, 147.0],
            'High': [148.0, 149.0, 150.0],
            'Low': [144.0, 145.0, 146.0],
            'Close': [147.0, 148.0, 149.0],
            'Volume': [1000000, 1100000, 1200000]
        }, index=pd.date_range('2024-01-01', periods=3))

        with patch('app.services.market_data.yahoo_finance_provider.yf.Ticker', return_value=mock_ticker):
            prices = await provider.get_historical_prices(
                "AAPL",
                date(2024, 1, 1),
                date(2024, 1, 3)
            )

            assert len(prices) == 3
            assert prices[0].close == Decimal("147.0")
            assert prices[1].close == Decimal("148.0")
            assert prices[2].close == Decimal("149.0")

    @pytest.mark.asyncio
    async def test_search_symbol(self, provider):
        """Should search for symbol by query."""
        mock_ticker = Mock()
        mock_ticker.info = {
            'symbol': 'AAPL',
            'longName': 'Apple Inc.',
            'quoteType': 'EQUITY',
            'exchange': 'NASDAQ',
            'currency': 'USD'
        }

        with patch('app.services.market_data.yahoo_finance_provider.yf.Ticker', return_value=mock_ticker):
            results = await provider.search_symbol("AAPL")

            assert len(results) == 1
            assert results[0].symbol == "AAPL"
            assert results[0].name == "Apple Inc."
            assert results[0].type == "equity"

    def test_supports_realtime(self, provider):
        """Should indicate real-time support."""
        assert provider.supports_realtime() is True

    def test_get_rate_limits(self, provider):
        """Should return rate limit info."""
        limits = provider.get_rate_limits()

        assert 'calls_per_minute' in limits
        assert 'calls_per_day' in limits
        assert limits['calls_per_minute'] == 0  # Unlimited (soft limit)

    def test_get_provider_name(self, provider):
        """Should return provider name."""
        assert provider.get_provider_name() == "Yahoo Finance"


class TestYahooFinanceProviderSecurity:
    """Security-focused tests for Yahoo Finance provider."""

    @pytest.fixture
    def provider(self):
        return YahooFinanceProvider()

    @pytest.mark.asyncio
    async def test_validates_symbol_before_api_call(self, provider):
        """Should validate symbol format before making API call."""
        # Mock yf.Ticker to ensure it's never called
        with patch('app.services.market_data.yahoo_finance_provider.yf.Ticker') as mock_ticker:
            with pytest.raises(ValueError):
                await provider.get_quote("../../../etc/passwd")

            # Ticker should never be called with invalid symbol
            mock_ticker.assert_not_called()

    @pytest.mark.asyncio
    async def test_symbol_length_validation(self, provider):
        """Should reject symbols that are too long."""
        with pytest.raises(ValueError, match="Symbol too long"):
            await provider.get_quote("A" * 20)  # 20 characters

    @pytest.mark.asyncio
    async def test_symbol_pattern_validation(self, provider):
        """Should only allow alphanumeric, dots, and hyphens."""
        invalid_symbols = [
            "AAPL;DROP TABLE",
            "AAPL<script>",
            "AAPL&cmd",
            "AAPL|ls",
            "AAPL`whoami`",
        ]

        for invalid in invalid_symbols:
            with pytest.raises(ValueError):
                await provider.get_quote(invalid)

    @pytest.mark.asyncio
    async def test_uppercase_normalization(self, provider):
        """Should normalize symbols to uppercase."""
        mock_ticker = Mock()
        mock_ticker.info = {
            'symbol': 'AAPL',
            'currentPrice': 150.25,
        }

        with patch('app.services.market_data.yahoo_finance_provider.yf.Ticker', return_value=mock_ticker):
            quote = await provider.get_quote("aapl")  # lowercase

            assert quote.symbol == "AAPL"  # Should be uppercase


class TestYahooFinanceProviderLogging:
    """Test logging functionality."""

    @pytest.fixture
    def provider(self):
        return YahooFinanceProvider()

    @pytest.mark.asyncio
    async def test_logs_api_call(self, provider, caplog):
        """Should log external API calls."""
        import logging
        caplog.set_level(logging.INFO)

        mock_ticker = Mock()
        mock_ticker.info = {
            'symbol': 'AAPL',
            'currentPrice': 150.25,
        }

        with patch('app.services.market_data.yahoo_finance_provider.yf.Ticker', return_value=mock_ticker):
            await provider.get_quote("AAPL")

            # Should have logged the API call
            assert "external_api_call" in caplog.text
            assert "yahoo_finance" in caplog.text
            assert "AAPL" in caplog.text

    @pytest.mark.asyncio
    async def test_logs_success_with_timing(self, provider, caplog):
        """Should log successful API calls with duration."""
        import logging
        caplog.set_level(logging.INFO)

        mock_ticker = Mock()
        mock_ticker.info = {
            'symbol': 'AAPL',
            'currentPrice': 150.25,
        }

        with patch('app.services.market_data.yahoo_finance_provider.yf.Ticker', return_value=mock_ticker):
            await provider.get_quote("AAPL")

            # Should log success with duration
            assert "external_api_success" in caplog.text
            assert "duration_ms" in caplog.text

    @pytest.mark.asyncio
    async def test_logs_failure(self, provider, caplog):
        """Should log failed API calls."""
        import logging
        caplog.set_level(logging.ERROR)

        with patch('app.services.market_data.yahoo_finance_provider.yf.Ticker', side_effect=Exception("Network error")):
            with pytest.raises(ValueError):
                await provider.get_quote("AAPL")

            # Should log failure
            assert "external_api_failure" in caplog.text
            assert "Network error" in caplog.text
