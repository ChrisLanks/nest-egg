"""CSRF protection middleware using double-submit cookie pattern."""

import hmac
import logging
import secrets
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.config import settings


logger = logging.getLogger(__name__)


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    CSRF protection middleware using double-submit cookie pattern.

    NOTE: This app primarily uses JWT bearer tokens in Authorization headers,
    which are inherently CSRF-safe. This middleware provides defense-in-depth.

    How it works:
    1. On GET requests, generates a CSRF token and sets it as a cookie
    2. On state-changing requests (POST/PUT/PATCH/DELETE), validates token
    3. Token must match between cookie and header (X-CSRF-Token)

    Exempt paths:
    - /api/v1/auth/* (authentication endpoints)
    - /api/v1/plaid/webhook (external webhooks)
    - /api/v1/teller/webhook (external webhooks)
    - /health, /, /docs (public endpoints)
    """

    # Paths exempt via exact match (short public endpoints).
    # Must NOT use startswith for these — "/" would otherwise match every path.
    EXEMPT_EXACT: frozenset[str] = frozenset({"/", "/health", "/docs", "/openapi.json", "/metrics"})

    # Paths exempt via prefix match (whole subtrees).
    EXEMPT_PREFIXES = [
        "/api/v1/auth/",
        "/api/v1/plaid/webhook",
        "/api/v1/teller/webhook",
    ]

    # Methods that modify state and require CSRF protection
    STATE_CHANGING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Validate CSRF token on state-changing requests."""
        path = request.url.path
        method = request.method

        # Skip CSRF check for exempt paths.
        # Exact-match set handles short paths like "/" and "/health".
        # Prefix list handles subtrees like "/api/v1/auth/".
        is_exempt = (
            path in self.EXEMPT_EXACT
            or any(path.startswith(p) for p in self.EXEMPT_PREFIXES)
        )

        if is_exempt:
            response = await call_next(request)
            return response

        # Only check CSRF on state-changing methods
        if method in self.STATE_CHANGING_METHODS:
            # Get CSRF token from cookie
            csrf_cookie = request.cookies.get("csrf_token")

            # Get CSRF token from header
            csrf_header = request.headers.get("X-CSRF-Token")

            # Validate tokens match
            if not csrf_cookie or not csrf_header:
                logger.warning(
                    f"CSRF validation failed: Missing token | "
                    f"path={path} | method={method} | "
                    f"has_cookie={csrf_cookie is not None} | "
                    f"has_header={csrf_header is not None}"
                )

                # Only bypass in pytest — guarded by explicit flag, not ENVIRONMENT,
                # so a mis-set ENVIRONMENT=test in staging/prod can't disable CSRF.
                if settings.SKIP_CSRF_IN_TESTS:
                    logger.warning("CSRF check failed but allowing (SKIP_CSRF_IN_TESTS=true)")
                else:
                    return Response(
                        content='{"detail":"CSRF token missing"}',
                        status_code=403,
                        media_type="application/json",
                    )

            elif not hmac.compare_digest(csrf_cookie, csrf_header):
                logger.warning(
                    f"CSRF validation failed: Token mismatch | " f"path={path} | method={method}"
                )

                # Only bypass in pytest — guarded by explicit flag, not ENVIRONMENT.
                if settings.SKIP_CSRF_IN_TESTS:
                    logger.warning("CSRF token mismatch but allowing (SKIP_CSRF_IN_TESTS=true)")
                else:
                    return Response(
                        content='{"detail":"CSRF token invalid"}',
                        status_code=403,
                        media_type="application/json",
                    )

        # Process request
        response = await call_next(request)

        # On successful GET requests, set CSRF token cookie if not present
        if method == "GET" and response.status_code < 400:
            csrf_cookie = request.cookies.get("csrf_token")

            if not csrf_cookie:
                # Generate new CSRF token
                csrf_token = secrets.token_urlsafe(32)

                # Set cookie (HttpOnly=False so JavaScript can read it to set header)
                response.set_cookie(
                    key="csrf_token",
                    value=csrf_token,
                    httponly=False,  # Allow JS to read for setting header
                    secure=not settings.DEBUG,  # HTTPS only in production
                    samesite="lax",
                    max_age=86400,  # 24 hours
                )

        return response
