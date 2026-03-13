"""
Redis-backed circuit breaker for external API calls.

Protects against cascading failures when external services (Plaid, Teller, MX)
are down or degraded. Instead of hammering a failing API and making users wait
for timeouts, the circuit breaker fails fast and lets the service recover.

States:
    CLOSED  - Normal operation. Failures are counted.
    OPEN    - Fail fast. All calls raise CircuitOpenError immediately.
    HALF_OPEN - Probe. A limited number of calls are allowed through to test recovery.

Redis keys per service:
    cb:{service_name}:state        - Current state (closed / open / half_open)
    cb:{service_name}:failures     - Consecutive failure count
    cb:{service_name}:last_failure - Timestamp of most recent failure (ISO 8601)
    cb:{service_name}:half_open_ok - Successful probe count while half-open
"""

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Optional

import redis.asyncio as redis

from app.config import settings

logger = logging.getLogger(__name__)

# ── Defaults ──────────────────────────────────────────────────────────────────
DEFAULT_FAILURE_THRESHOLD = 5
DEFAULT_COOLDOWN_SECONDS = 60
DEFAULT_HALF_OPEN_SUCCESSES = 2

# All known service names — used by the monitoring endpoint to enumerate breakers.
KNOWN_SERVICES = ("plaid", "teller", "mx")


class CircuitOpenError(Exception):
    """Raised when a call is rejected because the circuit is open."""

    def __init__(self, service_name: str):
        self.service_name = service_name
        super().__init__(f"Circuit breaker OPEN for {service_name} — failing fast")


