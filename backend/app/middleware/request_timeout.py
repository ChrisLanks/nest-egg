"""Middleware to enforce a maximum request duration.

Prevents slow queries or runaway endpoints from tying up Uvicorn workers
indefinitely. If a request exceeds the timeout, the response is aborted
with a 504 Gateway Timeout so the worker can serve other requests.
"""

import asyncio
import logging

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

# Default timeout (seconds).  Override via constructor.
DEFAULT_TIMEOUT = 120


class RequestTimeoutMiddleware(BaseHTTPMiddleware):
    """Abort requests that exceed *timeout_seconds*."""

    def __init__(self, app, timeout_seconds: int = DEFAULT_TIMEOUT):
        super().__init__(app)
        self.timeout_seconds = timeout_seconds

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            return await asyncio.wait_for(
                call_next(request), timeout=self.timeout_seconds
            )
        except asyncio.TimeoutError:
            logger.warning(
                "Request timeout (%ds): %s %s",
                self.timeout_seconds,
                request.method,
                request.url.path,
            )
            return JSONResponse(
                status_code=504,
                content={"detail": "Request timed out"},
            )
