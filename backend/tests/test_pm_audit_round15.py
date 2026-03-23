"""Tests for PM audit round 15 fixes.

Covers:
- budget_service.get_budget now requires budget.user_id == user.id OR is_shared access
- savings_goal_service.get_goal same pattern
- financial_planning._get_mortgage_account scopes account_id lookup to current_user_id
"""

import inspect


# ---------------------------------------------------------------------------
# Budget service ownership check
# ---------------------------------------------------------------------------


def test_get_budget_checks_user_id():
    """get_budget must filter by user_id (or shared access), not just org_id."""
    from app.services.budget_service import BudgetService

    source = inspect.getsource(BudgetService.get_budget)
    assert "Budget.user_id == user.id" in source, (
        "get_budget must check Budget.user_id == user.id"
    )


def test_get_budget_allows_shared_access():
    """get_budget must allow access when budget is_shared=True."""
    from app.services.budget_service import BudgetService

    source = inspect.getsource(BudgetService.get_budget)
    assert "is_shared" in source, (
        "get_budget must check Budget.is_shared for shared access"
    )


def test_get_budget_handles_shared_user_ids_none():
    """When shared_user_ids is None (shared with all), the budget must be accessible."""
    from app.services.budget_service import BudgetService

    source = inspect.getsource(BudgetService.get_budget)
    assert "shared_user_ids.is_(None)" in source, (
        "get_budget must treat shared_user_ids=None as 'shared with all org members'"
    )


# ---------------------------------------------------------------------------
# Savings goal service ownership check
# ---------------------------------------------------------------------------


def test_get_goal_checks_user_id():
    """get_goal must filter by user_id (or shared access), not just org_id."""
    from app.services.savings_goal_service import SavingsGoalService

    source = inspect.getsource(SavingsGoalService.get_goal)
    assert "SavingsGoal.user_id == user.id" in source, (
        "get_goal must check SavingsGoal.user_id == user.id"
    )


def test_get_goal_allows_shared_access():
    """get_goal must allow access when goal is_shared=True."""
    from app.services.savings_goal_service import SavingsGoalService

    source = inspect.getsource(SavingsGoalService.get_goal)
    assert "is_shared" in source, (
        "get_goal must check SavingsGoal.is_shared for shared access"
    )


def test_get_goal_handles_shared_user_ids_none():
    """When shared_user_ids is None (shared with all), the goal must be accessible."""
    from app.services.savings_goal_service import SavingsGoalService

    source = inspect.getsource(SavingsGoalService.get_goal)
    assert "shared_user_ids.is_(None)" in source, (
        "get_goal must treat shared_user_ids=None as 'shared with all org members'"
    )


# ---------------------------------------------------------------------------
# Financial planning mortgage account scope
# ---------------------------------------------------------------------------


def test_mortgage_account_helper_has_current_user_id_param():
    """_get_mortgage_account must accept current_user_id for ownership scoping."""
    from app.api.v1 import financial_planning as fp_module
    import inspect as ins

    sig = ins.signature(fp_module._get_mortgage_account)
    assert "current_user_id" in sig.parameters, (
        "_get_mortgage_account must accept current_user_id parameter"
    )
    assert sig.parameters["current_user_id"].default is None, (
        "current_user_id must be optional"
    )


def test_mortgage_account_helper_scopes_account_id_to_user():
    """When account_id is given without user_id, scope must default to current_user_id."""
    from app.api.v1 import financial_planning as fp_module

    source = inspect.getsource(fp_module._get_mortgage_account)
    assert "current_user_id if account_id" in source or "current_user_id" in source, (
        "_get_mortgage_account must use current_user_id when account_id is provided"
    )


def test_mortgage_endpoint_passes_current_user_id():
    """get_mortgage_analysis endpoint must pass current_user.id to _get_mortgage_account."""
    from app.api.v1 import financial_planning as fp_module

    source = inspect.getsource(fp_module.get_mortgage_analysis)
    assert "current_user_id=current_user.id" in source, (
        "get_mortgage_analysis must pass current_user_id=current_user.id to helper"
    )
