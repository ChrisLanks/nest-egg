"""Request/response logging middleware for audit trails."""

import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from jose import JWTError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.security import decode_token
from app.utils.logging_utils import redact_email, redact_ip


logger = logging.getLogger(__name__)


class UserContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract user context from JWT token and add to request state.

    This middleware runs BEFORE logging middleware to provide user context.
    Does NOT validate the token (that's done by get_current_user dependency).
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Extract user email from token if present."""
        # Try to extract user email from Authorization header
        auth_header = request.headers.get("Authorization")

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")

            try:
                # Decode token to get email (don't validate, just extract)
                payload = decode_token(token)
                user_email = payload.get("email")

                if user_email:
                    request.state.user_email = user_email

            except (JWTError, Exception):
                # Token invalid or expired - ignore, will be handled by auth dependency
                pass

        return await call_next(request)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging all API requests and responses.

    Provides audit trail for:
    - Request ID tracking
    - Response time monitoring
    - Failed request logging
    - User action auditing
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details."""
        # Generate unique request ID
        request_id = str(uuid.uuid4())

        # Start timer
        start_time = time.time()

        # Extract request details
        method = request.method
        path = request.url.path
        client_host = request.client.host if request.client else "unknown"

        # Get user email from request state (set by auth middleware)
        user_email = getattr(request.state, "user_email", None)

        # Log request start
        logger.info(
            f"Request started | "
            f"id={request_id} | "
            f"method={method} | "
            f"path={path} | "
            f"user={redact_email(user_email)} | "
            f"ip={redact_ip(client_host)}"
        )

        # Add request ID to request state for downstream use
        request.state.request_id = request_id

        # Process request
        try:
            response = await call_next(request)

            # Calculate response time
            duration_ms = int((time.time() - start_time) * 1000)

            # Log successful response
            logger.info(
                f"Request completed | "
                f"id={request_id} | "
                f"method={method} | "
                f"path={path} | "
                f"status={response.status_code} | "
                f"duration={duration_ms}ms | "
                f"user={redact_email(user_email)}"
            )

            # Add request ID to response headers for debugging
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            # Calculate response time
            duration_ms = int((time.time() - start_time) * 1000)

            # Log failed request
            logger.error(
                f"Request failed | "
                f"id={request_id} | "
                f"method={method} | "
                f"path={path} | "
                f"duration={duration_ms}ms | "
                f"user={redact_email(user_email)} | "
                f"error={type(e).__name__}: {str(e)}"
            )

            # Re-raise exception to be handled by FastAPI
            raise


class AuditLogMiddleware(BaseHTTPMiddleware):
    """
    Middleware for auditing sensitive operations.

    Logs detailed information for:
    - Authentication attempts
    - Financial data modifications
    - Account changes
    - Permission changes
    """

    # Paths that should be audited
    AUDIT_PATHS = {
        "/api/v1/auth/login": "LOGIN_ATTEMPT",
        "/api/v1/auth/register": "REGISTRATION",
        "/api/v1/auth/password": "PASSWORD_CHANGE",
        "/api/v1/accounts": "ACCOUNT_OPERATION",
        "/api/v1/transactions": "TRANSACTION_OPERATION",
        "/api/v1/household/members": "HOUSEHOLD_CHANGE",
    }

    # Methods that modify data
    MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Audit sensitive operations."""
        path = request.url.path
        method = request.method

        # Check if this path should be audited
        audit_type = None
        for audit_path, action_type in self.AUDIT_PATHS.items():
            if path.startswith(audit_path):
                audit_type = action_type
                break

        # Only audit mutating operations or specific paths
        should_audit = audit_type or (method in self.MUTATING_METHODS and "/api/v1/" in path)

        if not should_audit:
            return await call_next(request)

        # Get request details
        user_email = getattr(request.state, "user_email", None)
        client_host = request.client.host if request.client else "unknown"
        request_id = getattr(request.state, "request_id", "unknown")

        # Process request
        response = await call_next(request)

        # Log audit entry
        action = audit_type or f"{method}_{path.split('/')[-1].upper()}"

        logger.info(
            f"AUDIT | "
            f"action={action} | "
            f"method={method} | "
            f"path={path} | "
            f"status={response.status_code} | "
            f"user={redact_email(user_email)} | "
            f"ip={redact_ip(client_host)} | "
            f"request_id={request_id}"
        )

        return response
