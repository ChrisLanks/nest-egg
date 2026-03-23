"""Tests for PM audit round 17 fixes.

Covers:
1. taxgraphs_provider: naive datetime.now() → datetime.now(timezone.utc)
   - tax_year() and _load_data() both used naive datetime, risking wrong year
     at midnight UTC on year boundaries when server is in a non-UTC timezone.

2. retirement_planner_service: N+1 query in get_scenario_summary_with_scores
   - Was calling get_latest_result() in a loop (1 query per scenario).
   - Fixed to use a single batch subquery join.
"""

import inspect
from datetime import timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


# ─── Tax rate provider: UTC datetime ─────────────────────────────────────────


def test_taxgraphs_provider_tax_year_uses_utc():
    """tax_year() must return datetime.now(timezone.utc).year, not naive datetime.now().year."""
    from app.services.tax_rate_providers.taxgraphs_provider import TaxGraphsProvider

    source = inspect.getsource(TaxGraphsProvider.tax_year)
    assert "datetime.now()" not in source, (
        "tax_year() must not use naive datetime.now() — use datetime.now(timezone.utc)"
    )
    assert "timezone.utc" in source, "tax_year() must use timezone.utc"


def test_taxgraphs_provider_load_data_uses_utc():
    """_load_data() must use timezone-aware datetime for current_year."""
    from app.services.tax_rate_providers import taxgraphs_provider

    source = inspect.getsource(taxgraphs_provider)
    # Must not contain bare datetime.now() anywhere
    assert "datetime.now()" not in source, (
        "_load_data() must not use naive datetime.now() — use datetime.now(timezone.utc)"
    )


def test_taxgraphs_provider_tax_year_returns_int():
    """tax_year() must return current UTC year as an int."""
    from app.services.tax_rate_providers.taxgraphs_provider import TaxGraphsProvider

    provider = TaxGraphsProvider.__new__(TaxGraphsProvider)
    year = provider.tax_year()
    assert isinstance(year, int)
    assert year >= 2024


def test_taxgraphs_provider_import_has_timezone():
    """taxgraphs_provider must import timezone from datetime."""
    from app.services.tax_rate_providers import taxgraphs_provider

    source = inspect.getsource(taxgraphs_provider)
    assert "from datetime import" in source
    assert "timezone" in source


# ─── Retirement planner service: batch query (no N+1) ────────────────────────


def test_get_scenario_summary_no_n_plus_one_in_source():
    """get_scenario_summary_with_scores must NOT call get_latest_result() — that's the N+1 pattern."""
    from app.services.retirement.retirement_planner_service import RetirementPlannerService

    source = inspect.getsource(RetirementPlannerService.get_scenario_summary_with_scores)
    # Must not *call* get_latest_result (mentions in docstring are fine)
    assert "await RetirementPlannerService.get_latest_result" not in source, (
        "get_scenario_summary_with_scores must not call get_latest_result() — use batch query"
    )
    assert "await self.get_latest_result" not in source


def test_get_scenario_summary_uses_batch_query():
    """get_scenario_summary_with_scores must use a subquery + in_() batch fetch."""
    from app.services.retirement.retirement_planner_service import RetirementPlannerService

    source = inspect.getsource(RetirementPlannerService.get_scenario_summary_with_scores)
    assert "scenario_ids" in source, "Must collect scenario_ids for batch query"
    assert ".in_(" in source, "Must use .in_() to batch fetch results"
    assert "group_by" in source, "Must group_by scenario_id for latest result"


def test_get_scenario_summary_empty_list():
    """Returns [] immediately when scenarios list is empty — no DB query."""
    import asyncio
    from app.services.retirement.retirement_planner_service import RetirementPlannerService

    db = AsyncMock()
    result = asyncio.get_event_loop().run_until_complete(
        RetirementPlannerService.get_scenario_summary_with_scores(db, [])
    )
    assert result == []
    db.execute.assert_not_called()


def test_get_scenario_summary_with_results():
    """Correctly merges batch results into summary dicts."""
    import asyncio
    from decimal import Decimal
    from unittest.mock import patch as mock_patch
    from app.services.retirement.retirement_planner_service import RetirementPlannerService

    sid1 = uuid4()
    sid2 = uuid4()

    # Mock scenarios
    s1 = MagicMock()
    s1.id = sid1
    s1.user_id = uuid4()
    s1.name = "Scenario A"
    s1.retirement_age = 65
    s1.is_default = True
    s1.updated_at = None

    s2 = MagicMock()
    s2.id = sid2
    s2.user_id = uuid4()
    s2.name = "Scenario B"
    s2.retirement_age = 62
    s2.is_default = False
    s2.updated_at = None

    # Mock DB result — only s1 has a result
    result_row = MagicMock()
    result_row.scenario_id = sid1
    result_row.readiness_score = 82
    result_row.success_rate = Decimal("0.87")

    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [result_row]
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value = mock_scalars

    db = AsyncMock()
    db.execute.return_value = mock_execute_result

    summaries = asyncio.get_event_loop().run_until_complete(
        RetirementPlannerService.get_scenario_summary_with_scores(db, [s1, s2])
    )

    assert len(summaries) == 2

    a = next(x for x in summaries if x["id"] == sid1)
    assert a["readiness_score"] == 82
    assert abs(a["success_rate"] - 0.87) < 0.001

    b = next(x for x in summaries if x["id"] == sid2)
    assert b["readiness_score"] is None
    assert b["success_rate"] is None

    # DB was queried exactly once (batch), not twice
    assert db.execute.call_count == 1
