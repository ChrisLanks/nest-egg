"""Tests for savings_goal_service JSON → JSONB cast fix.

The shared_user_ids column is JSON (not JSONB). SQLAlchemy's .contains()
generates @> which is JSONB-only. All three methods that check
shared_user_ids must now cast to JSONB before calling .contains().
"""

import inspect


def test_get_goal_uses_jsonb_cast():
    """get_goal must cast shared_user_ids to JSONB before .contains()."""
    from app.services.savings_goal_service import SavingsGoalService
    source = inspect.getsource(SavingsGoalService.get_goal)
    assert "JSONB" in source or "cast" in source, (
        "get_goal must cast shared_user_ids to JSONB"
    )
    assert ".contains(" in source, "get_goal must use .contains() for shared_user_ids check"


def test_auto_sync_goals_uses_jsonb_cast():
    """auto_sync_goals must cast shared_user_ids to JSONB before .contains()."""
    from app.services.savings_goal_service import SavingsGoalService
    source = inspect.getsource(SavingsGoalService.auto_sync_goals)
    assert "JSONB" in source or "cast" in source, (
        "auto_sync_goals must cast shared_user_ids to JSONB"
    )
    assert ".contains(" in source


def test_reorder_goals_uses_jsonb_cast():
    """reorder_goals must cast shared_user_ids to JSONB before .contains()."""
    from app.services.savings_goal_service import SavingsGoalService
    source = inspect.getsource(SavingsGoalService.reorder_goals)
    assert "JSONB" in source or "cast" in source, (
        "reorder_goals must cast shared_user_ids to JSONB"
    )
    assert ".contains(" in source


def test_jsonb_import_present():
    """JSONB must be imported from sqlalchemy.dialects.postgresql."""
    import app.services.savings_goal_service as mod
    source = inspect.getsource(mod)
    assert "from sqlalchemy.dialects.postgresql import JSONB" in source, (
        "JSONB must be imported from sqlalchemy.dialects.postgresql"
    )
