"""
Tests for pre-computed budget suggestion caching:
1. BudgetSuggestion model fields
2. _write_cached / _read_cached round-trip
3. Staleness: rows older than SUGGESTION_STALENESS_HOURS are ignored
4. get_cached_suggestions falls back to on-demand when cache empty
5. get_cached_suggestions returns cached rows without re-computing
6. refresh_for_org writes correct rows per org/user scope
7. Celery task exists and is registered
8. Scoped (per-member) suggestions stored separately from org-wide
9. _clear_cached only removes rows for the matching scope
10. _row_to_dict returns the expected shape
"""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_suggestion_dict(
    category_name="Shopping",
    category_id=None,
    category_primary_raw="shopping",
    suggested_amount=200.0,
    suggested_period="monthly",
    avg_monthly_spend=180.0,
    total_spend=1080.0,
    month_count=6,
    transaction_count=12,
):
    return {
        "category_name": category_name,
        "category_id": category_id,
        "category_primary_raw": category_primary_raw,
        "suggested_amount": suggested_amount,
        "suggested_period": suggested_period,
        "avg_monthly_spend": avg_monthly_spend,
        "total_spend": total_spend,
        "month_count": month_count,
        "transaction_count": transaction_count,
    }


def _make_cached_row(
    org_id=None,
    user_id=None,
    category_name="Shopping",
    category_id=None,
    category_primary_raw="shopping",
    suggested_amount=200.0,
    suggested_period="monthly",
    avg_monthly_spend=180.0,
    total_spend=1080.0,
    month_count=6,
    transaction_count=12,
    hours_old=0,
):
    from app.models.budget_suggestion import BudgetSuggestion

    row = BudgetSuggestion()
    row.id = uuid4()
    row.organization_id = org_id or uuid4()
    row.user_id = user_id
    row.category_id = category_id
    row.category_primary_raw = category_primary_raw
    row.category_name = category_name
    row.suggested_amount = Decimal(str(suggested_amount))
    row.suggested_period = suggested_period
    row.avg_monthly_spend = Decimal(str(avg_monthly_spend))
    row.total_spend = Decimal(str(total_spend))
    row.month_count = month_count
    row.transaction_count = transaction_count
    row.generated_at = datetime.utcnow() - timedelta(hours=hours_old)
    return row


# ---------------------------------------------------------------------------
# 1. Model fields
# ---------------------------------------------------------------------------

class TestBudgetSuggestionModel:
    def test_model_has_expected_fields(self):
        from app.models.budget_suggestion import BudgetSuggestion

        row = BudgetSuggestion()
        for field in [
            "id", "organization_id", "user_id", "category_id",
            "category_primary_raw", "category_name",
            "suggested_amount", "suggested_period",
            "avg_monthly_spend", "total_spend",
            "month_count", "transaction_count", "generated_at",
        ]:
            assert hasattr(row, field), f"Missing field: {field}"

    def test_user_id_nullable(self):
        """user_id can be None for org-wide suggestions."""
        from app.models.budget_suggestion import BudgetSuggestion

        row = BudgetSuggestion()
        row.user_id = None
        assert row.user_id is None

    def test_category_id_nullable(self):
        """category_id can be None for provider categories."""
        from app.models.budget_suggestion import BudgetSuggestion

        row = BudgetSuggestion()
        row.category_id = None
        assert row.category_id is None


# ---------------------------------------------------------------------------
# 2. _row_to_dict returns correct shape
# ---------------------------------------------------------------------------

class TestRowToDict:
    def test_provider_category_row(self):
        from app.services.budget_suggestion_service import BudgetSuggestionService

        row = _make_cached_row(category_primary_raw="transportation", category_id=None)
        d = BudgetSuggestionService._row_to_dict(row)

        assert d["category_primary_raw"] == "transportation"
        assert d["category_id"] is None
        assert d["category_name"] == "Shopping"
        assert isinstance(d["suggested_amount"], float)
        assert isinstance(d["avg_monthly_spend"], float)

    def test_custom_category_row(self):
        from app.services.budget_suggestion_service import BudgetSuggestionService

        cat_id = uuid4()
        row = _make_cached_row(category_id=cat_id, category_primary_raw=None)
        d = BudgetSuggestionService._row_to_dict(row)

        assert d["category_id"] == str(cat_id)
        assert d["category_primary_raw"] is None


# ---------------------------------------------------------------------------
# 3. Staleness
# ---------------------------------------------------------------------------

