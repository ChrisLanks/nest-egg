"""
Rate limiter for API endpoints.

Prevents abuse and DoS attacks by limiting requests per user.
Two implementations are provided:

- RateLimiter: sync in-memory sliding window (used by market_data and tests)
- AsyncRateLimiter: async Redis-backed sliding window with in-memory fallback
  (used by the global RateLimitMiddleware so it works across multiple workers)
"""

import uuid
from typing import Dict, Optional
from time import time
from collections import defaultdict
from fastapi import HTTPException, status
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    In-memory rate limiter with sliding window.

    For production horizontal scaling use AsyncRateLimiter instead.
    """

    def __init__(self, calls_per_minute: int = 100):
        """
        Initialize rate limiter.

        Args:
            calls_per_minute: Maximum calls allowed per minute per key
        """
        self.calls_per_minute = calls_per_minute
        self.calls: Dict[str, list] = defaultdict(list)
        self._last_cleanup: float = time()

    def is_allowed(self, key: str) -> bool:
        """
        Check if request is allowed.

        Args:
            key: Unique identifier (e.g., user_id, IP address)

        Returns:
            True if allowed, False if rate limit exceeded
        """
        now = time()
        minute_ago = now - 60

        # Remove calls older than 1 minute (sliding window)
        self.calls[key] = [timestamp for timestamp in self.calls[key] if timestamp > minute_ago]

        # Check if limit exceeded
        if len(self.calls[key]) >= self.calls_per_minute:
            logger.warning(
                f"Rate limit exceeded for {key}: " f"{len(self.calls[key])} calls in last minute"
            )
            return False

        # Record this call
        self.calls[key].append(now)

        # Periodic cleanup to prevent unbounded memory growth
        if now - self._last_cleanup > 300:  # Every 5 minutes
            self.cleanup_old_entries(max_age_seconds=300)
            self._last_cleanup = now

        return True

    def get_remaining_calls(self, key: str) -> int:
        """Get remaining calls for this minute."""
        now = time()
        minute_ago = now - 60

        # Count calls in last minute
        recent_calls = sum(1 for t in self.calls.get(key, []) if t > minute_ago)
        return max(0, self.calls_per_minute - recent_calls)

    def reset(self, key: str) -> None:
        """Reset rate limit for a specific key (admin use)."""
        if key in self.calls:
            del self.calls[key]
            logger.info(f"Rate limit reset for {key}")

    def cleanup_old_entries(self, max_age_seconds: int = 3600) -> None:
        """
        Cleanup old entries to prevent memory leak.

        Call this periodically (e.g., every hour via Celery task).
        """
        now = time()
        cutoff = now - max_age_seconds

        keys_to_delete = []
        for key, timestamps in self.calls.items():
            # Remove old timestamps
            self.calls[key] = [t for t in timestamps if t > cutoff]

            # If no recent calls, mark for deletion
            if not self.calls[key]:
                keys_to_delete.append(key)

        # Delete empty entries
        for key in keys_to_delete:
            del self.calls[key]

        logger.info(f"Rate limiter cleanup: removed {len(keys_to_delete)} inactive keys")


# Lua script for atomic Redis sliding-window rate limiting.
# Returns 1 if the request is allowed, 0 if rate-limited.
_RATE_LIMIT_SCRIPT = """
local key     = KEYS[1]
local now     = tonumber(ARGV[1])
local window  = tonumber(ARGV[2])
local limit   = tonumber(ARGV[3])
local member  = ARGV[4]

redis.call('ZREMRANGEBYSCORE', key, 0, now - window)

local count = redis.call('ZCARD', key)

if count < limit then
    redis.call('ZADD', key, now, member)
    redis.call('EXPIRE', key, window + 60)
    return 1
else
    return 0
