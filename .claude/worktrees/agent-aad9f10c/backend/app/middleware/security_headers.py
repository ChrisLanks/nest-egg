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
        is_docs_path = request.url.path in ("/docs", "/redoc", "/openapi.json")

        if settings.DEBUG and is_docs_path:
            # Swagger UI / ReDoc need CDN resources + inline scripts
            cdn = "https://cdn.jsdelivr.net"
            fastapi_cdn = "https://fastapi.tiangolo.com"
            unpkg = "https://unpkg.com"
            csp = (
                "default-src 'self'; "
                f"script-src 'self' 'unsafe-inline' 'unsafe-eval' {cdn}; "
                f"style-src 'self' 'unsafe-inline' {cdn} {unpkg}; "
                f"img-src 'self' data: {fastapi_cdn}; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )
        else:
            if settings.DEBUG:
                script_src = "'self' 'unsafe-eval'"
            else:
                script_src = "'self'"

            csp = (
                "default-src 'none'; "
                f"script-src {script_src}; "
                "style-src 'self'; "
                "img-src 'self' data:; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )

        response.headers["Content-Security-Policy"] = csp

        # Prevent clickjacking attacks
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Enable browser XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Enforce HTTPS for 1 year (only in production)
        # This header tells browsers to always use HTTPS for this domain
        if request.url.hostname not in ["localhost", "127.0.0.1"]:
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
