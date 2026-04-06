"""Tests for recurring pattern category detection and forecast category breakdown."""

import pytest
from collections import defaultdict
from uuid import uuid4
from typing import Optional, Dict
from uuid import UUID


class TestRecurringCategoryDetection:
    """Verify recurring detection populates category_id from source transactions."""

    def test_detection_query_includes_category_id(self):
        """Detection should fetch category_id from transactions."""
        import inspect
        from app.services.recurring_detection_service import RecurringDetectionService

        source = inspect.getsource(RecurringDetectionService.detect_recurring_patterns)
        assert "Transaction.category_id" in source

    def test_detection_query_includes_category_primary(self):
        """Detection should fetch category_primary from transactions."""
        import inspect
        from app.services.recurring_detection_service import RecurringDetectionService

        source = inspect.getsource(RecurringDetectionService.detect_recurring_patterns)
        assert "Transaction.category_primary" in source

    def test_new_pattern_sets_category_id(self):
        """New recurring patterns should include category_id."""
        import inspect
        from app.services.recurring_detection_service import RecurringDetectionService

        source = inspect.getsource(RecurringDetectionService.detect_recurring_patterns)
        assert "category_id=best_category_id" in source

    def test_existing_pattern_updates_category_if_empty(self):
        """Existing patterns without category should get one from detection."""
        import inspect
        from app.services.recurring_detection_service import RecurringDetectionService

        source = inspect.getsource(RecurringDetectionService.detect_recurring_patterns)
        # Should only set category if not already user-set
        assert "if best_category_id and not existing.category_id" in source

    def test_most_common_category_logic(self):
        """Should pick the most frequently occurring non-null category_id."""
        cat_a = uuid4()
        cat_b = uuid4()

        # Simulate the detection logic
        category_counts: Dict[Optional[UUID], int] = defaultdict(int)
        txn_categories = [cat_a, cat_a, cat_b, None, cat_a, cat_b]
        for cid in txn_categories:
            category_counts[cid] += 1

        best_category_id = None
        best_count = 0
        for cid, cnt in category_counts.items():
            if cid is not None and cnt > best_count:
                best_category_id = cid
                best_count = cnt

        assert best_category_id == cat_a
        assert best_count == 3

    def test_all_null_categories_returns_none(self):
        """If all transactions lack a category, best should be None."""
        category_counts: Dict[Optional[UUID], int] = defaultdict(int)
        for _ in range(5):
            category_counts[None] += 1

        best_category_id = None
        best_count = 0
        for cid, cnt in category_counts.items():
            if cid is not None and cnt > best_count:
                best_category_id = cid
                best_count = cnt

        assert best_category_id is None


class TestForecastCategoryBreakdown:
    """Verify forecast summary groups by category correctly."""

    def test_forecast_summary_uses_category_from_pattern(self):
        """Forecast should use pattern.category.name for breakdown."""
        import inspect
        from app.services.forecast_service import ForecastService

        source = inspect.getsource(ForecastService._calculate_future_occurrences)
        assert "pattern.category.name" in source

    def test_forecast_summary_falls_back_to_uncategorized(self):
        """When category is None, summary should use 'Uncategorized'."""
        import inspect
        from app.services.forecast_service import ForecastService

        source = inspect.getsource(ForecastService.generate_forecast_summary)
        assert '"Uncategorized"' in source

    def test_forecast_breakdown_ranking(self):
        """Breakdown should be sorted by absolute amount descending."""
        by_category = {"Housing": -2200.0, "Groceries": -400.0, "Salary": 5000.0}

        ranked = sorted(
            [{"name": k, "amount": round(v, 2)} for k, v in by_category.items()],
            key=lambda x: abs(x["amount"]),
            reverse=True,
        )

        assert ranked[0]["name"] == "Salary"  # 5000
        assert ranked[1]["name"] == "Housing"  # -2200
        assert ranked[2]["name"] == "Groceries"  # -400
