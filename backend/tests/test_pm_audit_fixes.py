"""Tests for PM audit fixes: auth rate limits, cache invalidation, pagination caps."""

import pytest


# ── Auth rate limit configuration ──────────────────────────────────────────────

class TestAuthRateLimits:
    """Verify auth endpoints have tightened rate limits."""

    def test_login_rate_limit_is_5_per_minute(self):
        """Login should allow max 5 attempts per minute per IP."""
        import ast
        import inspect
        from app.api.v1 import auth

        source = inspect.getsource(auth.login)
        # The rate_limit_service.check_rate_limit call should have max_requests=5
        assert "max_requests=5" in source
        assert "window_seconds=60" in source

    def test_register_rate_limit_is_5_per_10_minutes(self):
        """Registration should allow max 5 attempts per 10 minutes per IP."""
        import inspect
        from app.api.v1 import auth

        source = inspect.getsource(auth.register)
        assert "max_requests=5" in source
        assert "window_seconds=600" in source

    def test_forgot_password_rate_limit_is_3_per_hour(self):
        """Forgot password should allow max 3 attempts per hour."""
        import inspect
        from app.api.v1 import auth

        source = inspect.getsource(auth.forgot_password)
        assert "max_requests=3" in source
        assert "window_seconds=3600" in source

    def test_reset_password_rate_limit_is_3_per_hour(self):
        """Reset password should allow max 3 attempts per hour."""
        import inspect
        from app.api.v1 import auth

        source = inspect.getsource(auth.reset_password)
        assert "max_requests=3" in source
        assert "window_seconds=3600" in source


# ── Cache invalidation on category/label mutations ────────────────────────────

class TestCacheInvalidation:
    """Verify category and label mutations invalidate dashboard caches."""

    def test_category_create_invalidates_cache(self):
        """Creating a category should invalidate dashboard caches."""
        import inspect
        from app.api.v1 import categories

        source = inspect.getsource(categories.create_category)
        assert "cache_delete_pattern" in source

    def test_category_update_invalidates_cache(self):
        """Updating a category should invalidate dashboard caches."""
        import inspect
        from app.api.v1 import categories

        source = inspect.getsource(categories.update_category)
        assert "cache_delete_pattern" in source

    def test_category_delete_invalidates_cache(self):
        """Deleting a category should invalidate dashboard caches."""
        import inspect
        from app.api.v1 import categories

        source = inspect.getsource(categories.delete_category)
        assert "cache_delete_pattern" in source

    def test_label_create_invalidates_cache(self):
        """Creating a label should invalidate dashboard caches."""
        import inspect
        from app.api.v1 import labels

        source = inspect.getsource(labels.create_label)
        assert "cache_delete_pattern" in source

    def test_label_update_invalidates_cache(self):
        """Updating a label should invalidate dashboard caches."""
        import inspect
        from app.api.v1 import labels

        source = inspect.getsource(labels.update_label)
        assert "cache_delete_pattern" in source

    def test_label_delete_invalidates_cache(self):
        """Deleting a label should invalidate dashboard caches."""
        import inspect
        from app.api.v1 import labels

        source = inspect.getsource(labels.delete_label)
        assert "cache_delete_pattern" in source


# ── Pagination caps ────────────────────────────────────────────────────────────

class TestPaginationCaps:
    """Verify all list endpoints cap page_size at 200."""

    def test_transactions_list_capped_at_200(self):
        """Transaction list page_size should be capped at 200."""
        import inspect
        from app.api.v1 import transactions

        source = inspect.getsource(transactions.list_transactions)
        assert "le=200" in source

    def test_flagged_transactions_capped_at_200(self):
        """Flagged transactions page_size should be capped at 200."""
        import inspect
        from app.api.v1 import transactions

        source = inspect.getsource(transactions.list_flagged_transactions)
        assert "le=200" in source


# ── Cache invalidation pattern correctness ─────────────────────────────────────

class TestCachePatternFormat:
    """Verify cache invalidation uses correct key pattern."""

    def test_category_uses_org_scoped_pattern(self):
        """Cache invalidation should include org_id in pattern."""
        import inspect
        from app.api.v1 import categories

        source = inspect.getsource(categories.create_category)
        # Should match pattern: dashboard:*:{org_id}:*
        assert "dashboard:*:" in source
        assert "organization_id" in source

    def test_label_uses_org_scoped_pattern(self):
        """Cache invalidation should include org_id in pattern."""
        import inspect
        from app.api.v1 import labels

        source = inspect.getsource(labels.create_label)
        assert "dashboard:*:" in source
        assert "organization_id" in source
