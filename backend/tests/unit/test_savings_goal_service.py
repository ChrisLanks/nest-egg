"""Unit tests for savings goal service allocation logic."""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import uuid4

import pytest

from app.models.user import User
from app.services.savings_goal_service import SavingsGoalService


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
    Mock db.execute to return:
      1. goals (initial fetch by org)
      2. accounts (balance lookup)
      3. goals again (post-commit batch reload — replaces N individual db.refresh calls)
    db.commit is a no-op.
    """
    db = AsyncMock()

    goals_result = MagicMock()
    goals_result.scalars.return_value.all.return_value = goals

    accounts_result = MagicMock()
    accounts_result.scalars.return_value.all.return_value = accounts_list

    # 3rd execute: batch reload of updated goals (avoids N+1 db.refresh loop)
    reload_result = MagicMock()
    reload_result.scalars.return_value.all.return_value = goals

    db.execute.side_effect = [goals_result, accounts_result, reload_result]
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
            db,
            test_user,
            name="Goal A",
            target_amount=Decimal("1000.00"),
            current_amount=Decimal("0"),
            start_date=date.today(),
            account_id=test_account.id,
        )
        goal_b = await service.create_goal(
            db,
            test_user,
            name="Goal B",
            target_amount=Decimal("2000.00"),
            current_amount=Decimal("0"),
            start_date=date.today(),
            account_id=test_account.id,
        )
        goal_c = await service.create_goal(
            db,
            test_user,
            name="Goal C",
            target_amount=Decimal("3000.00"),
            current_amount=Decimal("0"),
            start_date=date.today(),
            account_id=test_account.id,
        )

        goals = await service.get_goals(db, test_user)
        active = [g for g in goals if not g.is_completed and not g.is_funded]

        ids_in_order = [g.id for g in active]
        assert ids_in_order.index(goal_a.id) < ids_in_order.index(goal_b.id)
        assert ids_in_order.index(goal_b.id) < ids_in_order.index(goal_c.id)

    @pytest.mark.asyncio
    async def test_goals_from_multiple_accounts_all_returned(self, db, test_user, test_account):
        """
        get_goals() returns goals regardless of which account they belong to —
        the frontend groups them client-side.
        """
        from app.models.account import Account, AccountSource, AccountType

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
            db,
            test_user,
            name="Goal for Account A",
            target_amount=Decimal("1000.00"),
            current_amount=Decimal("0"),
            start_date=date.today(),
            account_id=test_account.id,
        )
        goal_2 = await service.create_goal(
            db,
            test_user,
            name="Goal for Account B",
            target_amount=Decimal("2000.00"),
            current_amount=Decimal("0"),
            start_date=date.today(),
            account_id=account_b.id,
        )
        goal_3 = await service.create_goal(
            db,
            test_user,
            name="Unlinked Goal",
            target_amount=Decimal("500.00"),
            current_amount=Decimal("0"),
            start_date=date.today(),
        )

        goals = await service.get_goals(db, test_user)
        goal_ids = {g.id for g in goals}

        assert goal_1.id in goal_ids
        assert goal_2.id in goal_ids
        assert goal_3.id in goal_ids

    @pytest.mark.asyncio
    async def test_reorder_updates_priority_for_account_group(self, db, test_user, test_account):
        """
        After drag-and-drop reorder, get_goals() reflects the new priority order.
        This is what the frontend sends after the user drags a card.
        """
        service = SavingsGoalService()

        goal_a = await service.create_goal(
            db,
            test_user,
            name="First",
            target_amount=Decimal("1000.00"),
            current_amount=Decimal("0"),
            start_date=date.today(),
            account_id=test_account.id,
        )
        goal_b = await service.create_goal(
            db,
            test_user,
            name="Second",
            target_amount=Decimal("2000.00"),
            current_amount=Decimal("0"),
            start_date=date.today(),
            account_id=test_account.id,
        )

        # User drags goal_b above goal_a
        await service.reorder_goals(db, test_user, goal_ids=[goal_b.id, goal_a.id])

        goals = await service.get_goals(db, test_user)
        active = [g for g in goals if not g.is_completed and not g.is_funded]
        ids_in_order = [g.id for g in active]

        assert ids_in_order.index(goal_b.id) < ids_in_order.index(goal_a.id)


@pytest.mark.unit
class TestSharedGoals:
    """Tests for shared goal creation and update."""

    @pytest.mark.asyncio
    async def test_create_shared_goal(self, db, test_user):
        """Should create a shared savings goal."""
        service = SavingsGoalService()
        other_user_id = str(uuid4())

        goal = await service.create_goal(
            db=db,
            user=test_user,
            name="Family Vacation",
            target_amount=Decimal("5000.00"),
            start_date=date.today(),
            is_shared=True,
            shared_user_ids=[other_user_id],
        )

        assert goal.is_shared is True
        assert goal.shared_user_ids == [other_user_id]
        assert goal.user_id == test_user.id

    @pytest.mark.asyncio
    async def test_create_goal_defaults_not_shared(self, db, test_user):
        """Goal should default to not shared."""
        service = SavingsGoalService()

        goal = await service.create_goal(
            db=db,
            user=test_user,
            name="Personal",
            target_amount=Decimal("1000.00"),
            start_date=date.today(),
        )

        assert goal.is_shared is False
        assert goal.shared_user_ids is None

    @pytest.mark.asyncio
    async def test_update_goal_shared_status(self, db, test_user):
        """Should toggle is_shared via update."""
        service = SavingsGoalService()

        goal = await service.create_goal(
            db,
            test_user,
            name="Toggle",
            target_amount=Decimal("1000.00"),
            start_date=date.today(),
        )
        assert goal.is_shared is False

        updated = await service.update_goal(db, goal.id, test_user, is_shared=True)
        assert updated.is_shared is True

    @pytest.mark.asyncio
    async def test_goal_stores_user_id(self, db, test_user):
        """Goal should store the creating user's ID."""
        service = SavingsGoalService()

        goal = await service.create_goal(
            db=db,
            user=test_user,
            name="My Goal",
            target_amount=Decimal("2000.00"),
            start_date=date.today(),
        )

        assert goal.user_id == test_user.id


