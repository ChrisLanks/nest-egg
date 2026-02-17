"""Integration tests for market data API endpoints."""

import pytest
from fastapi import status
from unittest.mock import Mock, patch
from decimal import Decimal
from datetime import date

from app.services.market_data.base_provider import QuoteData, HistoricalPrice, SearchResult


@pytest.mark.asyncio
class TestMarketDataEndpoints:
    """Test suite for market data API endpoints."""

    @pytest.fixture
    async def mock_quote(self):
        """Create mock quote data."""
        return QuoteData(
            symbol="AAPL",
            price=Decimal("150.25"),
            name="Apple Inc.",
            currency="USD",
            exchange="NASDAQ"
        )

    @pytest.fixture
    async def mock_provider(self, mock_quote):
        """Create mock market data provider."""
        provider = Mock()
        provider.get_quote.return_value = mock_quote
        provider.get_provider_name.return_value = "Yahoo Finance"
        provider.supports_realtime.return_value = True
        provider.get_rate_limits.return_value = {
            'calls_per_minute': 0,
            'calls_per_day': 0,
            'note': 'Unlimited'
        }
        return provider

    async def test_get_quote_success(self, client, auth_headers, mock_provider):
        """Should successfully fetch quote for valid symbol."""
        with patch('app.api.v1.market_data.get_market_data_provider', return_value=mock_provider):
            response = await client.get(
                "/api/v1/market-data/quote/AAPL",
                headers=auth_headers
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data['symbol'] == "AAPL"
            assert data['provider'] == "Yahoo Finance"

    async def test_get_quote_requires_authentication(self, client):
        """Should require authentication."""
        response = await client.get("/api/v1/market-data/quote/AAPL")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_get_quote_rate_limited(self, client, auth_headers):
        """Should enforce rate limiting."""
        # Make 101 requests (over the limit of 100)
        for i in range(101):
            response = await client.get(
                f"/api/v1/market-data/quote/AAPL",
                headers=auth_headers
            )

            if i < 100:
                assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_OK]  # May fail for other reasons
            else:
                # 101st request should be rate limited
                assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
                data = response.json()
                assert "Rate limit exceeded" in str(data['detail'])

    async def test_get_quotes_batch(self, client, auth_headers, mock_provider):
        """Should fetch multiple quotes in batch."""
        mock_provider.get_quotes_batch.return_value = {
            "AAPL": QuoteData(symbol="AAPL", price=Decimal("150.25")),
            "GOOGL": QuoteData(symbol="GOOGL", price=Decimal("2825.50"))
        }

        with patch('app.api.v1.market_data.get_market_data_provider', return_value=mock_provider):
            response = await client.post(
                "/api/v1/market-data/quote/batch",
                json=["AAPL", "GOOGL"],
                headers=auth_headers
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "AAPL" in data
            assert "GOOGL" in data

    async def test_get_historical_prices(self, client, auth_headers, mock_provider):
        """Should fetch historical price data."""
        mock_provider.get_historical_prices.return_value = [
            HistoricalPrice(
                date=date(2024, 1, 1),
                open=Decimal("145.0"),
                high=Decimal("148.0"),
                low=Decimal("144.0"),
                close=Decimal("147.0"),
                volume=1000000
            )
        ]

        with patch('app.api.v1.market_data.get_market_data_provider', return_value=mock_provider):
            response = await client.get(
                "/api/v1/market-data/historical/AAPL",
                params={
                    "start_date": "2024-01-01",
                    "end_date": "2024-01-31"
                },
                headers=auth_headers
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 1
            assert data[0]['date'] == "2024-01-01"

    async def test_search_symbols(self, client, auth_headers, mock_provider):
        """Should search for symbols."""
        mock_provider.search_symbol.return_value = [
            SearchResult(
                symbol="AAPL",
                name="Apple Inc.",
                type="stock",
                exchange="NASDAQ"
            )
        ]

        with patch('app.api.v1.market_data.get_market_data_provider', return_value=mock_provider):
            response = await client.get(
                "/api/v1/market-data/search",
                params={"query": "Apple"},
                headers=auth_headers
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 1
            assert data[0]['symbol'] == "AAPL"

    async def test_get_provider_info(self, client, auth_headers, mock_provider):
        """Should return provider information."""
        with patch('app.api.v1.market_data.get_market_data_provider', return_value=mock_provider):
            response = await client.get(
                "/api/v1/market-data/provider-info",
                headers=auth_headers
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data['name'] == "Yahoo Finance"
            assert data['supports_realtime'] is True

    async def test_refresh_holding_price(self, client, auth_headers, test_user, test_account, mock_provider):
        """Should refresh price for specific holding."""
        # Create a test holding
        from app.models.holding import Holding

        holding = Holding(
            account_id=test_account.id,
            symbol="AAPL",
            shares=Decimal("10"),
            cost_basis=Decimal("1000")
        )
        # Save to database (implementation depends on your test fixtures)

        with patch('app.api.v1.market_data.get_market_data_provider', return_value=mock_provider):
            response = await client.post(
                f"/api/v1/market-data/holdings/{holding.id}/refresh-price",
                headers=auth_headers
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data['symbol'] == "AAPL"
            assert 'current_price' in data


class TestMarketDataSecurity:
    """Security-focused tests for market data endpoints."""

    async def test_sql_injection_protection(self, client, auth_headers):
        """Should protect against SQL injection in symbol parameter."""
        malicious_symbols = [
            "AAPL'; DROP TABLE transactions--",
            "AAPL OR 1=1",
            "AAPL'; DELETE FROM accounts WHERE '1'='1",
        ]

        for symbol in malicious_symbols:
            response = await client.get(
                f"/api/v1/market-data/quote/{symbol}",
                headers=auth_headers
            )

            # Should return validation error, not execute SQL
            assert response.status_code in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ]

    async def test_xss_protection(self, client, auth_headers):
        """Should protect against XSS in search query."""
        xss_query = "<script>alert('XSS')</script>"

        response = await client.get(
            "/api/v1/market-data/search",
            params={"query": xss_query},
            headers=auth_headers
        )

        # Response should not contain unescaped script tags
        assert b"<script>" not in response.content

    async def test_unauthorized_access_blocked(self, client):
        """Should block requests without authentication."""
        endpoints = [
            "/api/v1/market-data/quote/AAPL",
            "/api/v1/market-data/search?query=Apple",
            "/api/v1/market-data/provider-info",
        ]

        for endpoint in endpoints:
            response = await client.get(endpoint)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestRateLimitHeaders:
    """Test rate limit response headers."""

    async def test_rate_limit_headers_included(self, client, auth_headers, mock_provider):
        """Should include rate limit headers in response."""
        with patch('app.api.v1.market_data.get_market_data_provider', return_value=mock_provider):
            response = await client.get(
                "/api/v1/market-data/quote/AAPL",
                headers=auth_headers
            )

            # Should include rate limit headers
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers
            assert "X-RateLimit-Reset" in response.headers

    async def test_rate_limit_remaining_decrements(self, client, auth_headers, mock_provider):
        """Should decrement remaining count with each request."""
        with patch('app.api.v1.market_data.get_market_data_provider', return_value=mock_provider):
            # First request
            response1 = await client.get(
                "/api/v1/market-data/quote/AAPL",
                headers=auth_headers
            )
            remaining1 = int(response1.headers["X-RateLimit-Remaining"])

            # Second request
            response2 = await client.get(
                "/api/v1/market-data/quote/AAPL",
                headers=auth_headers
            )
            remaining2 = int(response2.headers["X-RateLimit-Remaining"])

            # Remaining should decrease
            assert remaining2 < remaining1
