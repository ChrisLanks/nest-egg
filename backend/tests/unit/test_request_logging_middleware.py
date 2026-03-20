"""Unit tests for request logging middleware."""

from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import Request, Response
from jwt.exceptions import InvalidTokenError as JWTError

from app.middleware.request_logging import (
    AuditLogMiddleware,
    RequestLoggingMiddleware,
    UserContextMiddleware,
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
        request.cookies = {}
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
    async def test_extracts_user_id_from_valid_token(
        self, middleware, mock_request, mock_call_next
    ):
        """Should extract user_id from valid JWT token."""
        mock_request.headers = {"Authorization": "Bearer valid-token"}

        with patch("app.middleware.request_logging.decode_token") as mock_decode:
            mock_decode.return_value = {"sub": "user-123"}

            await middleware.dispatch(mock_request, mock_call_next)

            assert mock_request.state.user_id == "user-123"

    @pytest.mark.asyncio
    async def test_extracts_user_id_from_refresh_cookie(
        self, middleware, mock_request, mock_call_next
    ):
        """Should extract user_id from refresh token cookie when no auth header."""
        mock_request.headers = {}
        mock_request.cookies = {"refresh_token": "refresh-jwt"}

        with patch("app.middleware.request_logging.decode_token") as mock_decode:
            mock_decode.return_value = {"sub": "user-456"}

            await middleware.dispatch(mock_request, mock_call_next)

            assert mock_request.state.user_id == "user-456"

    @pytest.mark.asyncio
    async def test_prefers_auth_header_over_cookie(self, middleware, mock_request, mock_call_next):
        """Should prefer Authorization header over refresh cookie."""
        mock_request.headers = {"Authorization": "Bearer access-jwt"}
        mock_request.cookies = {"refresh_token": "refresh-jwt"}

        with patch("app.middleware.request_logging.decode_token") as mock_decode:
            mock_decode.return_value = {"sub": "user-from-header"}

            await middleware.dispatch(mock_request, mock_call_next)

            # Should have decoded the access token, not the refresh cookie
            mock_decode.assert_called_once_with("access-jwt")
            assert mock_request.state.user_id == "user-from-header"

    @pytest.mark.asyncio
    async def test_handles_missing_authorization_header(
        self, middleware, mock_request, mock_call_next
    ):
        """Should handle requests without Authorization header or cookie."""
        mock_request.headers = {}
        mock_request.cookies = {}

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
    async def test_handles_token_without_sub(self, middleware, mock_request, mock_call_next):
        """Should handle token payload without sub field."""
        mock_request.headers = {"Authorization": "Bearer valid-token"}

        with patch("app.middleware.request_logging.decode_token") as mock_decode:
            mock_decode.return_value = {"type": "access"}

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
        request.headers = {}
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
    async def test_logs_user_id_when_available(self, middleware, mock_request, mock_call_next):
        """Should include user_id in logs when available."""
        mock_request.state.user_id = "abc-123"

        with patch("app.middleware.request_logging.logger") as mock_logger:
            await middleware.dispatch(mock_request, mock_call_next)
            start_log = mock_logger.info.call_args_list[0][0][0]
            assert "user=abc-123" in start_log

    @pytest.mark.asyncio
    async def test_logs_na_when_no_user(self, middleware, mock_request, mock_call_next):
        """Should log user=N/A when no user context."""
        with patch("app.middleware.request_logging.logger") as mock_logger:
            await middleware.dispatch(mock_request, mock_call_next)
            start_log = mock_logger.info.call_args_list[0][0][0]
            assert "user=N/A" in start_log

    @pytest.mark.asyncio
    async def test_no_email_in_logs(self, middleware, mock_request, mock_call_next):
        """Should never include email addresses in logs."""
        mock_request.state.user_id = "user-123"

        with patch("app.middleware.request_logging.logger") as mock_logger:
            await middleware.dispatch(mock_request, mock_call_next)
            for call in mock_logger.info.call_args_list:
                log_msg = call[0][0]
                assert "@" not in log_msg, f"Email address found in log: {log_msg}"

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
        with patch("app.middleware.request_logging.logger") as mock_logger:
            await middleware.dispatch(mock_request, mock_call_next)
            start_log = mock_logger.info.call_args_list[0][0][0]
            # IP should be redacted (last octet replaced)
            assert "127.0.0.***" in start_log


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
        request.state.user_id = "user-123"
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
    async def test_skips_non_mutating_get_requests(self, middleware, mock_request, mock_call_next):
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
            await middleware.dispatch(mock_request, mock_call_next)
            assert mock_logger.info.called
            log_message = mock_logger.info.call_args[0][0]
            assert "AUDIT" in log_message

    @pytest.mark.asyncio
    async def test_includes_user_id_in_audit(self, middleware, mock_request, mock_call_next):
        """Should include user_id in audit logs."""
        mock_request.url.path = "/api/v1/auth/login"
        mock_request.state.user_id = "abc-456"

        with patch("app.middleware.request_logging.logger") as mock_logger:
            await middleware.dispatch(mock_request, mock_call_next)
            log_message = mock_logger.info.call_args[0][0]
            assert "user=abc-456" in log_message

    @pytest.mark.asyncio
    async def test_no_email_in_audit_logs(self, middleware, mock_request, mock_call_next):
        """Should never include email addresses in audit logs."""
        mock_request.url.path = "/api/v1/auth/login"

        with patch("app.middleware.request_logging.logger") as mock_logger:
            await middleware.dispatch(mock_request, mock_call_next)
            log_message = mock_logger.info.call_args[0][0]
            assert "@" not in log_message, f"Email address found in audit log: {log_message}"

    @pytest.mark.asyncio
    async def test_includes_client_ip_in_audit(self, middleware, mock_request, mock_call_next):
        """Should include redacted client IP in audit logs."""
        mock_request.url.path = "/api/v1/auth/login"

        with patch("app.middleware.request_logging.logger") as mock_logger:
            await middleware.dispatch(mock_request, mock_call_next)
            log_message = mock_logger.info.call_args[0][0]
            assert "ip=127.0.0.***" in log_message

    @pytest.mark.asyncio
    async def test_includes_request_id_in_audit(self, middleware, mock_request, mock_call_next):
        """Should include request ID in audit logs."""
        mock_request.url.path = "/api/v1/auth/login"

        with patch("app.middleware.request_logging.logger") as mock_logger:
            await middleware.dispatch(mock_request, mock_call_next)
            log_message = mock_logger.info.call_args[0][0]
            assert "request_id=req-123" in log_message

    @pytest.mark.asyncio
    async def test_handles_missing_user_id(self, middleware, mock_request, mock_call_next):
        """Should show N/A when user_id is not set."""
        mock_request.url.path = "/api/v1/auth/login"
        mock_request.state = MockState()
        mock_request.state.request_id = "req-123"

        with patch("app.middleware.request_logging.logger") as mock_logger:
            response = await middleware.dispatch(mock_request, mock_call_next)
            assert response.status_code == 200
            log_message = mock_logger.info.call_args[0][0]
            assert "user=N/A" in log_message

    @pytest.mark.asyncio
    async def test_handles_missing_client(self, middleware, mock_request, mock_call_next):
        """Should handle audit logs without client info."""
        mock_request.url.path = "/api/v1/auth/login"
        mock_request.client = None

        with patch("app.middleware.request_logging.logger"):
            response = await middleware.dispatch(mock_request, mock_call_next)
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_handles_missing_request_id(self, middleware, mock_request, mock_call_next):
        """Should handle audit logs without request ID."""
        mock_request.url.path = "/api/v1/auth/login"
        mock_request.state = MockState()
        mock_request.state.user_id = "user-123"

        with patch("app.middleware.request_logging.logger"):
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

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "path,expected_type",
        [
            ("/api/v1/auth/logout", "LOGOUT"),
            ("/api/v1/auth/logout-all", "LOGOUT_ALL"),
            ("/api/v1/auth/reset-password", "PASSWORD_RESET"),
            ("/api/v1/auth/forgot-password", "PASSWORD_RESET_REQUEST"),
            ("/api/v1/auth/mfa", "MFA_OPERATION"),
            ("/api/v1/settings/delete", "ACCOUNT_DELETE"),
            ("/api/v1/settings/profile", "PROFILE_UPDATE"),
        ],
    )
    async def test_new_audit_paths_are_covered(
        self, middleware, mock_request, mock_call_next, path, expected_type
    ):
        """All security-sensitive paths added in the hardening pass must be audited."""
        mock_request.url.path = path

        with patch("app.middleware.request_logging.logger") as mock_logger:
            await middleware.dispatch(mock_request, mock_call_next)
            assert mock_logger.info.called, f"No audit log for {path}"
            log_message = mock_logger.info.call_args[0][0]
            assert "AUDIT" in log_message
            assert expected_type in log_message

    @pytest.mark.asyncio
    async def test_audit_log_calls_celery_task(self, middleware, mock_request, mock_call_next):
        """Audit middleware must enqueue persist_audit_log_task via Celery, not asyncio."""
        mock_request.url.path = "/api/v1/auth/login"
        mock_request.state.request_id = "req-abc"
        mock_request.state.user_id = "user-xyz"

        mock_task = MagicMock()

        with (
            patch("app.middleware.request_logging.logger"),
            patch(
                "app.workers.tasks.auth_tasks.persist_audit_log_task",
                mock_task,
            ),
        ):
            await middleware.dispatch(mock_request, mock_call_next)

        mock_task.delay.assert_called_once()
        kwargs = mock_task.delay.call_args.kwargs
        assert kwargs["action"] == "LOGIN_ATTEMPT"
        assert kwargs["path"] == "/api/v1/auth/login"

    @pytest.mark.asyncio
    async def test_audit_log_celery_unavailable_does_not_raise(
        self, middleware, mock_request, mock_call_next
    ):
        """If Celery broker is down, the audit middleware must NOT raise — response unblocked."""
        mock_request.url.path = "/api/v1/auth/login"

        mock_task = MagicMock()
        mock_task.delay.side_effect = Exception("broker unavailable")

        with (
            patch("app.middleware.request_logging.logger") as mock_logger,
            patch(
                "app.workers.tasks.auth_tasks.persist_audit_log_task",
                mock_task,
            ),
        ):
            response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 200
        # Should have logged a WARNING about degraded DB persistence
        warning_calls = [str(c) for c in mock_logger.warning.call_args_list]
        assert any("audit_log" in w for w in warning_calls)
