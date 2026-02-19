"""Request logging middleware for FastAPI.

DEPRECATED: This file is superseded by app.middleware.request_logging, which is
the active implementation registered in main.py. This file is retained only because
its unit tests (test_logging_middleware.py) import it directly. Do not register
RequestLoggingMiddleware from this module in main.py.
"""

import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all HTTP requests with timing and status information.

    Logs include:
    - HTTP method and path
    - Status code
    - Response time in milliseconds
    - User ID if authenticated
    - Client IP address
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details."""
        # Skip logging for health check endpoints
        if request.url.path in ["/health", "/api/health"]:
            return await call_next(request)

        start_time = time.time()

        # Extract user info if available
        user_id = None
        if hasattr(request.state, "user") and request.state.user:
            user_id = str(request.state.user.id)

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()

        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000

            # Log request with details
            log_data = {
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "client_ip": client_ip,
            }

            if user_id:
                log_data["user_id"] = user_id

            # Use different log levels based on status code
            if response.status_code >= 500:
                logger.error(f"Request failed: {log_data}")
            elif response.status_code >= 400:
                logger.warning(f"Client error: {log_data}")
            elif duration_ms > 1000:  # Slow request threshold
                logger.warning(f"Slow request: {log_data}")
            else:
                logger.info(f"Request: {log_data}")

            return response

        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000

            # Log exception
            logger.exception(
                f"Request exception: "
                f"method={request.method} "
                f"path={request.url.path} "
                f"duration_ms={round(duration_ms, 2)} "
                f"client_ip={client_ip} "
                f"user_id={user_id} "
                f"error={str(exc)}"
            )
            raise


async def log_request(request: Request, call_next: Callable) -> Response:
    """
    Legacy function-based middleware for request logging.
    Use RequestLoggingMiddleware class instead for better performance.
    """
    start_time = time.time()

    try:
        response = await call_next(request)
        duration = time.time() - start_time

        logger.info(
            f"{request.method} {request.url.path} "
            f"completed in {duration * 1000:.2f}ms "
            f"with status {response.status_code}"
        )

        return response
    except Exception as exc:
        duration = time.time() - start_time
        logger.exception(
            f"{request.method} {request.url.path} "
            f"failed after {duration * 1000:.2f}ms: {str(exc)}"
        )
        raise