# ---------------------------------------------------------------------------
# Additional coverage for update, delete, sync, fund, progress, emergency fund
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGoalUpdateAndDelete:
    """Tests for update_goal and delete_goal methods."""

    @pytest.mark.asyncio
    async def test_update_goal_basic(self, db, test_user):
        """Should update goal fields."""
        service = SavingsGoalService()
        goal = await service.create_goal(
            db,
            test_user,
            name="Original",
            target_amount=Decimal("1000.00"),
            start_date=date.today(),
        )

        updated = await service.update_goal(
            db,
            goal.id,
            test_user,
            name="Updated Name",
            target_amount=Decimal("2000.00"),
        )
        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.target_amount == Decimal("2000.00")

    @pytest.mark.asyncio
    async def test_update_goal_not_found(self, db, test_user):
        """Should return None for non-existent goal."""
        service = SavingsGoalService()
        result = await service.update_goal(db, uuid4(), test_user, name="X")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_goal_clears_auto_sync_when_account_removed(
        self, db, test_user, test_account
    ):
        """Clearing account_id should disable auto_sync."""
        service = SavingsGoalService()
        goal = await service.create_goal(
            db,
            test_user,
            name="Synced Goal",
            target_amount=Decimal("5000.00"),
            start_date=date.today(),
            account_id=test_account.id,
            auto_sync=True,
        )
        assert goal.auto_sync is True

        updated = await service.update_goal(db, goal.id, test_user, account_id=None)
        assert updated.auto_sync is False

    @pytest.mark.asyncio
    async def test_update_goal_sets_completed_at(self, db, test_user):
        """Setting is_completed=True should set completed_at."""
        service = SavingsGoalService()
        goal = await service.create_goal(
            db,
            test_user,
            name="Complete Me",
            target_amount=Decimal("1000.00"),
            start_date=date.today(),
        )
        assert goal.completed_at is None

        updated = await service.update_goal(db, goal.id, test_user, is_completed=True)
        assert updated.is_completed is True
        assert updated.completed_at is not None

    @pytest.mark.asyncio
    async def test_update_goal_clears_completed_at(self, db, test_user):
        """Setting is_completed=False should clear completed_at."""
        service = SavingsGoalService()
        goal = await service.create_goal(
            db,
            test_user,
            name="Uncomplete Me",
            target_amount=Decimal("1000.00"),
            start_date=date.today(),
        )
        # First complete it
        await service.update_goal(db, goal.id, test_user, is_completed=True)
        # Then un-complete it
        updated = await service.update_goal(db, goal.id, test_user, is_completed=False)
        assert updated.is_completed is False
        assert updated.completed_at is None

    @pytest.mark.asyncio
    async def test_delete_goal_success(self, db, test_user):
        """Should delete an existing goal."""
        service = SavingsGoalService()
        goal = await service.create_goal(
            db,
            test_user,
            name="Delete Me",
            target_amount=Decimal("500.00"),
            start_date=date.today(),
        )
        result = await service.delete_goal(db, goal.id, test_user)
        assert result is True

        # Verify it's gone
        found = await service.get_goal(db, goal.id, test_user)
        assert found is None

    @pytest.mark.asyncio
    async def test_delete_goal_not_found(self, db, test_user):
        """Should return False for non-existent goal."""
        service = SavingsGoalService()
        result = await service.delete_goal(db, uuid4(), test_user)
        assert result is False


