"""Tests for notification service."""

import pytest
from datetime import timedelta
from uuid import uuid4

from app.services.notification_service import NotificationService
from app.models.notification import NotificationType, NotificationPriority
from app.utils.datetime_utils import utc_now


class TestNotificationService:
    """Test suite for notification service."""

    @pytest.mark.asyncio
    async def test_create_basic_notification(self, db, test_user):
        """Should create basic notification."""
        service = NotificationService()

        notification = await service.create_notification(
            db=db,
            organization_id=test_user.organization_id,
            type=NotificationType.BUDGET_ALERT,
            title="Budget Warning",
            message="You've exceeded your grocery budget",
        )

        assert notification.id is not None
        assert notification.organization_id == test_user.organization_id
        assert notification.type == NotificationType.BUDGET_ALERT
        assert notification.title == "Budget Warning"
        assert notification.message == "You've exceeded your grocery budget"
        assert notification.priority == NotificationPriority.MEDIUM  # Default
        assert notification.is_read is False
        assert notification.is_dismissed is False
        assert notification.user_id is None  # Org-wide by default

    @pytest.mark.asyncio
    async def test_create_notification_with_all_parameters(self, db, test_user):
        """Should create notification with all optional parameters."""
        service = NotificationService()
        account_id = uuid4()

        notification = await service.create_notification(
            db=db,
            organization_id=test_user.organization_id,
            type=NotificationType.REAUTH_REQUIRED,
            title="Reconnect Account",
            message="Your Chase account needs reconnection",
            priority=NotificationPriority.HIGH,
            user_id=test_user.id,
            related_entity_type="account",
            related_entity_id=account_id,
            action_url=f"/accounts/{account_id}",
            action_label="Reconnect Now",
            expires_in_days=7,
        )

        assert notification.priority == NotificationPriority.HIGH
        assert notification.user_id == test_user.id
        assert notification.related_entity_type == "account"
        assert notification.related_entity_id == account_id
        assert notification.action_url == f"/accounts/{account_id}"
        assert notification.action_label == "Reconnect Now"
        assert notification.expires_at is not None

        # Expires_at should be ~7 days from now
        expected_expiry = utc_now() + timedelta(days=7)
        assert abs((notification.expires_at - expected_expiry).total_seconds()) < 10

    @pytest.mark.asyncio
    async def test_create_user_specific_notification(self, db, test_user):
        """Should create notification for specific user."""
        service = NotificationService()

        notification = await service.create_notification(
            db=db,
            organization_id=test_user.organization_id,
            type=NotificationType.LARGE_TRANSACTION,
            title="Large Transaction",
            message="Detected $5,000 purchase at Best Buy",
            user_id=test_user.id,
        )

        assert notification.user_id == test_user.id

    @pytest.mark.asyncio
    async def test_create_org_wide_notification(self, db, test_user):
        """Should create notification for entire organization."""
        service = NotificationService()

        notification = await service.create_notification(
            db=db,
            organization_id=test_user.organization_id,
            type=NotificationType.SYNC_STALE,
            title="Data Sync Stale",
            message="Some accounts haven't synced in 7 days",
            user_id=None,  # Org-wide
        )

        assert notification.user_id is None

    @pytest.mark.asyncio
    async def test_create_notification_priority_levels(self, db, test_user):
        """Should support all priority levels."""
        service = NotificationService()

        priorities = [
            NotificationPriority.LOW,
            NotificationPriority.MEDIUM,
            NotificationPriority.HIGH,
            NotificationPriority.URGENT,
        ]

        for priority in priorities:
            notification = await service.create_notification(
                db=db,
                organization_id=test_user.organization_id,
                type=NotificationType.BUDGET_ALERT,
                title=f"{priority.value} priority",
                message="Test message",
                priority=priority,
            )

            assert notification.priority == priority

    @pytest.mark.asyncio
    async def test_get_user_notifications_unread_only(self, db, test_user):
        """Should get unread notifications only by default."""
        service = NotificationService()

        # Create unread notification
        unread = await service.create_notification(
            db=db,
            organization_id=test_user.organization_id,
            type=NotificationType.BUDGET_ALERT,
            title="Unread",
            message="Unread notification",
        )

        # Create read notification
        read = await service.create_notification(
            db=db,
            organization_id=test_user.organization_id,
            type=NotificationType.BUDGET_ALERT,
            title="Read",
            message="Read notification",
        )
        read.is_read = True
        read.read_at = utc_now()
        await db.commit()

        # Get notifications
        notifications = await service.get_user_notifications(
            db=db,
            user=test_user,
            include_read=False,
        )

        # Should only return unread
        assert len(notifications) == 1
        assert notifications[0].id == unread.id

    @pytest.mark.asyncio
    async def test_get_user_notifications_include_read(self, db, test_user):
        """Should include read notifications when requested."""
        service = NotificationService()

        # Create unread
        await service.create_notification(
            db=db,
            organization_id=test_user.organization_id,
            type=NotificationType.BUDGET_ALERT,
            title="Unread",
            message="Unread",
        )

        # Create read
        read = await service.create_notification(
            db=db,
            organization_id=test_user.organization_id,
            type=NotificationType.BUDGET_ALERT,
            title="Read",
            message="Read",
        )
        read.is_read = True
        await db.commit()

        # Get all notifications
        notifications = await service.get_user_notifications(
            db=db,
            user=test_user,
            include_read=True,
        )

        assert len(notifications) == 2

    @pytest.mark.asyncio
    async def test_get_user_notifications_excludes_dismissed(self, db, test_user):
        """Should exclude dismissed notifications."""
        service = NotificationService()

        # Create active notification
        await service.create_notification(
            db=db,
            organization_id=test_user.organization_id,
            type=NotificationType.BUDGET_ALERT,
            title="Active",
            message="Active",
        )

        # Create dismissed notification
        dismissed = await service.create_notification(
            db=db,
            organization_id=test_user.organization_id,
            type=NotificationType.BUDGET_ALERT,
            title="Dismissed",
            message="Dismissed",
        )
        dismissed.is_dismissed = True
        await db.commit()

        notifications = await service.get_user_notifications(
            db=db,
            user=test_user,
        )

        # Should only return active
        assert len(notifications) == 1
        assert notifications[0].title == "Active"

    @pytest.mark.asyncio
    async def test_get_user_notifications_excludes_expired(self, db, test_user):
        """Should exclude expired notifications."""
        service = NotificationService()

        # Create active notification
        await service.create_notification(
            db=db,
            organization_id=test_user.organization_id,
            type=NotificationType.BUDGET_ALERT,
            title="Active",
            message="Active",
        )

        # Create expired notification
        expired = await service.create_notification(
            db=db,
            organization_id=test_user.organization_id,
            type=NotificationType.BUDGET_ALERT,
            title="Expired",
            message="Expired",
        )
        expired.expires_at = utc_now() - timedelta(days=1)  # Yesterday
        await db.commit()

        notifications = await service.get_user_notifications(
            db=db,
            user=test_user,
        )

        # Should only return active
        assert len(notifications) == 1
        assert notifications[0].title == "Active"

    @pytest.mark.asyncio
    async def test_get_user_notifications_includes_user_specific(self, db, test_user):
        """Should include user-specific notifications."""
        service = NotificationService()

        notification = await service.create_notification(
            db=db,
            organization_id=test_user.organization_id,
            type=NotificationType.LARGE_TRANSACTION,
            title="Your Transaction",
            message="Large transaction detected",
            user_id=test_user.id,
        )

        notifications = await service.get_user_notifications(
            db=db,
            user=test_user,
        )

        assert len(notifications) == 1
        assert notifications[0].id == notification.id

    @pytest.mark.asyncio
    async def test_get_user_notifications_includes_org_wide(self, db, test_user):
        """Should include org-wide notifications."""
        service = NotificationService()

        notification = await service.create_notification(
            db=db,
            organization_id=test_user.organization_id,
            type=NotificationType.SYNC_STALE,
            title="Org Notification",
            message="Organization-wide message",
            user_id=None,  # Org-wide
        )

        notifications = await service.get_user_notifications(
            db=db,
            user=test_user,
        )

        assert len(notifications) == 1
        assert notifications[0].id == notification.id

    @pytest.mark.asyncio
    async def test_get_user_notifications_excludes_other_users(self, db, test_user):
        """Should not return notifications for other users."""
        service = NotificationService()
        other_user_id = uuid4()

        # Create notification for other user
        await service.create_notification(
            db=db,
            organization_id=test_user.organization_id,
            type=NotificationType.LARGE_TRANSACTION,
            title="Other User",
            message="Not for test_user",
            user_id=other_user_id,
        )

        notifications = await service.get_user_notifications(
            db=db,
            user=test_user,
        )

        # Should not include other user's notification
        assert len(notifications) == 0

    @pytest.mark.asyncio
    async def test_get_user_notifications_ordered_by_priority(self, db, test_user):
        """Should order by priority (high first) then created_at."""
        service = NotificationService()

        # Create in random order
        low = await service.create_notification(
            db=db,
            organization_id=test_user.organization_id,
            type=NotificationType.BUDGET_ALERT,
            title="Low",
            message="Low",
            priority=NotificationPriority.LOW,
        )

        high = await service.create_notification(
            db=db,
            organization_id=test_user.organization_id,
            type=NotificationType.REAUTH_REQUIRED,
            title="High",
            message="High",
            priority=NotificationPriority.HIGH,
        )

        medium = await service.create_notification(
            db=db,
            organization_id=test_user.organization_id,
            type=NotificationType.SYNC_FAILED,
            title="Medium",
            message="Medium",
            priority=NotificationPriority.MEDIUM,
        )

        notifications = await service.get_user_notifications(
            db=db,
            user=test_user,
        )

        # Should be ordered high, medium, low
        assert len(notifications) == 3
        assert notifications[0].id == high.id
        assert notifications[1].id == medium.id
        assert notifications[2].id == low.id

    @pytest.mark.asyncio
    async def test_get_user_notifications_limit(self, db, test_user):
        """Should respect limit parameter."""
        service = NotificationService()

        # Create 10 notifications
        for i in range(10):
            await service.create_notification(
                db=db,
                organization_id=test_user.organization_id,
                type=NotificationType.BUDGET_ALERT,
                title=f"Notification {i}",
                message=f"Message {i}",
            )

        # Request only 5
        notifications = await service.get_user_notifications(
            db=db,
            user=test_user,
            limit=5,
        )

        assert len(notifications) == 5

    @pytest.mark.asyncio
    async def test_mark_as_read(self, db, test_user):
        """Should mark notification as read."""
        service = NotificationService()

        notification = await service.create_notification(
            db=db,
            organization_id=test_user.organization_id,
            type=NotificationType.BUDGET_ALERT,
            title="Test",
            message="Test",
        )

        assert notification.is_read is False
        assert notification.read_at is None

        # Mark as read
        updated = await service.mark_as_read(
            db=db,
            notification_id=notification.id,
            user=test_user,
        )

        assert updated is not None
        assert updated.is_read is True
        assert updated.read_at is not None
        assert abs((updated.read_at - utc_now()).total_seconds()) < 10

    @pytest.mark.asyncio
    async def test_mark_as_read_cross_org_blocked(self, db, test_user):
        """Should not allow marking notifications from other orgs."""
        service = NotificationService()
        other_org_id = uuid4()

        # Create notification in other org
        notification = await service.create_notification(
            db=db,
            organization_id=other_org_id,
            type=NotificationType.BUDGET_ALERT,
            title="Other Org",
            message="Other Org",
        )

        # Try to mark as read
        result = await service.mark_as_read(
            db=db,
            notification_id=notification.id,
            user=test_user,
        )

        # Should not find it
        assert result is None

    @pytest.mark.asyncio
    async def test_mark_as_dismissed(self, db, test_user):
        """Should mark notification as dismissed."""
        service = NotificationService()

        notification = await service.create_notification(
            db=db,
            organization_id=test_user.organization_id,
            type=NotificationType.BUDGET_ALERT,
            title="Test",
            message="Test",
        )

        assert notification.is_dismissed is False
        assert notification.dismissed_at is None

        # Dismiss
        updated = await service.mark_as_dismissed(
            db=db,
            notification_id=notification.id,
            user=test_user,
        )

        assert updated is not None
        assert updated.is_dismissed is True
        assert updated.dismissed_at is not None

    @pytest.mark.asyncio
    async def test_mark_as_dismissed_cross_org_blocked(self, db, test_user):
        """Should not allow dismissing notifications from other orgs."""
        service = NotificationService()
        other_org_id = uuid4()

        notification = await service.create_notification(
            db=db,
            organization_id=other_org_id,
            type=NotificationType.BUDGET_ALERT,
            title="Other Org",
            message="Other Org",
        )

        result = await service.mark_as_dismissed(
            db=db,
            notification_id=notification.id,
            user=test_user,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_mark_all_as_read(self, db, test_user):
        """Should mark all user notifications as read."""
        service = NotificationService()

        # Create 3 unread notifications
        for i in range(3):
            await service.create_notification(
                db=db,
                organization_id=test_user.organization_id,
                type=NotificationType.BUDGET_ALERT,
                title=f"Test {i}",
                message=f"Message {i}",
            )

        # Mark all as read
        count = await service.mark_all_as_read(
            db=db,
            user=test_user,
        )

        assert count == 3

        # Verify all are read
        notifications = await service.get_user_notifications(
            db=db,
            user=test_user,
            include_read=True,
        )

        for notification in notifications:
            assert notification.is_read is True
            assert notification.read_at is not None

    @pytest.mark.asyncio
    async def test_mark_all_as_read_user_specific_only(self, db, test_user):
        """Should only mark user's notifications as read."""
        service = NotificationService()
        other_user_id = uuid4()

        # Create notification for test_user
        await service.create_notification(
            db=db,
            organization_id=test_user.organization_id,
            type=NotificationType.BUDGET_ALERT,
            title="Test User",
            message="Test",
            user_id=test_user.id,
        )

        # Create notification for other user
        other_notification = await service.create_notification(
            db=db,
            organization_id=test_user.organization_id,
            type=NotificationType.BUDGET_ALERT,
            title="Other User",
            message="Other",
            user_id=other_user_id,
        )

        # Create org-wide notification
        await service.create_notification(
            db=db,
            organization_id=test_user.organization_id,
            type=NotificationType.SYNC_STALE,
            title="Org Wide",
            message="Org",
            user_id=None,
        )

        # Mark all as read for test_user
        count = await service.mark_all_as_read(
            db=db,
            user=test_user,
        )

        # Should mark 2 (user-specific + org-wide), not other user's
        assert count == 2

        # Verify other user's notification still unread
        await db.refresh(other_notification)
        assert other_notification.is_read is False

    @pytest.mark.asyncio
    async def test_get_unread_count(self, db, test_user):
        """Should get count of unread notifications."""
        service = NotificationService()

        # Create 3 unread
        for i in range(3):
            await service.create_notification(
                db=db,
                organization_id=test_user.organization_id,
                type=NotificationType.BUDGET_ALERT,
                title=f"Unread {i}",
                message="Unread",
            )

        # Create 2 read
        for i in range(2):
            notification = await service.create_notification(
                db=db,
                organization_id=test_user.organization_id,
                type=NotificationType.BUDGET_ALERT,
                title=f"Read {i}",
                message="Read",
            )
            notification.is_read = True
            await db.commit()

        count = await service.get_unread_count(
            db=db,
            user=test_user,
        )

        assert count == 3

    @pytest.mark.asyncio
    async def test_get_unread_count_excludes_dismissed(self, db, test_user):
        """Should not count dismissed notifications."""
        service = NotificationService()

        # Create unread
        await service.create_notification(
            db=db,
            organization_id=test_user.organization_id,
            type=NotificationType.BUDGET_ALERT,
            title="Unread",
            message="Unread",
        )

        # Create dismissed
        dismissed = await service.create_notification(
            db=db,
            organization_id=test_user.organization_id,
            type=NotificationType.BUDGET_ALERT,
            title="Dismissed",
            message="Dismissed",
        )
        dismissed.is_dismissed = True
        await db.commit()

        count = await service.get_unread_count(
            db=db,
            user=test_user,
        )

        assert count == 1

    @pytest.mark.asyncio
    async def test_get_unread_count_excludes_expired(self, db, test_user):
        """Should not count expired notifications."""
        service = NotificationService()

        # Create active
        await service.create_notification(
            db=db,
            organization_id=test_user.organization_id,
            type=NotificationType.BUDGET_ALERT,
            title="Active",
            message="Active",
        )

        # Create expired
        expired = await service.create_notification(
            db=db,
            organization_id=test_user.organization_id,
            type=NotificationType.BUDGET_ALERT,
            title="Expired",
            message="Expired",
        )
        expired.expires_at = utc_now() - timedelta(days=1)
        await db.commit()

        count = await service.get_unread_count(
            db=db,
            user=test_user,
        )

        assert count == 1

    @pytest.mark.asyncio
    async def test_create_account_sync_notification_reauth(self, db, test_user):
        """Should create reauth notification for account sync failure."""
        service = NotificationService()
        account_id = uuid4()

        notification = await service.create_account_sync_notification(
            db=db,
            organization_id=test_user.organization_id,
            account_id=account_id,
            account_name="Chase Checking",
            error_message="Authentication expired",
            needs_reauth=True,
        )

        assert notification.type == NotificationType.REAUTH_REQUIRED
        assert notification.priority == NotificationPriority.HIGH
        assert notification.title == "Reconnect Chase Checking"
        assert "Chase Checking" in notification.message
        assert "expired" in notification.message
        assert notification.related_entity_type == "account"
        assert notification.related_entity_id == account_id
        assert notification.action_url == f"/accounts/{account_id}"
        assert notification.action_label == "Reconnect Account"
        assert notification.expires_at is not None

    @pytest.mark.asyncio
    async def test_create_account_sync_notification_sync_failed(self, db, test_user):
        """Should create sync failed notification."""
        service = NotificationService()
        account_id = uuid4()

        notification = await service.create_account_sync_notification(
            db=db,
            organization_id=test_user.organization_id,
            account_id=account_id,
            account_name="Wells Fargo Savings",
            error_message="Server timeout",
            needs_reauth=False,
        )

        assert notification.type == NotificationType.SYNC_FAILED
        assert notification.priority == NotificationPriority.MEDIUM
        assert notification.title == "Sync Failed: Wells Fargo Savings"
        assert "Wells Fargo Savings" in notification.message
        assert "Server timeout" in notification.message
        assert notification.action_label == "View Account"

    @pytest.mark.asyncio
    async def test_notification_not_found(self, db, test_user):
        """Should return None when notification not found."""
        service = NotificationService()
        fake_id = uuid4()

        result = await service.mark_as_read(
            db=db,
            notification_id=fake_id,
            user=test_user,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_no_notifications_returns_empty_list(self, db, test_user):
        """Should return empty list when no notifications exist."""
        service = NotificationService()

        notifications = await service.get_user_notifications(
            db=db,
            user=test_user,
        )

        assert notifications == []

    @pytest.mark.asyncio
    async def test_unread_count_zero_when_no_notifications(self, db, test_user):
        """Should return 0 when no notifications exist."""
        service = NotificationService()

        count = await service.get_unread_count(
            db=db,
            user=test_user,
        )

        assert count == 0

    @pytest.mark.asyncio
    async def test_mark_all_as_read_returns_zero_when_none_exist(self, db, test_user):
        """Should return 0 when no notifications to mark."""
        service = NotificationService()

        count = await service.mark_all_as_read(
            db=db,
            user=test_user,
        )

        assert count == 0

    @pytest.mark.asyncio
    async def test_notification_types_coverage(self, db, test_user):
        """Should support all notification types."""
        service = NotificationService()

        types = [
            NotificationType.SYNC_FAILED,
            NotificationType.REAUTH_REQUIRED,
            NotificationType.SYNC_STALE,
            NotificationType.ACCOUNT_ERROR,
            NotificationType.BUDGET_ALERT,
            NotificationType.TRANSACTION_DUPLICATE,
            NotificationType.LARGE_TRANSACTION,
        ]

        for notification_type in types:
            notification = await service.create_notification(
                db=db,
                organization_id=test_user.organization_id,
                type=notification_type,
                title=f"Test {notification_type.value}",
                message="Test message",
            )

            assert notification.type == notification_type

    @pytest.mark.asyncio
    async def test_singleton_instance(self):
        """Should provide singleton instance."""
        from app.services.notification_service import notification_service

        assert notification_service is not None
        assert isinstance(notification_service, NotificationService)
