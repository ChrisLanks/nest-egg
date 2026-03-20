"""Unit tests for goal notification logic added to SavingsGoalService.

Tests cover:
- GOAL_COMPLETED fires when is_completed transitions True (update_goal)
- GOAL_COMPLETED fires when current_amount crosses target_amount (update_goal)
- GOAL_COMPLETED does NOT fire for unrelated updates
- GOAL_COMPLETED does NOT fire when goal was already completed
- GOAL_COMPLETED fires from sync_goal_from_account when balance crosses target
- GOAL_COMPLETED does NOT fire from sync if already completed or funded
- GOAL_FUNDED fires from fund_goal
- GOAL_FUNDED does NOT fire when goal not found

All tests use AsyncMock / Mock to avoid a real DB connection.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest

from app.models.notification import NotificationPriority, NotificationType
from app.services.savings_goal_service import SavingsGoalService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user():
    user = Mock()
    user.id = uuid4()
    user.organization_id = uuid4()
    return user


def _make_goal(
    *,
    target_amount="5000.00",
    current_amount="2000.00",
    is_completed=False,
    is_funded=False,
    account_id=None,
):
    goal = Mock()
    goal.id = uuid4()
    goal.name = "Test Goal"
    goal.target_amount = Decimal(target_amount)
    goal.current_amount = Decimal(current_amount)
    goal.is_completed = is_completed
    goal.is_funded = is_funded
    goal.completed_at = None
    goal.account_id = account_id
    goal.auto_sync = False
    goal.updated_at = None
    return goal


def _make_db_with_goal(goal):
    """DB mock where get_goal returns the given goal and commit/refresh are no-ops."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock(side_effect=lambda obj: None)
    return db