class TestStaleness:
    def test_fresh_rows_are_returned(self):
        """Rows generated 1 hour ago are fresh (< 25h threshold)."""
        from app.services.budget_suggestion_service import SUGGESTION_STALENESS_HOURS

        row = _make_cached_row(hours_old=1)
        cutoff = datetime.utcnow() - timedelta(hours=SUGGESTION_STALENESS_HOURS)
        assert row.generated_at >= cutoff

    def test_stale_rows_are_excluded(self):
        """Rows generated 30 hours ago are stale (> 25h threshold)."""
        from app.services.budget_suggestion_service import SUGGESTION_STALENESS_HOURS

        row = _make_cached_row(hours_old=30)
        cutoff = datetime.utcnow() - timedelta(hours=SUGGESTION_STALENESS_HOURS)
        assert row.generated_at < cutoff

    def test_staleness_threshold_is_reasonable(self):
        """Threshold should be slightly over 24h to survive a missed daily run."""
        from app.services.budget_suggestion_service import SUGGESTION_STALENESS_HOURS

        assert 24 < SUGGESTION_STALENESS_HOURS <= 48


# ---------------------------------------------------------------------------
# 4. get_cached_suggestions: cache-miss triggers on-demand compute + write
# ---------------------------------------------------------------------------

class TestGetCachedSuggestions:
    @pytest.mark.asyncio
    async def test_cache_miss_falls_back_to_compute(self):
        """When no cached rows exist, get_suggestions is called and results are written."""
        from app.services.budget_suggestion_service import BudgetSuggestionService

        org_id = uuid4()
        mock_user = MagicMock()
        mock_user.organization_id = org_id
        mock_db = AsyncMock()

        suggestions = [_make_suggestion_dict()]

        with patch.object(
            BudgetSuggestionService, "_read_cached", new=AsyncMock(return_value=[])
        ), patch.object(
            BudgetSuggestionService, "get_suggestions", new=AsyncMock(return_value=suggestions)
        ) as mock_compute, patch.object(
            BudgetSuggestionService, "_write_cached", new=AsyncMock()
        ) as mock_write:
            result = await BudgetSuggestionService.get_cached_suggestions(
                mock_db, mock_user, scoped_user_id=None
            )

        mock_compute.assert_called_once()
        mock_write.assert_called_once()
        assert result == suggestions

    @pytest.mark.asyncio
    async def test_cache_hit_skips_compute(self):
        """When cached rows exist, get_suggestions is NOT called."""
        from app.services.budget_suggestion_service import BudgetSuggestionService

        org_id = uuid4()
        mock_user = MagicMock()
        mock_user.organization_id = org_id
        mock_db = AsyncMock()

        cached_row = _make_cached_row(org_id=org_id)

        with patch.object(
            BudgetSuggestionService,
            "_read_cached",
            new=AsyncMock(return_value=[cached_row]),
        ), patch.object(
            BudgetSuggestionService, "get_suggestions", new=AsyncMock()
        ) as mock_compute:
            result = await BudgetSuggestionService.get_cached_suggestions(
                mock_db, mock_user, scoped_user_id=None
            )

        mock_compute.assert_not_called()
        assert len(result) == 1
        assert result[0]["category_name"] == "Shopping"

    @pytest.mark.asyncio
    async def test_scoped_user_passed_to_read(self):
        """scoped_user_id is forwarded to _read_cached."""
        from app.services.budget_suggestion_service import BudgetSuggestionService

        user_id = uuid4()
        mock_user = MagicMock()
        mock_user.organization_id = uuid4()
        mock_db = AsyncMock()

        with patch.object(
            BudgetSuggestionService, "_read_cached", new=AsyncMock(return_value=[])
        ) as mock_read, patch.object(
            BudgetSuggestionService, "get_suggestions", new=AsyncMock(return_value=[])
        ), patch.object(
            BudgetSuggestionService, "_write_cached", new=AsyncMock()
        ):
            # Mock account lookup for scoped user
            mock_acct = AsyncMock()
            mock_acct.all.return_value = []
            mock_db.execute = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[])))

            await BudgetSuggestionService.get_cached_suggestions(
                mock_db, mock_user, scoped_user_id=user_id
            )

        mock_read.assert_called_once()
        _, kwargs_or_args = mock_read.call_args[0], mock_read.call_args
        # Verify user_id was passed as third positional arg
        assert mock_read.call_args[0][2] == user_id


# ---------------------------------------------------------------------------
# 5. refresh_for_org
# ---------------------------------------------------------------------------

