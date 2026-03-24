"""Unit tests for notification API endpoints."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.notifications import (
    create_notification,
    create_test_notification,
    dismiss_notification,
    get_household_digest,
    get_unread_count,
    list_notifications,
    mark_all_notifications_read,
    mark_notification_read,
)
from app.models.notification import NotificationPriority, NotificationType
from app.schemas.notification import NotificationCreate
from app.models.user import User


def _mock_user():
    user = Mock(spec=User)
    user.id = uuid4()
    user.organization_id = uuid4()
    return user


def _mock_notification(ntype_value="budget_alert", priority_value="medium", is_read=False):
    n = Mock()
    n.id = uuid4()
    n.user_id = uuid4()
    n.type = Mock(value=ntype_value)
    n.title = "Test notification"
    n.message = "Test message"
    n.priority = Mock(value=priority_value)
    n.is_read = is_read
    n.created_at = datetime.now(timezone.utc)
    return n


@pytest.mark.unit
class TestListNotifications:
    @pytest.mark.asyncio
    async def test_returns_notifications(self):
        mock_db = AsyncMock()
        user = _mock_user()
        notifications = [Mock(), Mock()]

        with patch("app.api.v1.notifications.notification_service") as mock_svc:
            mock_svc.get_user_notifications = AsyncMock(return_value=notifications)
            result = await list_notifications(
                include_read=False, limit=50, current_user=user, db=mock_db
            )

        assert result == notifications
        mock_svc.get_user_notifications.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_include_read_passed(self):
        mock_db = AsyncMock()
        user = _mock_user()

        with patch("app.api.v1.notifications.notification_service") as mock_svc:
            mock_svc.get_user_notifications = AsyncMock(return_value=[])
            await list_notifications(include_read=True, limit=100, current_user=user, db=mock_db)

        call_kwargs = mock_svc.get_user_notifications.call_args[1]
        assert call_kwargs["include_read"] is True
        assert call_kwargs["limit"] == 100


@pytest.mark.unit
class TestGetUnreadCount:
    @pytest.mark.asyncio
    async def test_returns_count(self):
        mock_db = AsyncMock()
        user = _mock_user()

        with patch("app.api.v1.notifications.notification_service") as mock_svc:
            mock_svc.get_unread_count = AsyncMock(return_value=5)
            result = await get_unread_count(current_user=user, db=mock_db)

        assert result == {"count": 5}


@pytest.mark.unit
class TestGetHouseholdDigest:
    @pytest.mark.asyncio
    async def test_returns_grouped_notifications(self):
        mock_db = AsyncMock()
        user = _mock_user()

        n1 = _mock_notification("budget_alert")
        n2 = _mock_notification("sync_complete")

        scalars_mock = Mock()
        scalars_mock.all.return_value = [n1, n2]
        result_mock = Mock()
        result_mock.scalars.return_value = scalars_mock
        mock_db.execute.return_value = result_mock

        result = await get_household_digest(days=7, current_user=user, db=mock_db)

        assert result["organization_id"] == str(user.organization_id)
        assert result["days"] == 7
        assert result["total_notifications"] == 2
        assert "groups" in result

    @pytest.mark.asyncio
    async def test_empty_notifications(self):
        mock_db = AsyncMock()
        user = _mock_user()

        scalars_mock = Mock()
        scalars_mock.all.return_value = []
        result_mock = Mock()
        result_mock.scalars.return_value = scalars_mock
        mock_db.execute.return_value = result_mock

        result = await get_household_digest(days=7, current_user=user, db=mock_db)

        assert result["total_notifications"] == 0
        assert result["groups"] == {}


@pytest.mark.unit
class TestMarkNotificationRead:
    @pytest.mark.asyncio
    async def test_marks_read_success(self):
        mock_db = AsyncMock()
        user = _mock_user()
        notification = Mock()

        with patch("app.api.v1.notifications.notification_service") as mock_svc:
            mock_svc.mark_as_read = AsyncMock(return_value=notification)
            result = await mark_notification_read(
                notification_id=uuid4(), current_user=user, db=mock_db
            )

        assert result == notification


@pytest.mark.unit
class TestCreateNotification:
    """Tests for POST /notifications/ — frontend-driven bell persistence."""

    def _make_payload(self, **overrides):
        defaults = dict(
            type=NotificationType.BUDGET_ALERT,
            priority=NotificationPriority.MEDIUM,
            title="You hit your budget",
            message="Your groceries budget is 90% spent.",
            action_url="/budgets",
            action_label="View budgets",
            expires_in_days=30,
        )
        defaults.update(overrides)
        return NotificationCreate(**defaults)

    @pytest.mark.asyncio
    async def test_creates_notification_scoped_to_calling_user(self):
        """When no user_id in payload, notification is scoped to the calling user."""
        mock_db = AsyncMock()
        user = _mock_user()
        payload = self._make_payload()
        created = Mock()

        with patch("app.api.v1.notifications.NotificationService") as MockNS:
            MockNS.create_notification = AsyncMock(return_value=created)
            result = await create_notification(payload=payload, current_user=user, db=mock_db)

        assert result == created
        call_kwargs = MockNS.create_notification.call_args[1]
        assert call_kwargs["user_id"] == user.id
        assert call_kwargs["organization_id"] == user.organization_id
        assert call_kwargs["type"] == NotificationType.BUDGET_ALERT
        assert call_kwargs["title"] == "You hit your budget"
        assert call_kwargs["priority"] == NotificationPriority.MEDIUM

    @pytest.mark.asyncio
    async def test_explicit_user_id_in_payload_is_used(self):
        """When payload.user_id is set, that ID is forwarded (household member support)."""
        mock_db = AsyncMock()
        user = _mock_user()
        other_user_id = uuid4()
        payload = self._make_payload(user_id=other_user_id)
        created = Mock()

        with patch("app.api.v1.notifications.NotificationService") as MockNS:
            MockNS.create_notification = AsyncMock(return_value=created)
            await create_notification(payload=payload, current_user=user, db=mock_db)

        call_kwargs = MockNS.create_notification.call_args[1]
        assert call_kwargs["user_id"] == other_user_id

    @pytest.mark.asyncio
    async def test_optional_fields_forwarded(self):
        """related_entity_type / action_url and expires_in_days are passed through."""
        mock_db = AsyncMock()
        user = _mock_user()
        entity_id = uuid4()
        payload = self._make_payload(
            related_entity_type="account",
            related_entity_id=entity_id,
            expires_in_days=7,
        )

        with patch("app.api.v1.notifications.NotificationService") as MockNS:
            MockNS.create_notification = AsyncMock(return_value=Mock())
            await create_notification(payload=payload, current_user=user, db=mock_db)

        call_kwargs = MockNS.create_notification.call_args[1]
        assert call_kwargs["related_entity_type"] == "account"
        assert call_kwargs["related_entity_id"] == entity_id
        assert call_kwargs["expires_in_days"] == 7

    @pytest.mark.asyncio
    async def test_not_found_raises_404(self):
        mock_db = AsyncMock()
        user = _mock_user()

        with patch("app.api.v1.notifications.notification_service") as mock_svc:
            mock_svc.mark_as_read = AsyncMock(return_value=None)
            with pytest.raises(HTTPException) as exc_info:
                await mark_notification_read(notification_id=uuid4(), current_user=user, db=mock_db)
        assert exc_info.value.status_code == 404


@pytest.mark.unit
class TestDismissNotification:
    @pytest.mark.asyncio
    async def test_dismiss_success(self):
        mock_db = AsyncMock()
        user = _mock_user()
        notification = Mock()

        with patch("app.api.v1.notifications.notification_service") as mock_svc:
            mock_svc.mark_as_dismissed = AsyncMock(return_value=notification)
            result = await dismiss_notification(
                notification_id=uuid4(), current_user=user, db=mock_db
            )

        assert result == notification

    @pytest.mark.asyncio
    async def test_not_found_raises_404(self):
        mock_db = AsyncMock()
        user = _mock_user()

        with patch("app.api.v1.notifications.notification_service") as mock_svc:
            mock_svc.mark_as_dismissed = AsyncMock(return_value=None)
            with pytest.raises(HTTPException) as exc_info:
                await dismiss_notification(notification_id=uuid4(), current_user=user, db=mock_db)
        assert exc_info.value.status_code == 404


@pytest.mark.unit
class TestMarkAllNotificationsRead:
    @pytest.mark.asyncio
    async def test_returns_count(self):
        mock_db = AsyncMock()
        user = _mock_user()

        with patch("app.api.v1.notifications.notification_service") as mock_svc, \
             patch("app.services.rate_limit_service.rate_limit_service.check_rate_limit", new_callable=AsyncMock):
            mock_svc.mark_all_as_read = AsyncMock(return_value=10)
            result = await mark_all_notifications_read(http_request=MagicMock(), current_user=user, db=mock_db)

        assert result == {"marked_read": 10}


@pytest.mark.unit
class TestCreateTestNotification:
    @pytest.mark.asyncio
    async def test_production_returns_404(self):
        mock_db = AsyncMock()
        user = _mock_user()

        with patch("app.api.v1.notifications.settings") as mock_settings:
            mock_settings.ENVIRONMENT = "production"
            with pytest.raises(HTTPException) as exc_info:
                await create_test_notification(current_user=user, db=mock_db)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_non_production_creates_notification(self):
        mock_db = AsyncMock()
        user = _mock_user()
        notification = Mock()

        with (
            patch("app.api.v1.notifications.settings") as mock_settings,
            patch("app.api.v1.notifications.NotificationService") as MockNS,
        ):
            mock_settings.ENVIRONMENT = "development"
            MockNS.create_notification = AsyncMock(return_value=notification)
            result = await create_test_notification(current_user=user, db=mock_db)

        assert result == notification
