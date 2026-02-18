"""Unit tests for security headers middleware."""

import pytest
from unittest.mock import Mock, patch
from fastapi import Request, Response

from app.middleware.security_headers import SecurityHeadersMiddleware


@pytest.mark.unit
class TestSecurityHeadersMiddleware:
    """Test security headers middleware."""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance."""
        app = Mock()
        return SecurityHeadersMiddleware(app)

    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        request = Mock(spec=Request)
        request.url = Mock()
        request.url.hostname = "example.com"
        return request

    @pytest.fixture
    def mock_call_next(self):
        """Create mock call_next."""
        async def call_next(request):
            response = Mock(spec=Response)
            response.headers = {}
            return response

        return call_next

    @pytest.mark.asyncio
    async def test_adds_csp_header(self, middleware, mock_request, mock_call_next):
        """Should add Content-Security-Policy header."""
        response = await middleware.dispatch(mock_request, mock_call_next)
        assert "Content-Security-Policy" in response.headers

    @pytest.mark.asyncio
    async def test_adds_x_frame_options(self, middleware, mock_request, mock_call_next):
        """Should add X-Frame-Options header."""
        response = await middleware.dispatch(mock_request, mock_call_next)
        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"

    @pytest.mark.asyncio
    async def test_adds_x_content_type_options(self, middleware, mock_request, mock_call_next):
        """Should add X-Content-Type-Options header."""
        response = await middleware.dispatch(mock_request, mock_call_next)
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"

    @pytest.mark.asyncio
    async def test_adds_x_xss_protection(self, middleware, mock_request, mock_call_next):
        """Should add X-XSS-Protection header."""
        response = await middleware.dispatch(mock_request, mock_call_next)
        assert "X-XSS-Protection" in response.headers
        assert response.headers["X-XSS-Protection"] == "1; mode=block"

    @pytest.mark.asyncio
    async def test_adds_referrer_policy(self, middleware, mock_request, mock_call_next):
        """Should add Referrer-Policy header."""
        response = await middleware.dispatch(mock_request, mock_call_next)
        assert "Referrer-Policy" in response.headers
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    @pytest.mark.asyncio
    async def test_adds_permissions_policy(self, middleware, mock_request, mock_call_next):
        """Should add Permissions-Policy header."""
        response = await middleware.dispatch(mock_request, mock_call_next)
        assert "Permissions-Policy" in response.headers

    @pytest.mark.asyncio
    async def test_adds_hsts_for_non_localhost(self, middleware, mock_request, mock_call_next):
        """Should add HSTS header for non-localhost hosts."""
        mock_request.url.hostname = "example.com"
        response = await middleware.dispatch(mock_request, mock_call_next)
        assert "Strict-Transport-Security" in response.headers
        assert "max-age=31536000" in response.headers["Strict-Transport-Security"]

    @pytest.mark.asyncio
    async def test_skips_hsts_for_localhost(self, middleware, mock_request, mock_call_next):
        """Should not add HSTS header for localhost."""
        mock_request.url.hostname = "localhost"
        response = await middleware.dispatch(mock_request, mock_call_next)
        assert "Strict-Transport-Security" not in response.headers

    @pytest.mark.asyncio
    async def test_skips_hsts_for_127_0_0_1(self, middleware, mock_request, mock_call_next):
        """Should not add HSTS header for 127.0.0.1."""
        mock_request.url.hostname = "127.0.0.1"
        response = await middleware.dispatch(mock_request, mock_call_next)
        assert "Strict-Transport-Security" not in response.headers

    @pytest.mark.asyncio
    @patch("app.middleware.security_headers.settings")
    async def test_csp_in_debug_mode(self, mock_settings, middleware, mock_request, mock_call_next):
        """Should allow unsafe-eval in DEBUG mode."""
        mock_settings.DEBUG = True
        response = await middleware.dispatch(mock_request, mock_call_next)
        assert "unsafe-eval" in response.headers["Content-Security-Policy"]

    @pytest.mark.asyncio
    @patch("app.middleware.security_headers.settings")
    async def test_csp_in_production_mode(self, mock_settings, middleware, mock_request, mock_call_next):
        """Should not allow unsafe directives in production."""
        mock_settings.DEBUG = False
        response = await middleware.dispatch(mock_request, mock_call_next)
        csp = response.headers["Content-Security-Policy"]
        assert "unsafe-eval" not in csp
        assert "unsafe-inline" not in csp

    @pytest.mark.asyncio
    async def test_csp_blocks_by_default(self, middleware, mock_request, mock_call_next):
        """Should block everything by default in CSP."""
        response = await middleware.dispatch(mock_request, mock_call_next)
        assert "default-src 'none'" in response.headers["Content-Security-Policy"]

    @pytest.mark.asyncio
    async def test_csp_prevents_frame_embedding(self, middleware, mock_request, mock_call_next):
        """Should prevent frame embedding in CSP."""
        response = await middleware.dispatch(mock_request, mock_call_next)
        assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
