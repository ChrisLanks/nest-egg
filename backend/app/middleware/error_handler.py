"""Production error handler middleware with PII redaction."""

import logging
from typing import Callable
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.error_logging_service import error_logging_service
from app.config import settings

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Middleware for handling uncaught exceptions.

    - Logs errors with PII redaction
    - Returns safe error messages to clients (no stack traces in production)
    - Tracks error context for debugging
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle request and catch any uncaught exceptions."""
        try:
            response = await call_next(request)
            return response

        except Exception as exc:
            # Get user context if available (from auth)
            user_id = None
            try:
                # Try to get user from request state (set by auth dependency)
                if hasattr(request.state, "user"):
                    user_id = str(request.state.user.id)
            except:
                pass

            # Build error context
            context = {
                "method": request.method,
                "url": str(request.url),
                "client_host": request.client.host if request.client else None,
            }

            # Log error with PII redaction
            error_logging_service.log_error(
                logger=logger, error=exc, context=context, user_id=user_id
            )

            # Determine response based on environment
            if settings.DEBUG:
                # Development: Show detailed error
                error_detail = {
                    "error": str(exc),
                    "type": type(exc).__name__,
                    "detail": "An error occurred processing your request",
                }
            else:
                # Production: Generic error message (never expose internals)
                error_detail = {
                    "error": "Internal server error",
                    "detail": "An unexpected error occurred. Please try again later.",
                    "support": "If this persists, contact support with the timestamp",
                }

            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=error_detail
            )
