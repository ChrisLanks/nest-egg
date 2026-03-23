"""Tests for PM audit round 20 fixes.

Covers:
- budget_suggestion_service._get_monthly_breakdown: child category query was
  missing organization_id filter. A category from org A could theoretically
  include child categories from org B if IDs collided. Fixed to scope the
  child lookup to the requesting org.
"""

import inspect
from uuid import UUID, uuid4


def test_get_monthly_breakdown_accepts_organization_id():
    """_get_monthly_breakdown must accept an organization_id parameter."""
    from app.services.budget_suggestion_service import BudgetSuggestionService

    sig = inspect.signature(BudgetSuggestionService._get_monthly_breakdown)
    assert "organization_id" in sig.parameters, (
        "_get_monthly_breakdown must accept organization_id parameter"
    )


def test_get_monthly_breakdown_scopes_child_query():
    """Child category lookup must filter by organization_id when provided."""
    from app.services.budget_suggestion_service import BudgetSuggestionService

    source = inspect.getsource(BudgetSuggestionService._get_monthly_breakdown)
    assert "organization_id" in source, "Must reference organization_id in method body"
    # The child query must conditionally add the org filter
    assert "Category.organization_id" in source, (
        "Child category query must filter by Category.organization_id"
    )


def test_get_suggestions_passes_org_id_to_breakdown():
    """get_suggestions must pass user.organization_id to _get_monthly_breakdown."""
    from app.services.budget_suggestion_service import BudgetSuggestionService

    source = inspect.getsource(BudgetSuggestionService.get_suggestions)
    assert "user.organization_id" in source, (
        "get_suggestions must pass user.organization_id to _get_monthly_breakdown"
    )


def test_child_category_query_unscoped_pattern_removed():
    """The old unscoped child query pattern must not appear in the service."""
    from app.services import budget_suggestion_service as m

    source = inspect.getsource(m)
    # The old unscoped pattern: select(Category.id).where(Category.parent_category_id == ...)
    # without any org filter immediately following. We check that organization_id
    # appears near the parent_category_id filter.
    lines = source.splitlines()
    parent_lines = [i for i, l in enumerate(lines) if "parent_category_id ==" in l]
    for idx in parent_lines:
        # Within 5 lines of the parent_category_id filter there must be org scoping
        nearby = "\n".join(lines[idx: idx + 5])
        assert "organization_id" in nearby, (
            f"Line {idx}: child category query near parent_category_id must scope to org"
        )
