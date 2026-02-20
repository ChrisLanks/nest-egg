"""Unit tests for savings goal service allocation logic."""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from uuid import uuid4
from decimal import Decimal

from app.services.savings_goal_service import SavingsGoalService
from app.models.user import User


def _make_goal(account_id, target_amount, priority=1):
    """Build a minimal goal mock with the fields auto_sync_goals reads/writes."""
    goal = Mock()
    goal.id = uuid4()
    goal.account_id = account_id
    goal.target_amount = Decimal(str(target_amount))
    goal.priority = priority
    goal.current_amount = Decimal("0")
    return goal


def _make_account(account_id, balance):
    """Build a minimal account mock."""
    account = Mock()
    account.id = account_id
    account.current_balance = Decimal(str(balance))
    return account


def _make_db(goals, accounts_list):
    """
    Mock db.execute to return goals on the first call, accounts on the second.
    db.commit and db.refresh are no-ops.
    """
    db = AsyncMock()

    goals_result = MagicMock()
    goals_result.scalars.return_value.all.return_value = goals

    accounts_result = MagicMock()
    accounts_result.scalars.return_value.all.return_value = accounts_list

    db.execute.side_effect = [goals_result, accounts_result]
    return db


@pytest.mark.unit
class TestWaterfallAllocation:
    """Waterfall: goals in priority order, each claims up to its target."""

    @pytest.mark.asyncio
    async def test_priority_1_fills_first_remainder_flows_to_priority_2(self):
        """
        Account balance $3,000.
        Goal A (priority 1, target $2,000) → gets $2,000.
        Goal B (priority 2, target $2,000) → gets remaining $1,000.
        """
        account_id = uuid4()

        goal_a = _make_goal(account_id, "2000.00", priority=1)
        goal_b = _make_goal(account_id, "2000.00", priority=2)

        account = _make_account(account_id, "3000.00")

        user = Mock(spec=User)
        user.organization_id = uuid4()

        db = _make_db([goal_a, goal_b], [account])

        await SavingsGoalService.auto_sync_goals(db, user, method="waterfall")

        assert goal_a.current_amount == Decimal("2000.00")
        assert goal_b.current_amount == Decimal("1000.00")

    @pytest.mark.asyncio
    async def test_balance_covers_all_goals(self):
        """
        Account balance $5,000.
        Goal A (target $2,000) → gets $2,000 (full).
        Goal B (target $2,000) → gets $2,000 (full).
        $1,000 left over — no goal gets more than its target.
        """
        account_id = uuid4()

        goal_a = _make_goal(account_id, "2000.00", priority=1)
        goal_b = _make_goal(account_id, "2000.00", priority=2)

        account = _make_account(account_id, "5000.00")

        user = Mock(spec=User)
        user.organization_id = uuid4()

        db = _make_db([goal_a, goal_b], [account])

        await SavingsGoalService.auto_sync_goals(db, user, method="waterfall")

        assert goal_a.current_amount == Decimal("2000.00")
        assert goal_b.current_amount == Decimal("2000.00")

    @pytest.mark.asyncio
    async def test_balance_insufficient_for_priority_1(self):
        """
        Account balance $500.
        Goal A (priority 1, target $2,000) → gets all $500.
        Goal B (priority 2, target $2,000) → gets $0.
        """
        account_id = uuid4()

        goal_a = _make_goal(account_id, "2000.00", priority=1)
        goal_b = _make_goal(account_id, "2000.00", priority=2)

        account = _make_account(account_id, "500.00")

        user = Mock(spec=User)
        user.organization_id = uuid4()

        db = _make_db([goal_a, goal_b], [account])

        await SavingsGoalService.auto_sync_goals(db, user, method="waterfall")

        assert goal_a.current_amount == Decimal("500.00")
        assert goal_b.current_amount == Decimal("0")


@pytest.mark.unit
class TestProportionalAllocation:
    """Proportional: balance split by each goal's share of the total target."""

    @pytest.mark.asyncio
    async def test_equal_targets_split_balance_evenly(self):
        """
        Account balance $3,000.
        Goal A (target $2,000) → 50% share → $1,500.
        Goal B (target $2,000) → 50% share → $1,500.
        """
        account_id = uuid4()

        goal_a = _make_goal(account_id, "2000.00", priority=1)
        goal_b = _make_goal(account_id, "2000.00", priority=2)

        account = _make_account(account_id, "3000.00")

        user = Mock(spec=User)
        user.organization_id = uuid4()

        db = _make_db([goal_a, goal_b], [account])

        await SavingsGoalService.auto_sync_goals(db, user, method="proportional")

        assert goal_a.current_amount == Decimal("1500.00")
        assert goal_b.current_amount == Decimal("1500.00")

    @pytest.mark.asyncio
    async def test_unequal_targets_split_proportionally(self):
        """
        Account balance $3,000.
        Goal A (target $1,000) → 25% share → $750.
        Goal B (target $3,000) → 75% share → $2,250.
        """
        account_id = uuid4()

        goal_a = _make_goal(account_id, "1000.00", priority=1)
        goal_b = _make_goal(account_id, "3000.00", priority=2)

        account = _make_account(account_id, "3000.00")

        user = Mock(spec=User)
        user.organization_id = uuid4()

        db = _make_db([goal_a, goal_b], [account])

        await SavingsGoalService.auto_sync_goals(db, user, method="proportional")

        assert goal_a.current_amount == Decimal("750.00")
        assert goal_b.current_amount == Decimal("2250.00")

    @pytest.mark.asyncio
    async def test_allocation_capped_at_target(self):
        """
        Account balance $10,000 (more than enough for both goals).
        Goal A (target $2,000) → capped at $2,000.
        Goal B (target $2,000) → capped at $2,000.
        """
        account_id = uuid4()

        goal_a = _make_goal(account_id, "2000.00", priority=1)
        goal_b = _make_goal(account_id, "2000.00", priority=2)

        account = _make_account(account_id, "10000.00")

        user = Mock(spec=User)
        user.organization_id = uuid4()

        db = _make_db([goal_a, goal_b], [account])

        await SavingsGoalService.auto_sync_goals(db, user, method="proportional")

        assert goal_a.current_amount == Decimal("2000.00")
        assert goal_b.current_amount == Decimal("2000.00")