@pytest.mark.unit
class TestGoalSync:
    """Tests for sync_goal_from_account."""

    @pytest.mark.asyncio
    async def test_sync_goal_from_account_success(self, db, test_user, test_account):
        """Should sync goal amount from linked account balance."""
        service = SavingsGoalService()
        goal = await service.create_goal(
            db,
            test_user,
            name="Sync Goal",
            target_amount=Decimal("10000.00"),
            start_date=date.today(),
            account_id=test_account.id,
        )

        synced = await service.sync_goal_from_account(db, goal.id, test_user)
        assert synced is not None
        assert synced.current_amount == test_account.current_balance

    @pytest.mark.asyncio
    async def test_sync_goal_no_account_linked(self, db, test_user):
        """Should return None if no account is linked."""
        service = SavingsGoalService()
        goal = await service.create_goal(
            db,
            test_user,
            name="No Account",
            target_amount=Decimal("5000.00"),
            start_date=date.today(),
        )

        synced = await service.sync_goal_from_account(db, goal.id, test_user)
        assert synced is None

    @pytest.mark.asyncio
    async def test_sync_goal_not_found(self, db, test_user):
        """Should return None for non-existent goal."""
        service = SavingsGoalService()
        result = await service.sync_goal_from_account(db, uuid4(), test_user)
        assert result is None


@pytest.mark.unit
class TestGoalFund:
    """Tests for fund_goal."""

    @pytest.mark.asyncio
    async def test_fund_goal_success(self, db, test_user):
        """Should mark goal as funded."""
        service = SavingsGoalService()
        goal = await service.create_goal(
            db,
            test_user,
            name="Fund Me",
            target_amount=Decimal("5000.00"),
            start_date=date.today(),
        )

        funded = await service.fund_goal(db, goal.id, test_user)
        assert funded is not None
        assert funded.is_funded is True
        assert funded.funded_at is not None

    @pytest.mark.asyncio
    async def test_fund_goal_not_found(self, db, test_user):
        """Should return None for non-existent goal."""
        service = SavingsGoalService()
        result = await service.fund_goal(db, uuid4(), test_user)
        assert result is None