end
"""


class AsyncRateLimiter:
    """
    Async rate limiter with Redis-backed sliding window.

    Falls back to an in-memory sliding window when Redis is unavailable
    (e.g., local development without Redis running).  Uses a Lua script
    for atomic check-and-increment to avoid race conditions across workers.
    """

    def __init__(self, calls_per_minute: int = 100):
        self.calls_per_minute = calls_per_minute
        self._redis_client = None
        self._redis_initialized = False
        self._script_sha: Optional[str] = None
        # In-memory fallback state
        self._memory_calls: Dict[str, list] = defaultdict(list)
        self._last_cleanup: float = time()

    async def _get_redis(self):
        """Lazily initialise the Redis client; returns None when unavailable."""
        if not self._redis_initialized:
            try:
                import redis.asyncio as aioredis

                client = aioredis.from_url(
                    settings.REDIS_URL, encoding="utf-8", decode_responses=True
                )
                await client.ping()
                self._redis_client = client
                logger.debug("AsyncRateLimiter: Redis connection established")
            except Exception as e:
                logger.debug(
                    f"AsyncRateLimiter: Redis unavailable, using in-memory fallback ({e})"
                )
                self._redis_client = None
            finally:
                self._redis_initialized = True
        return self._redis_client

    async def _load_script(self, redis_client) -> str:
        """Load (or return cached SHA of) the Lua rate-limit script."""
        if self._script_sha is None:
            self._script_sha = await redis_client.script_load(_RATE_LIMIT_SCRIPT)
        return self._script_sha

    async def is_allowed(self, key: str) -> bool:
        """
        Check if request is allowed (async, Redis-backed with memory fallback).

        Args:
            key: Unique identifier (e.g., 'user:abc123', 'ip:1.2.3.4')

        Returns:
            True if allowed, False if rate limit exceeded
        """
        redis_client = await self._get_redis()

        if redis_client is not None:
            try:
                sha = await self._load_script(redis_client)
                now = time()
                member = f"{now}:{uuid.uuid4()}"
                result = await redis_client.evalsha(
                    sha,
                    1,
                    f"ratelimit:{key}",
                    str(now),
                    "60",
                    str(self.calls_per_minute),
                    member,
                )
                allowed = bool(result)
                if not allowed:
                    logger.warning(f"Rate limit exceeded for {key} (Redis)")
                return allowed
            except Exception as e:
                logger.warning(f"AsyncRateLimiter Redis error, falling back to memory: {e}")
                # Reset so next request retries the Redis connection
                self._redis_initialized = False

        return self._memory_is_allowed(key)

    def _memory_is_allowed(self, key: str) -> bool:
        now = time()
        minute_ago = now - 60
        self._memory_calls[key] = [t for t in self._memory_calls[key] if t > minute_ago]

        if len(self._memory_calls[key]) >= self.calls_per_minute:
            logger.warning(f"Rate limit exceeded for {key} (memory)")
            return False

        self._memory_calls[key].append(now)

        # Periodic cleanup to prevent unbounded memory growth
        if now - self._last_cleanup > 300:  # Every 5 minutes
            stale_keys = [k for k, v in self._memory_calls.items() if not v or v[-1] < now - 300]
            for k in stale_keys:
                del self._memory_calls[k]
            self._last_cleanup = now

        return True

    async def get_remaining_calls(self, key: str) -> int:
        """Return the number of requests still allowed in the current window."""
        redis_client = await self._get_redis()

        if redis_client is not None:
            try:
                now = time()
                redis_key = f"ratelimit:{key}"
                pipe = redis_client.pipeline()
                pipe.zremrangebyscore(redis_key, 0, now - 60)
                pipe.zcard(redis_key)
                results = await pipe.execute()
                count = results[1]
                return max(0, self.calls_per_minute - count)
            except Exception as e:
                logger.warning(f"AsyncRateLimiter Redis error in get_remaining_calls: {e}")

        # Memory fallback
        now = time()
        minute_ago = now - 60
        recent = sum(1 for t in self._memory_calls.get(key, []) if t > minute_ago)
        return max(0, self.calls_per_minute - recent)

    def reset(self, key: str) -> None:
        """Reset in-memory state for a key (Redis entries expire naturally)."""
        if key in self._memory_calls:
            del self._memory_calls[key]


# Global rate limiters for different endpoint types
market_data_limiter = AsyncRateLimiter(calls_per_minute=100)  # Market data endpoints (async, Redis-backed)
api_limiter = AsyncRateLimiter(calls_per_minute=1000)  # Global middleware (async, Redis-backed)


async def check_rate_limit(
    user_id: str, limiter: Optional[AsyncRateLimiter] = None, endpoint: str = "api"
) -> None:
    """
    Check rate limit and raise HTTPException if exceeded.

    Args:
        user_id: User identifier
        limiter: Rate limiter instance (uses market_data_limiter if None)
        endpoint: Endpoint name for logging

    Raises:
        HTTPException: 429 Too Many Requests if rate limit exceeded
    """
    if limiter is None:
        limiter = market_data_limiter

    key = f"user:{user_id}"

    if not await limiter.is_allowed(key):
        remaining = await limiter.get_remaining_calls(key)
        logger.warning(
            f"Rate limit exceeded for user {user_id} on {endpoint}. " f"Remaining: {remaining}"
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "message": f"Too many requests. Maximum {limiter.calls_per_minute} requests per minute.",
                "retry_after": 60,  # seconds
                "remaining_calls": remaining,
            },
        )

    # Log rate limit status for monitoring
    remaining = await limiter.get_remaining_calls(key)
    if remaining < 10:
        logger.info(
            f"User {user_id} approaching rate limit on {endpoint}. "
            f"Remaining: {remaining}/{limiter.calls_per_minute}"
        )
