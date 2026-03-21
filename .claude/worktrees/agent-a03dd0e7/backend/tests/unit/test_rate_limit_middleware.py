"""Unit tests for rate limit middleware.

Tests both the IP-based (Layer 1) and per-user (Layer 2) rate limiting.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import Request, Response

from app.middleware.rate_limit import EXEMPT_PATHS, RateLimitMiddleware


def _make_limiter_mock(*, allowed=True, remaining=50, calls_per_minute=100):
    """Helper to create a mock AsyncRateLimiter."""
    m = Mock()
    m.is_allowed = AsyncMock(return_value=allowed)
    m.get_remaining_calls = AsyncMock(return_value=remaining)
    m.calls_per_minute = calls_per_minute
    return m


@pytest.mark.unit
class TestRateLimitMiddleware:
    """Test rate limit middleware."""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance."""
        app = Mock()
        return RateLimitMiddleware(app)

    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        request = Mock(spec=Request)
        request.url = Mock()
        request.url.path = "/api/v1/test"
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.state = Mock()
        return request

    @pytest.fixture
    def mock_call_next(self):
        """Create mock call_next that succeeds."""

        async def call_next(request):
            response = Mock(spec=Response)
            response.status_code = 200
            response.headers = {}
            return response

        return call_next

    # ── Exempt paths ──────────────────────────────────────────────────────

    @pytest.mark.asyncio
    @pytest.mark.parametrize("exempt_path", EXEMPT_PATHS)
    async def test_skips_exempt_paths(self, middleware, mock_request, mock_call_next, exempt_path):
        """Should skip rate limiting for exempt paths."""
        mock_request.url.path = exempt_path

        with (
            patch("app.middleware.rate_limit.api_limiter") as mock_ip,
            patch("app.middleware.rate_limit.user_api_limiter") as mock_user,
        ):
            response = await middleware.dispatch(mock_request, mock_call_next)
            assert response.status_code == 200
            assert not mock_ip.is_allowed.called
            assert not mock_user.is_allowed.called

    # ── IP-based limiting (Layer 1) ───────────────────────────────────────

    @pytest.mark.asyncio
    async def test_uses_ip_when_unauthenticated(self, middleware, mock_request, mock_call_next):
        """Should use only IP-based rate limit for unauthenticated requests."""
        delattr(mock_request.state, "user_id")

        with (
            patch("app.middleware.rate_limit.api_limiter") as mock_ip,
            patch("app.middleware.rate_limit.user_api_limiter") as mock_user,
        ):
            mock_ip.is_allowed = AsyncMock(return_value=True)
            mock_ip.get_remaining_calls = AsyncMock(return_value=50)
            mock_ip.calls_per_minute = 1000

            await middleware.dispatch(mock_request, mock_call_next)

            mock_ip.is_allowed.assert_called_once_with("ip:127.0.0.1")
            # Per-user limiter should NOT be called for unauthenticated requests
            assert not mock_user.is_allowed.called

    @pytest.mark.asyncio
    async def test_handles_missing_client(self, middleware, mock_request, mock_call_next):
        """Should handle requests without client info."""
        mock_request.client = None
        delattr(mock_request.state, "user_id")

        with (
            patch("app.middleware.rate_limit.api_limiter") as mock_ip,
            patch("app.middleware.rate_limit.user_api_limiter"),
        ):
            mock_ip.is_allowed = AsyncMock(return_value=True)
            mock_ip.get_remaining_calls = AsyncMock(return_value=50)
            mock_ip.calls_per_minute = 1000

            await middleware.dispatch(mock_request, mock_call_next)

            mock_ip.is_allowed.assert_called_once_with("ip:unknown")

    @pytest.mark.asyncio
    async def test_rejects_when_ip_limit_exceeded(self, middleware, mock_request, mock_call_next):
        """Should reject requests when IP-based rate limit is exceeded."""
        delattr(mock_request.state, "user_id")

        with (
            patch("app.middleware.rate_limit.api_limiter") as mock_ip,
            patch("app.middleware.rate_limit.user_api_limiter"),
        ):
            mock_ip.is_allowed = AsyncMock(return_value=False)
            mock_ip.get_remaining_calls = AsyncMock(return_value=0)
            mock_ip.calls_per_minute = 1000

            response = await middleware.dispatch(mock_request, mock_call_next)

            assert response.status_code == 429

    # ── Per-user limiting (Layer 2) ───────────────────────────────────────

    @pytest.mark.asyncio
    async def test_uses_user_id_when_authenticated(self, middleware, mock_request, mock_call_next):
        """Should check both IP and per-user rate limits for authenticated requests."""
        mock_request.state.user_id = "user-123"

        with (
            patch("app.middleware.rate_limit.api_limiter") as mock_ip,
            patch("app.middleware.rate_limit.user_api_limiter") as mock_user,
        ):
            mock_ip.is_allowed = AsyncMock(return_value=True)
            mock_ip.get_remaining_calls = AsyncMock(return_value=900)
            mock_ip.calls_per_minute = 1000

            mock_user.is_allowed = AsyncMock(return_value=True)
            mock_user.get_remaining_calls = AsyncMock(return_value=50)
            mock_user.calls_per_minute = 300

            await middleware.dispatch(mock_request, mock_call_next)

            # IP limiter should always be checked
            mock_ip.is_allowed.assert_called_once_with("ip:127.0.0.1")
            # Per-user limiter should also be checked for authenticated requests
            mock_user.is_allowed.assert_called_once_with("user:user-123")

    @pytest.mark.asyncio
    async def test_rejects_when_user_limit_exceeded(self, middleware, mock_request, mock_call_next):
        """Should reject when per-user rate limit exceeded, even if IP limit is fine."""
        mock_request.state.user_id = "user-123"

        with (
            patch("app.middleware.rate_limit.api_limiter") as mock_ip,
            patch("app.middleware.rate_limit.user_api_limiter") as mock_user,
        ):
            # IP limit is fine
            mock_ip.is_allowed = AsyncMock(return_value=True)
            mock_ip.get_remaining_calls = AsyncMock(return_value=900)
            mock_ip.calls_per_minute = 1000

            # User limit exceeded
            mock_user.is_allowed = AsyncMock(return_value=False)
            mock_user.get_remaining_calls = AsyncMock(return_value=0)
            mock_user.calls_per_minute = 300

            response = await middleware.dispatch(mock_request, mock_call_next)

            assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_ip_limit_checked_before_user_limit(
        self, middleware, mock_request, mock_call_next
    ):
        """IP limit should be checked first; if it fails, user limiter is not invoked."""
        mock_request.state.user_id = "user-123"

        with (
            patch("app.middleware.rate_limit.api_limiter") as mock_ip,
            patch("app.middleware.rate_limit.user_api_limiter") as mock_user,
        ):
            # IP limit exceeded
            mock_ip.is_allowed = AsyncMock(return_value=False)
            mock_ip.get_remaining_calls = AsyncMock(return_value=0)
            mock_ip.calls_per_minute = 1000

            response = await middleware.dispatch(mock_request, mock_call_next)

            assert response.status_code == 429
            # User limiter should NOT be called if IP limit already exceeded
            assert not mock_user.is_allowed.called

    # ── Allows / headers ──────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_allows_request_under_both_limits(self, middleware, mock_request, mock_call_next):
        """Should allow requests under both rate limits."""
        mock_request.state.user_id = "user-123"

        with (
            patch("app.middleware.rate_limit.api_limiter") as mock_ip,
            patch("app.middleware.rate_limit.user_api_limiter") as mock_user,
        ):
            mock_ip.is_allowed = AsyncMock(return_value=True)
            mock_ip.get_remaining_calls = AsyncMock(return_value=900)
            mock_ip.calls_per_minute = 1000

            mock_user.is_allowed = AsyncMock(return_value=True)
            mock_user.get_remaining_calls = AsyncMock(return_value=50)
            mock_user.calls_per_minute = 300

            response = await middleware.dispatch(mock_request, mock_call_next)
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_headers_show_user_limit_when_authenticated(
        self, middleware, mock_request, mock_call_next
    ):
        """Response headers should reflect the more restrictive per-user limit."""
        mock_request.state.user_id = "user-123"

        with (
            patch("app.middleware.rate_limit.api_limiter") as mock_ip,
            patch("app.middleware.rate_limit.user_api_limiter") as mock_user,
        ):
            mock_ip.is_allowed = AsyncMock(return_value=True)
            mock_ip.get_remaining_calls = AsyncMock(return_value=900)
            mock_ip.calls_per_minute = 1000

            mock_user.is_allowed = AsyncMock(return_value=True)
            mock_user.get_remaining_calls = AsyncMock(return_value=42)
            mock_user.calls_per_minute = 300

            response = await middleware.dispatch(mock_request, mock_call_next)

            assert response.headers["X-RateLimit-Limit"] == "300"
            assert response.headers["X-RateLimit-Remaining"] == "42"
            assert response.headers["X-RateLimit-Reset"] == "60"

    @pytest.mark.asyncio
    async def test_headers_show_ip_limit_when_unauthenticated(
        self, middleware, mock_request, mock_call_next
    ):
        """Response headers should reflect the IP-based limit for unauthenticated requests."""
        delattr(mock_request.state, "user_id")

        with (
            patch("app.middleware.rate_limit.api_limiter") as mock_ip,
            patch("app.middleware.rate_limit.user_api_limiter"),
        ):
            mock_ip.is_allowed = AsyncMock(return_value=True)
            mock_ip.get_remaining_calls = AsyncMock(return_value=800)
            mock_ip.calls_per_minute = 1000

            response = await middleware.dispatch(mock_request, mock_call_next)

            assert response.headers["X-RateLimit-Limit"] == "1000"
            assert response.headers["X-RateLimit-Remaining"] == "800"

    # ── Logging ───────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_logs_warning_when_ip_limit_exceeded(
        self, middleware, mock_request, mock_call_next
    ):
        """Should log warning when IP rate limit exceeded."""
        delattr(mock_request.state, "user_id")

        with (
            patch("app.middleware.rate_limit.api_limiter") as mock_ip,
            patch("app.middleware.rate_limit.user_api_limiter"),
            patch("app.middleware.rate_limit.logger") as mock_logger,
        ):
            mock_ip.is_allowed = AsyncMock(return_value=False)
            mock_ip.get_remaining_calls = AsyncMock(return_value=0)
            mock_ip.calls_per_minute = 1000

            response = await middleware.dispatch(mock_request, mock_call_next)

            assert response.status_code == 429
            assert mock_logger.warning.called

    @pytest.mark.asyncio
    async def test_logs_warning_when_user_limit_exceeded(
        self, middleware, mock_request, mock_call_next
    ):
        """Should log warning when per-user rate limit exceeded."""
        mock_request.state.user_id = "user-123"

        with (
            patch("app.middleware.rate_limit.api_limiter") as mock_ip,
            patch("app.middleware.rate_limit.user_api_limiter") as mock_user,
            patch("app.middleware.rate_limit.logger") as mock_logger,
        ):
            mock_ip.is_allowed = AsyncMock(return_value=True)
            mock_ip.get_remaining_calls = AsyncMock(return_value=900)
            mock_ip.calls_per_minute = 1000

            mock_user.is_allowed = AsyncMock(return_value=False)
            mock_user.get_remaining_calls = AsyncMock(return_value=0)
            mock_user.calls_per_minute = 300

            response = await middleware.dispatch(mock_request, mock_call_next)

            assert response.status_code == 429
            assert mock_logger.warning.called

    @pytest.mark.asyncio
    async def test_logs_info_when_approaching_ip_limit(
        self, middleware, mock_request, mock_call_next
    ):
        """Should log info when approaching IP rate limit (< 10 remaining)."""
        delattr(mock_request.state, "user_id")

        with (
            patch("app.middleware.rate_limit.api_limiter") as mock_ip,
            patch("app.middleware.rate_limit.user_api_limiter"),
            patch("app.middleware.rate_limit.logger") as mock_logger,
        ):
            mock_ip.is_allowed = AsyncMock(return_value=True)
            mock_ip.get_remaining_calls = AsyncMock(return_value=5)
            mock_ip.calls_per_minute = 1000

            await middleware.dispatch(mock_request, mock_call_next)
            assert mock_logger.info.called

    @pytest.mark.asyncio
    async def test_logs_info_when_approaching_user_limit(
        self, middleware, mock_request, mock_call_next
    ):
        """Should log info when approaching per-user rate limit (< 10 remaining)."""
        mock_request.state.user_id = "user-123"

        with (
            patch("app.middleware.rate_limit.api_limiter") as mock_ip,
            patch("app.middleware.rate_limit.user_api_limiter") as mock_user,
            patch("app.middleware.rate_limit.logger") as mock_logger,
        ):
            mock_ip.is_allowed = AsyncMock(return_value=True)
            mock_ip.get_remaining_calls = AsyncMock(return_value=900)
            mock_ip.calls_per_minute = 1000

            mock_user.is_allowed = AsyncMock(return_value=True)
            mock_user.get_remaining_calls = AsyncMock(return_value=3)
            mock_user.calls_per_minute = 300

            await middleware.dispatch(mock_request, mock_call_next)
            assert mock_logger.info.called

    @pytest.mark.asyncio
    async def test_does_not_log_when_not_approaching_limit(
        self, middleware, mock_request, mock_call_next
    ):
        """Should not log info when not approaching any rate limit (>= 10 remaining)."""
        mock_request.state.user_id = "user-123"

        with (
            patch("app.middleware.rate_limit.api_limiter") as mock_ip,
            patch("app.middleware.rate_limit.user_api_limiter") as mock_user,
            patch("app.middleware.rate_limit.logger") as mock_logger,
        ):
            mock_ip.is_allowed = AsyncMock(return_value=True)
            mock_ip.get_remaining_calls = AsyncMock(return_value=900)
            mock_ip.calls_per_minute = 1000

            mock_user.is_allowed = AsyncMock(return_value=True)
            mock_user.get_remaining_calls = AsyncMock(return_value=50)
            mock_user.calls_per_minute = 300

            await middleware.dispatch(mock_request, mock_call_next)
            assert not mock_logger.info.called

    # ── Error detail ──────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_ip_error_detail_includes_retry_info(
        self, middleware, mock_request, mock_call_next
    ):
        """Should include retry information in IP rate limit error detail."""
        delattr(mock_request.state, "user_id")

        with (
            patch("app.middleware.rate_limit.api_limiter") as mock_ip,
            patch("app.middleware.rate_limit.user_api_limiter"),
        ):
            mock_ip.is_allowed = AsyncMock(return_value=False)
            mock_ip.get_remaining_calls = AsyncMock(return_value=0)
            mock_ip.calls_per_minute = 1000

            response = await middleware.dispatch(mock_request, mock_call_next)

            assert response.status_code == 429
            import json

            body = json.loads(response.body.decode())
            detail = body["detail"]
            assert detail["retry_after"] == 60
            assert detail["remaining_calls"] == 0
            assert "1000" in detail["message"]

    @pytest.mark.asyncio
    async def test_user_error_detail_includes_retry_info(
        self, middleware, mock_request, mock_call_next
    ):
        """Should include retry information in per-user rate limit error detail."""
        mock_request.state.user_id = "user-123"

        with (
            patch("app.middleware.rate_limit.api_limiter") as mock_ip,
            patch("app.middleware.rate_limit.user_api_limiter") as mock_user,
        ):
            mock_ip.is_allowed = AsyncMock(return_value=True)
            mock_ip.get_remaining_calls = AsyncMock(return_value=900)
            mock_ip.calls_per_minute = 1000

            mock_user.is_allowed = AsyncMock(return_value=False)
            mock_user.get_remaining_calls = AsyncMock(return_value=0)
            mock_user.calls_per_minute = 300

            response = await middleware.dispatch(mock_request, mock_call_next)

            assert response.status_code == 429
            import json

            body = json.loads(response.body.decode())
            detail = body["detail"]
            assert detail["retry_after"] == 60
            assert detail["remaining_calls"] == 0
            assert "300" in detail["message"]
            assert "per user" in detail["message"]

    # ── Graceful degradation ──────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_allows_request_when_limiter_raises(
        self, middleware, mock_request, mock_call_next
    ):
        """Should allow requests through when rate limiter raises unexpected errors."""
        mock_request.state.user_id = "user-123"

        with (
            patch("app.middleware.rate_limit.api_limiter") as mock_ip,
            patch("app.middleware.rate_limit.user_api_limiter"),
            patch("app.middleware.rate_limit.logger"),
        ):
            mock_ip.is_allowed = AsyncMock(side_effect=ConnectionError("Redis down"))

            response = await middleware.dispatch(mock_request, mock_call_next)
            assert response.status_code == 200
