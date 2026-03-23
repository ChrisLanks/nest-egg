"""Tests for PM audit round 21 fixes.

Covers three savings-goal authorization bugs:

1. record_contribution: was only checking organization_id — any org member
   could contribute to any goal. Fixed to use get_goal() which enforces
   user_id ownership + is_shared access rules.

2. auto_sync_goals: fetched ALL org auto-sync goals, leaking private goals
   from other users. Fixed to scope to user_id owner or shared access.

3. reorder_goals: allowed reordering any org goal by ID. Fixed to scope to
   goals the requesting user owns or has shared access to.
"""

import inspect


def test_record_contribution_uses_get_goal():
    """record_contribution must use savings_goal_service.get_goal() not a direct org-only query."""
    from app.api.v1.savings_goals import record_contribution

    source = inspect.getsource(record_contribution)
    # Must delegate to get_goal for proper ownership check
    assert "get_goal" in source, (
        "record_contribution must call savings_goal_service.get_goal() to verify ownership"
    )
    # Must NOT use the old direct org-only query
    assert "SavingsGoal.organization_id == current_user.organization_id" not in source, (
        "record_contribution must not bypass ownership with org-only query"
    )


def test_auto_sync_goals_scoped_to_user():
    """auto_sync_goals must filter by user_id or shared access, not just organization_id."""
    from app.services.savings_goal_service import SavingsGoalService

    source = inspect.getsource(SavingsGoalService.auto_sync_goals)
    assert "user_id == user.id" in source or "SavingsGoal.user_id" in source, (
        "auto_sync_goals must filter by user_id ownership"
    )
    assert "is_shared" in source, (
        "auto_sync_goals must include shared-goal access logic"
    )


def test_reorder_goals_scoped_to_user():
    """reorder_goals must filter by user_id or shared access, not just organization_id."""
    from app.services.savings_goal_service import SavingsGoalService

    source = inspect.getsource(SavingsGoalService.reorder_goals)
    assert "user_id == user.id" in source or "SavingsGoal.user_id" in source, (
        "reorder_goals must filter by user_id ownership"
    )
    assert "is_shared" in source, (
        "reorder_goals must include shared-goal access logic"
    )


def test_auto_sync_ownership_matches_get_goal_pattern():
    """auto_sync_goals ownership filter must mirror the get_goal() pattern."""
    from app.services.savings_goal_service import SavingsGoalService

    sync_source = inspect.getsource(SavingsGoalService.auto_sync_goals)
    get_source = inspect.getsource(SavingsGoalService.get_goal)

    # Both must use shared_user_ids.contains() for shared access
    assert "shared_user_ids.contains" in sync_source, (
        "auto_sync_goals must check shared_user_ids.contains() like get_goal()"
    )
    assert "shared_user_ids.contains" in get_source


def test_reorder_ownership_matches_get_goal_pattern():
    """reorder_goals ownership filter must mirror the get_goal() pattern."""
    from app.services.savings_goal_service import SavingsGoalService

    reorder_source = inspect.getsource(SavingsGoalService.reorder_goals)
    assert "shared_user_ids.contains" in reorder_source, (
        "reorder_goals must check shared_user_ids.contains() like get_goal()"
    )
