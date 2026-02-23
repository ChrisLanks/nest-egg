"""Tests for the /health endpoint."""

import pytest


class TestHealthEndpoint:
    """Verify health check returns real dependency status."""

    @pytest.mark.asyncio
    async def test_health_returns_200_with_database_ok(self, async_client):
        """Health endpoint should return 200 with database: ok when DB is reachable."""
        response = await async_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["checks"]["database"] == "ok"

    @pytest.mark.asyncio
    async def test_health_is_unauthenticated(self, async_client):
        """Health endpoint should not require authentication."""
        # async_client has no auth headers — should still work
        response = await async_client.get("/health")
        assert response.status_code == 200
