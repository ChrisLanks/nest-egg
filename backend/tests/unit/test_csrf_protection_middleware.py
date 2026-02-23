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
        app = Mock()
        return CSRFProtectionMiddleware(app)

    @pytest.fixture
    def mock_request(self):
        request = Mock(spec=Request)
        request.url = Mock()
        request.url.path = "/api/v1/test"
        request.method = "POST"
        request.cookies = {}
        request.headers = {}
        return request

    @pytest.fixture
    def mock_call_next(self):
        async def call_next(request):
            response = Mock()
            response.status_code = 200
            response.set_cookie = Mock()
            return response
        return call_next

    @pytest.mark.asyncio
    @pytest.mark.parametrize("exempt_path", [
        "/api/v1/auth/login",
        "/api/v1/plaid/webhook",
        "/api/v1/teller/webhook",
        "/health",
        "/",
        "/docs",
        "/openapi.json",
        "/metrics",
    ])
    async def test_skips_csrf_check_for_exempt_paths(
        self, middleware, mock_request, mock_call_next, exempt_path
    ):
        """Should skip CSRF check for exempt paths."""
        mock_request.url.path = exempt_path
        mock_request.method = "POST"
        response = await middleware.dispatch(mock_request, mock_call_next)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_enforces_csrf_on_non_exempt_api_path(
        self, middleware, mock_request, mock_call_next
    ):
        """Non-exempt paths must have CSRF token — '/' prefix must not exempt them."""
        from app import config
        mock_request.url.path = "/api/v1/accounts"
        mock_request.method = "POST"
        mock_request.cookies = {}
        mock_request.headers = {}
        with patch.object(config.settings, "SKIP_CSRF_IN_TESTS", False):
            response = await middleware.dispatch(mock_request, mock_call_next)
        assert response.status_code == 403

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
    async def test_rejects_missing_cookie(self, middleware, mock_request, mock_call_next):
        """Should reject request with missing CSRF cookie."""
        from app import config
        mock_request.method = "POST"
        mock_request.cookies = {}
        mock_request.headers = {"X-CSRF-Token": "test-token"}
        with patch.object(config.settings, "SKIP_CSRF_IN_TESTS", False):
            response = await middleware.dispatch(mock_request, mock_call_next)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_rejects_missing_header(self, middleware, mock_request, mock_call_next):
        """Should reject request with missing CSRF header."""
        from app import config
        mock_request.method = "POST"
        mock_request.cookies = {"csrf_token": "test-token"}
        mock_request.headers = {}
        with patch.object(config.settings, "SKIP_CSRF_IN_TESTS", False):
            response = await middleware.dispatch(mock_request, mock_call_next)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_rejects_mismatched_tokens(self, middleware, mock_request, mock_call_next):
        """Should reject request when CSRF tokens don't match."""
        from app import config
        mock_request.method = "POST"
        mock_request.cookies = {"csrf_token": "token-1"}
        mock_request.headers = {"X-CSRF-Token": "token-2"}
        with patch.object(config.settings, "SKIP_CSRF_IN_TESTS", False):
            response = await middleware.dispatch(mock_request, mock_call_next)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_allows_bypass_when_skip_csrf_in_tests(
        self, middleware, mock_request, mock_call_next
    ):
        """Should allow missing token when SKIP_CSRF_IN_TESTS=true (pytest only)."""
        from app import config
        mock_request.method = "POST"
        mock_request.cookies = {}
        mock_request.headers = {}
        with patch.object(config.settings, "SKIP_CSRF_IN_TESTS", True):
            response = await middleware.dispatch(mock_request, mock_call_next)
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_allows_mismatch_when_skip_csrf_in_tests(
        self, middleware, mock_request, mock_call_next
    ):
        """Should allow mismatched tokens when SKIP_CSRF_IN_TESTS=true (pytest only)."""
        from app import config
        mock_request.method = "POST"
        mock_request.cookies = {"csrf_token": "token-1"}
        mock_request.headers = {"X-CSRF-Token": "token-2"}
        with patch.object(config.settings, "SKIP_CSRF_IN_TESTS", True):
            response = await middleware.dispatch(mock_request, mock_call_next)
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_does_not_bypass_csrf_when_environment_is_test(
        self, middleware, mock_request, mock_call_next
    ):
        """ENVIRONMENT=test must NOT bypass CSRF — only SKIP_CSRF_IN_TESTS can."""
        from app import config
        mock_request.method = "POST"
        mock_request.cookies = {}
        mock_request.headers = {}
        with patch.object(config.settings, "ENVIRONMENT", "test"):
            with patch.object(config.settings, "SKIP_CSRF_IN_TESTS", False):
                response = await middleware.dispatch(mock_request, mock_call_next)
                assert response.status_code == 403

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
