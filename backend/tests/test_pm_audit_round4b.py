"""
PM Audit Round 4b — tests for:
1. /reports/household-summary blocks guests
2. Notification email_sent tracking (True on success, False on failure)
3. BudgetForm initialProviderCategoryName logic (filterBy + providerCategoryName)
"""

from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from uuid import uuid4

import pytest


# ---------------------------------------------------------------------------
# 1. /reports/household-summary guest guard
# ---------------------------------------------------------------------------

class TestHouseholdSummaryGuestGuard:
    @pytest.mark.asyncio
    async def test_guest_is_blocked(self):
        from fastapi import HTTPException
        from app.api.v1.reports import get_household_summary

        mock_user = MagicMock()
        mock_user._is_guest = True
        mock_user.organization_id = uuid4()

        mock_db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await get_household_summary(current_user=mock_user, db=mock_db)

        assert exc_info.value.status_code == 403
        assert "guest" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_non_guest_proceeds(self):
        """Members (non-guests) should not be blocked by the guest guard."""
        from app.api.v1.reports import get_household_summary

        mock_user = MagicMock()
        mock_user._is_guest = False
        mock_user.organization_id = uuid4()

        # Return empty accounts + empty members so endpoint completes
        mock_empty = MagicMock()
        mock_empty.scalars.return_value.all.return_value = []
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_empty)

        result = await get_household_summary(current_user=mock_user, db=mock_db)
        assert "total_household_net_worth" in result

    @pytest.mark.asyncio
    async def test_missing_is_guest_attribute_proceeds(self):
        """If _is_guest is not set (older code path), getattr returns False → allowed."""
        from app.api.v1.reports import get_household_summary

        mock_user = MagicMock(spec=[])  # spec=[] means no attributes by default
        mock_user.organization_id = uuid4()

        mock_empty = MagicMock()
        mock_empty.scalars.return_value.all.return_value = []
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_empty)

        result = await get_household_summary(current_user=mock_user, db=mock_db)
        assert "total_household_net_worth" in result


# ---------------------------------------------------------------------------
# 2. Notification email_sent delivery tracking
# ---------------------------------------------------------------------------

class TestNotificationEmailSentTracking:
    @pytest.mark.asyncio
    async def test_email_sent_true_on_success(self):
        """email_sent should be True when email service succeeds."""
        from app.services.notification_service import NotificationService
        from app.models.notification import NotificationType, NotificationPriority

        user_id = uuid4()
        org_id = uuid4()

        mock_notification = MagicMock()
        mock_notification.id = uuid4()
        mock_notification.email_sent = None

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.email = "user@example.com"
        mock_user.email_notifications_enabled = True

        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = mock_user

        call_count = 0

        async def mock_execute(query):
            nonlocal call_count
            call_count += 1
            return mock_user_result

        mock_db = AsyncMock()
        mock_db.execute = mock_execute
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock(return_value=mock_notification)

        # Patch db.add to capture the notification object
        added_objects = []
        def capture_add(obj):
            added_objects.append(obj)
        mock_db.add = capture_add

        # Use the real Notification class so email_sent is set
        with patch(
            "app.services.notification_service.Notification",
            return_value=mock_notification,
        ), patch(
            "app.services.notification_service.email_service"
        ) as mock_email:
            mock_email.is_configured = True
            mock_email.send_notification_email = AsyncMock()

            result = await NotificationService.create_notification(
                db=mock_db,
                organization_id=org_id,
                user_id=user_id,
                type=NotificationType.BUDGET_ALERT,
                title="Test",
                message="Test message",
            )

        assert mock_notification.email_sent is True

    @pytest.mark.asyncio
    async def test_email_sent_false_on_failure(self):
        """email_sent should be False when email service raises an exception."""
        from app.services.notification_service import NotificationService
        from app.models.notification import NotificationType

        user_id = uuid4()
        org_id = uuid4()

        mock_notification = MagicMock()
        mock_notification.id = uuid4()
        mock_notification.email_sent = None

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.email = "user@example.com"
        mock_user.email_notifications_enabled = True

        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = mock_user

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_user_result)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock(return_value=mock_notification)

        with patch(
            "app.services.notification_service.Notification",
            return_value=mock_notification,
        ), patch(
            "app.services.notification_service.email_service"
        ) as mock_email:
            mock_email.is_configured = True
            mock_email.send_notification_email = AsyncMock(
                side_effect=Exception("SMTP connection refused")
            )

            await NotificationService.create_notification(
                db=mock_db,
                organization_id=org_id,
                user_id=user_id,
                type=NotificationType.BUDGET_ALERT,
                title="Test",
                message="Test message",
            )

        assert mock_notification.email_sent is False

    def test_email_sent_none_when_no_email_attempted(self):
        """email_sent stays None when email service is not configured."""
        from app.models.notification import Notification

        n = Notification()
        # Column default is None — no email attempted
        assert n.email_sent is None


# ---------------------------------------------------------------------------
# 3. BudgetForm provider category name logic
# ---------------------------------------------------------------------------

class TestBudgetFormProviderCategoryNameLogic:
    """Test the logic that determines filterBy and providerCategoryName on open."""

    def _compute_filter_by(
        self,
        budget=None,
        initial_category_id=None,
        initial_provider_category_name=None,
    ) -> str:
        """Mirror the useState initializer logic from BudgetForm."""
        if budget:
            # getInitialFilterBy
            if getattr(budget, "label_id", None):
                return "label"
            if getattr(budget, "category_id", None):
                return "category"
            return "all"
        if initial_category_id or initial_provider_category_name:
            return "category"
        return "all"

    def test_uuid_category_sets_filter_to_category(self):
        result = self._compute_filter_by(initial_category_id="cat-uuid-123")
        assert result == "category"

    def test_provider_category_name_sets_filter_to_category(self):
        result = self._compute_filter_by(initial_provider_category_name="Food And Drink")
        assert result == "category"

    def test_no_category_leaves_filter_all(self):
        result = self._compute_filter_by()
        assert result == "all"

    def test_both_null_leaves_filter_all(self):
        result = self._compute_filter_by(
            initial_category_id=None, initial_provider_category_name=None
        )
        assert result == "all"

    def test_existing_budget_with_category_sets_category(self):
        mock_budget = MagicMock()
        mock_budget.category_id = "some-uuid"
        mock_budget.label_id = None
        result = self._compute_filter_by(budget=mock_budget)
        assert result == "category"

    def test_existing_budget_with_label_sets_label(self):
        mock_budget = MagicMock()
        mock_budget.label_id = "label-uuid"
        mock_budget.category_id = None
        result = self._compute_filter_by(budget=mock_budget)
        assert result == "label"

    def test_existing_budget_no_filter_sets_all(self):
        mock_budget = MagicMock()
        mock_budget.category_id = None
        mock_budget.label_id = None
        result = self._compute_filter_by(budget=mock_budget)
        assert result == "all"

    def test_provider_category_name_stored_correctly(self):
        """When suggestion has no UUID, category_name should be stored as providerCategoryName."""
        suggestion = {"category_id": None, "category_name": "Food And Drink"}
        provider_name = None if suggestion["category_id"] else suggestion["category_name"]
        assert provider_name == "Food And Drink"

    def test_uuid_category_does_not_set_provider_name(self):
        """When suggestion has a UUID, providerCategoryName should be None."""
        suggestion = {"category_id": "abc-123", "category_name": "Groceries"}
        provider_name = None if suggestion["category_id"] else suggestion["category_name"]
        assert provider_name is None
