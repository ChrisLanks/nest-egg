"""Unit tests for savings goal service allocation logic."""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from uuid import uuid4
from decimal import Decimal
from datetime import date

from app.services.savings_goal_service import SavingsGoalService
from app.models.user import User
from app.models.savings_goal import SavingsGoal


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


# ---------------------------------------------------------------------------
# Integration tests for get_goals() — account grouping behavior
# These use the real DB so the frontend "By Account" view gets correct data.
# ---------------------------------------------------------------------------


class TestGetGoalsByAccount:
    """
    get_goals() must return goals with account_id intact and sorted by priority
    so the frontend can group them by account and display them in priority order
    within each account section.
    """

    @pytest.mark.asyncio
    async def test_goals_include_account_id(self, db, test_user, test_account):
        """Goals linked to an account should be returned with that account_id."""
        service = SavingsGoalService()

        goal = await service.create_goal(
            db,
            test_user,
            name="House Down Payment",
            target_amount=Decimal("50000.00"),
            current_amount=Decimal("5000.00"),
            start_date=date.today(),
            account_id=test_account.id,
        )

        goals = await service.get_goals(db, test_user)

        matched = next((g for g in goals if g.id == goal.id), None)
        assert matched is not None
        assert matched.account_id == test_account.id

    @pytest.mark.asyncio
    async def test_unlinked_goals_have_null_account_id(self, db, test_user):
        """Goals not linked to an account should have account_id = None."""
        service = SavingsGoalService()

        goal = await service.create_goal(
            db,
            test_user,
            name="Emergency Fund",
            target_amount=Decimal("10000.00"),
            current_amount=Decimal("0.00"),
            start_date=date.today(),
        )

        goals = await service.get_goals(db, test_user)

        matched = next((g for g in goals if g.id == goal.id), None)
        assert matched is not None
        assert matched.account_id is None

    @pytest.mark.asyncio
    async def test_goals_returned_in_priority_order(self, db, test_user, test_account):
        """
        get_goals() orders by priority ASC so within each account group the
        frontend shows goals in the user-defined drag-and-drop priority order.
        """
        service = SavingsGoalService()

        # Create three goals — they get priority 1, 2, 3 in order of creation
        goal_a = await service.create_goal(
            db, test_user, name="Goal A",
            target_amount=Decimal("1000.00"), current_amount=Decimal("0"),
            start_date=date.today(), account_id=test_account.id,
        )
        goal_b = await service.create_goal(
            db, test_user, name="Goal B",
            target_amount=Decimal("2000.00"), current_amount=Decimal("0"),
            start_date=date.today(), account_id=test_account.id,
        )
        goal_c = await service.create_goal(
            db, test_user, name="Goal C",
            target_amount=Decimal("3000.00"), current_amount=Decimal("0"),
            start_date=date.today(), account_id=test_account.id,
        )

        goals = await service.get_goals(db, test_user)
        active = [g for g in goals if not g.is_completed and not g.is_funded]

        ids_in_order = [g.id for g in active]
        assert ids_in_order.index(goal_a.id) < ids_in_order.index(goal_b.id)
        assert ids_in_order.index(goal_b.id) < ids_in_order.index(goal_c.id)

    @pytest.mark.asyncio
    async def test_goals_from_multiple_accounts_all_returned(
        self, db, test_user, test_account
    ):
        """
        get_goals() returns goals regardless of which account they belong to —
        the frontend groups them client-side.
        """
        from app.models.account import Account, AccountType, AccountSource

        service = SavingsGoalService()

        # Create a second account for the same org
        account_b = Account(
            user_id=test_user.id,
            organization_id=test_user.organization_id,
            name="Savings Account B",
            account_type=AccountType.SAVINGS,
            account_source=AccountSource.MANUAL,
        )
        db.add(account_b)
        await db.commit()

        goal_1 = await service.create_goal(
            db, test_user, name="Goal for Account A",
            target_amount=Decimal("1000.00"), current_amount=Decimal("0"),
            start_date=date.today(), account_id=test_account.id,
        )
        goal_2 = await service.create_goal(
            db, test_user, name="Goal for Account B",
            target_amount=Decimal("2000.00"), current_amount=Decimal("0"),
            start_date=date.today(), account_id=account_b.id,
        )
        goal_3 = await service.create_goal(
            db, test_user, name="Unlinked Goal",
            target_amount=Decimal("500.00"), current_amount=Decimal("0"),
            start_date=date.today(),
        )

        goals = await service.get_goals(db, test_user)
        goal_ids = {g.id for g in goals}

        assert goal_1.id in goal_ids
        assert goal_2.id in goal_ids
        assert goal_3.id in goal_ids

    @pytest.mark.asyncio
    async def test_reorder_updates_priority_for_account_group(
        self, db, test_user, test_account
    ):
        """
        After drag-and-drop reorder, get_goals() reflects the new priority order.
        This is what the frontend sends after the user drags a card.
        """
        service = SavingsGoalService()

        goal_a = await service.create_goal(
            db, test_user, name="First",
            target_amount=Decimal("1000.00"), current_amount=Decimal("0"),
            start_date=date.today(), account_id=test_account.id,
        )
        goal_b = await service.create_goal(
            db, test_user, name="Second",
            target_amount=Decimal("2000.00"), current_amount=Decimal("0"),
            start_date=date.today(), account_id=test_account.id,
        )

        # User drags goal_b above goal_a
        await service.reorder_goals(db, test_user, goal_ids=[goal_b.id, goal_a.id])

        goals = await service.get_goals(db, test_user)
        active = [g for g in goals if not g.is_completed and not g.is_funded]
        ids_in_order = [g.id for g in active]

        assert ids_in_order.index(goal_b.id) < ids_in_order.index(goal_a.id)
