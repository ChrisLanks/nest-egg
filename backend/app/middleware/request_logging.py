"""Request/response logging middleware for audit trails."""

import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from jwt.exceptions import InvalidTokenError as JWTError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.security import decode_token
from app.utils.logging_utils import redact_ip

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
        """Extract user id from JWT token if present."""
        token = None
        # 1. Try Authorization header (access token)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")

        # 2. Fallback: refresh token cookie
        if not token:
            token = request.cookies.get("refresh_token")

        if token:
            try:
                payload = decode_token(token)
                user_id = payload.get("sub")

                if user_id:
                    request.state.user_id = user_id

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
        # Use incoming X-Request-ID if provided (e.g. from load balancer or client),
        # otherwise generate a new one for correlation across logs and services.
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Start timer
        start_time = time.time()

        # Extract request details
        method = request.method
        path = request.url.path
        client_host = request.client.host if request.client else "unknown"

        # Get user ID from request state (set by UserContextMiddleware)
        user_id = getattr(request.state, "user_id", None) or "N/A"

        # Log request start
        logger.info(
            f"Request started | "
            f"id={request_id} | "
            f"method={method} | "
            f"path={path} | "
            f"user={user_id} | "
            f"ip={redact_ip(client_host)}"
        )

        # Add request ID to request state for downstream use
        request.state.request_id = request_id

        # Process request
        try:
            response = await call_next(request)

            # Calculate response time
            duration_ms = int((time.time() - start_time) * 1000)

            # Re-read user_id in case it was set during request processing
            completed_user = getattr(request.state, "user_id", None) or user_id

            # Log successful response
            logger.info(
                f"Request completed | "
                f"id={request_id} | "
                f"method={method} | "
                f"path={path} | "
                f"status={response.status_code} | "
                f"duration={duration_ms}ms | "
                f"user={completed_user}"
            )

            # Add request ID to response headers for debugging
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            # Calculate response time
            duration_ms = int((time.time() - start_time) * 1000)

            failed_user = getattr(request.state, "user_id", None) or user_id

            # Log failed request
            logger.error(
                f"Request failed | "
                f"id={request_id} | "
                f"method={method} | "
                f"path={path} | "
                f"duration={duration_ms}ms | "
                f"user={failed_user} | "
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

    # Paths that should be audited (mutating operations)
    AUDIT_PATHS = {
        "/api/v1/auth/login": "LOGIN_ATTEMPT",
        "/api/v1/auth/register": "REGISTRATION",
        "/api/v1/auth/logout": "LOGOUT",
        "/api/v1/auth/logout-all": "LOGOUT_ALL",
        "/api/v1/auth/password": "PASSWORD_CHANGE",
        "/api/v1/auth/reset-password": "PASSWORD_RESET",  # pragma: allowlist secret
        "/api/v1/auth/forgot-password": "PASSWORD_RESET_REQUEST",  # pragma: allowlist secret
        "/api/v1/auth/mfa": "MFA_OPERATION",
        "/api/v1/accounts": "ACCOUNT_OPERATION",
        "/api/v1/transactions": "TRANSACTION_OPERATION",
        "/api/v1/household/members": "HOUSEHOLD_CHANGE",
        "/api/v1/budgets": "BUDGET_OPERATION",
        "/api/v1/reports": "REPORT_OPERATION",
        "/api/v1/permissions": "PERMISSION_CHANGE",
        "/api/v1/guest-access": "GUEST_ACCESS_OPERATION",
        "/api/v1/plaid/exchange-token": "PLAID_LINK",
        "/api/v1/teller/webhook": "TELLER_WEBHOOK",
        "/api/v1/csv-import": "CSV_IMPORT",
        "/api/v1/settings/delete": "ACCOUNT_DELETE",
        "/api/v1/settings/profile": "PROFILE_UPDATE",
    }

    # Sensitive read operations that should also be audited (GET requests)
    AUDIT_READ_PATHS = {
        "/api/v1/settings/export": "DATA_EXPORT",
        "/api/v1/settings/profile": "PROFILE_VIEW",
        "/api/v1/holdings/portfolio": "PORTFOLIO_VIEW",
        "/api/v1/accounts/export": "ACCOUNT_EXPORT",
        "/api/v1/transactions/export": "TRANSACTION_EXPORT",
        "/api/v1/budgets/export": "BUDGET_EXPORT",
        "/api/v1/labels/tax-deductible/export": "TAX_DATA_EXPORT",
        "/api/v1/reports/templates": "REPORT_TEMPLATE_VIEW",
    }

    # Methods that modify data
    MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Audit sensitive operations."""
        start_time = time.time()
        path = request.url.path
        method = request.method

        # Check if this path should be audited
        audit_type = None
        for audit_path, action_type in self.AUDIT_PATHS.items():
            if path.startswith(audit_path):
                audit_type = action_type
                break

        # Also check sensitive read paths for GET requests
        if not audit_type and method == "GET":
            for audit_path, action_type in self.AUDIT_READ_PATHS.items():
                if path.startswith(audit_path):
                    audit_type = action_type
                    break

        # Audit mutating operations, specific paths, or sensitive reads
        should_audit = audit_type or (method in self.MUTATING_METHODS and "/api/v1/" in path)

        if not should_audit:
            return await call_next(request)

        # Get request details
        user_id = getattr(request.state, "user_id", None) or "N/A"
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
            f"user={user_id} | "
            f"ip={redact_ip(client_host)} | "
            f"request_id={request_id}"
        )

        # Enqueue DB persistence via Celery — non-blocking, durable, retried on failure.
        # The AUDIT log line above is already written; this task writes the DB record.
        duration_ms = int((time.time() - start_time) * 1000)
        try:
            from app.workers.tasks.auth_tasks import persist_audit_log_task

            persist_audit_log_task.delay(
                request_id=request_id,
                action=action,
                method=method,
                path=path,
                status_code=response.status_code,
                user_id=user_id if user_id != "N/A" else None,
                ip_address=redact_ip(client_host),
                duration_ms=duration_ms,
            )
        except Exception:
            # Celery broker unavailable — the structured log line above still serves
            # as the audit record.  Log at WARNING so operators know DB persistence
            # is degraded, but never raise (never block the HTTP response).
            logger.warning(
                "audit_log: Celery unavailable, DB record not persisted for request_id=%s",
                request_id,
            )

        return response
