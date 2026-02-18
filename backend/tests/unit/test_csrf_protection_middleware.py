"""Unit tests for CSRF protection middleware."""

import pytest
from unittest.mock import Mock, patch
from fastapi import Request
from starlette.responses import Response

from app.middleware.csrf_protection import CSRFProtectionMiddleware


@pytest.mark.unit
class TestCSRFProtectionMiddleware:
    """Test CSRF protection middleware."""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance."""
        app = Mock()
        return CSRFProtectionMiddleware(app)

    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        request = Mock(spec=Request)
        request.url = Mock()
        request.url.path = "/api/v1/test"
        request.method = "POST"
        request.cookies = {}
        request.headers = {}
        return request

    @pytest.fixture
    def mock_call_next(self):
        """Create mock call_next that succeeds."""

        async def call_next(request):
            response = Mock()
            response.status_code = 200
            response.set_cookie = Mock()
            return response

        return call_next

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "exempt_path",
        [
            "/api/v1/auth/login",
            "/api/v1/plaid/webhook",
            "/api/v1/teller/webhook",
            "/health",
            "/",
            "/docs",
            "/openapi.json",
            "/metrics",
        ],
    )
    async def test_skips_csrf_check_for_exempt_paths(
        self, middleware, mock_request, mock_call_next, exempt_path
    ):
        """Should skip CSRF check for exempt paths."""
        mock_request.url.path = exempt_path
        mock_request.method = "POST"

        response = await middleware.dispatch(mock_request, mock_call_next)
        assert response.status_code == 200

    @pytest.mark.asyncio
    @pytest.mark.parametrize("method", ["GET", "HEAD", "OPTIONS"])
    async def test_skips_csrf_check_for_safe_methods(
        self, middleware, mock_request, mock_call_next, method
    ):
        """Should skip CSRF validation for safe HTTP methods."""
        mock_request.method = method

        response = await middleware.dispatch(mock_request, mock_call_next)
        assert response.status_code == 200

    @pytest.mark.asyncio
    @pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
    async def test_validates_csrf_for_state_changing_methods(
        self, middleware, mock_request, mock_call_next, method
    ):
        """Should validate CSRF token for state-changing methods."""
        mock_request.method = method
        mock_request.cookies = {"csrf_token": "test-token"}
        mock_request.headers = {"X-CSRF-Token": "test-token"}

        response = await middleware.dispatch(mock_request, mock_call_next)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_accepts_matching_tokens(self, middleware, mock_request, mock_call_next):
        """Should accept request when CSRF tokens match."""
        mock_request.method = "POST"
        mock_request.cookies = {"csrf_token": "test-token-123"}
        mock_request.headers = {"X-CSRF-Token": "test-token-123"}

        response = await middleware.dispatch(mock_request, mock_call_next)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_rejects_missing_cookie_in_production(
        self, middleware, mock_request, mock_call_next
    ):
        """Should reject request with missing CSRF cookie in production."""
        mock_request.method = "POST"
        mock_request.cookies = {}
        mock_request.headers = {"X-CSRF-Token": "test-token"}

        with patch("app.middleware.csrf_protection.settings.DEBUG", False):
            response = await middleware.dispatch(mock_request, mock_call_next)
            assert response.status_code == 403
            assert isinstance(response, Response)

    @pytest.mark.asyncio
    async def test_rejects_missing_header_in_production(
        self, middleware, mock_request, mock_call_next
    ):
        """Should reject request with missing CSRF header in production."""
        mock_request.method = "POST"
        mock_request.cookies = {"csrf_token": "test-token"}
        mock_request.headers = {}

        with patch("app.middleware.csrf_protection.settings.DEBUG", False):
            response = await middleware.dispatch(mock_request, mock_call_next)
            assert response.status_code == 403
            assert isinstance(response, Response)

    @pytest.mark.asyncio
    async def test_rejects_mismatched_tokens_in_production(
        self, middleware, mock_request, mock_call_next
    ):
        """Should reject request when CSRF tokens don't match in production."""
        mock_request.method = "POST"
        mock_request.cookies = {"csrf_token": "token-1"}
        mock_request.headers = {"X-CSRF-Token": "token-2"}

        with patch("app.middleware.csrf_protection.settings.DEBUG", False):
            response = await middleware.dispatch(mock_request, mock_call_next)
            assert response.status_code == 403
            assert isinstance(response, Response)

    @pytest.mark.asyncio
    async def test_allows_missing_token_in_debug_mode(
        self, middleware, mock_request, mock_call_next
    ):
        """Should allow request with missing CSRF token in debug mode."""
        mock_request.method = "POST"
        mock_request.cookies = {}
        mock_request.headers = {}

        with patch("app.middleware.csrf_protection.settings.DEBUG", True):
            with patch("app.middleware.csrf_protection.logger"):
                response = await middleware.dispatch(mock_request, mock_call_next)
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_allows_mismatched_token_in_debug_mode(
        self, middleware, mock_request, mock_call_next
    ):
        """Should allow request with mismatched CSRF token in debug mode."""
        mock_request.method = "POST"
        mock_request.cookies = {"csrf_token": "token-1"}
        mock_request.headers = {"X-CSRF-Token": "token-2"}

        with patch("app.middleware.csrf_protection.settings.DEBUG", True):
            with patch("app.middleware.csrf_protection.logger"):
                response = await middleware.dispatch(mock_request, mock_call_next)
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_logs_warning_for_missing_token(
        self, middleware, mock_request, mock_call_next
    ):
        """Should log warning when CSRF token is missing."""
        mock_request.method = "POST"
        mock_request.cookies = {}
        mock_request.headers = {}

        with patch("app.middleware.csrf_protection.settings.DEBUG", True):
            with patch("app.middleware.csrf_protection.logger") as mock_logger:
                await middleware.dispatch(mock_request, mock_call_next)
                assert mock_logger.warning.called

    @pytest.mark.asyncio
    async def test_logs_warning_for_mismatched_token(
        self, middleware, mock_request, mock_call_next
    ):
        """Should log warning when CSRF tokens don't match."""
        mock_request.method = "POST"
        mock_request.cookies = {"csrf_token": "token-1"}
        mock_request.headers = {"X-CSRF-Token": "token-2"}

        with patch("app.middleware.csrf_protection.settings.DEBUG", True):
            with patch("app.middleware.csrf_protection.logger") as mock_logger:
                await middleware.dispatch(mock_request, mock_call_next)
                assert mock_logger.warning.called

    @pytest.mark.asyncio
    async def test_sets_csrf_cookie_on_get_request(
        self, middleware, mock_request, mock_call_next
    ):
        """Should set CSRF cookie on successful GET request."""
        mock_request.method = "GET"
        mock_request.cookies = {}

        with patch("app.middleware.csrf_protection.settings.DEBUG", False):
            with patch("app.middleware.csrf_protection.secrets.token_urlsafe") as mock_token_urlsafe:
                mock_token_urlsafe.return_value = "new-csrf-token"

                response = await middleware.dispatch(mock_request, mock_call_next)

                response.set_cookie.assert_called_once()
                call_kwargs = response.set_cookie.call_args.kwargs
                assert call_kwargs["key"] == "csrf_token"
                assert call_kwargs["value"] == "new-csrf-token"
                assert call_kwargs["httponly"] is False
                assert call_kwargs["secure"] is True
                assert call_kwargs["samesite"] == "lax"
                assert call_kwargs["max_age"] == 86400

    @pytest.mark.asyncio
    async def test_does_not_set_cookie_if_already_present(
        self, middleware, mock_request, mock_call_next
    ):
        """Should not set CSRF cookie if already present."""
        mock_request.method = "GET"
        mock_request.cookies = {"csrf_token": "existing-token"}

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert not response.set_cookie.called

    @pytest.mark.asyncio
    async def test_cookie_secure_flag_in_debug_mode(
        self, middleware, mock_request, mock_call_next
    ):
        """Should set secure=False for CSRF cookie in debug mode."""
        mock_request.method = "GET"
        mock_request.cookies = {}

        with patch("app.middleware.csrf_protection.settings.DEBUG", True):
            with patch("app.middleware.csrf_protection.secrets.token_urlsafe") as mock_token_urlsafe:
                mock_token_urlsafe.return_value = "new-csrf-token"

                response = await middleware.dispatch(mock_request, mock_call_next)

                call_kwargs = response.set_cookie.call_args.kwargs
                assert call_kwargs["secure"] is False

    @pytest.mark.asyncio
    async def test_does_not_set_cookie_on_failed_request(
        self, middleware, mock_request, mock_call_next
    ):
        """Should not set CSRF cookie on failed GET request."""
        mock_request.method = "GET"
        mock_request.cookies = {}

        async def call_next_error(request):
            response = Mock()
            response.status_code = 500
            response.set_cookie = Mock()
            return response

        response = await middleware.dispatch(mock_request, call_next_error)

        assert not response.set_cookie.called