class CircuitBreaker:
    """Redis-backed circuit breaker."""

    def __init__(
        self,
        failure_threshold: int = DEFAULT_FAILURE_THRESHOLD,
        cooldown_seconds: int = DEFAULT_COOLDOWN_SECONDS,
        half_open_successes: int = DEFAULT_HALF_OPEN_SUCCESSES,
    ):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.half_open_successes = half_open_successes
        self._redis: Optional[redis.Redis] = None

    # ── Redis access ──────────────────────────────────────────────────────

    async def _get_redis(self) -> redis.Redis:
        """Lazy-connect to Redis (same pattern as RateLimitService)."""
        if self._redis is None:
            self._redis = redis.from_url(
                settings.REDIS_URL, encoding="utf-8", decode_responses=True
            )
        return self._redis

    # ── Key helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _key(service_name: str, suffix: str) -> str:
        return f"cb:{service_name}:{suffix}"

    # ── Public API ────────────────────────────────────────────────────────

    async def call(
        self,
        service_name: str,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Wrap an async function call with circuit-breaker logic.

        Args:
            service_name: Logical name of the external service (e.g. "teller").
            func: An async callable to execute.
            *args, **kwargs: Forwarded to *func*.

        Returns:
            Whatever *func* returns on success.

        Raises:
            CircuitOpenError: If the circuit is open and cooldown has not elapsed.
            Exception: Any exception raised by *func* (after recording the failure).
        """
        try:
            r = await self._get_redis()
        except Exception:
            # Redis unavailable — fall through to normal behaviour.
            logger.debug("Circuit breaker Redis unavailable — bypassing for %s", service_name)
            return await func(*args, **kwargs)

        state = await self._get_state(r, service_name)

        # ── OPEN state ────────────────────────────────────────────────────
        if state == "open":
            if await self._cooldown_elapsed(r, service_name):
                # Transition to half-open and allow a probe call.
                await self._set_state(r, service_name, "half_open")
                logger.info(
                    "Circuit breaker %s: OPEN -> HALF_OPEN (cooldown elapsed)", service_name
                )
            else:
                raise CircuitOpenError(service_name)

        # ── Execute the call (CLOSED or HALF_OPEN) ───────────────────────
        try:
            result = await func(*args, **kwargs)
        except Exception:
            await self._record_failure(r, service_name)
            raise

        # ── Record success ────────────────────────────────────────────────
        await self._record_success(r, service_name)
        return result

    # ── State queries (used by monitoring endpoint) ───────────────────────

    async def get_service_status(self, service_name: str) -> dict:
        """Return current breaker status for a single service."""
        try:
            r = await self._get_redis()
        except Exception:
            return {
                "service": service_name,
                "state": "unknown",
                "failures": 0,
                "last_failure": None,
                "error": "Redis unavailable",
            }

        state = await self._get_state(r, service_name)

        # If open and cooldown has elapsed, report as half_open
        if state == "open" and await self._cooldown_elapsed(r, service_name):
            state = "half_open"

        failures = await r.get(self._key(service_name, "failures"))
        last_failure = await r.get(self._key(service_name, "last_failure"))

        return {
            "service": service_name,
            "state": state,
            "failures": int(failures) if failures else 0,
            "last_failure": last_failure,
            "failure_threshold": self.failure_threshold,
            "cooldown_seconds": self.cooldown_seconds,
        }

    async def get_all_statuses(self) -> list[dict]:
        """Return breaker status for all known services."""
        return [await self.get_service_status(s) for s in KNOWN_SERVICES]

    # ── Internal helpers ──────────────────────────────────────────────────

    async def _get_state(self, r: redis.Redis, service_name: str) -> str:
        try:
            val = await r.get(self._key(service_name, "state"))
            return val or "closed"
        except Exception:
            return "closed"

    async def _set_state(self, r: redis.Redis, service_name: str, state: str) -> None:
        try:
            await r.set(self._key(service_name, "state"), state)
            if state == "half_open":
                # Reset the probe success counter.
                await r.set(self._key(service_name, "half_open_ok"), 0)
        except Exception:
            logger.warning("Circuit breaker: failed to set state for %s", service_name)

    async def _cooldown_elapsed(self, r: redis.Redis, service_name: str) -> bool:
        try:
            last = await r.get(self._key(service_name, "last_failure"))
            if not last:
                return True
            last_dt = datetime.fromisoformat(last)
            elapsed = (datetime.now(timezone.utc) - last_dt).total_seconds()
            return elapsed >= self.cooldown_seconds
        except Exception:
            return True

    async def _record_failure(self, r: redis.Redis, service_name: str) -> None:
        try:
            pipe = r.pipeline()
            pipe.incr(self._key(service_name, "failures"))
            pipe.set(
                self._key(service_name, "last_failure"),
                datetime.now(timezone.utc).isoformat(),
            )
            results = await pipe.execute()
            failure_count = results[0]

            current_state = await self._get_state(r, service_name)

            if current_state == "half_open":
                # Any failure while probing re-opens the circuit immediately.
                await self._set_state(r, service_name, "open")
                logger.warning("Circuit breaker %s: HALF_OPEN -> OPEN (probe failed)", service_name)
            elif failure_count >= self.failure_threshold:
                await self._set_state(r, service_name, "open")
                logger.warning(
                    "Circuit breaker %s: CLOSED -> OPEN (failures=%d >= threshold=%d)",
                    service_name,
                    failure_count,
                    self.failure_threshold,
                )
        except Exception:
            logger.warning("Circuit breaker: failed to record failure for %s", service_name)

    async def _record_success(self, r: redis.Redis, service_name: str) -> None:
        try:
            current_state = await self._get_state(r, service_name)

            if current_state == "half_open":
                ok_count = await r.incr(self._key(service_name, "half_open_ok"))
                if ok_count >= self.half_open_successes:
                    # Enough successful probes — close the circuit.
                    await self._reset(r, service_name)
                    logger.info(
                        "Circuit breaker %s: HALF_OPEN -> CLOSED (probes=%d >= required=%d)",
                        service_name,
                        ok_count,
                        self.half_open_successes,
                    )
            elif current_state == "closed":
                # Reset the failure counter on any success while closed.
                await r.set(self._key(service_name, "failures"), 0)
        except Exception:
            logger.warning("Circuit breaker: failed to record success for %s", service_name)

    async def _reset(self, r: redis.Redis, service_name: str) -> None:
        """Reset a circuit to closed / clean state."""
        pipe = r.pipeline()
        pipe.set(self._key(service_name, "state"), "closed")
        pipe.set(self._key(service_name, "failures"), 0)
        pipe.delete(self._key(service_name, "last_failure"))
        pipe.delete(self._key(service_name, "half_open_ok"))
        await pipe.execute()


# ── Singleton ─────────────────────────────────────────────────────────────────

_circuit_breaker: Optional[CircuitBreaker] = None


def get_circuit_breaker() -> CircuitBreaker:
    """Get or create the circuit-breaker singleton."""
    global _circuit_breaker
    if _circuit_breaker is None:
        _circuit_breaker = CircuitBreaker()
    return _circuit_breaker
