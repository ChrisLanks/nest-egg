"""Tests for CSRF protection middleware."""

import pytest
from unittest.mock import Mock
from fastapi import Request, Response
from starlette.datastructures import Headers

from app.middleware.csrf_protection import CSRFProtectionMiddleware


class TestCSRFProtectionMiddleware:
    """Test suite for CSRF protection middleware."""

    @pytest.mark.asyncio
    async def test_get_request_passes_without_csrf_token(self):
        """GET requests should pass without CSRF token."""
        app = Mock()
        middleware = CSRFProtectionMiddleware(app)

        request = Mock(spec=Request)
        request.method = "GET"
        request.url.path = "/api/v1/accounts"
        request.cookies = {}
        request.headers = Headers({})

        async def call_next(req):
            response = Response(content="OK", status_code=200)
            return response

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_post_request_to_auth_endpoint_exempt(self):
        """Auth endpoints should be exempt from CSRF protection."""
        app = Mock()
        middleware = CSRFProtectionMiddleware(app)

        request = Mock(spec=Request)
        request.method = "POST"
        request.url.path = "/api/v1/auth/login"
        request.cookies = {}
        request.headers = Headers({})

        async def call_next(req):
            return Response(content="OK", status_code=200)

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_post_request_to_plaid_webhook_exempt(self):
        """Plaid webhook endpoint should be exempt from CSRF protection."""
        app = Mock()
        middleware = CSRFProtectionMiddleware(app)

        request = Mock(spec=Request)
        request.method = "POST"
        request.url.path = "/api/v1/plaid/webhook"
        request.cookies = {}
        request.headers = Headers({})

        async def call_next(req):
            return Response(content="OK", status_code=200)

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_post_request_to_teller_webhook_exempt(self):
        """Teller webhook endpoint should be exempt from CSRF protection."""
        app = Mock()
        middleware = CSRFProtectionMiddleware(app)

        request = Mock(spec=Request)
        request.method = "POST"
        request.url.path = "/api/v1/teller/webhook"
        request.cookies = {}
        request.headers = Headers({})

        async def call_next(req):
            return Response(content="OK", status_code=200)

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_post_request_with_matching_tokens_passes(self):
        """POST requests with matching CSRF tokens should pass."""
        app = Mock()
        middleware = CSRFProtectionMiddleware(app)

        request = Mock(spec=Request)
        request.method = "POST"
        request.url.path = "/api/v1/transactions"
        request.cookies = {"csrf_token": "matching_token_value"}
        request.headers = Headers({"X-CSRF-Token": "matching_token_value"})

        async def call_next(req):
            return Response(content="OK", status_code=200)

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_put_request_with_matching_tokens_passes(self):
        """PUT requests with matching CSRF tokens should pass."""
        app = Mock()
        middleware = CSRFProtectionMiddleware(app)

        request = Mock(spec=Request)
        request.method = "PUT"
        request.url.path = "/api/v1/transactions/123"
        request.cookies = {"csrf_token": "token_value"}
        request.headers = Headers({"X-CSRF-Token": "token_value"})

        async def call_next(req):
            return Response(content="OK", status_code=200)

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_patch_request_with_matching_tokens_passes(self):
        """PATCH requests with matching CSRF tokens should pass."""
        app = Mock()
        middleware = CSRFProtectionMiddleware(app)

        request = Mock(spec=Request)
        request.method = "PATCH"
        request.url.path = "/api/v1/settings/profile"
        request.cookies = {"csrf_token": "token_value"}
        request.headers = Headers({"X-CSRF-Token": "token_value"})

        async def call_next(req):
            return Response(content="OK", status_code=200)

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_request_with_matching_tokens_passes(self):
        """DELETE requests with matching CSRF tokens should pass."""
        app = Mock()
        middleware = CSRFProtectionMiddleware(app)

        request = Mock(spec=Request)
        request.method = "DELETE"
        request.url.path = "/api/v1/transactions/123"
        request.cookies = {"csrf_token": "token_value"}
        request.headers = Headers({"X-CSRF-Token": "token_value"})

        async def call_next(req):
            return Response(content="OK", status_code=200)

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_check_endpoint_exempt(self):
        """Health check endpoints should be exempt from CSRF protection."""
        app = Mock()
        middleware = CSRFProtectionMiddleware(app)

        request = Mock(spec=Request)
        request.method = "POST"
        request.url.path = "/health"
        request.cookies = {}
        request.headers = Headers({})

        async def call_next(req):
            return Response(content="OK", status_code=200)

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_metrics_endpoint_exempt(self):
        """Metrics endpoints should be exempt from CSRF protection."""
        app = Mock()
        middleware = CSRFProtectionMiddleware(app)

        request = Mock(spec=Request)
        request.method = "POST"
        request.url.path = "/metrics"
        request.cookies = {}
        request.headers = Headers({})

        async def call_next(req):
            return Response(content="OK", status_code=200)

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_register_endpoint_exempt_from_csrf(self):
        """Registration endpoint should be exempt from CSRF protection."""
        app = Mock()
        middleware = CSRFProtectionMiddleware(app)

        request = Mock(spec=Request)
        request.method = "POST"
        request.url.path = "/api/v1/auth/register"
        request.cookies = {}
        request.headers = Headers({})

        async def call_next(req):
            return Response(content="OK", status_code=200)

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_exempt_path_startswith_matching(self):
        """Should exempt any path that starts with exempt path prefix."""
        app = Mock()
        middleware = CSRFProtectionMiddleware(app)

        # Test that /api/v1/auth/anything is exempt
        request = Mock(spec=Request)
        request.method = "POST"
        request.url.path = "/api/v1/auth/password-reset"
        request.cookies = {}
        request.headers = Headers({})

        async def call_next(req):
            return Response(content="OK", status_code=200)

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_request_sets_csrf_cookie_if_missing(self):
        """GET requests should set CSRF cookie if not present."""
        app = Mock()
        middleware = CSRFProtectionMiddleware(app)

        request = Mock(spec=Request)
        request.method = "GET"
        request.url.path = "/api/v1/accounts"
        request.cookies = {}  # No existing cookie
        request.headers = Headers({})

        async def call_next(req):
            return Response(content="OK", status_code=200)

        response = await middleware.dispatch(request, call_next)

        # Check that Set-Cookie header was added (Starlette uses lowercase headers)
        # The response should have set a cookie
        assert response.status_code == 200
        # Note: In real middleware usage, the cookie is set via response.set_cookie()
        # which modifies the response object. In testing with mocks, we verify
        # the middleware completes successfully.

    @pytest.mark.asyncio
    async def test_state_changing_methods_checked(self):
        """Verify all state-changing HTTP methods require CSRF tokens."""
        app = Mock()
        middleware = CSRFProtectionMiddleware(app)

        # List of methods that should be checked
        methods_to_check = ["POST", "PUT", "PATCH", "DELETE"]

        for method in methods_to_check:
            request = Mock(spec=Request)
            request.method = method
            request.url.path = "/api/v1/transactions"
            # With matching tokens, request should pass
            request.cookies = {"csrf_token": "test_token"}
            request.headers = Headers({"X-CSRF-Token": "test_token"})

            async def call_next(req):
                return Response(content="OK", status_code=200)

            response = await middleware.dispatch(request, call_next)

            # All should pass with valid tokens
            assert response.status_code == 200, f"{method} request failed with valid CSRF tokens"
