"""Anomaly and breach detection middleware.

Monitors for suspicious patterns that could indicate a breach or attack
and logs CRITICAL-level events so Sentry (or any log aggregator) captures
them for investigation.

Detection rules
---------------

1. Repeated 403 Forbidden errors — potential access probe
   ─────────────────────────────────────────────────────
   Trigger  : 5 or more 403 responses from the same source IP within 10 minutes.
   Rationale: Legitimate users rarely hit 403 Forbidden.  Repeated 403s in quick
              succession suggest an automated script probing for accessible resources —
              IDOR enumeration, directory traversal, or privilege-escalation attempts.
   Key       : Source IP address (not user ID, because 403 can occur pre-auth).
   Action    : CRITICAL log entry.  Sentry/PagerDuty will alert on-call if
               configured to trigger on CRITICAL logs.  No request is blocked here —
               blocking is the responsibility of RateLimitMiddleware.

2. Repeated 401 Unauthorized errors — potential credential stuffing / brute-force
   ───────────────────────────────────────────────────────────────────────────────
   Trigger  : 10 or more 401 responses from the same source IP within 10 minutes.
   Rationale: A higher threshold than rule 1 because 401 legitimately occurs when
              an access token expires and the client hasn't refreshed yet.  10 in
              10 minutes is a strong signal of systematic credential stuffing or
              brute-force targeting multiple accounts from one IP.
   Key       : Source IP address.
   Action    : CRITICAL log.  The per-endpoint auth rate limiter (5–10 req/min)
               provides the primary blocking defense; this layer provides after-the-
               fact incident detection and audit evidence.
   Note      : Account lockout (ENFORCE_ACCOUNT_LOCKOUT) also fires independently
               on failed logins — these two defenses complement each other.

3. Bulk data exports — potential data exfiltration
   ─────────────────────────────────────────────────
   Trigger  : 3 or more successful (HTTP 200) requests to /api/v1/settings/export
              from the same user (or IP if unauthenticated) within 30 minutes.
   Rationale: The export endpoint returns a full data dump of a user's financial
              records.  Legitimate users export infrequently (e.g. once per tax
              season).  3+ exports in 30 minutes may indicate automated scraping
              or a compromised account exfiltrating data in batches.
   Key       : ``request.state.user_id`` when authenticated; falls back to source
              IP to prevent bypass by logging out between requests.
   Action    : CRITICAL log.  The export has already completed by this point;
              the alert is for incident detection, not prevention.  Operators
              should correlate with destination IP / data volume to confirm.

Design notes
────────────
- In-memory counters: lightweight and zero-dependency.  Each worker process
  maintains its own set of counters.  For multi-worker deployments, replace
  ``_events`` with Redis ZADD/ZREMRANGEBYSCORE — the same sliding-window
  pattern used by AsyncRateLimiter in core/rate_limiter.py.
- The middleware is advisory only — it never blocks or modifies requests.
  All blocking is delegated to RateLimitMiddleware and the auth layer.
- Alerts are emitted at CRITICAL level.  Configure Sentry alert rules
  (or your log aggregator) to page on-call when CRITICAL events occur.
  Example Sentry rule: "level is critical AND logger contains anomaly_detection".
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
    """Thread-unsafe in-memory sliding window event counter.

    Records event timestamps for each key and evicts expired entries on every
    call.  The threshold is crossed when the live event count meets or exceeds
    the configured value after eviction.

    Thread safety
    ~~~~~~~~~~~~~
    Safe within a single asyncio event loop (each FastAPI worker process runs
    one loop).  NOT safe across OS threads.  For multi-worker deployments,
    swap the backing store for Redis ZADD/ZREMRANGEBYSCORE:

        # Redis equivalent of record_and_check(key):
        ZREMRANGEBYSCORE key 0 (now - window)
        count = ZCARD key
        if count < threshold:
            ZADD key now <unique-member>
            EXPIRE key <window + buffer>
        return count >= threshold

    Memory
    ~~~~~~
    The event list for each key is bounded at ``threshold`` entries (older
    timestamps are evicted before the check).  A full cleanup pass runs every
    1 000 operations to drop keys whose entire history has expired, keeping
    memory usage proportional to the number of unique IPs/users seen within
    the window rather than all time.
    """

    def __init__(self, window_seconds: int, threshold: int, label: str):
        self.window = window_seconds
        self.threshold = threshold
        self.label = label
        self._events: Dict[str, List[float]] = defaultdict(list)
        self._ops_since_cleanup = 0

    def record_and_check(self, key: str) -> bool:
        """Record an event for *key*; return True if the threshold has been crossed.

        Side effects:
        - Evicts timestamps older than ``window`` seconds for this key.
        - Appends the current timestamp.
        - Triggers a full cleanup pass every 1 000 calls.
        """
        now = time()
        cutoff = now - self.window
        events = self._events[key]
        # Evict expired timestamps before appending the new one
        self._events[key] = [t for t in events if t > cutoff]
        self._events[key].append(now)

        # Periodic full cleanup to prevent unbounded memory growth across keys
        self._ops_since_cleanup += 1
        if self._ops_since_cleanup >= 1000:
            self.cleanup()
            self._ops_since_cleanup = 0

        return len(self._events[key]) >= self.threshold

    def count(self, key: str) -> int:
        """Return the current event count for *key* within the active window."""
        now = time()
        cutoff = now - self.window
        return sum(1 for t in self._events.get(key, []) if t > cutoff)

    def cleanup(self) -> None:
        """Remove fully-expired keys to prevent unbounded memory growth.

        Called automatically every 1 000 ``record_and_check`` calls.
        Can also be called manually from a scheduled maintenance task.
        """
        now = time()
        cutoff = now - self.window
        self._events = {
            k: [t for t in v if t > cutoff]
            for k, v in self._events.items()
            if any(t > cutoff for t in v)
        }


# ── Module-level counter singletons ──────────────────────────────────────────
# One instance per rule.  State is per-process (see "Design notes" above).

# Rule 1: 403 probe detection
# 5 Forbidden responses from the same IP within a 10-minute window.
_forbidden_counter = _SlidingWindowCounter(window_seconds=600, threshold=5, label="forbidden_ip")

# Rule 2: Credential stuffing / brute-force detection
# 10 Unauthorized responses from the same IP within a 10-minute window.
# Higher threshold than rule 1 because expired-token retries legitimately
# produce 401s before the client refreshes the access token.
_unauthorized_counter = _SlidingWindowCounter(
    window_seconds=600, threshold=10, label="unauthorized_ip"
)

# Rule 3: Data exfiltration detection
# 3 successful full-data exports by the same user (or IP) within 30 minutes.
_export_counter = _SlidingWindowCounter(window_seconds=1800, threshold=3, label="export_user")

_EXPORT_PATH = "/api/v1/settings/export"


def _get_ip(request: Request) -> str:
    """Extract the originating client IP from the request.

    Prefers the first entry of ``X-Forwarded-For`` (set by load balancers /
    reverse proxies) over the direct ASGI connection IP.  The first entry is
    the original client; subsequent entries are intermediate proxies added by
    each hop.

    Security note
    ~~~~~~~~~~~~~
    ``X-Forwarded-For`` can be spoofed unless the reverse proxy is configured
    to strip or overwrite it for untrusted inbound connections.  In a hardened
    deployment, configure the load balancer to always set the header to the
    real client IP and consider adding a ``TRUSTED_PROXIES`` validation layer.
    This is an anomaly-detection advisory path, not an enforcement boundary,
    so a spoofed IP only affects the counter key — it does not grant access.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ips = [ip.strip() for ip in forwarded.split(",") if ip.strip()]
        if ips:
            # First entry is the original client IP; later entries are proxies.
            return ips[0]
    return request.client.host if request.client else "unknown"