# ---------------------------------------------------------------------------
# update_goal — GOAL_COMPLETED notification
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUpdateGoalNotifications:
    """Notification logic in update_goal."""

    @pytest.mark.asyncio
    async def test_goal_completed_fires_when_is_completed_set_true(self):
        """GOAL_COMPLETED fires when is_completed transitions False → True."""
        user = _make_user()
        goal = _make_goal(is_completed=False)
        db = _make_db_with_goal(goal)

        with (
            patch.object(SavingsGoalService, "get_goal", return_value=goal),
            patch(
                "app.services.savings_goal_service.NotificationService.create_notification",
                new_callable=AsyncMock,
            ) as mock_notify,
        ):
            # Simulate the attribute assignment done inside update_goal
            async def fake_refresh(obj):
                pass

            db.refresh.side_effect = fake_refresh

            # Manually drive the logic: set is_completed = True after get_goal
            goal.is_completed = True  # will be set by setattr inside update_goal
            await SavingsGoalService.update_goal(db, goal.id, user, is_completed=True)

        mock_notify.assert_called_once()
        call_kwargs = mock_notify.call_args.kwargs
        assert call_kwargs["type"] == NotificationType.GOAL_COMPLETED
        assert call_kwargs["priority"] == NotificationPriority.HIGH
        assert "Test Goal" in call_kwargs["title"]
        assert call_kwargs["user_id"] == user.id
        assert call_kwargs["organization_id"] == user.organization_id

    @pytest.mark.asyncio
    async def test_goal_completed_fires_when_amount_crosses_target(self):
        """GOAL_COMPLETED fires when current_amount crosses target_amount (not completed flag)."""
        user = _make_user()
        # Before update: amount below target; after: at target
        goal = _make_goal(target_amount="5000.00", current_amount="4000.00", is_completed=False)
        db = _make_db_with_goal(goal)

        with (
            patch.object(SavingsGoalService, "get_goal", return_value=goal),
            patch(
                "app.services.savings_goal_service.NotificationService.create_notification",
                new_callable=AsyncMock,
            ) as mock_notify,
        ):
            # Simulate amount being set to target by update_goal's setattr
            goal.current_amount = Decimal("5000.00")
            await SavingsGoalService.update_goal(
                db, goal.id, user, current_amount=Decimal("5000.00")
            )

        mock_notify.assert_called_once()
        call_kwargs = mock_notify.call_args.kwargs
        assert call_kwargs["type"] == NotificationType.GOAL_COMPLETED

    @pytest.mark.asyncio
    async def test_no_notification_for_unrelated_update(self):
        """No GOAL_COMPLETED when name is updated without any completion trigger."""
        user = _make_user()
        goal = _make_goal(
            target_amount="5000.00",
            current_amount="2000.00",
            is_completed=False,
        )
        db = _make_db_with_goal(goal)

        with (
            patch.object(SavingsGoalService, "get_goal", return_value=goal),
            patch(
                "app.services.savings_goal_service.NotificationService.create_notification",
                new_callable=AsyncMock,
            ) as mock_notify,
        ):
            await SavingsGoalService.update_goal(db, goal.id, user, name="New Name")

        mock_notify.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_notification_when_already_completed(self):
        """No duplicate GOAL_COMPLETED when goal was already completed before update."""
        user = _make_user()
        goal = _make_goal(is_completed=True)  # already completed
        db = _make_db_with_goal(goal)

        with (
            patch.object(SavingsGoalService, "get_goal", return_value=goal),
            patch(
                "app.services.savings_goal_service.NotificationService.create_notification",
                new_callable=AsyncMock,
            ) as mock_notify,
        ):
            # Update something else while it's still completed
            await SavingsGoalService.update_goal(db, goal.id, user, name="Still Done")

        mock_notify.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_notification_when_amount_does_not_reach_target(self):
        """No notification when amount increases but stays below target."""
        user = _make_user()
        goal = _make_goal(target_amount="5000.00", current_amount="1000.00", is_completed=False)
        db = _make_db_with_goal(goal)

        with (
            patch.object(SavingsGoalService, "get_goal", return_value=goal),
            patch(
                "app.services.savings_goal_service.NotificationService.create_notification",
                new_callable=AsyncMock,
            ) as mock_notify,
        ):
            goal.current_amount = Decimal("3000.00")  # still below $5k
            await SavingsGoalService.update_goal(
                db, goal.id, user, current_amount=Decimal("3000.00")
            )

        mock_notify.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_notification_when_target_is_zero(self):
        """No notification when target is 0 (division guard)."""
        user = _make_user()
        goal = _make_goal(target_amount="0.00", current_amount="0.00", is_completed=False)
        db = _make_db_with_goal(goal)

        with (
            patch.object(SavingsGoalService, "get_goal", return_value=goal),
            patch(
                "app.services.savings_goal_service.NotificationService.create_notification",
                new_callable=AsyncMock,
            ) as mock_notify,
        ):
            await SavingsGoalService.update_goal(db, goal.id, user, name="Zero Target")

        mock_notify.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_none_for_missing_goal(self):
        """update_goal returns None and does not fire notification for missing goal."""
        user = _make_user()
        db = AsyncMock()

        with (
            patch.object(SavingsGoalService, "get_goal", return_value=None),
            patch(
                "app.services.savings_goal_service.NotificationService.create_notification",
                new_callable=AsyncMock,
            ) as mock_notify,
        ):
            result = await SavingsGoalService.update_goal(db, uuid4(), user, name="X")

        assert result is None
        mock_notify.assert_not_called()


