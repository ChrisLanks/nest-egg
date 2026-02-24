"""Unit tests for logging middleware."""

import pytest
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import Request, Response
from starlette.datastructures import Headers

from app.middleware.logging_middleware import RequestLoggingMiddleware, log_request


@pytest.mark.unit
class TestRequestLoggingMiddleware:
    """Test request logging middleware."""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance."""
        app = Mock()
        return RequestLoggingMiddleware(app)

    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        request = Mock(spec=Request)
        request.url = Mock()
        request.url.path = "/api/test"
        request.method = "GET"
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.headers = Headers({})
        request.state = Mock()
        return request

    @pytest.fixture
    def mock_call_next(self):
        """Create mock call_next."""
        async def call_next(request):
            response = Mock(spec=Response)
            response.status_code = 200
            return response

        return call_next

    @pytest.mark.asyncio
    async def test_skips_health_check_endpoints(self, middleware, mock_request, mock_call_next):
        """Should skip logging for health check endpoints."""
        mock_request.url.path = "/health"

        with patch("app.middleware.logging_middleware.logger") as mock_logger:
            await middleware.dispatch(mock_request, mock_call_next)
            # Should not log anything
            assert not mock_logger.info.called
            assert not mock_logger.warning.called
            assert not mock_logger.error.called

    @pytest.mark.asyncio
    async def test_skips_api_health_endpoint(self, middleware, mock_request, mock_call_next):
        """Should skip logging for /api/health endpoint."""
        mock_request.url.path = "/api/health"

        with patch("app.middleware.logging_middleware.logger") as mock_logger:
            await middleware.dispatch(mock_request, mock_call_next)
            # Should not log anything
            assert not mock_logger.info.called

    @pytest.mark.asyncio
    async def test_logs_successful_request(self, middleware, mock_request, mock_call_next):
        """Should log successful request at info level."""
        with patch("app.middleware.logging_middleware.logger") as mock_logger:
            await middleware.dispatch(mock_request, mock_call_next)

            # Should log at info level
            assert mock_logger.info.called
            log_message = mock_logger.info.call_args[0][0]
            assert "GET" in log_message
            assert "/api/test" in log_message
            assert "200" in log_message

    @pytest.mark.asyncio
    async def test_logs_request_with_authenticated_user(self, middleware, mock_request, mock_call_next):
        """Should include user ID in logs for authenticated requests."""
        # Add user to request state
        mock_user = Mock()
        mock_user.id = "test-user-id"
        mock_request.state.user = mock_user

        with patch("app.middleware.logging_middleware.logger") as mock_logger:
            await middleware.dispatch(mock_request, mock_call_next)

            log_message = mock_logger.info.call_args[0][0]
            assert "test-user-id" in log_message

    @pytest.mark.asyncio
    async def test_logs_request_without_user(self, middleware, mock_request, mock_call_next):
        """Should handle requests without authenticated user."""
        # No user in request state
        delattr(mock_request.state, "user")

        with patch("app.middleware.logging_middleware.logger") as mock_logger:
            await middleware.dispatch(mock_request, mock_call_next)

            assert mock_logger.info.called

    @pytest.mark.asyncio
    async def test_extracts_client_ip_from_x_forwarded_for(self, middleware, mock_request, mock_call_next):
        """Should extract client IP from X-Forwarded-For header."""
        mock_request.headers = Headers({"X-Forwarded-For": "192.168.1.1, 10.0.0.1"})

        with patch("app.middleware.logging_middleware.logger") as mock_logger:
            await middleware.dispatch(mock_request, mock_call_next)

            log_message = mock_logger.info.call_args[0][0]
            # Rightmost XFF IP is used (trusted proxy), not leftmost (spoofable)
            assert "10.0.0.1" in log_message

    @pytest.mark.asyncio
    async def test_handles_missing_client(self, middleware, mock_request, mock_call_next):
        """Should handle request without client info."""
        mock_request.client = None

        with patch("app.middleware.logging_middleware.logger") as mock_logger:
            await middleware.dispatch(mock_request, mock_call_next)

            log_message = mock_logger.info.call_args[0][0]
            assert "unknown" in log_message

    @pytest.mark.asyncio
    async def test_logs_4xx_errors_as_warning(self, middleware, mock_request):
        """Should log 4xx errors at warning level."""
        async def call_next_400(request):
            response = Mock(spec=Response)
            response.status_code = 404
            return response

        with patch("app.middleware.logging_middleware.logger") as mock_logger:
            await middleware.dispatch(mock_request, call_next_400)

            # Should log at warning level
            assert mock_logger.warning.called
            log_message = mock_logger.warning.call_args[0][0]
            assert "Client error" in log_message
            assert "404" in log_message

    @pytest.mark.asyncio
    async def test_logs_5xx_errors_as_error(self, middleware, mock_request):
        """Should log 5xx errors at error level."""
        async def call_next_500(request):
            response = Mock(spec=Response)
            response.status_code = 500
            return response

        with patch("app.middleware.logging_middleware.logger") as mock_logger:
            await middleware.dispatch(mock_request, call_next_500)

            # Should log at error level
            assert mock_logger.error.called
            log_message = mock_logger.error.call_args[0][0]
            assert "Request failed" in log_message
            assert "500" in log_message

    @pytest.mark.asyncio
    async def test_logs_slow_requests_as_warning(self, middleware, mock_request):
        """Should log slow requests (>1000ms) at warning level."""
        async def call_next_slow(request):
            # Simulate slow request
            await asyncio.sleep(1.1)
            response = Mock(spec=Response)
            response.status_code = 200
            return response

        import asyncio

        with patch("app.middleware.logging_middleware.logger") as mock_logger:
            await middleware.dispatch(mock_request, call_next_slow)

            # Should log at warning level for slow request
            assert mock_logger.warning.called
            log_message = mock_logger.warning.call_args[0][0]
            assert "Slow request" in log_message

    @pytest.mark.asyncio
    async def test_logs_exceptions_and_reraises(self, middleware, mock_request):
        """Should log exceptions and re-raise them."""
        async def call_next_exception(request):
            raise ValueError("Test exception")

        with patch("app.middleware.logging_middleware.logger") as mock_logger:
            with pytest.raises(ValueError, match="Test exception"):
                await middleware.dispatch(mock_request, call_next_exception)

            # Should log exception
            assert mock_logger.exception.called
            log_message = mock_logger.exception.call_args[0][0]
            assert "Request exception" in log_message
            assert "GET" in log_message
            assert "/api/test" in log_message

    @pytest.mark.asyncio
    async def test_includes_duration_in_logs(self, middleware, mock_request, mock_call_next):
        """Should include request duration in logs."""
        with patch("app.middleware.logging_middleware.logger") as mock_logger:
            with patch("time.time", side_effect=[100.0, 100.5]):  # 500ms duration
                await middleware.dispatch(mock_request, mock_call_next)

            log_message = mock_logger.info.call_args[0][0]
            assert "duration_ms" in log_message
            assert "500" in log_message


@pytest.mark.unit
class TestLegacyLogRequest:
    """Test legacy log_request function."""

    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        request = Mock(spec=Request)
        request.url = Mock()
        request.url.path = "/api/legacy"
        request.method = "POST"
        return request

    @pytest.fixture
    def mock_call_next(self):
        """Create mock call_next."""
        async def call_next(request):
            response = Mock(spec=Response)
            response.status_code = 201
            return response

        return call_next

    @pytest.mark.asyncio
    async def test_logs_successful_request(self, mock_request, mock_call_next):
        """Should log successful request."""
        with patch("app.middleware.logging_middleware.logger") as mock_logger:
            await log_request(mock_request, mock_call_next)

            assert mock_logger.info.called
            log_message = mock_logger.info.call_args[0][0]
            assert "POST" in log_message
            assert "/api/legacy" in log_message
            assert "201" in log_message
            assert "completed" in log_message

    @pytest.mark.asyncio
    async def test_logs_exceptions(self, mock_request):
        """Should log exceptions."""
        async def call_next_exception(request):
            raise RuntimeError("Legacy exception")

        with patch("app.middleware.logging_middleware.logger") as mock_logger:
            with pytest.raises(RuntimeError, match="Legacy exception"):
                await log_request(mock_request, call_next_exception)

            assert mock_logger.exception.called
            log_message = mock_logger.exception.call_args[0][0]
            assert "POST" in log_message
            assert "/api/legacy" in log_message
            assert "failed" in log_message

    @pytest.mark.asyncio
    async def test_includes_duration(self, mock_request, mock_call_next):
        """Should include duration in logs."""
        with patch("app.middleware.logging_middleware.logger") as mock_logger:
            with patch("time.time", side_effect=[200.0, 200.25]):  # 250ms duration
                await log_request(mock_request, mock_call_next)

            log_message = mock_logger.info.call_args[0][0]
            assert "250" in log_message or "250.0" in log_message
            assert "ms" in log_message
