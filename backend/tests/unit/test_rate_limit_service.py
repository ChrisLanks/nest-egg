"""Unit tests for RateLimitService — rate limiting, IP extraction, fail-open."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.services.rate_limit_service import RateLimitService


@pytest.fixture
def service():
    return RateLimitService()


def _make_request(path="/api/test", xff=None, client_host="1.2.3.4"):
    """Build a minimal mock request."""
    request = MagicMock()
    request.url.path = path
    request.headers = {}
    if xff is not None:
        request.headers["X-Forwarded-For"] = xff
    client = MagicMock()
    client.host = client_host
    request.client = client
    return request


def _make_pipeline_mock(count=1):
    """Build a mock redis pipeline with sync incr/expire and async execute."""
    mock_pipe = MagicMock()
    mock_pipe.incr = MagicMock(return_value=mock_pipe)
    mock_pipe.expire = MagicMock(return_value=mock_pipe)
    mock_pipe.execute = AsyncMock(return_value=[count, True])
    return mock_pipe


class TestRateLimitKeyGeneration:
    def test_deterministic_key(self, service):
        k1 = service._get_rate_limit_key("1.2.3.4", "/api/login")
        k2 = service._get_rate_limit_key("1.2.3.4", "/api/login")
        assert k1 == k2

    def test_different_endpoints_different_keys(self, service):
        k1 = service._get_rate_limit_key("1.2.3.4", "/api/login")
        k2 = service._get_rate_limit_key("1.2.3.4", "/api/register")
        assert k1 != k2

    def test_different_ips_different_keys(self, service):
        k1 = service._get_rate_limit_key("1.2.3.4", "/api/login")
        k2 = service._get_rate_limit_key("5.6.7.8", "/api/login")
        assert k1 != k2


class TestCheckRateLimit:
    @pytest.mark.asyncio
    @patch("app.services.rate_limit_service.settings")
    async def test_skips_in_development(self, mock_settings, service):
        mock_settings.ENVIRONMENT = "development"
        request = _make_request()
        # Should not raise
        await service.check_rate_limit(request, max_requests=1)

    @pytest.mark.asyncio
    @patch("app.services.rate_limit_service.settings")
    async def test_skips_unknown_identifier(self, mock_settings, service):
        mock_settings.ENVIRONMENT = "production"
        request = _make_request(client_host="unknown")
        request.client = None
        request.headers = {}
        await service.check_rate_limit(request, max_requests=1)

    @pytest.mark.asyncio
    @patch("app.services.rate_limit_service.settings")
    async def test_raises_429_when_exceeded(self, mock_settings, service):
        mock_settings.ENVIRONMENT = "production"
        mock_settings.REDIS_URL = "redis://localhost:6379"

        mock_pipe = _make_pipeline_mock(count=6)

        mock_redis = AsyncMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)
        mock_redis.ttl = AsyncMock(return_value=55)

        service.redis_client = mock_redis

        request = _make_request()
        with pytest.raises(HTTPException) as exc_info:
            await service.check_rate_limit(request, max_requests=5, window_seconds=60)
        assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    @patch("app.services.rate_limit_service.settings")
    async def test_allows_within_limit(self, mock_settings, service):
        mock_settings.ENVIRONMENT = "production"
        mock_settings.REDIS_URL = "redis://localhost:6379"

        mock_pipe = _make_pipeline_mock(count=3)

        mock_redis = AsyncMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)

        service.redis_client = mock_redis

        request = _make_request()
        # Should not raise
        await service.check_rate_limit(request, max_requests=5)

    @pytest.mark.asyncio
    @patch("app.services.rate_limit_service.settings")
    async def test_fail_open_on_redis_error(self, mock_settings, service):
        """When Redis is down, requests should be allowed through."""
        mock_settings.ENVIRONMENT = "production"
        mock_settings.REDIS_URL = "redis://localhost:6379"

        mock_redis = AsyncMock()
        mock_redis.pipeline = MagicMock(side_effect=ConnectionError("Redis down"))

        service.redis_client = mock_redis

        request = _make_request()
        # Should not raise — fail-open
        await service.check_rate_limit(request, max_requests=5)


class TestIPExtraction:
    @pytest.mark.asyncio
    @patch("app.services.rate_limit_service.settings")
    async def test_uses_rightmost_xff(self, mock_settings, service):
        """Should use rightmost (last) X-Forwarded-For IP, not leftmost."""
        mock_settings.ENVIRONMENT = "production"
        mock_settings.REDIS_URL = "redis://localhost:6379"

        mock_pipe = _make_pipeline_mock(count=1)

        mock_redis = AsyncMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)

        service.redis_client = mock_redis

        request = _make_request(xff="spoofed.ip, real.proxy.ip")
        await service.check_rate_limit(request, max_requests=5)

        # The key should be based on "real.proxy.ip", not "spoofed.ip"
        expected_key = service._get_rate_limit_key("real.proxy.ip", "/api/test")
        actual_calls = mock_pipe.incr.call_args_list
        assert len(actual_calls) == 1
        assert actual_calls[0][0][0] == expected_key


class TestGetRemainingAttempts:
    @pytest.mark.asyncio
    async def test_full_remaining_when_no_hits(self, service):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        service.redis_client = mock_redis

        remaining = await service.get_remaining_attempts("1.2.3.4", "/api/login", 5)
        assert remaining == 5

    @pytest.mark.asyncio
    async def test_reduced_remaining(self, service):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="3")
        service.redis_client = mock_redis

        remaining = await service.get_remaining_attempts("1.2.3.4", "/api/login", 5)
        assert remaining == 2

    @pytest.mark.asyncio
    async def test_zero_remaining_at_limit(self, service):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="5")
        service.redis_client = mock_redis

        remaining = await service.get_remaining_attempts("1.2.3.4", "/api/login", 5)
        assert remaining == 0
