"""Unit tests for rate limiter."""

import pytest
import time
from app.core.rate_limiter import RateLimiter, check_rate_limit
from fastapi import HTTPException


class TestRateLimiter:
    """Test suite for RateLimiter class."""

    def test_allows_requests_under_limit(self):
        """Should allow requests under the rate limit."""
        limiter = RateLimiter(calls_per_minute=10)

        for _ in range(10):
            assert limiter.is_allowed("user123") is True

    def test_blocks_requests_over_limit(self):
        """Should block requests over the rate limit."""
        limiter = RateLimiter(calls_per_minute=10)

        # Use up the limit
        for _ in range(10):
            limiter.is_allowed("user123")

        # Next request should be blocked
        assert limiter.is_allowed("user123") is False

    def test_resets_after_minute(self):
        """Should reset rate limit after 60 seconds."""
        limiter = RateLimiter(calls_per_minute=5)

        # Use up the limit
        for _ in range(5):
            limiter.is_allowed("user123")

        # Should be blocked
        assert limiter.is_allowed("user123") is False

        # Wait 61 seconds (slightly more than a minute)
        time.sleep(61)

        # Should be allowed again
        assert limiter.is_allowed("user123") is True

    def test_sliding_window(self):
        """Should use sliding window (not fixed window)."""
        limiter = RateLimiter(calls_per_minute=5)

        # Make 5 requests at t=0
        for _ in range(5):
            limiter.is_allowed("user123")

        # Wait 30 seconds
        time.sleep(30)

        # Should still be blocked (sliding window)
        assert limiter.is_allowed("user123") is False

        # Wait another 31 seconds (total 61 seconds from start)
        time.sleep(31)

        # Now should be allowed (requests from t=0 expired)
        assert limiter.is_allowed("user123") is True

    def test_separate_limits_per_user(self):
        """Should track limits separately for each user."""
        limiter = RateLimiter(calls_per_minute=5)

        # User 1 uses up their limit
        for _ in range(5):
            limiter.is_allowed("user1")

        # User 1 should be blocked
        assert limiter.is_allowed("user1") is False

        # User 2 should still be allowed
        assert limiter.is_allowed("user2") is True

    def test_get_remaining_calls(self):
        """Should correctly report remaining calls."""
        limiter = RateLimiter(calls_per_minute=10)

        # Initially should have 10 remaining
        assert limiter.get_remaining_calls("user123") == 10

        # After 3 calls, should have 7 remaining
        for _ in range(3):
            limiter.is_allowed("user123")

        assert limiter.get_remaining_calls("user123") == 7

    def test_reset_function(self):
        """Should reset rate limit for specific key."""
        limiter = RateLimiter(calls_per_minute=5)

        # Use up the limit
        for _ in range(5):
            limiter.is_allowed("user123")

        # Should be blocked
        assert limiter.is_allowed("user123") is False

        # Reset the user
        limiter.reset("user123")

        # Should be allowed again
        assert limiter.is_allowed("user123") is True

    def test_cleanup_old_entries(self):
        """Should cleanup old entries to prevent memory leak."""
        limiter = RateLimiter(calls_per_minute=10)

        # Make requests from multiple users
        for i in range(100):
            limiter.is_allowed(f"user{i}")

        # Should have 100 keys
        assert len(limiter.calls) == 100

        # Wait 2 seconds (more than max_age_seconds in test)
        time.sleep(2)

        # Cleanup with 1 second max age
        limiter.cleanup_old_entries(max_age_seconds=1)

        # Should have removed all keys (no recent calls)
        assert len(limiter.calls) == 0


class TestCheckRateLimitFunction:
    """Test suite for check_rate_limit helper function."""

    def test_check_rate_limit_raises_http_exception(self):
        """Should raise HTTPException when limit exceeded."""
        limiter = RateLimiter(calls_per_minute=5)

        # Use up the limit
        for _ in range(5):
            limiter.is_allowed("user:testuser")

        # Next check should raise 429
        with pytest.raises(HTTPException) as exc_info:
            check_rate_limit("testuser", limiter, "test_endpoint")

        assert exc_info.value.status_code == 429
        assert "Rate limit exceeded" in str(exc_info.value.detail)

    def test_check_rate_limit_allows_under_limit(self):
        """Should not raise exception when under limit."""
        limiter = RateLimiter(calls_per_minute=10)

        # Should not raise
        check_rate_limit("testuser", limiter, "test_endpoint")

    def test_check_rate_limit_formats_key(self):
        """Should format key with 'user:' prefix."""
        limiter = RateLimiter(calls_per_minute=5)

        # Use up the limit for user:testuser
        for _ in range(5):
            limiter.is_allowed("user:testuser")

        # Should be blocked
        with pytest.raises(HTTPException):
            check_rate_limit("testuser", limiter, "test_endpoint")

        # Different user should still work
        check_rate_limit("otheruser", limiter, "test_endpoint")


@pytest.mark.slow
class TestRateLimiterPerformance:
    """Performance tests for rate limiter (marked as slow)."""

    def test_handles_high_volume(self):
        """Should handle high volume of requests efficiently."""
        limiter = RateLimiter(calls_per_minute=1000)

        start_time = time.time()

        # Make 10,000 requests
        for i in range(10000):
            limiter.is_allowed(f"user{i % 100}")  # 100 users

        duration = time.time() - start_time

        # Should complete in under 1 second
        assert duration < 1.0

    def test_memory_efficiency(self):
        """Should not leak memory with many users."""
        limiter = RateLimiter(calls_per_minute=100)

        # Simulate 1000 users
        for i in range(1000):
            limiter.is_allowed(f"user{i}")

        # Wait for entries to age
        time.sleep(61)

        # Cleanup
        limiter.cleanup_old_entries(max_age_seconds=60)

        # Should have cleaned up all old entries
        assert len(limiter.calls) == 0