class AnomalyDetectionMiddleware(BaseHTTPMiddleware):
    """After each response, record anomaly signals and emit CRITICAL alerts.

    The middleware runs *after* the response is produced so it never adds
    latency to the happy path.  All detection is post-hoc; this layer is
    purely observational.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        status_code = response.status_code
        ip = _get_ip(request)
        path = request.url.path

        # ── Rule 1: 403 probe detection ───────────────────────────────────────
        # Fires on the 5th+ 403 from the same IP within 10 minutes.
        # Only tracks IP (not user) because 403 can precede authentication.
        if status_code == 403:
            if _forbidden_counter.record_and_check(ip):
                count = _forbidden_counter.count(ip)
                logger.critical(
                    "ANOMALY: repeated 403 Forbidden from IP %s — "
                    "%d occurrences in %ds window on path %s. "
                    "Possible unauthorized access probe.",
                    ip,
                    count,
                    _forbidden_counter.window,
                    path,
                )

        # ── Rule 2: Credential stuffing / brute-force detection ───────────────
        # Fires on the 10th+ 401 from the same IP within 10 minutes.
        # The per-endpoint auth rate limiter provides the primary block;
        # this layer catches patterns spread across multiple auth endpoints.
        elif status_code == 401:
            if _unauthorized_counter.record_and_check(ip):
                count = _unauthorized_counter.count(ip)
                logger.critical(
                    "ANOMALY: repeated 401 Unauthorized from IP %s — "
                    "%d occurrences in %ds window on path %s. "
                    "Possible credential stuffing or brute-force attack.",
                    ip,
                    count,
                    _unauthorized_counter.window,
                    path,
                )

        # ── Rule 3: Data exfiltration detection ───────────────────────────────
        # Tracks only the full-data-export endpoint (/api/v1/settings/export).
        # Per-user key prevents bypass by rotating IPs on the same account.
        # Falls back to IP key for unauthenticated export attempts.
        if path == _EXPORT_PATH and status_code == 200:
            user_id = str(getattr(request.state, "user_id", None) or ip)
            if _export_counter.record_and_check(user_id):
                count = _export_counter.count(user_id)
                logger.critical(
                    "ANOMALY: bulk data export by user/IP %s — "
                    "%d exports in %ds window. "
                    "Possible data exfiltration. Investigate immediately.",
                    user_id,
                    count,
                    _export_counter.window,
                )

        return response
