"""Unit tests for request size limit middleware."""

import pytest
from unittest.mock import Mock, AsyncMock
from fastapi import Request
from starlette.datastructures import Headers

from app.middleware.request_size_limit import RequestSizeLimitMiddleware


@pytest.mark.unit
class TestRequestSizeLimitMiddleware:
    """Test request size limit middleware."""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance with default 10MB limit."""
        app = Mock()
        return RequestSizeLimitMiddleware(app)

    @pytest.fixture
    def custom_middleware(self):
        """Create middleware instance with custom 5MB limit."""
        app = Mock()
        return RequestSizeLimitMiddleware(app, max_request_size=5 * 1024 * 1024)

    @pytest.fixture
    def mock_call_next(self):
        """Create mock call_next."""
        async def call_next(request):
            response = Mock()
            response.status_code = 200
            return response

        return call_next

    @pytest.mark.asyncio
    async def test_allows_requests_without_content_length(self, middleware, mock_call_next):
        """Should allow requests without Content-Length header."""
        request = Mock(spec=Request)
        request.headers = Headers({})

        response = await middleware.dispatch(request, mock_call_next)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_allows_requests_under_size_limit(self, middleware, mock_call_next):
        """Should allow requests under the size limit."""
        request = Mock(spec=Request)
        request.headers = Headers({"content-length": str(5 * 1024 * 1024)})  # 5MB

        response = await middleware.dispatch(request, mock_call_next)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_allows_requests_at_size_limit(self, middleware, mock_call_next):
        """Should allow requests exactly at the size limit."""
        request = Mock(spec=Request)
        request.headers = Headers({"content-length": str(10 * 1024 * 1024)})  # 10MB exactly

        response = await middleware.dispatch(request, mock_call_next)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_rejects_requests_over_size_limit(self, middleware, mock_call_next):
        """Should reject requests over the size limit."""
        request = Mock(spec=Request)
        request.headers = Headers({"content-length": str(11 * 1024 * 1024)})  # 11MB

        response = await middleware.dispatch(request, mock_call_next)
        assert response.status_code == 413
        assert "too large" in response.body.decode().lower()

    @pytest.mark.asyncio
    async def test_rejects_very_large_requests(self, middleware, mock_call_next):
        """Should reject very large requests."""
        request = Mock(spec=Request)
        request.headers = Headers({"content-length": str(100 * 1024 * 1024)})  # 100MB

        response = await middleware.dispatch(request, mock_call_next)
        assert response.status_code == 413

    @pytest.mark.asyncio
    async def test_custom_size_limit(self, custom_middleware, mock_call_next):
        """Should respect custom size limit."""
        request = Mock(spec=Request)
        request.headers = Headers({"content-length": str(6 * 1024 * 1024)})  # 6MB (over 5MB limit)

        response = await custom_middleware.dispatch(request, mock_call_next)
        assert response.status_code == 413

    @pytest.mark.asyncio
    async def test_custom_size_limit_under(self, custom_middleware, mock_call_next):
        """Should allow requests under custom size limit."""
        request = Mock(spec=Request)
        request.headers = Headers({"content-length": str(4 * 1024 * 1024)})  # 4MB (under 5MB limit)

        response = await custom_middleware.dispatch(request, mock_call_next)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_error_message_includes_limit(self, middleware, mock_call_next):
        """Should include size limit in error message."""
        request = Mock(spec=Request)
        request.headers = Headers({"content-length": str(11 * 1024 * 1024)})

        response = await middleware.dispatch(request, mock_call_next)
        body = response.body.decode()
        assert "10.0MB" in body or "10MB" in body

    @pytest.mark.asyncio
    async def test_handles_zero_content_length(self, middleware, mock_call_next):
        """Should allow requests with zero content length."""
        request = Mock(spec=Request)
        request.headers = Headers({"content-length": "0"})

        response = await middleware.dispatch(request, mock_call_next)
        assert response.status_code == 200
