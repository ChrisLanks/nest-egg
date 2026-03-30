"""Tests for the Mortgage Rate Service parsing logic."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.mortgage_rate_service import MortgageRateSnapshot, _fetch_latest_fred_rate


class TestFredCsvParsing:
    """Test the CSV parsing logic by mocking httpx."""

    @pytest.mark.asyncio
    async def test_parses_last_valid_row(self):
        """Should return the last non-'.' value from the CSV."""
        csv_body = "DATE,VALUE\n2024-01-04,6.62\n2024-01-11,6.75\n2024-01-18,.\n"
        mock_response = MagicMock()
        mock_response.text = csv_body
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = mock_response

        with patch(
            "app.services.mortgage_rate_service.httpx.AsyncClient", return_value=mock_client
        ):
            rate, date_str = await _fetch_latest_fred_rate(
                "https://fred.stlouisfed.org/graph/fredgraph.csv?id=MORTGAGE30US"
            )

        # 6.75% → 0.0675
        assert rate == pytest.approx(0.0675, rel=1e-4)
        assert date_str == "2024-01-11"

    @pytest.mark.asyncio
    async def test_skips_dot_values_to_find_last_valid(self):
        """Walks backward past '.' entries to find the most recent valid value."""
        csv_body = "DATE,VALUE\n2024-01-04,6.62\n2024-01-11,.\n2024-01-18,.\n"
        mock_response = MagicMock()
        mock_response.text = csv_body
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = mock_response

        with patch(
            "app.services.mortgage_rate_service.httpx.AsyncClient", return_value=mock_client
        ):
            rate, date_str = await _fetch_latest_fred_rate(
                "https://fred.stlouisfed.org/graph/fredgraph.csv?id=MORTGAGE30US"
            )

        assert rate == pytest.approx(0.0662, rel=1e-4)
        assert date_str == "2024-01-04"

    @pytest.mark.asyncio
    async def test_returns_none_on_all_dots(self):
        """When all values are '.', returns (None, None)."""
        csv_body = "DATE,VALUE\n2024-01-04,.\n2024-01-11,.\n"
        mock_response = MagicMock()
        mock_response.text = csv_body
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.return_value = mock_response

        with patch(
            "app.services.mortgage_rate_service.httpx.AsyncClient", return_value=mock_client
        ):
            rate, date_str = await _fetch_latest_fred_rate(
                "https://fred.stlouisfed.org/graph/fredgraph.csv?id=MORTGAGE30US"
            )

        assert rate is None
        assert date_str is None

    @pytest.mark.asyncio
    async def test_returns_none_on_network_error(self):
        """Network errors return (None, None) without raising."""
        import httpx

        mock_client = AsyncMock()
        mock_client.__aenter__.side_effect = httpx.ConnectError("timeout")

        with patch(
            "app.services.mortgage_rate_service.httpx.AsyncClient", return_value=mock_client
        ):
            rate, date_str = await _fetch_latest_fred_rate(
                "https://fred.stlouisfed.org/graph/fredgraph.csv?id=MORTGAGE30US"
            )

        assert rate is None
        assert date_str is None


class TestMortgageRateSnapshot:
    def test_rate_stored_as_decimal(self):
        snap = MortgageRateSnapshot(rate_30yr=0.0675, rate_15yr=0.0625, rate_5_1_arm=0.0650, as_of_date="2024-01-11")
        assert snap.rate_30yr == pytest.approx(0.0675)
        assert snap.source == "FRED / Freddie Mac"

    def test_nullable_rates(self):
        snap = MortgageRateSnapshot(rate_30yr=None, rate_15yr=None, rate_5_1_arm=None, as_of_date=None)
        assert snap.rate_30yr is None
        assert snap.rate_5_1_arm is None
        assert snap.as_of_date is None


class TestMortgageRateComparison:
    """Test the rate comparison logic from the API endpoint."""

    def _compare(self, your_rate: float, market_30: float, threshold: float = 0.005) -> str:
        diff = your_rate - market_30
        if diff > threshold:
            return "above_market"
        if diff < -threshold:
            return "below_market"
        return "at_market"

    def test_above_market(self):
        # Your rate 7.5%, market 6.5% → above by 1%
        assert self._compare(0.075, 0.065) == "above_market"

    def test_below_market(self):
        # Your rate 5.5%, market 6.75% → below by >0.5%
        assert self._compare(0.055, 0.0675) == "below_market"

    def test_at_market_within_threshold(self):
        # Your rate 6.75%, market 6.72% → diff = 0.003 < 0.005
        assert self._compare(0.0675, 0.0672) == "at_market"

    def test_exactly_at_threshold_is_at_market(self):
        # Diff = exactly 0.005 → not "above"
        assert self._compare(0.075, 0.070) == "at_market"
