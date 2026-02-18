"""
Rate limiter for API endpoints.

Prevents abuse and DoS attacks by limiting requests per user.
"""

from typing import Dict, Optional
from time import time
from collections import defaultdict
from fastapi import HTTPException, status
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    In-memory rate limiter with sliding window.

    For production, consider Redis-based rate limiting for distributed systems.
    """

    def __init__(self, calls_per_minute: int = 100):
        """
        Initialize rate limiter.

        Args:
            calls_per_minute: Maximum calls allowed per minute per key
        """
        self.calls_per_minute = calls_per_minute
        self.calls: Dict[str, list] = defaultdict(list)

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


# Global rate limiters for different endpoint types
market_data_limiter = RateLimiter(calls_per_minute=100)  # Market data endpoints
api_limiter = RateLimiter(calls_per_minute=1000)  # General API endpoints


def check_rate_limit(
    user_id: str, limiter: Optional[RateLimiter] = None, endpoint: str = "api"
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

    if not limiter.is_allowed(key):
        remaining = limiter.get_remaining_calls(key)
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
    remaining = limiter.get_remaining_calls(key)
    if remaining < 10:
        logger.info(
            f"User {user_id} approaching rate limit on {endpoint}. "
            f"Remaining: {remaining}/{limiter.calls_per_minute}"
        )
