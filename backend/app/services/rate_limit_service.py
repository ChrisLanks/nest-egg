"""Rate limiting service using Redis with in-memory fallback.

Two layers of protection:
1. Redis (primary) — atomic Lua script, shared across all workers.
2. In-memory sliding window (fallback) — used when Redis is unavailable.
   This ensures rate limits are NEVER silently skipped; the fallback is
   per-process so limits are less precise under load, but they still apply.
"""

import hashlib
import logging
from collections import defaultdict
from time import time
from typing import Dict, Optional

import redis.asyncio as redis
from fastapi import HTTPException, Request, status

from app.config import settings

logger = logging.getLogger(__name__)

_REDIS_RETRY_COOLDOWN = 30  # seconds before re-attempting Redis after a failure

# Atomic rate-limit check via Lua script: INCR + conditional EXPIRE + TTL
_RATE_LIMIT_SCRIPT = """
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local current = redis.call('INCR', key)
if current == 1 then
    redis.call('EXPIRE', key, window)
end
local ttl = redis.call('TTL', key)
return {current, ttl}
"""


class RateLimitService:
    """Service for rate limiting API endpoints using Redis with in-memory fallback."""

    def __init__(self):
        """Initialize Redis connection and in-memory fallback state."""
        self.redis_client: Optional[redis.Redis] = None
        self._redis_failed_at: Optional[float] = None
        # In-memory fallback: key → list of (timestamp, window, max_requests) tuples
        # Simplified to list of timestamps per key; max_requests checked per call.
        self._memory_calls: Dict[str, list] = defaultdict(list)

    async def get_redis(self) -> Optional[redis.Redis]:
        """Get or create Redis connection, respecting the cooldown after failures."""
        # If Redis failed recently, don't retry until cooldown expires
        if self._redis_failed_at is not None:
            if time() - self._redis_failed_at < _REDIS_RETRY_COOLDOWN:
                return None
            # Cooldown elapsed — reset and retry
            self._redis_failed_at = None
            self.redis_client = None

        if self.redis_client is None:
            try:
                client = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
                await client.ping()
                self.redis_client = client
            except Exception as exc:
                logger.warning(
                    "RateLimitService: Redis unavailable, using memory fallback: %s", exc
                )
                self._redis_failed_at = time()
                return None
        return self.redis_client

    def _get_rate_limit_key(self, identifier: str, endpoint: str) -> str:
        """
        Generate rate limit key for Redis.

        Args:
            identifier: IP address or user identifier
            endpoint: API endpoint being accessed

        Returns:
            Redis key for rate limiting
        """
        # Hash to normalize key length — not used for security
        raw = f"{identifier}:{endpoint}".encode()
        hash_key = hashlib.md5(raw, usedforsecurity=False).hexdigest()  # nosec B324
        return f"rate_limit:{hash_key}"

    async def check_rate_limit(
        self,
        request: Request,
        max_requests: int = 5,
        window_seconds: int = 60,
        identifier: Optional[str] = None,
    ) -> None:
        """
        Check if request exceeds rate limit.

        Args:
            request: FastAPI request object
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
            identifier: Custom identifier (defaults to IP address)

        Raises:
            HTTPException: 429 Too Many Requests if limit exceeded
        """
        # Use IP address if no custom identifier provided
        if identifier is None:
            # Always use the direct client IP from the ASGI server.
            # X-Forwarded-For is not trustworthy without a verified proxy chain.
            identifier = request.client.host if request.client else "unknown"

        # Skip rate limiting when no real client IP is available (e.g., test environment)
        if identifier == "unknown":
            return

        # Skip rate limiting in test environment only — not development.
        # Development should still enforce rate limits for security parity.
        if settings.ENVIRONMENT == "test":
            return

        key = self._get_rate_limit_key(identifier, request.url.path)

        # Try Redis first; fall back to in-memory if unavailable
        redis_client = await self.get_redis()

        if redis_client is not None:
            try:
                # Atomic increment + expire + TTL via Lua script
                result = await redis_client.eval(
                    _RATE_LIMIT_SCRIPT, 1, key, max_requests, window_seconds
                )
                current_count, ttl = result[0], result[1]

                if current_count > max_requests:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail={
                            "error": "Rate limit exceeded",
                            "message": f"Too many requests. Please try again in {ttl} seconds.",
                            "retry_after": ttl,
                        },
                        headers={"Retry-After": str(ttl)},
                    )
                return  # Redis check passed

            except HTTPException:
                raise
            except Exception as exc:
                # Redis call failed mid-request — mark cooldown and fall through to memory
                logger.warning(
                    "RateLimitService Redis eval failed, switching to memory fallback: %s", exc
                )
                self._redis_failed_at = time()
                self.redis_client = None

        # In-memory fallback — never fail-open
        self._memory_check(key, max_requests, window_seconds)

    def _memory_check(self, key: str, max_requests: int, window_seconds: int) -> None:
        """In-memory sliding-window rate check. Raises 429 if limit exceeded."""
        now = time()
        cutoff = now - window_seconds
        calls = self._memory_calls[key]
        # Evict expired entries
        self._memory_calls[key] = [t for t in calls if t > cutoff]

        if len(self._memory_calls[key]) >= max_requests:
            retry_after = window_seconds
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Please try again in {retry_after} seconds.",
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        self._memory_calls[key].append(now)

    async def reset_rate_limit(self, identifier: str, endpoint: str) -> None:
        """
        Reset rate limit for a specific identifier and endpoint.

        Useful for testing or after successful authentication.

        Args:
            identifier: IP address or user identifier
            endpoint: API endpoint
        """
        redis_client = await self.get_redis()
        key = self._get_rate_limit_key(identifier, endpoint)
        await redis_client.delete(key)

    async def get_remaining_attempts(
        self, identifier: str, endpoint: str, max_requests: int = 5
    ) -> int:
        """
        Get remaining attempts before rate limit.

        Args:
            identifier: IP address or user identifier
            endpoint: API endpoint
            max_requests: Maximum requests allowed

        Returns:
            Number of remaining attempts
        """
        redis_client = await self.get_redis()
        key = self._get_rate_limit_key(identifier, endpoint)

        current = await redis_client.get(key)
        if current is None:
            return max_requests

        current_count = int(current)
        remaining = max_requests - current_count
        return max(0, remaining)


# Singleton instance
_rate_limit_service = None


def get_rate_limit_service() -> RateLimitService:
    """Get or create rate limit service singleton."""
    global _rate_limit_service
    if _rate_limit_service is None:
        _rate_limit_service = RateLimitService()
    return _rate_limit_service


# Create singleton instance for direct import
rate_limit_service = get_rate_limit_service()
