"""Middleware to limit request body size and prevent DoS attacks."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to limit request body size.

    Prevents DoS attacks from extremely large request bodies.
    """

    def __init__(self, app, max_request_size: int = 10 * 1024 * 1024):
        """
        Initialize middleware.

        Args:
            app: FastAPI application
            max_request_size: Maximum request size in bytes (default: 10MB)
        """
        super().__init__(app)
        self.max_request_size = max_request_size

    async def dispatch(self, request: Request, call_next):
        """Check request size before processing."""
        max_mb = f"{self.max_request_size / (1024 * 1024):.1f}MB"

        # Fast path: reject obviously oversized requests via Content-Length header
        content_length = request.headers.get("content-length")
        if content_length:
            if int(content_length) > self.max_request_size:
                return JSONResponse(
                    status_code=413,
                    content={"detail": f"Request body too large. Maximum size is {max_mb}"},
                )

        # For state-changing methods, verify actual body size.
        # Content-Length can be omitted or spoofed with chunked encoding.
        if request.method in ("POST", "PUT", "PATCH"):
            body = await request.body()
            if len(body) > self.max_request_size:
                return JSONResponse(
                    status_code=413,
                    content={"detail": f"Request body too large. Maximum size is {max_mb}"},
                )

        response: Response = await call_next(request)
        return response
