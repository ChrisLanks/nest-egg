"""Rate limiting service using Redis."""

import hashlib
import logging
from typing import Optional

import redis.asyncio as redis
from fastapi import HTTPException, Request, status

from app.config import settings

logger = logging.getLogger(__name__)


class RateLimitService:
    """Service for rate limiting API endpoints using Redis."""

    def __init__(self):
        """Initialize Redis connection."""
        self.redis_client: Optional[redis.Redis] = None

    async def get_redis(self) -> redis.Redis:
        """Get or create Redis connection."""
        if self.redis_client is None:
            self.redis_client = redis.from_url(
                settings.REDIS_URL, encoding="utf-8", decode_responses=True
            )
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
        hash_key = hashlib.md5(f"{identifier}:{endpoint}".encode(), usedforsecurity=False).hexdigest()  # nosec B324
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
            # Use the rightmost X-Forwarded-For IP (set by the last trusted proxy).
            # The leftmost IPs are client-supplied and can be spoofed; only the
            # rightmost entry is appended by infrastructure we control.
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                ips = [ip.strip() for ip in forwarded.split(",") if ip.strip()]
                identifier = ips[-1] if ips else (request.client.host if request.client else "unknown")
            else:
                identifier = request.client.host if request.client else "unknown"

        # Skip rate limiting when no real client IP is available (e.g., test environment)
        if identifier == "unknown":
            return

        # Skip rate limiting in development — Redis may not be running locally,
        # and devs need rapid iteration without hitting limits.
        if settings.ENVIRONMENT == "development":
            return

        # Get Redis client
        redis_client = await self.get_redis()

        # Generate rate limit key
        key = self._get_rate_limit_key(identifier, request.url.path)

        try:
            # Get current count
            current = await redis_client.get(key)

            if current is None:
                # First request in window
                await redis_client.setex(key, window_seconds, 1)
            else:
                current_count = int(current)

                if current_count >= max_requests:
                    # Rate limit exceeded
                    ttl = await redis_client.ttl(key)
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail={
                            "error": "Rate limit exceeded",
                            "message": f"Too many requests. Please try again in {ttl} seconds.",
                            "retry_after": ttl,
                        },
                        headers={"Retry-After": str(ttl)},
                    )

                # Increment counter
                await redis_client.incr(key)

        except HTTPException:
            # Re-raise rate limit errors
            raise
        except Exception as e:
            # Fail-open: if Redis is unavailable, allow the request through
            # rather than blocking all users.  This is acceptable because the
            # global RateLimitMiddleware (AsyncRateLimiter) provides a second
            # layer of defense, and individual endpoints are also protected by
            # per-IP rate limits once Redis recovers.
            logger.warning("Rate limit check failed (fail-open): %s", e)

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
