"""
Global rate limiting middleware.

Applies rate limiting to all API endpoints except health checks and documentation.
"""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.rate_limiter import api_limiter
import logging

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
        """Apply rate limiting to all requests except exempt paths."""

        # Skip rate limiting for exempt paths
        if any(request.url.path.startswith(path) for path in EXEMPT_PATHS):
            return await call_next(request)

        # Get user ID from request state (set by auth middleware)
        # For unauthenticated requests, use IP address
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            # Use IP address for unauthenticated requests
            client_ip = request.client.host if request.client else "unknown"
            rate_limit_key = f"ip:{client_ip}"
        else:
            rate_limit_key = f"user:{user_id}"

        # Check rate limit
        if not api_limiter.is_allowed(rate_limit_key):
            remaining = api_limiter.get_remaining_calls(rate_limit_key)
            logger.warning(
                f"Rate limit exceeded for {rate_limit_key} on {request.url.path}. "
                f"Remaining: {remaining}/{api_limiter.calls_per_minute}"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Maximum {api_limiter.calls_per_minute} requests per minute.",
                    "retry_after": 60,  # seconds
                    "remaining_calls": remaining,
                },
            )

        # Log rate limit status for monitoring (only when approaching limit)
        remaining = api_limiter.get_remaining_calls(rate_limit_key)
        if remaining < 10:
            logger.info(
                f"{rate_limit_key} approaching rate limit on {request.url.path}. "
                f"Remaining: {remaining}/{api_limiter.calls_per_minute}"
            )

        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(api_limiter.calls_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = "60"  # seconds until reset

        return response
