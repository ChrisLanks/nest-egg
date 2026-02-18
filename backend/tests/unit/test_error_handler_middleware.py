"""Unit tests for error handler middleware."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import Request, Response

from app.middleware.error_handler import ErrorHandlerMiddleware


@pytest.mark.unit
class TestErrorHandlerMiddleware:
    """Test error handler middleware."""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance."""
        app = Mock()
        return ErrorHandlerMiddleware(app)

    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        request = Mock(spec=Request)
        request.method = "GET"
        request.url = Mock()
        request.url.__str__ = Mock(return_value="http://test.com/api/test")
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.state = Mock()
        return request

    @pytest.fixture
    def mock_call_next_success(self):
        """Create mock call_next that succeeds."""
        async def call_next(request):
            response = Mock(spec=Response)
            response.status_code = 200
            return response

        return call_next

    @pytest.fixture
    def mock_call_next_error(self):
        """Create mock call_next that raises error."""
        async def call_next(request):
            raise ValueError("Test error")

        return call_next

    @pytest.mark.asyncio
    async def test_passes_through_successful_requests(self, middleware, mock_request, mock_call_next_success):
        """Should pass through successful requests unchanged."""
        response = await middleware.dispatch(mock_request, mock_call_next_success)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_catches_exceptions(self, middleware, mock_request, mock_call_next_error):
        """Should catch exceptions and return 500 error."""
        response = await middleware.dispatch(mock_request, mock_call_next_error)
        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_logs_exceptions(self, middleware, mock_request, mock_call_next_error):
        """Should log exceptions with PII redaction."""
        with patch("app.middleware.error_handler.error_logging_service") as mock_logging:
            await middleware.dispatch(mock_request, mock_call_next_error)
            assert mock_logging.log_error.called

    @pytest.mark.asyncio
    async def test_includes_context_in_logs(self, middleware, mock_request, mock_call_next_error):
        """Should include request context in error logs."""
        with patch("app.middleware.error_handler.error_logging_service") as mock_logging:
            await middleware.dispatch(mock_request, mock_call_next_error)
            call_args = mock_logging.log_error.call_args
            context = call_args.kwargs.get("context")
            assert context is not None
            assert "method" in context
            assert "url" in context

    @pytest.mark.asyncio
    async def test_extracts_user_id_if_available(self, middleware, mock_request, mock_call_next_error):
        """Should extract user ID from request state if available."""
        mock_user = Mock()
        mock_user.id = "test-user-123"
        mock_request.state.user = mock_user

        with patch("app.middleware.error_handler.error_logging_service") as mock_logging:
            await middleware.dispatch(mock_request, mock_call_next_error)
            call_args = mock_logging.log_error.call_args
            user_id = call_args.kwargs.get("user_id")
            assert user_id == "test-user-123"

    @pytest.mark.asyncio
    async def test_handles_missing_user_gracefully(self, middleware, mock_request, mock_call_next_error):
        """Should handle requests without user gracefully."""
        delattr(mock_request.state, "user")

        with patch("app.middleware.error_handler.error_logging_service") as mock_logging:
            response = await middleware.dispatch(mock_request, mock_call_next_error)
            assert response.status_code == 500

    @pytest.mark.asyncio
    @patch("app.middleware.error_handler.settings")
    async def test_shows_detailed_error_in_debug_mode(self, mock_settings, middleware, mock_request, mock_call_next_error):
        """Should show detailed error in DEBUG mode."""
        mock_settings.DEBUG = True

        response = await middleware.dispatch(mock_request, mock_call_next_error)
        assert response.status_code == 500
        body = response.body.decode()
        assert "Test error" in body or "ValueError" in body

    @pytest.mark.asyncio
    @patch("app.middleware.error_handler.settings")
    async def test_hides_error_details_in_production(self, mock_settings, middleware, mock_request, mock_call_next_error):
        """Should hide error details in production."""
        mock_settings.DEBUG = False

        response = await middleware.dispatch(mock_request, mock_call_next_error)
        assert response.status_code == 500
        body = response.body.decode()
        assert "Internal server error" in body
        assert "Test error" not in body  # Should not leak implementation details

    @pytest.mark.asyncio
    async def test_handles_error_extracting_user(self, middleware, mock_request, mock_call_next_error):
        """Should handle errors when extracting user ID."""
        # Make user.id raise an exception
        mock_user = Mock()
        mock_user.id = Mock(side_effect=AttributeError("No ID"))
        mock_request.state.user = mock_user

        with patch("app.middleware.error_handler.error_logging_service"):
            response = await middleware.dispatch(mock_request, mock_call_next_error)
            assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_includes_client_host_in_context(self, middleware, mock_request, mock_call_next_error):
        """Should include client host in error context."""
        with patch("app.middleware.error_handler.error_logging_service") as mock_logging:
            await middleware.dispatch(mock_request, mock_call_next_error)
            call_args = mock_logging.log_error.call_args
            context = call_args.kwargs.get("context")
            assert "client_host" in context

    @pytest.mark.asyncio
    async def test_handles_missing_client(self, middleware, mock_request, mock_call_next_error):
        """Should handle requests without client info."""
        mock_request.client = None

        with patch("app.middleware.error_handler.error_logging_service") as mock_logging:
            response = await middleware.dispatch(mock_request, mock_call_next_error)
            assert response.status_code == 500
            call_args = mock_logging.log_error.call_args
            context = call_args.kwargs.get("context")
            assert context["client_host"] is None