@pytest.mark.unit
class TestGoalProgress:
    """Tests for get_goal_progress."""

    @pytest.mark.asyncio
    async def test_get_goal_progress_basic(self, db, test_user):
        """Should calculate progress metrics."""
        service = SavingsGoalService()
        goal = await service.create_goal(
            db,
            test_user,
            name="Progress Goal",
            target_amount=Decimal("10000.00"),
            current_amount=Decimal("5000.00"),
            start_date=date.today() - timedelta(days=30),
            target_date=date.today() + timedelta(days=60),
        )

        progress = await service.get_goal_progress(db, goal.id, test_user)
        assert progress is not None
        assert progress["progress_percentage"] == 50.0
        assert progress["remaining_amount"] == Decimal("5000.00")
        assert progress["days_elapsed"] == 30
        assert progress["days_remaining"] == 60
        assert progress["monthly_required"] is not None
        assert progress["on_track"] is not None

    @pytest.mark.asyncio
    async def test_get_goal_progress_no_target_date(self, db, test_user):
        """Progress without target_date should have None for time-based metrics."""
        service = SavingsGoalService()
        goal = await service.create_goal(
            db,
            test_user,
            name="No Deadline",
            target_amount=Decimal("5000.00"),
            current_amount=Decimal("1000.00"),
            start_date=date.today(),
        )

        progress = await service.get_goal_progress(db, goal.id, test_user)
        assert progress is not None
        assert progress["days_remaining"] is None
        assert progress["monthly_required"] is None
        assert progress["on_track"] is None

    @pytest.mark.asyncio
    async def test_get_goal_progress_not_found(self, db, test_user):
        """Should return None for non-existent goal."""
        service = SavingsGoalService()
        result = await service.get_goal_progress(db, uuid4(), test_user)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_goal_progress_zero_target(self, db, test_user):
        """Zero target amount should handle division safely."""
        service = SavingsGoalService()
        goal = await service.create_goal(
            db,
            test_user,
            name="Zero Target",
            target_amount=Decimal("0.00"),
            current_amount=Decimal("0.00"),
            start_date=date.today(),
        )

        progress = await service.get_goal_progress(db, goal.id, test_user)
        assert progress is not None
        assert progress["progress_percentage"] == 0


@pytest.mark.unit
class TestGetGoalsFiltering:
    """Tests for get_goals with completion filtering."""

    @pytest.mark.asyncio
    async def test_get_active_goals(self, db, test_user):
        """Should return only active (not completed, not funded) goals."""
        service = SavingsGoalService()

        active_goal = await service.create_goal(
            db,
            test_user,
            name="Active",
            target_amount=Decimal("1000.00"),
            start_date=date.today(),
        )
        completed_goal = await service.create_goal(
            db,
            test_user,
            name="Completed",
            target_amount=Decimal("1000.00"),
            start_date=date.today(),
        )
        await service.update_goal(db, completed_goal.id, test_user, is_completed=True)

        goals = await service.get_goals(db, test_user, is_completed=False)
        goal_ids = {g.id for g in goals}
        assert active_goal.id in goal_ids
        assert completed_goal.id not in goal_ids

    @pytest.mark.asyncio
    async def test_get_completed_goals(self, db, test_user):
        """Should return only completed or funded goals."""
        service = SavingsGoalService()

        active_goal = await service.create_goal(
            db,
            test_user,
            name="Still Active",
            target_amount=Decimal("1000.00"),
            start_date=date.today(),
        )
        completed_goal = await service.create_goal(
            db,
            test_user,
            name="Done",
            target_amount=Decimal("1000.00"),
            start_date=date.today(),
        )
        await service.update_goal(db, completed_goal.id, test_user, is_completed=True)

        goals = await service.get_goals(db, test_user, is_completed=True)
        goal_ids = {g.id for g in goals}
        assert active_goal.id not in goal_ids
        assert completed_goal.id in goal_ids


@pytest.mark.unit
class TestEmptyAutoSync:
    """Test auto_sync_goals with no matching goals."""

    @pytest.mark.asyncio
    async def test_auto_sync_no_goals_returns_empty(self):
        """auto_sync_goals with no auto-sync goals returns empty list."""
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        db.execute.return_value = result_mock

        user = Mock(spec=User)
        user.organization_id = uuid4()

        result = await SavingsGoalService.auto_sync_goals(db, user)
        assert result == []


@pytest.mark.unit
class TestReorderGoals:
    """Tests for reorder_goals."""

    @pytest.mark.asyncio
    async def test_reorder_empty_list(self, db, test_user):
        """Empty goal_ids should succeed without changes."""
        service = SavingsGoalService()
        result = await service.reorder_goals(db, test_user, goal_ids=[])
        assert result is True