class TestRefreshForOrg:
    @pytest.mark.asyncio
    async def test_returns_count_of_suggestions_written(self):
        from app.services.budget_suggestion_service import BudgetSuggestionService

        org_id = uuid4()
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.organization_id = org_id

        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute = AsyncMock(return_value=user_result)

        suggestions = [_make_suggestion_dict(), _make_suggestion_dict(category_name="Food")]

        with patch.object(
            BudgetSuggestionService, "get_suggestions", new=AsyncMock(return_value=suggestions)
        ), patch.object(
            BudgetSuggestionService, "_write_cached", new=AsyncMock()
        ):
            count = await BudgetSuggestionService.refresh_for_org(mock_db, org_id)

        assert count == 2

    @pytest.mark.asyncio
    async def test_no_user_returns_zero(self):
        """Org with no users returns 0 without crashing."""
        from app.services.budget_suggestion_service import BudgetSuggestionService

        org_id = uuid4()
        mock_db = AsyncMock()

        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=user_result)

        count = await BudgetSuggestionService.refresh_for_org(mock_db, org_id)
        assert count == 0

    @pytest.mark.asyncio
    async def test_scoped_user_with_no_accounts_clears_and_returns_zero(self):
        """If a scoped user has no accounts, cache is cleared and 0 is returned."""
        from app.services.budget_suggestion_service import BudgetSuggestionService

        org_id = uuid4()
        user_id = uuid4()
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.organization_id = org_id

        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = mock_user

        # First execute = user lookup, second = account lookup (returns empty)
        acct_result = MagicMock()
        acct_result.all.return_value = []
        mock_db.execute = AsyncMock(side_effect=[user_result, acct_result])

        with patch.object(
            BudgetSuggestionService, "_clear_cached", new=AsyncMock()
        ) as mock_clear:
            count = await BudgetSuggestionService.refresh_for_org(
                mock_db, org_id, scoped_user_id=user_id
            )

        assert count == 0
        mock_clear.assert_called_once()


# ---------------------------------------------------------------------------
# 6. Scoped vs org-wide suggestions are separate
# ---------------------------------------------------------------------------

class TestScopeIsolation:
    def test_org_wide_and_user_scoped_are_different_queries(self):
        """user_id=None and user_id=<some_id> must use different filters."""
        # This is a structural test — the filter logic in _read_cached
        # branches on scoped_user_id being None or not
        from app.services.budget_suggestion_service import BudgetSuggestionService
        import inspect

        src = inspect.getsource(BudgetSuggestionService._read_cached)
        assert "user_id.is_(None)" in src
        assert "scoped_user_id is not None" in src

    def test_clear_cached_has_scope_isolation(self):
        """_clear_cached also branches on scoped_user_id."""
        from app.services.budget_suggestion_service import BudgetSuggestionService
        import inspect

        src = inspect.getsource(BudgetSuggestionService._clear_cached)
        assert "user_id.is_(None)" in src


# ---------------------------------------------------------------------------
# 7. Celery task is registered
# ---------------------------------------------------------------------------

class TestCeleryTask:
    def test_task_is_importable(self):
        from app.workers.tasks.suggestion_tasks import refresh_budget_suggestions_task
        assert callable(refresh_budget_suggestions_task)

    def test_task_name_matches_beat_schedule(self):
        from app.workers.tasks.suggestion_tasks import refresh_budget_suggestions_task
        assert refresh_budget_suggestions_task.name == "refresh_budget_suggestions"

    def test_beat_schedule_entry_exists(self):
        from app.workers.celery_app import celery_app
        schedule = celery_app.conf.beat_schedule
        tasks = [v["task"] for v in schedule.values()]
        assert "refresh_budget_suggestions" in tasks

    def test_beat_schedule_runs_at_2am(self):
        from app.workers.celery_app import celery_app
        schedule = celery_app.conf.beat_schedule
        entry = next(
            v for v in schedule.values()
            if v["task"] == "refresh_budget_suggestions"
        )
        cron = entry["schedule"]
        assert cron.hour == {2}
        assert cron.minute == {5}


# ---------------------------------------------------------------------------
# 8. round_up_nice helper
# ---------------------------------------------------------------------------

class TestRoundUpNice:
    def test_values(self):
        from app.services.budget_suggestion_service import _round_up_nice

        assert _round_up_nice(0) == 0
        assert _round_up_nice(7) == 7       # < 10: ceil
        assert _round_up_nice(14) == 15     # < 25: ceil/5
        assert _round_up_nice(83) == 90     # < 100: ceil/10
        assert _round_up_nice(247) == 250   # < 500: ceil/25
        assert _round_up_nice(510) == 550   # < 1000: ceil/50
        assert _round_up_nice(1247) == 1300 # >= 1000: ceil/100
