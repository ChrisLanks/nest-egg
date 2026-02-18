"""Security headers middleware for production security hardening."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        # Content Security Policy - Prevent XSS attacks
        # This is an API-only backend (no HTML served), so we use strict CSP
        # No unsafe-inline or unsafe-eval in production for maximum security
        if settings.DEBUG:
            # Development: Allow eval for debugging
            script_src = "'self' 'unsafe-eval'"
        else:
            # Production: No unsafe directives
            script_src = "'self'"

        # Strict CSP for API responses (no inline scripts/styles)
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; "  # Block everything by default (API doesn't need resources)
            f"script-src {script_src}; "  # Only if API docs served
            "style-src 'self'; "  # Only for API docs styling
            "img-src 'self' data:; "  # Only for API docs images
            "connect-src 'self'; "  # API calls to self only
            "frame-ancestors 'none'; "  # Prevent embedding
            "base-uri 'self'; "
            "form-action 'self'"
        )

        # Prevent clickjacking attacks
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Enable browser XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Enforce HTTPS for 1 year (only in production)
        # This header tells browsers to always use HTTPS for this domain
        if not request.url.hostname in ["localhost", "127.0.0.1"]:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Referrer policy - don't send referrer to external sites
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions policy - disable unnecessary browser features
        response.headers["Permissions-Policy"] = (
            "geolocation=(), " "microphone=(), " "camera=(), " "payment=()"
        )

        return response
