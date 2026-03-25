"""Tests for expanded notification triggers.

Tests cover:
- New NotificationType enum values exist
- Household join/leave/remove notifications
- FIRE milestone detection (Coast FI, Financial Independence)
- FIRE milestone deduplication
- Retirement scenario stale notification
- Account connected notification
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.models.notification import NotificationPriority, NotificationType


class TestNewNotificationTypes:
    """Verify new notification type enum values exist."""

    def test_household_member_joined_type_exists(self):
        assert NotificationType.HOUSEHOLD_MEMBER_JOINED == "household_member_joined"

    def test_household_member_left_type_exists(self):
        assert NotificationType.HOUSEHOLD_MEMBER_LEFT == "household_member_left"

    def test_fire_coast_fi_type_exists(self):
        assert NotificationType.FIRE_COAST_FI == "fire_coast_fi"

    def test_fire_independent_type_exists(self):
        assert NotificationType.FIRE_INDEPENDENT == "fire_independent"

    def test_retirement_scenario_stale_type_exists(self):
        assert NotificationType.RETIREMENT_SCENARIO_STALE == "retirement_scenario_stale"

    def test_all_notification_types_count(self):
        """Ensure we have the expected number of notification types."""
        assert len(NotificationType) == 32


class TestHouseholdNotifications:
    """Test household join/leave notification creation."""

    @pytest.mark.asyncio
    async def test_household_join_creates_notification(self, db, test_user):
        """Accepting an invitation should create HOUSEHOLD_MEMBER_JOINED notification."""
        from app.services.notification_service import NotificationService

        notification = await NotificationService.create_notification(
            db=db,
            organization_id=test_user.organization_id,
            type=NotificationType.HOUSEHOLD_MEMBER_JOINED,
            title="Alice joined your household!",
            message="Alice has accepted the invitation and joined your household.",
            priority=NotificationPriority.MEDIUM,
            action_url="/settings",
            action_label="View Household",
            expires_in_days=14,
        )

        assert notification.id is not None
        assert notification.type == NotificationType.HOUSEHOLD_MEMBER_JOINED
        assert notification.priority == NotificationPriority.MEDIUM
        assert notification.user_id is None  # Org-wide
        assert "Alice" in notification.title
        assert notification.action_url == "/settings"
        assert notification.expires_at is not None

    @pytest.mark.asyncio
    async def test_household_leave_creates_notification(self, db, test_user):
        """Leaving a household should create HOUSEHOLD_MEMBER_LEFT notification."""
        from app.services.notification_service import NotificationService

        notification = await NotificationService.create_notification(
            db=db,
            organization_id=test_user.organization_id,
            type=NotificationType.HOUSEHOLD_MEMBER_LEFT,
            title="Bob left the household",
            message="Bob has left your household. Their accounts have been moved.",
            priority=NotificationPriority.MEDIUM,
            action_url="/settings",
            action_label="View Household",
            expires_in_days=14,
        )

        assert notification.type == NotificationType.HOUSEHOLD_MEMBER_LEFT
        assert "Bob" in notification.title
        assert notification.action_url == "/settings"

    @pytest.mark.asyncio
    async def test_household_remove_creates_notification(self, db, test_user):
        """Removing a member should create HOUSEHOLD_MEMBER_LEFT notification."""
        from app.services.notification_service import NotificationService

        notification = await NotificationService.create_notification(
            db=db,
            organization_id=test_user.organization_id,
            type=NotificationType.HOUSEHOLD_MEMBER_LEFT,
            title="Charlie was removed from the household",
            message=(
                "Charlie has been removed. "
                "Their accounts are no longer part of your shared finances."
            ),
            priority=NotificationPriority.MEDIUM,
            action_url="/settings",
            action_label="View Household",
            expires_in_days=14,
        )

        assert notification.type == NotificationType.HOUSEHOLD_MEMBER_LEFT
        assert "removed" in notification.title


class TestFireMilestoneDetection:
    """Test FIRE milestone detection logic."""

    @pytest.mark.asyncio
    async def test_fire_independent_notification_created(self, db, test_user):
        """Should create FIRE_INDEPENDENT notification when fi_ratio >= 1.0."""
        from app.services.fire_service import FireService

        service = FireService(db)
        org_id = test_user.organization_id

        # Mock get_fire_dashboard to return FI achieved state
        mock_metrics = {
            "fi_ratio": {
                "fi_ratio": 1.2,
                "investable_assets": 1200000,
                "annual_expenses": 40000,
                "fi_number": 1000000,
            },
            "savings_rate": {
                "savings_rate": 0.5,
                "income": 100000,
                "spending": 50000,
                "savings": 50000,
                "months": 12,
            },
            "years_to_fi": {
                "years_to_fi": 0,
                "fi_number": 1000000,
                "investable_assets": 1200000,
                "annual_savings": 50000,
                "withdrawal_rate": 0.04,
                "expected_return": 0.07,
                "already_fi": True,
            },
            "coast_fi": {
                "coast_fi_number": 300000,
                "fi_number": 1000000,
                "investable_assets": 1200000,
                "is_coast_fi": True,
                "retirement_age": 65,
                "years_until_retirement": 35,
                "expected_return": 0.07,
            },
        }

        with patch.object(
            service, "get_fire_dashboard", new_callable=AsyncMock, return_value=mock_metrics
        ):
            await service.check_fire_milestones(org_id)

        # Verify notification was created
        from sqlalchemy import select

        from app.models.notification import Notification

        result = await db.execute(
            select(Notification).where(
                Notification.organization_id == org_id,
                Notification.type == NotificationType.FIRE_INDEPENDENT,
            )
        )
        notification = result.scalar_one_or_none()
        assert notification is not None
        assert "Financial Independence" in notification.title
        assert notification.action_url == "/fire"

    @pytest.mark.asyncio
    async def test_fire_coast_fi_notification_created(self, db, test_user):
        """Should create FIRE_COAST_FI notification when is_coast_fi is true."""
        from app.services.fire_service import FireService

        service = FireService(db)
        org_id = test_user.organization_id

        mock_metrics = {
            "fi_ratio": {
                "fi_ratio": 0.5,
                "investable_assets": 500000,
                "annual_expenses": 40000,
                "fi_number": 1000000,
            },
            "savings_rate": {
                "savings_rate": 0.5,
                "income": 100000,
                "spending": 50000,
                "savings": 50000,
                "months": 12,
            },
            "years_to_fi": {
                "years_to_fi": 10,
                "fi_number": 1000000,
                "investable_assets": 500000,
                "annual_savings": 50000,
                "withdrawal_rate": 0.04,
                "expected_return": 0.07,
                "already_fi": False,
            },
            "coast_fi": {
                "coast_fi_number": 300000,
                "fi_number": 1000000,
                "investable_assets": 500000,
                "is_coast_fi": True,
                "retirement_age": 65,
                "years_until_retirement": 35,
                "expected_return": 0.07,
            },
        }

        with patch.object(
            service, "get_fire_dashboard", new_callable=AsyncMock, return_value=mock_metrics
        ):
            await service.check_fire_milestones(org_id)

        from sqlalchemy import select

        from app.models.notification import Notification

        result = await db.execute(
            select(Notification).where(
                Notification.organization_id == org_id,
                Notification.type == NotificationType.FIRE_COAST_FI,
            )
        )
        notification = result.scalar_one_or_none()
        assert notification is not None
        assert "Coast FI" in notification.title

    @pytest.mark.asyncio
    async def test_fire_notifications_deduplicate(self, db, test_user):
        """Should not create duplicate FIRE notifications if one already exists."""
        from app.services.fire_service import FireService
        from app.services.notification_service import NotificationService

        org_id = test_user.organization_id

        # Create an existing FIRE_INDEPENDENT notification
        await NotificationService.create_notification(
            db=db,
            organization_id=org_id,
            type=NotificationType.FIRE_INDEPENDENT,
            title="Financial Independence reached!",
            message="Already notified.",
            priority=NotificationPriority.LOW,
        )

        service = FireService(db)
        mock_metrics = {
            "fi_ratio": {
                "fi_ratio": 1.5,
                "investable_assets": 1500000,
                "annual_expenses": 40000,
                "fi_number": 1000000,
            },
            "savings_rate": {
                "savings_rate": 0.5,
                "income": 100000,
                "spending": 50000,
                "savings": 50000,
                "months": 12,
            },
            "years_to_fi": {
                "years_to_fi": 0,
                "fi_number": 1000000,
                "investable_assets": 1500000,
                "annual_savings": 50000,
                "withdrawal_rate": 0.04,
                "expected_return": 0.07,
                "already_fi": True,
            },
            "coast_fi": {
                "coast_fi_number": 300000,
                "fi_number": 1000000,
                "investable_assets": 1500000,
                "is_coast_fi": True,
                "retirement_age": 65,
                "years_until_retirement": 35,
                "expected_return": 0.07,
            },
        }

        with patch.object(
            service, "get_fire_dashboard", new_callable=AsyncMock, return_value=mock_metrics
        ):
            await service.check_fire_milestones(org_id)

        # Should still only have 1 FIRE_INDEPENDENT notification (not 2)
        from sqlalchemy import func, select

        from app.models.notification import Notification

        result = await db.execute(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.organization_id == org_id,
                Notification.type == NotificationType.FIRE_INDEPENDENT,
            )
        )
        count = result.scalar_one()
        assert count == 1

    @pytest.mark.asyncio
    async def test_fire_no_notification_when_not_fi(self, db, test_user):
        """Should not create notifications when FI metrics are below thresholds."""
        from app.services.fire_service import FireService

        service = FireService(db)
        org_id = test_user.organization_id

        mock_metrics = {
            "fi_ratio": {
                "fi_ratio": 0.3,
                "investable_assets": 300000,
                "annual_expenses": 40000,
                "fi_number": 1000000,
            },
            "savings_rate": {
                "savings_rate": 0.3,
                "income": 100000,
                "spending": 70000,
                "savings": 30000,
                "months": 12,
            },
            "years_to_fi": {
                "years_to_fi": 20,
                "fi_number": 1000000,
                "investable_assets": 300000,
                "annual_savings": 30000,
                "withdrawal_rate": 0.04,
                "expected_return": 0.07,
                "already_fi": False,
            },
            "coast_fi": {
                "coast_fi_number": 300000,
                "fi_number": 1000000,
                "investable_assets": 200000,
                "is_coast_fi": False,
                "retirement_age": 65,
                "years_until_retirement": 35,
                "expected_return": 0.07,
            },
        }

        with patch.object(
            service, "get_fire_dashboard", new_callable=AsyncMock, return_value=mock_metrics
        ):
            await service.check_fire_milestones(org_id)

        from sqlalchemy import func, select

        from app.models.notification import Notification

        result = await db.execute(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.organization_id == org_id,
                Notification.type.in_(
                    [NotificationType.FIRE_INDEPENDENT, NotificationType.FIRE_COAST_FI]
                ),
            )
        )
        count = result.scalar_one()
        assert count == 0


class TestRetirementStaleNotification:
    """Test retirement scenario stale notification."""

    @pytest.mark.asyncio
    async def test_stale_notification_created(self, db, test_user):
        """Should create RETIREMENT_SCENARIO_STALE notification when scenarios are archived."""
        from app.services.notification_service import NotificationService

        notification = await NotificationService.create_notification(
            db=db,
            organization_id=test_user.organization_id,
            type=NotificationType.RETIREMENT_SCENARIO_STALE,
            title="Retirement scenario needs attention",
            message=(
                "2 retirement scenario(s) were archived "
                "because Bob is no longer in the household."
            ),
            priority=NotificationPriority.LOW,
            action_url="/retirement",
            action_label="View Scenarios",
            expires_in_days=30,
        )

        assert notification.type == NotificationType.RETIREMENT_SCENARIO_STALE
        assert "archived" in notification.message
        assert notification.action_url == "/retirement"


class TestAccountConnectedNotification:
    """Test account connected notification across all providers."""

    @pytest.mark.asyncio
    async def test_account_connected_plaid(self, db, test_user):
        """Should create ACCOUNT_CONNECTED notification on Plaid link."""
        from app.services.notification_service import NotificationService

        notification = await NotificationService.create_notification(
            db=db,
            organization_id=test_user.organization_id,
            type=NotificationType.ACCOUNT_CONNECTED,
            title="New account connected: Chase",
            message="Alice connected 3 account(s) from Chase via Plaid.",
            priority=NotificationPriority.LOW,
            action_url="/accounts",
            action_label="View Accounts",
            expires_in_days=14,
        )

        assert notification.type == NotificationType.ACCOUNT_CONNECTED
        assert "Chase" in notification.title
        assert "via Plaid" in notification.message
        assert notification.action_url == "/accounts"

    @pytest.mark.asyncio
    async def test_account_connected_teller(self, db, test_user):
        """Should create ACCOUNT_CONNECTED notification on Teller link."""
        from app.services.notification_service import NotificationService

        notification = await NotificationService.create_notification(
            db=db,
            organization_id=test_user.organization_id,
            type=NotificationType.ACCOUNT_CONNECTED,
            title="New account connected: Wells Fargo",
            message=("Bob connected 2 account(s) from Wells Fargo" " via Teller."),
            priority=NotificationPriority.LOW,
            action_url="/accounts",
            action_label="View Accounts",
            expires_in_days=14,
        )

        assert notification.type == NotificationType.ACCOUNT_CONNECTED
        assert "Wells Fargo" in notification.title
        assert "via Teller" in notification.message
        assert notification.expires_at is not None

    @pytest.mark.asyncio
    async def test_account_connected_mx(self, db, test_user):
        """Should create ACCOUNT_CONNECTED notification on MX link."""
        from app.services.notification_service import NotificationService

        notification = await NotificationService.create_notification(
            db=db,
            organization_id=test_user.organization_id,
            type=NotificationType.ACCOUNT_CONNECTED,
            title="New account connected: Bank of America",
            message=("Carol connected 1 account(s) from Bank of America" " via Mx."),
            priority=NotificationPriority.LOW,
            action_url="/accounts",
            action_label="View Accounts",
            expires_in_days=14,
        )

        assert notification.type == NotificationType.ACCOUNT_CONNECTED
        assert "Bank of America" in notification.title
        assert "via Mx" in notification.message
        assert notification.action_label == "View Accounts"

    @pytest.mark.asyncio
    async def test_account_connected_includes_provider(self, db, test_user):
        """Notification message should include provider name for clarity."""
        from app.services.notification_service import NotificationService

        notification = await NotificationService.create_notification(
            db=db,
            organization_id=test_user.organization_id,
            type=NotificationType.ACCOUNT_CONNECTED,
            title="New account connected: Fidelity",
            message=("Alice connected 1 account(s) from Fidelity" " via Plaid."),
            priority=NotificationPriority.LOW,
            action_url="/accounts",
            action_label="View Accounts",
            expires_in_days=14,
        )

        # user_id=None means org-wide (visible to all household members)
        assert notification.user_id is None
        # Provider detail is included in message
        assert "via Plaid" in notification.message


class TestFireMilestoneRenotification:
    """Test FIRE milestone re-notification after dismissal."""

    @pytest.mark.asyncio
    async def test_fire_renotifies_after_dismiss(self, db, test_user):
        """Should create new notification if previous one was dismissed."""
        from app.services.fire_service import FireService
        from app.services.notification_service import NotificationService

        org_id = test_user.organization_id

        # Create and dismiss an existing FIRE_COAST_FI notification
        notif = await NotificationService.create_notification(
            db=db,
            organization_id=org_id,
            type=NotificationType.FIRE_COAST_FI,
            title="Coast FI reached!",
            message="Previously notified.",
            priority=NotificationPriority.LOW,
        )
        # Directly dismiss it (mark_as_dismissed requires a User object)
        from app.utils.datetime_utils import utc_now

        notif.is_dismissed = True
        notif.dismissed_at = utc_now()
        await db.flush()

        service = FireService(db)
        mock_metrics = {
            "fi_ratio": {
                "fi_ratio": 0.6,
                "investable_assets": 600000,
                "annual_expenses": 40000,
                "fi_number": 1000000,
            },
            "savings_rate": {
                "savings_rate": 0.5,
                "income": 100000,
                "spending": 50000,
                "savings": 50000,
                "months": 12,
            },
            "years_to_fi": {
                "years_to_fi": 8,
                "fi_number": 1000000,
                "investable_assets": 600000,
                "annual_savings": 50000,
                "withdrawal_rate": 0.04,
                "expected_return": 0.07,
                "already_fi": False,
            },
            "coast_fi": {
                "coast_fi_number": 300000,
                "fi_number": 1000000,
                "investable_assets": 600000,
                "is_coast_fi": True,
                "retirement_age": 65,
                "years_until_retirement": 35,
                "expected_return": 0.07,
            },
        }

        with patch.object(
            service,
            "get_fire_dashboard",
            new_callable=AsyncMock,
            return_value=mock_metrics,
        ):
            await service.check_fire_milestones(org_id)

        # Should have created a new notification since old was dismissed
        from sqlalchemy import select

        from app.models.notification import Notification

        result = await db.execute(
            select(Notification).where(
                Notification.organization_id == org_id,
                Notification.type == NotificationType.FIRE_COAST_FI,
                Notification.is_dismissed.is_(False),
            )
        )
        new_notif = result.scalar_one_or_none()
        assert new_notif is not None
        assert new_notif.id != notif.id
