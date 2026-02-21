"""Integration tests for market data API endpoints."""

import pytest
from fastapi import status
from unittest.mock import Mock, AsyncMock, patch
from decimal import Decimal
from datetime import date

from app.services.market_data.base_provider import QuoteData, HistoricalPrice, SearchResult


# Module-level fixtures shared across all test classes
@pytest.fixture
def mock_quote():
    """Create mock quote data."""
    return QuoteData(
        symbol="AAPL",
        price=Decimal("150.25"),
        name="Apple Inc.",
        currency="USD",
        exchange="NASDAQ",
    )


@pytest.fixture
def mock_provider(mock_quote):
    """Create mock market data provider."""
    provider = Mock()
    provider.get_quote = AsyncMock(return_value=mock_quote)
    provider.get_quotes_batch = AsyncMock(return_value={})
    provider.get_historical_prices = AsyncMock(return_value=[])
    provider.search_symbol = AsyncMock(return_value=[])
    provider.get_provider_name.return_value = "Yahoo Finance"
    provider.supports_realtime.return_value = True
    provider.get_rate_limits.return_value = {
        "calls_per_minute": 0,
        "calls_per_day": 0,
        "note": "Unlimited",
    }
    return provider


@pytest.mark.asyncio
class TestMarketDataEndpoints:
    """Test suite for market data API endpoints."""

    def test_get_quote_success(self, client, auth_headers, mock_provider):
        """Should successfully fetch quote for valid symbol."""
        with patch("app.api.v1.market_data.get_market_data_provider", return_value=mock_provider):
            response = client.get("/api/v1/market-data/quote/AAPL", headers=auth_headers)

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["symbol"] == "AAPL"
            assert data["provider"] == "Yahoo Finance"

    def test_get_quote_requires_authentication(self, client):
        """Should require authentication."""
        response = client.get("/api/v1/market-data/quote/AAPL")

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_get_quote_rate_limited(self, client, auth_headers, mock_provider):
        """Should enforce rate limiting."""
        # Make 101 requests (over the limit of 100), mock provider to avoid real network calls
        with patch("app.api.v1.market_data.get_market_data_provider", return_value=mock_provider):
            for i in range(101):
                response = client.get("/api/v1/market-data/quote/AAPL", headers=auth_headers)

                if i < 100:
                    assert response.status_code in [
                        status.HTTP_200_OK,
                        status.HTTP_500_INTERNAL_SERVER_ERROR,
                        status.HTTP_404_NOT_FOUND,
                    ]  # May fail for other reasons
                else:
                    # 101st request should be rate limited
                    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
                    data = response.json()
                    assert "Rate limit exceeded" in str(data["detail"])

    def test_get_quotes_batch(self, client, auth_headers, mock_provider):
        """Should fetch multiple quotes in batch."""
        mock_provider.get_quotes_batch = AsyncMock(return_value={
            "AAPL": QuoteData(symbol="AAPL", price=Decimal("150.25")),
            "GOOGL": QuoteData(symbol="GOOGL", price=Decimal("2825.50")),
        })

        with patch("app.api.v1.market_data.get_market_data_provider", return_value=mock_provider):
            response = client.post(
                "/api/v1/market-data/quote/batch", json=["AAPL", "GOOGL"], headers=auth_headers
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "AAPL" in data
            assert "GOOGL" in data

    def test_get_historical_prices(self, client, auth_headers, mock_provider):
        """Should fetch historical price data."""
        mock_provider.get_historical_prices = AsyncMock(return_value=[
            HistoricalPrice(
                date=date(2024, 1, 1),
                open=Decimal("145.0"),
                high=Decimal("148.0"),
                low=Decimal("144.0"),
                close=Decimal("147.0"),
                volume=1000000,
            )
        ])

        with patch("app.api.v1.market_data.get_market_data_provider", return_value=mock_provider):
            response = client.get(
                "/api/v1/market-data/historical/AAPL",
                params={"start_date": "2024-01-01", "end_date": "2024-01-31"},
                headers=auth_headers,
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 1
            assert data[0]["date"] == "2024-01-01"

    def test_search_symbols(self, client, auth_headers, mock_provider):
        """Should search for symbols."""
        mock_provider.search_symbol = AsyncMock(return_value=[
            SearchResult(symbol="AAPL", name="Apple Inc.", type="stock", exchange="NASDAQ")
        ])

        with patch("app.api.v1.market_data.get_market_data_provider", return_value=mock_provider):
            response = client.get(
                "/api/v1/market-data/search", params={"query": "Apple"}, headers=auth_headers
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 1
            assert data[0]["symbol"] == "AAPL"

    def test_get_provider_info(self, client, auth_headers, mock_provider):
        """Should return provider information."""
        with patch("app.api.v1.market_data.get_market_data_provider", return_value=mock_provider):
            response = client.get("/api/v1/market-data/provider-info", headers=auth_headers)

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["name"] == "Yahoo Finance"
            assert data["supports_realtime"] is True

    def test_refresh_holding_price(
        self, client, auth_headers, test_user, test_account, mock_provider
    ):
        """Should refresh price for specific holding - returns 404 if holding not in DB."""
        from uuid import uuid4

        non_existent_id = uuid4()

        with patch("app.api.v1.market_data.get_market_data_provider", return_value=mock_provider):
            response = client.post(
                f"/api/v1/market-data/holdings/{non_existent_id}/refresh-price",
                headers=auth_headers,
            )

            # Holding doesn't exist, so 404 is expected
            assert response.status_code == status.HTTP_404_NOT_FOUND


class TestMarketDataSecurity:
    """Security-focused tests for market data endpoints."""

    def test_sql_injection_protection(self, client, auth_headers):
        """Should protect against SQL injection in symbol parameter."""
        malicious_symbols = [
            "AAPL'; DROP TABLE transactions--",
            "AAPL OR 1=1",
            "AAPL'; DELETE FROM accounts WHERE '1'='1",
        ]

        for symbol in malicious_symbols:
            response = client.get(f"/api/v1/market-data/quote/{symbol}", headers=auth_headers)

            # Should return validation error or not found, not execute SQL
            assert response.status_code in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_404_NOT_FOUND,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ]

    def test_xss_protection(self, client, auth_headers):
        """Should protect against XSS in search query."""
        xss_query = "<script>alert('XSS')</script>"

        response = client.get(
            "/api/v1/market-data/search", params={"query": xss_query}, headers=auth_headers
        )

        # Response should not contain unescaped script tags
        assert b"<script>" not in response.content

    def test_unauthorized_access_blocked(self, client):
        """Should block requests without authentication."""
        endpoints = [
            "/api/v1/market-data/quote/AAPL",
            "/api/v1/market-data/search?query=Apple",
            "/api/v1/market-data/provider-info",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code in [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ]


class TestRateLimitHeaders:
    """Test rate limit response headers."""

    def test_rate_limit_headers_included(self, client, auth_headers, mock_provider):
        """Should include rate limit headers in response."""
        with patch("app.api.v1.market_data.get_market_data_provider", return_value=mock_provider):
            response = client.get("/api/v1/market-data/quote/AAPL", headers=auth_headers)

            # Should include rate limit headers
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers
            assert "X-RateLimit-Reset" in response.headers

    def test_rate_limit_remaining_decrements(self, client, auth_headers, mock_provider):
        """Should decrement remaining count with each request."""
        with patch("app.api.v1.market_data.get_market_data_provider", return_value=mock_provider):
            # First request
            response1 = client.get("/api/v1/market-data/quote/AAPL", headers=auth_headers)
            remaining1 = int(response1.headers["X-RateLimit-Remaining"])

            # Second request
            response2 = client.get("/api/v1/market-data/quote/AAPL", headers=auth_headers)
            remaining2 = int(response2.headers["X-RateLimit-Remaining"])

            # Remaining should decrease
            assert remaining2 < remaining1
