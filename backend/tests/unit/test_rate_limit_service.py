"""Unit tests for RateLimitService — rate limiting, IP extraction, fail-open."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
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


def _make_eval_redis(count=1, ttl=55):
    """Build a mock redis client whose eval() returns [count, ttl]."""
    mock_redis = AsyncMock()
    mock_redis.eval = AsyncMock(return_value=[count, ttl])
    return mock_redis


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
    async def test_skips_in_test_environment(self, mock_settings, service):
        mock_settings.ENVIRONMENT = "test"
        request = _make_request()
        # Should not raise — rate limiting is bypassed in test environment
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

        service.redis_client = _make_eval_redis(count=6, ttl=55)

        request = _make_request()
        with pytest.raises(HTTPException) as exc_info:
            await service.check_rate_limit(request, max_requests=5, window_seconds=60)
        assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    @patch("app.services.rate_limit_service.settings")
    async def test_allows_within_limit(self, mock_settings, service):
        mock_settings.ENVIRONMENT = "production"
        mock_settings.REDIS_URL = "redis://localhost:6379"

        service.redis_client = _make_eval_redis(count=3, ttl=58)

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
        mock_redis.eval = AsyncMock(side_effect=ConnectionError("Redis down"))

        service.redis_client = mock_redis

        request = _make_request()
        # Should not raise — fail-open
        await service.check_rate_limit(request, max_requests=5)


class TestIPExtraction:
    @pytest.mark.asyncio
    @patch("app.services.rate_limit_service.settings")
    async def test_uses_direct_client_host(self, mock_settings, service):
        """Should use request.client.host directly, ignoring X-Forwarded-For."""
        mock_settings.ENVIRONMENT = "production"
        mock_settings.REDIS_URL = "redis://localhost:6379"

        mock_redis = _make_eval_redis(count=1, ttl=60)
        service.redis_client = mock_redis

        request = _make_request(xff="spoofed.ip, real.proxy.ip", client_host="trusted.client.ip")
        await service.check_rate_limit(request, max_requests=5)

        # The key should be based on client.host, not X-Forwarded-For
        expected_key = service._get_rate_limit_key("trusted.client.ip", "/api/test")
        actual_calls = mock_redis.eval.call_args_list
        assert len(actual_calls) == 1
        # eval args: script, num_keys, key, limit, window
        assert actual_calls[0][0][2] == expected_key


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