@pytest.mark.unit
class TestAllocateBalancesNPlusOne:
    """Regression tests: allocate_balances must reload goals in one query, not N refreshes."""

    @pytest.mark.asyncio
    async def test_batch_reload_not_individual_refreshes(self):
        """After commit, goals must be reloaded with a single SELECT IN query, not N db.refresh calls."""
        account_id = uuid4()
        goal_a = _make_goal(account_id, "1000.00", priority=1)
        goal_b = _make_goal(account_id, "1000.00", priority=2)
        goal_c = _make_goal(account_id, "1000.00", priority=3)

        account = _make_account(account_id, "3000.00")
        user = Mock(spec=User)
        user.organization_id = uuid4()

        db = _make_db([goal_a, goal_b, goal_c], [account])

        await SavingsGoalService.auto_sync_goals(db, user, method="proportional")

        # Must never call db.refresh (that would be the N+1 pattern)
        db.refresh.assert_not_called()
        # Must call db.execute exactly 3 times: fetch goals, fetch accounts, batch reload
        assert db.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_no_goals_skips_reload_query(self):
        """When there are no goals to update, the batch reload query should not be issued."""
        user = Mock(spec=User)
        user.organization_id = uuid4()

        db = AsyncMock()
        empty_result = MagicMock()
        empty_result.scalars.return_value.all.return_value = []
        db.execute.return_value = empty_result

        await SavingsGoalService.auto_sync_goals(db, user, method="proportional")

        # Only 1 execute call: the initial goals fetch (no accounts fetch, no reload)
        assert db.execute.call_count == 1
        db.refresh.assert_not_called()


@pytest.mark.unit
class TestGetGoalProgressNullStartDate:
    """Regression: get_goal_progress must not crash when start_date is None."""

    @pytest.mark.asyncio
    async def test_null_start_date_returns_zero_days_elapsed(self, db, test_user):
        """
        Goals with a NULL start_date (edge case from old imports) should
        return days_elapsed=0 rather than raising a TypeError.
        The service null guard handles this without hitting the DB constraint.
        """
        from unittest.mock import AsyncMock as _AsyncMock, MagicMock as _MagicMock, patch

        # Build a goal mock with start_date=None to simulate old/corrupt data
        goal_mock = Mock()
        goal_mock.id = uuid4()
        goal_mock.name = "Null Start Goal"
        goal_mock.target_amount = Decimal("5000.00")
        goal_mock.current_amount = Decimal("2500.00")
        goal_mock.start_date = None  # the edge case we're guarding against
        goal_mock.target_date = None
        goal_mock.is_completed = False

        mock_result = _MagicMock()
        mock_result.scalar_one_or_none.return_value = goal_mock

        mock_db = _AsyncMock()
        mock_db.execute.return_value = mock_result

        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()

        progress = await SavingsGoalService.get_goal_progress(mock_db, goal_mock.id, user)
        assert progress is not None
        assert progress["days_elapsed"] == 0
        assert progress["progress_percentage"] == 50.0


@pytest.mark.unit
class TestNotificationFailureResilience:
    """Regression: notification failures in update_goal/fund_goal must not raise 500."""

    @pytest.mark.asyncio
    async def test_update_goal_completes_despite_notification_error(self, db, test_user):
        """
        If NotificationService.create_notification raises (e.g. enum not in DB),
        update_goal should still succeed and return the updated goal.
        """
        from unittest.mock import patch

        service = SavingsGoalService()
        goal = await service.create_goal(
            db,
            test_user,
            name="Complete Me",
            target_amount=Decimal("1000.00"),
            start_date=date.today(),
        )

        with patch(
            "app.services.savings_goal_service.NotificationService.create_notification",
            side_effect=Exception("invalid input value for enum notificationtype: goal_completed"),
        ):
            updated = await service.update_goal(db, goal.id, test_user, is_completed=True)

        assert updated is not None
        assert updated.is_completed is True
        assert updated.completed_at is not None

    @pytest.mark.asyncio
    async def test_fund_goal_completes_despite_notification_error(self, db, test_user):
        """
        If NotificationService.create_notification raises,
        fund_goal should still mark the goal as funded.
        """
        from unittest.mock import patch

        service = SavingsGoalService()
        goal = await service.create_goal(
            db,
            test_user,
            name="Fund Me",
            target_amount=Decimal("5000.00"),
            start_date=date.today(),
        )

        with patch(
            "app.services.savings_goal_service.NotificationService.create_notification",
            side_effect=Exception("invalid input value for enum notificationtype: goal_funded"),
        ):
            funded = await service.fund_goal(db, goal.id, test_user)

        assert funded is not None
        assert funded.is_funded is True
