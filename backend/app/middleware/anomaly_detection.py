"""Anomaly and breach detection middleware.

Monitors for suspicious patterns that could indicate a breach or attack
and logs CRITICAL-level events so Sentry (or any log aggregator) captures
them for investigation.

Patterns tracked (all use in-memory sliding windows):
  - Repeated 403 Forbidden errors from the same IP
    Threshold: 5 within 10 minutes → potential unauthorized access probe
  - Repeated data export calls from the same user
    Threshold: 3 within 30 minutes → potential data exfiltration
  - Repeated 401 Unauthorized errors from the same IP
    Threshold: 10 within 10 minutes → potential credential stuffing / brute-force

Design notes:
  - In-memory counters: lightweight, single-process.  For multi-worker
    deployments, replace with Redis ZADD/ZCOUNT (same sliding-window
    pattern used by AsyncRateLimiter).
  - The middleware never blocks requests — detection is advisory.
    Rate limiting is handled by RateLimitMiddleware; this layer is for
    audit / incident detection only.
  - Alerts are logged at CRITICAL level.  Configure Sentry (or your log
    aggregator) to page on-call when CRITICAL log events occur.
"""

import logging
from collections import defaultdict
from time import time
from typing import Dict, List

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class _SlidingWindowCounter:
    """Thread-unsafe in-memory sliding window counter.

    Sufficient for a single async event loop (FastAPI). For multi-worker
    deployments, replace the backing store with Redis ZADD/ZREMRANGEBYSCORE.
    """

    def __init__(self, window_seconds: int, threshold: int, label: str):
        self.window = window_seconds
        self.threshold = threshold
        self.label = label
        self._events: Dict[str, List[float]] = defaultdict(list)

    def record_and_check(self, key: str) -> bool:
        """Record an event; return True if the threshold has been crossed."""
        now = time()
        cutoff = now - self.window
        events = self._events[key]
        # Evict expired timestamps
        self._events[key] = [t for t in events if t > cutoff]
        self._events[key].append(now)
        return len(self._events[key]) >= self.threshold

    def count(self, key: str) -> int:
        """Current event count for key within the window."""
        now = time()
        cutoff = now - self.window
        return sum(1 for t in self._events.get(key, []) if t > cutoff)

    def cleanup(self) -> None:
        """Remove fully-expired keys to prevent unbounded memory growth."""
        now = time()
        cutoff = now - self.window
        self._events = {k: [t for t in v if t > cutoff]
                        for k, v in self._events.items() if any(t > cutoff for t in v)}


# --- Counters (module-level singletons) ---

# 5 × 403s from same IP within 10 minutes
_forbidden_counter = _SlidingWindowCounter(
    window_seconds=600, threshold=5, label="forbidden_ip"
)

# 10 × 401s from same IP within 10 minutes (credential stuffing)
_unauthorized_counter = _SlidingWindowCounter(
    window_seconds=600, threshold=10, label="unauthorized_ip"
)

# 3 × export calls from same user within 30 minutes
_export_counter = _SlidingWindowCounter(
    window_seconds=1800, threshold=3, label="export_user"
)

_EXPORT_PATH = "/api/v1/settings/export"


def _get_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


class AnomalyDetectionMiddleware(BaseHTTPMiddleware):
    """After each response, record anomaly signals and emit CRITICAL logs."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        status_code = response.status_code
        ip = _get_ip(request)
        path = request.url.path

        # --- 403 probe detection ---
        if status_code == 403:
            if _forbidden_counter.record_and_check(ip):
                count = _forbidden_counter.count(ip)
                logger.critical(
                    "ANOMALY: repeated 403 Forbidden from IP %s — "
                    "%d occurrences in %ds window on path %s. "
                    "Possible unauthorized access probe.",
                    ip, count, _forbidden_counter.window, path,
                )

        # --- Credential stuffing detection ---
        elif status_code == 401:
            if _unauthorized_counter.record_and_check(ip):
                count = _unauthorized_counter.count(ip)
                logger.critical(
                    "ANOMALY: repeated 401 Unauthorized from IP %s — "
                    "%d occurrences in %ds window on path %s. "
                    "Possible credential stuffing or brute-force attack.",
                    ip, count, _unauthorized_counter.window, path,
                )

        # --- Data exfiltration detection ---
        if path == _EXPORT_PATH and status_code == 200:
            # Extract user ID from request state (set by UserContextMiddleware)
            user_id = str(getattr(request.state, "user_id", None) or ip)
            if _export_counter.record_and_check(user_id):
                count = _export_counter.count(user_id)
                logger.critical(
                    "ANOMALY: bulk data export by user/IP %s — "
                    "%d exports in %ds window. "
                    "Possible data exfiltration. Investigate immediately.",
                    user_id, count, _export_counter.window,
                )

        return response
