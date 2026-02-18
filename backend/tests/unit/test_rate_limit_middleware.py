"""Unit tests for rate limit middleware."""

import pytest
from unittest.mock import Mock, patch
from fastapi import Request, Response

from app.middleware.rate_limit import RateLimitMiddleware, EXEMPT_PATHS


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

    @pytest.mark.asyncio
    @pytest.mark.parametrize("exempt_path", EXEMPT_PATHS)
    async def test_skips_exempt_paths(self, middleware, mock_request, mock_call_next, exempt_path):
        """Should skip rate limiting for exempt paths."""
        mock_request.url.path = exempt_path

        with patch("app.middleware.rate_limit.api_limiter") as mock_limiter:
            response = await middleware.dispatch(mock_request, mock_call_next)
            assert response.status_code == 200
            # Should not check rate limit for exempt paths
            assert not mock_limiter.is_allowed.called

    @pytest.mark.asyncio
    async def test_uses_user_id_when_authenticated(self, middleware, mock_request, mock_call_next):
        """Should use user ID for authenticated requests."""
        mock_request.state.user_id = "user-123"

        with patch("app.middleware.rate_limit.api_limiter") as mock_limiter:
            mock_limiter.is_allowed.return_value = True
            mock_limiter.get_remaining_calls.return_value = 50

            await middleware.dispatch(mock_request, mock_call_next)

            # Should use user ID in rate limit key
            mock_limiter.is_allowed.assert_called_once_with("user:user-123")

    @pytest.mark.asyncio
    async def test_uses_ip_when_unauthenticated(self, middleware, mock_request, mock_call_next):
        """Should use IP address for unauthenticated requests."""
        # No user_id on request.state
        delattr(mock_request.state, "user_id")

        with patch("app.middleware.rate_limit.api_limiter") as mock_limiter:
            mock_limiter.is_allowed.return_value = True
            mock_limiter.get_remaining_calls.return_value = 50

            await middleware.dispatch(mock_request, mock_call_next)

            # Should use IP address in rate limit key
            mock_limiter.is_allowed.assert_called_once_with("ip:127.0.0.1")

    @pytest.mark.asyncio
    async def test_handles_missing_client(self, middleware, mock_request, mock_call_next):
        """Should handle requests without client info."""
        mock_request.client = None
        delattr(mock_request.state, "user_id")

        with patch("app.middleware.rate_limit.api_limiter") as mock_limiter:
            mock_limiter.is_allowed.return_value = True
            mock_limiter.get_remaining_calls.return_value = 50

            await middleware.dispatch(mock_request, mock_call_next)

            # Should use 'unknown' for missing client
            mock_limiter.is_allowed.assert_called_once_with("ip:unknown")

    @pytest.mark.asyncio
    async def test_allows_request_under_limit(self, middleware, mock_request, mock_call_next):
        """Should allow requests under rate limit."""
        mock_request.state.user_id = "user-123"

        with patch("app.middleware.rate_limit.api_limiter") as mock_limiter:
            mock_limiter.is_allowed.return_value = True
            mock_limiter.get_remaining_calls.return_value = 50
            mock_limiter.calls_per_minute = 100

            response = await middleware.dispatch(mock_request, mock_call_next)
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_rejects_request_over_limit(self, middleware, mock_request, mock_call_next):
        """Should reject requests over rate limit."""
        mock_request.state.user_id = "user-123"

        with patch("app.middleware.rate_limit.api_limiter") as mock_limiter:
            mock_limiter.is_allowed.return_value = False
            mock_limiter.get_remaining_calls.return_value = 0
            mock_limiter.calls_per_minute = 100

            with pytest.raises(Exception) as exc_info:
                await middleware.dispatch(mock_request, mock_call_next)

            # Should raise HTTPException with 429 status
            assert exc_info.value.status_code == 429
            assert "Rate limit exceeded" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_logs_warning_when_limit_exceeded(
        self, middleware, mock_request, mock_call_next
    ):
        """Should log warning when rate limit exceeded."""
        mock_request.state.user_id = "user-123"

        with patch("app.middleware.rate_limit.api_limiter") as mock_limiter:
            mock_limiter.is_allowed.return_value = False
            mock_limiter.get_remaining_calls.return_value = 0
            mock_limiter.calls_per_minute = 100

            with patch("app.middleware.rate_limit.logger") as mock_logger:
                with pytest.raises(Exception):
                    await middleware.dispatch(mock_request, mock_call_next)

                assert mock_logger.warning.called

    @pytest.mark.asyncio
    async def test_logs_info_when_approaching_limit(
        self, middleware, mock_request, mock_call_next
    ):
        """Should log info when approaching rate limit (< 10 remaining)."""
        mock_request.state.user_id = "user-123"

        with patch("app.middleware.rate_limit.api_limiter") as mock_limiter:
            mock_limiter.is_allowed.return_value = True
            mock_limiter.get_remaining_calls.return_value = 5
            mock_limiter.calls_per_minute = 100

            with patch("app.middleware.rate_limit.logger") as mock_logger:
                await middleware.dispatch(mock_request, mock_call_next)
                assert mock_logger.info.called

    @pytest.mark.asyncio
    async def test_does_not_log_when_not_approaching_limit(
        self, middleware, mock_request, mock_call_next
    ):
        """Should not log info when not approaching rate limit (>= 10 remaining)."""
        mock_request.state.user_id = "user-123"

        with patch("app.middleware.rate_limit.api_limiter") as mock_limiter:
            mock_limiter.is_allowed.return_value = True
            mock_limiter.get_remaining_calls.return_value = 50
            mock_limiter.calls_per_minute = 100

            with patch("app.middleware.rate_limit.logger") as mock_logger:
                await middleware.dispatch(mock_request, mock_call_next)
                assert not mock_logger.info.called

    @pytest.mark.asyncio
    async def test_adds_rate_limit_headers(self, middleware, mock_request, mock_call_next):
        """Should add rate limit headers to response."""
        mock_request.state.user_id = "user-123"

        with patch("app.middleware.rate_limit.api_limiter") as mock_limiter:
            mock_limiter.is_allowed.return_value = True
            mock_limiter.get_remaining_calls.return_value = 50
            mock_limiter.calls_per_minute = 100

            response = await middleware.dispatch(mock_request, mock_call_next)

            assert response.headers["X-RateLimit-Limit"] == "100"
            assert response.headers["X-RateLimit-Remaining"] == "50"
            assert response.headers["X-RateLimit-Reset"] == "60"

    @pytest.mark.asyncio
    async def test_error_detail_includes_retry_info(
        self, middleware, mock_request, mock_call_next
    ):
        """Should include retry information in error detail."""
        mock_request.state.user_id = "user-123"

        with patch("app.middleware.rate_limit.api_limiter") as mock_limiter:
            mock_limiter.is_allowed.return_value = False
            mock_limiter.get_remaining_calls.return_value = 0
            mock_limiter.calls_per_minute = 100

            with pytest.raises(Exception) as exc_info:
                await middleware.dispatch(mock_request, mock_call_next)

            detail = exc_info.value.detail
            assert detail["retry_after"] == 60
            assert detail["remaining_calls"] == 0
            assert "100" in detail["message"]
