"""Tests for the /health endpoint."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest


class TestHealthEndpoint:
    """Verify health check returns real dependency status."""

    @pytest.mark.asyncio
    async def test_health_returns_200_with_database_ok(self, async_client):
        """Health endpoint should return 200 when DB is reachable."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()

        @asynccontextmanager
        async def mock_session_factory():
            yield mock_session

        with patch(
            "app.core.database.AsyncSessionLocal",
            mock_session_factory,
        ):
            response = await async_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["checks"]["database"] == "ok"

    @pytest.mark.asyncio
    async def test_health_is_unauthenticated(self, async_client):
        """Health endpoint should not require authentication."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()

        @asynccontextmanager
        async def mock_session_factory():
            yield mock_session

        with patch(
            "app.core.database.AsyncSessionLocal",
            mock_session_factory,
        ):
            response = await async_client.get("/health")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_returns_503_when_db_unreachable(self, async_client):
        """Health endpoint should return 503 when DB is unreachable."""

        @asynccontextmanager
        async def mock_session_factory():
            raise ConnectionError("DB unreachable")
            yield  # noqa: unreachable

        with patch(
            "app.core.database.AsyncSessionLocal",
            mock_session_factory,
        ):
            response = await async_client.get("/health")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["checks"]["database"] == "unreachable"
