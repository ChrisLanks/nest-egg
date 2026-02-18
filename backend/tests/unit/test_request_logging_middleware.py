"""Unit tests for request logging middleware."""

import pytest
from unittest.mock import Mock, patch, PropertyMock
from fastapi import Request, Response
from jose import JWTError

from app.middleware.request_logging import (
    UserContextMiddleware,
    RequestLoggingMiddleware,
    AuditLogMiddleware,
)


class MockState:
    """Mock request state that behaves like an object with attributes."""

    def __init__(self):
        self._attrs = {}

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        return self._attrs.get(name)

    def __setattr__(self, name, value):
        if name.startswith("_"):
            super().__setattr__(name, value)
        else:
            self._attrs[name] = value

    def __hasattr__(self, name):
        return name in self._attrs

    def __delattr__(self, name):
        if name in self._attrs:
            del self._attrs[name]


@pytest.mark.unit
class TestUserContextMiddleware:
    """Test user context middleware."""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance."""
        app = Mock()
        return UserContextMiddleware(app)

    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        request = Mock(spec=Request)
        request.headers = {}
        request.state = MockState()
        return request

    @pytest.fixture
    def mock_call_next(self):
        """Create mock call_next that succeeds."""

        async def call_next(request):
            response = Mock(spec=Response)
            response.status_code = 200
            return response

        return call_next

    @pytest.mark.asyncio
    async def test_extracts_email_from_valid_token(
        self, middleware, mock_request, mock_call_next
    ):
        """Should extract email from valid JWT token."""
        mock_request.headers = {"Authorization": "Bearer valid-token"}

        with patch("app.middleware.request_logging.decode_token") as mock_decode:
            mock_decode.return_value = {"email": "test@example.com"}

            await middleware.dispatch(mock_request, mock_call_next)

            assert mock_request.state.user_email == "test@example.com"

    @pytest.mark.asyncio
    async def test_handles_missing_authorization_header(
        self, middleware, mock_request, mock_call_next
    ):
        """Should handle requests without Authorization header."""
        mock_request.headers = {}

        response = await middleware.dispatch(mock_request, mock_call_next)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_handles_invalid_token_format(self, middleware, mock_request, mock_call_next):
        """Should handle Authorization header without Bearer prefix."""
        mock_request.headers = {"Authorization": "InvalidFormat token"}

        response = await middleware.dispatch(mock_request, mock_call_next)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_handles_jwt_decode_error(self, middleware, mock_request, mock_call_next):
        """Should handle JWTError when decoding token."""
        mock_request.headers = {"Authorization": "Bearer invalid-token"}

        with patch("app.middleware.request_logging.decode_token") as mock_decode:
            mock_decode.side_effect = JWTError("Invalid token")

            response = await middleware.dispatch(mock_request, mock_call_next)
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_handles_generic_exception(self, middleware, mock_request, mock_call_next):
        """Should handle generic exceptions when decoding token."""
        mock_request.headers = {"Authorization": "Bearer broken-token"}

        with patch("app.middleware.request_logging.decode_token") as mock_decode:
            mock_decode.side_effect = Exception("Unexpected error")

            response = await middleware.dispatch(mock_request, mock_call_next)
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_handles_token_without_email(self, middleware, mock_request, mock_call_next):
        """Should handle token payload without email field."""
        mock_request.headers = {"Authorization": "Bearer valid-token"}

        with patch("app.middleware.request_logging.decode_token") as mock_decode:
            mock_decode.return_value = {"sub": "user-123"}

            response = await middleware.dispatch(mock_request, mock_call_next)
            assert response.status_code == 200


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
        request.method = "GET"
        request.url = Mock()
        request.url.path = "/api/v1/test"
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.state = MockState()
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
    async def test_generates_request_id(self, middleware, mock_request, mock_call_next):
        """Should generate unique request ID."""
        with patch("app.middleware.request_logging.logger"):
            await middleware.dispatch(mock_request, mock_call_next)
            assert hasattr(mock_request.state, "request_id")

    @pytest.mark.asyncio
    async def test_adds_request_id_to_response_headers(
        self, middleware, mock_request, mock_call_next
    ):
        """Should add X-Request-ID header to response."""
        with patch("app.middleware.request_logging.logger"):
            response = await middleware.dispatch(mock_request, mock_call_next)
            assert "X-Request-ID" in response.headers

    @pytest.mark.asyncio
    async def test_logs_request_start(self, middleware, mock_request, mock_call_next):
        """Should log when request starts."""
        with patch("app.middleware.request_logging.logger") as mock_logger:
            await middleware.dispatch(mock_request, mock_call_next)
            assert mock_logger.info.call_count >= 1
            first_call = mock_logger.info.call_args_list[0][0][0]
            assert "Request started" in first_call

    @pytest.mark.asyncio
    async def test_logs_request_completion(self, middleware, mock_request, mock_call_next):
        """Should log when request completes."""
        with patch("app.middleware.request_logging.logger") as mock_logger:
            await middleware.dispatch(mock_request, mock_call_next)
            assert mock_logger.info.call_count >= 2
            second_call = mock_logger.info.call_args_list[1][0][0]
            assert "Request completed" in second_call

    @pytest.mark.asyncio
    async def test_logs_with_user_email(self, middleware, mock_request, mock_call_next):
        """Should include user email in logs when available."""
        mock_request.state.user_email = "test@example.com"

        with patch("app.middleware.request_logging.logger") as mock_logger:
            with patch("app.middleware.request_logging.redact_email") as mock_redact:
                mock_redact.return_value = "t***@example.com"
                await middleware.dispatch(mock_request, mock_call_next)
                assert mock_redact.called

    @pytest.mark.asyncio
    async def test_logs_without_user_email(self, middleware, mock_request, mock_call_next):
        """Should handle requests without user email."""
        with patch("app.middleware.request_logging.logger"):
            response = await middleware.dispatch(mock_request, mock_call_next)
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_logs_duration(self, middleware, mock_request, mock_call_next):
        """Should log request duration in milliseconds."""
        with patch("app.middleware.request_logging.logger") as mock_logger:
            await middleware.dispatch(mock_request, mock_call_next)
            completion_log = mock_logger.info.call_args_list[1][0][0]
            assert "duration=" in completion_log
            assert "ms" in completion_log

    @pytest.mark.asyncio
    async def test_logs_exceptions(self, middleware, mock_request):
        """Should log exceptions and re-raise them."""

        async def call_next_error(request):
            raise ValueError("Test error")

        with patch("app.middleware.request_logging.logger") as mock_logger:
            with pytest.raises(ValueError):
                await middleware.dispatch(mock_request, call_next_error)

            assert mock_logger.error.called
            error_log = mock_logger.error.call_args[0][0]
            assert "Request failed" in error_log
            assert "ValueError" in error_log

    @pytest.mark.asyncio
    async def test_handles_missing_client(self, middleware, mock_request, mock_call_next):
        """Should handle requests without client info."""
        mock_request.client = None

        with patch("app.middleware.request_logging.logger"):
            response = await middleware.dispatch(mock_request, mock_call_next)
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_redacts_client_ip(self, middleware, mock_request, mock_call_next):
        """Should redact client IP in logs."""
        with patch("app.middleware.request_logging.logger"):
            with patch("app.middleware.request_logging.redact_ip") as mock_redact_ip:
                mock_redact_ip.return_value = "127.0.0.x"
                await middleware.dispatch(mock_request, mock_call_next)
                assert mock_redact_ip.called


@pytest.mark.unit
class TestAuditLogMiddleware:
    """Test audit log middleware."""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance."""
        app = Mock()
        return AuditLogMiddleware(app)

    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        request = Mock(spec=Request)
        request.method = "POST"
        request.url = Mock()
        request.url.path = "/api/v1/test"
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.state = MockState()
        request.state.user_email = "test@example.com"
        request.state.request_id = "req-123"
        return request

    @pytest.fixture
    def mock_call_next(self):
        """Create mock call_next that succeeds."""

        async def call_next(request):
            response = Mock(spec=Response)
            response.status_code = 200
            return response

        return call_next

    @pytest.mark.asyncio
    async def test_skips_non_mutating_get_requests(
        self, middleware, mock_request, mock_call_next
    ):
        """Should skip audit for non-mutating GET requests."""
        mock_request.method = "GET"
        mock_request.url.path = "/api/v1/test"

        with patch("app.middleware.request_logging.logger") as mock_logger:
            await middleware.dispatch(mock_request, mock_call_next)
            assert not mock_logger.info.called

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "path,expected_type",
        [
            ("/api/v1/auth/login", "LOGIN_ATTEMPT"),
            ("/api/v1/auth/register", "REGISTRATION"),
            ("/api/v1/auth/password", "PASSWORD_CHANGE"),
            ("/api/v1/accounts", "ACCOUNT_OPERATION"),
            ("/api/v1/transactions", "TRANSACTION_OPERATION"),
            ("/api/v1/household/members", "HOUSEHOLD_CHANGE"),
        ],
    )
    async def test_audits_sensitive_paths(
        self, middleware, mock_request, mock_call_next, path, expected_type
    ):
        """Should audit specific sensitive paths."""
        mock_request.url.path = path

        with patch("app.middleware.request_logging.logger") as mock_logger:
            with patch("app.middleware.request_logging.redact_email"):
                with patch("app.middleware.request_logging.redact_ip"):
                    await middleware.dispatch(mock_request, mock_call_next)
                    assert mock_logger.info.called
                    log_message = mock_logger.info.call_args[0][0]
                    assert "AUDIT" in log_message
                    assert expected_type in log_message

    @pytest.mark.asyncio
    @pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
    async def test_audits_mutating_api_operations(
        self, middleware, mock_request, mock_call_next, method
    ):
        """Should audit mutating operations on API endpoints."""
        mock_request.method = method
        mock_request.url.path = "/api/v1/budgets"

        with patch("app.middleware.request_logging.logger") as mock_logger:
            with patch("app.middleware.request_logging.redact_email"):
                with patch("app.middleware.request_logging.redact_ip"):
                    await middleware.dispatch(mock_request, mock_call_next)
                    assert mock_logger.info.called
                    log_message = mock_logger.info.call_args[0][0]
                    assert "AUDIT" in log_message

    @pytest.mark.asyncio
    async def test_includes_user_email_in_audit(self, middleware, mock_request, mock_call_next):
        """Should include redacted user email in audit logs."""
        mock_request.url.path = "/api/v1/auth/login"

        with patch("app.middleware.request_logging.logger"):
            with patch("app.middleware.request_logging.redact_email") as mock_redact:
                with patch("app.middleware.request_logging.redact_ip"):
                    mock_redact.return_value = "t***@example.com"
                    await middleware.dispatch(mock_request, mock_call_next)
                    assert mock_redact.called

    @pytest.mark.asyncio
    async def test_includes_client_ip_in_audit(self, middleware, mock_request, mock_call_next):
        """Should include redacted client IP in audit logs."""
        mock_request.url.path = "/api/v1/auth/login"

        with patch("app.middleware.request_logging.logger"):
            with patch("app.middleware.request_logging.redact_email"):
                with patch("app.middleware.request_logging.redact_ip") as mock_redact_ip:
                    mock_redact_ip.return_value = "127.0.0.x"
                    await middleware.dispatch(mock_request, mock_call_next)
                    assert mock_redact_ip.called

    @pytest.mark.asyncio
    async def test_includes_request_id_in_audit(self, middleware, mock_request, mock_call_next):
        """Should include request ID in audit logs."""
        mock_request.url.path = "/api/v1/auth/login"

        with patch("app.middleware.request_logging.logger") as mock_logger:
            with patch("app.middleware.request_logging.redact_email"):
                with patch("app.middleware.request_logging.redact_ip"):
                    await middleware.dispatch(mock_request, mock_call_next)
                    log_message = mock_logger.info.call_args[0][0]
                    assert "request_id=req-123" in log_message

    @pytest.mark.asyncio
    async def test_handles_missing_user_email(self, middleware, mock_request, mock_call_next):
        """Should handle audit logs without user email."""
        mock_request.url.path = "/api/v1/auth/login"
        mock_request.state = MockState()
        mock_request.state.request_id = "req-123"

        with patch("app.middleware.request_logging.logger"):
            with patch("app.middleware.request_logging.redact_email"):
                with patch("app.middleware.request_logging.redact_ip"):
                    response = await middleware.dispatch(mock_request, mock_call_next)
                    assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_handles_missing_client(self, middleware, mock_request, mock_call_next):
        """Should handle audit logs without client info."""
        mock_request.url.path = "/api/v1/auth/login"
        mock_request.client = None

        with patch("app.middleware.request_logging.logger"):
            with patch("app.middleware.request_logging.redact_email"):
                with patch("app.middleware.request_logging.redact_ip"):
                    response = await middleware.dispatch(mock_request, mock_call_next)
                    assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_handles_missing_request_id(self, middleware, mock_request, mock_call_next):
        """Should handle audit logs without request ID."""
        mock_request.url.path = "/api/v1/auth/login"
        mock_request.state = MockState()
        mock_request.state.user_email = "test@example.com"

        with patch("app.middleware.request_logging.logger"):
            with patch("app.middleware.request_logging.redact_email"):
                with patch("app.middleware.request_logging.redact_ip"):
                    response = await middleware.dispatch(mock_request, mock_call_next)
                    assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_skips_non_api_paths(self, middleware, mock_request, mock_call_next):
        """Should not audit non-API paths."""
        mock_request.method = "POST"
        mock_request.url.path = "/health"

        with patch("app.middleware.request_logging.logger") as mock_logger:
            await middleware.dispatch(mock_request, mock_call_next)
            assert not mock_logger.info.called