# ---------------------------------------------------------------------------
# sync_goal_from_account — GOAL_COMPLETED notification
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSyncGoalNotifications:
    """Notification logic in sync_goal_from_account."""

    @pytest.mark.asyncio
    async def test_goal_completed_fires_when_sync_crosses_target(self):
        """GOAL_COMPLETED fires when synced balance crosses target for the first time."""
        user = _make_user()
        account_id = uuid4()
        goal = _make_goal(
            target_amount="10000.00",
            current_amount="8000.00",
            is_completed=False,
            is_funded=False,
            account_id=account_id,
        )

        account = Mock()
        account.current_balance = Decimal("10500.00")

        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=lambda obj: None)

        # First execute = get_goal lookup, second = account lookup
        goal_result = MagicMock()
        goal_result.scalar_one_or_none.return_value = goal

        # account lookup via db.execute inside sync_goal_from_account
        account_result_inner = MagicMock()
        account_result_inner.scalar_one_or_none.return_value = account

        db.execute.return_value = account_result_inner

        with (
            patch.object(SavingsGoalService, "get_goal", return_value=goal),
            patch(
                "app.services.savings_goal_service.NotificationService.create_notification",
                new_callable=AsyncMock,
            ) as mock_notify,
        ):
            goal.current_amount = Decimal("10500.00")  # simulates what service sets
            await SavingsGoalService.sync_goal_from_account(db, goal.id, user)

        mock_notify.assert_called_once()
        call_kwargs = mock_notify.call_args.kwargs
        assert call_kwargs["type"] == NotificationType.GOAL_COMPLETED
        assert call_kwargs["priority"] == NotificationPriority.HIGH

    @pytest.mark.asyncio
    async def test_no_notification_when_sync_does_not_cross_target(self):
        """No notification when synced balance is still below target."""
        user = _make_user()
        account_id = uuid4()
        goal = _make_goal(
            target_amount="10000.00",
            current_amount="5000.00",
            is_completed=False,
            account_id=account_id,
        )

        account = Mock()
        account.current_balance = Decimal("7000.00")

        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=lambda obj: None)

        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = account
        db.execute.return_value = account_result

        with (
            patch.object(SavingsGoalService, "get_goal", return_value=goal),
            patch(
                "app.services.savings_goal_service.NotificationService.create_notification",
                new_callable=AsyncMock,
            ) as mock_notify,
        ):
            goal.current_amount = Decimal("7000.00")
            await SavingsGoalService.sync_goal_from_account(db, goal.id, user)

        mock_notify.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_notification_when_goal_already_completed(self):
        """No duplicate notification when goal is already marked completed."""
        user = _make_user()
        account_id = uuid4()
        goal = _make_goal(
            target_amount="10000.00",
            current_amount="9000.00",
            is_completed=True,  # already done
            account_id=account_id,
        )

        account = Mock()
        account.current_balance = Decimal("11000.00")

        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=lambda obj: None)

        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = account
        db.execute.return_value = account_result

        with (
            patch.object(SavingsGoalService, "get_goal", return_value=goal),
            patch(
                "app.services.savings_goal_service.NotificationService.create_notification",
                new_callable=AsyncMock,
            ) as mock_notify,
        ):
            goal.current_amount = Decimal("11000.00")
            await SavingsGoalService.sync_goal_from_account(db, goal.id, user)

        mock_notify.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_notification_when_goal_already_funded(self):
        """No notification when goal is already funded."""
        user = _make_user()
        account_id = uuid4()
        goal = _make_goal(
            target_amount="10000.00",
            current_amount="9000.00",
            is_funded=True,
            account_id=account_id,
        )

        account = Mock()
        account.current_balance = Decimal("11000.00")

        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=lambda obj: None)

        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = account
        db.execute.return_value = account_result

        with (
            patch.object(SavingsGoalService, "get_goal", return_value=goal),
            patch(
                "app.services.savings_goal_service.NotificationService.create_notification",
                new_callable=AsyncMock,
            ) as mock_notify,
        ):
            goal.current_amount = Decimal("11000.00")
            await SavingsGoalService.sync_goal_from_account(db, goal.id, user)

        mock_notify.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_none_when_no_account_linked(self):
        """Returns None and fires no notification when goal has no linked account."""
        user = _make_user()
        goal = _make_goal(account_id=None)
        db = AsyncMock()

        with (
            patch.object(SavingsGoalService, "get_goal", return_value=goal),
            patch(
                "app.services.savings_goal_service.NotificationService.create_notification",
                new_callable=AsyncMock,
            ) as mock_notify,
        ):
            result = await SavingsGoalService.sync_goal_from_account(db, goal.id, user)

        assert result is None
        mock_notify.assert_not_called()


