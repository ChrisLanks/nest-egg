"""
Global rate limiting middleware.

Applies rate limiting to all API endpoints except health checks and documentation.
"""

import logging

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.rate_limiter import api_limiter, user_api_limiter

logger = logging.getLogger(__name__)

# Endpoints exempt from rate limiting
EXEMPT_PATHS = [
    "/docs",
    "/redoc",
    "/openapi.json",
    "/health",
    "/metrics",
    "/favicon.ico",
    # Auth endpoints use their own per-endpoint Redis rate limits in auth.py
    "/api/v1/auth/",
]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to apply rate limiting globally."""

    async def dispatch(self, request: Request, call_next):
        """Apply rate limiting to all requests except exempt paths.

        Two layers are checked:
        1. IP-based limit (``api_limiter``) — always applied.
        2. Per-user limit (``user_api_limiter``) — applied only when the
           request carries a valid JWT (``request.state.user_id`` set by
           ``UserContextMiddleware``).

        Both layers use the same Redis-backed ``AsyncRateLimiter`` with an
        in-memory fallback, so the system degrades gracefully when Redis is
        unavailable.
        """

        # Skip rate limiting for exempt paths
        if any(request.url.path.startswith(path) for path in EXEMPT_PATHS):
            return await call_next(request)

        # Build the IP-based key (always present)
        client_ip = request.client.host if request.client else "unknown"
        ip_key = f"ip:{client_ip}"

        # Check if authenticated — UserContextMiddleware sets user_id from JWT
        user_id = getattr(request.state, "user_id", None)
        user_key = f"user:{user_id}" if user_id else None

        # Track remaining counts for response headers
        ip_remaining = None
        user_remaining = None

        try:
            # --- Layer 1: IP-based rate limit (all requests) ---
            if not await api_limiter.is_allowed(ip_key):
                ip_remaining = await api_limiter.get_remaining_calls(ip_key)
                logger.warning(
                    f"IP rate limit exceeded for {ip_key} on {request.url.path}. "
                    f"Remaining: {ip_remaining}/{api_limiter.calls_per_minute}"
                )
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": {
                            "error": "Rate limit exceeded",
                            "message": (
                                f"Too many requests. Maximum"
                                f" {api_limiter.calls_per_minute}"
                                " requests per minute."
                            ),
                            "retry_after": 60,
                            "remaining_calls": 0,
                        }
                    },
                )

            ip_remaining = await api_limiter.get_remaining_calls(ip_key)
            if ip_remaining < 10:
                logger.info(
                    f"{ip_key} approaching rate limit on {request.url.path}. "
                    f"Remaining: {ip_remaining}/{api_limiter.calls_per_minute}"
                )

            # --- Layer 2: Per-user rate limit (authenticated requests only) ---
            if user_key is not None:
                if not await user_api_limiter.is_allowed(user_key):
                    user_remaining = await user_api_limiter.get_remaining_calls(user_key)
                    logger.warning(
                        f"User rate limit exceeded for {user_key} on {request.url.path}. "
                        f"Remaining: {user_remaining}/{user_api_limiter.calls_per_minute}"
                    )
                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={
                            "detail": {
                                "error": "Rate limit exceeded",
                                "message": (
                                    "Too many requests. Maximum"
                                    f" {user_api_limiter.calls_per_minute}"
                                    "requests per minute per user."
                                ),
                                "retry_after": 60,
                                "remaining_calls": 0,
                            }
                        },
                    )

                user_remaining = await user_api_limiter.get_remaining_calls(user_key)
                if user_remaining < 10:
                    logger.info(
                        f"{user_key} approaching rate limit on {request.url.path}. "
                        f"Remaining: {user_remaining}/{user_api_limiter.calls_per_minute}"
                    )

        except Exception as e:
            # AsyncRateLimiter should never raise (it has its own memory fallback),
            # so this branch only fires for truly unexpected errors (e.g. bugs).
            # Log at CRITICAL and apply a conservative in-process limit so we
            # never fail completely open.
            logger.critical(
                "RateLimitMiddleware unexpected error (%s): %s — "
                "applying conservative in-process limit.",
                type(e).__name__,
                e,
                exc_info=True,
            )
            # Re-use the in-memory path of api_limiter directly as last resort
            if not api_limiter._memory_is_allowed(ip_key):
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": {"error": "Rate limit exceeded", "retry_after": 60}},
                )

        response = await call_next(request)

        # Add rate limit headers (best-effort; skip on limiter failure).
        # When both limits apply, expose the more restrictive one so clients
        # can throttle proactively.
        try:
            if user_key is not None and user_remaining is not None:
                effective_limit = user_api_limiter.calls_per_minute
                effective_remaining = user_remaining
            else:
                effective_limit = api_limiter.calls_per_minute
                effective_remaining = ip_remaining if ip_remaining is not None else 0

            response.headers["X-RateLimit-Limit"] = str(effective_limit)
            response.headers["X-RateLimit-Remaining"] = str(effective_remaining)
            response.headers["X-RateLimit-Reset"] = "60"  # seconds until reset
        except Exception:
            pass

        return response
