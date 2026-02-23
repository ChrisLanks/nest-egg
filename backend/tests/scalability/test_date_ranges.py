"""Tests for date range validation across endpoints."""

import pytest


class TestDateRangeValidation:
    """Verify date range caps are enforced."""

    @pytest.mark.asyncio
    async def test_49_year_range_accepted(self, authenticated_client):
        """A range within the 18250-day cap (~49.9 years) should be accepted."""
        start = "1976-01-01"
        end = "2025-01-01"
        response = await authenticated_client.get(
            "/api/v1/dashboard/summary",
            params={"start_date": start, "end_date": end},
        )
        # Should not return 400 (may return 200 with empty data)
        assert response.status_code != 400

    @pytest.mark.asyncio
    async def test_51_year_range_rejected(self, authenticated_client):
        """A range exceeding ~50 years should be rejected with 400."""
        start = "1974-01-01"
        end = "2025-02-01"
        response = await authenticated_client.get(
            "/api/v1/dashboard/summary",
            params={"start_date": start, "end_date": end},
        )
        assert response.status_code == 400
        assert "Date range cannot exceed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_start_after_end_rejected(self, authenticated_client):
        """start_date after end_date should be rejected."""
        response = await authenticated_client.get(
            "/api/v1/dashboard/summary",
            params={"start_date": "2025-06-01", "end_date": "2025-01-01"},
        )
        assert response.status_code == 400
        assert "before or equal" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_date_before_1900_rejected(self, authenticated_client):
        """Dates before 1900 should be rejected."""
        response = await authenticated_client.get(
            "/api/v1/dashboard/summary",
            params={"start_date": "1899-12-31", "end_date": "2025-01-01"},
        )
        assert response.status_code == 400
        assert "1900" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_date_after_2100_rejected(self, authenticated_client):
        """Dates after 2100 should be rejected."""
        response = await authenticated_client.get(
            "/api/v1/dashboard/summary",
            params={"start_date": "2025-01-01", "end_date": "2101-01-01"},
        )
        assert response.status_code == 400
        assert "2100" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_dashboard_full_endpoint_validates_dates(self, authenticated_client):
        """The full dashboard endpoint should also validate date ranges."""
        response = await authenticated_client.get(
            "/api/v1/dashboard/",
            params={"start_date": "1974-01-01", "end_date": "2025-02-01"},
        )
        assert response.status_code == 400