# ---------------------------------------------------------------------------
# fund_goal — GOAL_FUNDED notification
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFundGoalNotifications:
    """Notification logic in fund_goal."""

    @pytest.mark.asyncio
    async def test_goal_funded_notification_fires(self):
        """GOAL_FUNDED notification fires when fund_goal succeeds."""
        user = _make_user()
        goal = _make_goal()
        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=lambda obj: None)

        with (
            patch.object(SavingsGoalService, "get_goal", return_value=goal),
            patch.object(SavingsGoalService, "auto_sync_goals", new_callable=AsyncMock),
            patch(
                "app.services.savings_goal_service.NotificationService.create_notification",
                new_callable=AsyncMock,
            ) as mock_notify,
        ):
            result = await SavingsGoalService.fund_goal(db, goal.id, user)

        assert result is not None
        mock_notify.assert_called_once()
        call_kwargs = mock_notify.call_args.kwargs
        assert call_kwargs["type"] == NotificationType.GOAL_FUNDED
        assert call_kwargs["priority"] == NotificationPriority.MEDIUM
        assert "Test Goal" in call_kwargs["title"]
        assert call_kwargs["user_id"] == user.id
        assert call_kwargs["organization_id"] == user.organization_id

    @pytest.mark.asyncio
    async def test_goal_funded_notification_not_fired_when_not_found(self):
        """No notification when fund_goal is called for a non-existent goal."""
        user = _make_user()
        db = AsyncMock()

        with (
            patch.object(SavingsGoalService, "get_goal", return_value=None),
            patch(
                "app.services.savings_goal_service.NotificationService.create_notification",
                new_callable=AsyncMock,
            ) as mock_notify,
        ):
            result = await SavingsGoalService.fund_goal(db, uuid4(), user)

        assert result is None
        mock_notify.assert_not_called()

    @pytest.mark.asyncio
    async def test_goal_funded_sets_is_funded_and_funded_at(self):
        """fund_goal sets is_funded=True and funded_at on the goal object."""
        user = _make_user()
        goal = _make_goal()
        assert goal.is_funded is False

        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=lambda obj: None)

        with (
            patch.object(SavingsGoalService, "get_goal", return_value=goal),
            patch.object(SavingsGoalService, "auto_sync_goals", new_callable=AsyncMock),
            patch(
                "app.services.savings_goal_service.NotificationService.create_notification",
                new_callable=AsyncMock,
            ),
        ):
            result = await SavingsGoalService.fund_goal(db, goal.id, user)

        assert result.is_funded is True
        assert result.funded_at is not None

    @pytest.mark.asyncio
    async def test_fund_goal_triggers_auto_sync_for_remaining_goals(self):
        """fund_goal calls auto_sync_goals after marking the goal as funded."""
        user = _make_user()
        goal = _make_goal()

        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=lambda obj: None)

        with (
            patch.object(SavingsGoalService, "get_goal", return_value=goal),
            patch.object(
                SavingsGoalService, "auto_sync_goals", new_callable=AsyncMock
            ) as mock_sync,
            patch(
                "app.services.savings_goal_service.NotificationService.create_notification",
                new_callable=AsyncMock,
            ),
        ):
            await SavingsGoalService.fund_goal(db, goal.id, user, method="proportional")

        mock_sync.assert_called_once_with(db, user, "proportional")


# ---------------------------------------------------------------------------
# Notification content correctness
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNotificationContent:
    """Verify notification message content is well-formed."""

    @pytest.mark.asyncio
    async def test_goal_completed_message_contains_amount_and_name(self):
        """GOAL_COMPLETED message includes the saved amount and goal name."""
        user = _make_user()
        goal = _make_goal(target_amount="10000.00", current_amount="0.00", is_completed=False)
        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=lambda obj: None)

        captured_kwargs = {}

        async def capture(**kwargs):
            captured_kwargs.update(kwargs)

        with (
            patch.object(SavingsGoalService, "get_goal", return_value=goal),
            patch(
                "app.services.savings_goal_service.NotificationService.create_notification",
                side_effect=capture,
            ),
        ):
            goal.is_completed = True
            await SavingsGoalService.update_goal(db, goal.id, user, is_completed=True)

        assert "Test Goal" in captured_kwargs.get("title", "")
        assert "Test Goal" in captured_kwargs.get("message", "")
        assert captured_kwargs.get("action_url") == "/goals"
        assert captured_kwargs.get("action_label") == "View Goals"

    @pytest.mark.asyncio
    async def test_goal_funded_message_contains_goal_name(self):
        """GOAL_FUNDED message includes the goal name."""
        user = _make_user()
        goal = _make_goal()
        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=lambda obj: None)

        captured_kwargs = {}

        async def capture(**kwargs):
            captured_kwargs.update(kwargs)

        with (
            patch.object(SavingsGoalService, "get_goal", return_value=goal),
            patch.object(SavingsGoalService, "auto_sync_goals", new_callable=AsyncMock),
            patch(
                "app.services.savings_goal_service.NotificationService.create_notification",
                side_effect=capture,
            ),
        ):
            await SavingsGoalService.fund_goal(db, goal.id, user)

        assert "Test Goal" in captured_kwargs.get("title", "")
        assert "Test Goal" in captured_kwargs.get("message", "")
        assert captured_kwargs.get("action_url") == "/goals"
        assert captured_kwargs.get("related_entity_type") == "savings_goal"
        assert captured_kwargs.get("related_entity_id") == goal.id
