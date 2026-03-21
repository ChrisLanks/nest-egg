"""Unit tests for subscriptions API endpoints."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.subscriptions import deactivate_subscription, get_subscriptions
from app.models.recurring_transaction import RecurringFrequency, RecurringTransaction
from app.models.user import User


@pytest.fixture
def mock_user():
    user = Mock(spec=User)
    user.id = uuid4()
    user.organization_id = uuid4()
    user.email = "test@example.com"
    user.is_active = True
    return user


@pytest.fixture
def mock_db():
    return AsyncMock(spec=AsyncSession)


def _make_subscription(org_id=None, **kwargs):
    """Return a minimal subscription-like Mock."""
    sub = Mock(spec=RecurringTransaction)
    sub.id = uuid4()
    sub.organization_id = org_id or uuid4()
    sub.account_id = uuid4()
    sub.merchant_name = kwargs.get("merchant_name", "Netflix")
    sub.frequency = kwargs.get("frequency", RecurringFrequency.MONTHLY)
    sub.average_amount = kwargs.get("average_amount", Decimal("-15.99"))
    sub.confidence_score = kwargs.get("confidence_score", Decimal("0.90"))
    sub.next_expected_date = kwargs.get("next_expected_date", date(2024, 7, 1))
    sub.occurrence_count = kwargs.get("occurrence_count", 6)
    sub.is_active = True
    return sub


@pytest.mark.unit
class TestGetSubscriptions:
    """Tests for GET /subscriptions/."""

    @pytest.mark.asyncio
    @patch("app.api.v1.subscriptions.RecurringDetectionService.get_subscription_summary")
    @patch("app.api.v1.subscriptions.RecurringDetectionService.get_subscriptions")
    async def test_returns_subscriptions(self, mock_get_subs, mock_get_summary, mock_user, mock_db):
        """Should return subscriptions with summary data."""
        subs = [
            _make_subscription(org_id=mock_user.organization_id, merchant_name="Netflix"),
            _make_subscription(org_id=mock_user.organization_id, merchant_name="Spotify"),
        ]
        mock_get_subs.return_value = subs
        mock_get_summary.return_value = {
            "total_count": 2,
            "monthly_cost": 25.98,
            "yearly_cost": 311.76,
        }

        result = await get_subscriptions(user_id=None, current_user=mock_user, db=mock_db)

        mock_get_subs.assert_awaited_once_with(mock_db, mock_user.organization_id, None)
        mock_get_summary.assert_awaited_once_with(mock_db, mock_user.organization_id, None)
        assert result.total_count == 2
        assert result.monthly_cost == 25.98
        assert result.yearly_cost == 311.76
        assert len(result.subscriptions) == 2
        assert result.subscriptions[0].merchant_name == "Netflix"
        assert result.subscriptions[1].merchant_name == "Spotify"
        assert result.subscriptions[0].average_amount == 15.99  # abs applied

    @pytest.mark.asyncio
    @patch("app.api.v1.subscriptions.verify_household_member")
    @patch("app.api.v1.subscriptions.RecurringDetectionService.get_subscription_summary")
    @patch("app.api.v1.subscriptions.RecurringDetectionService.get_subscriptions")
    async def test_with_user_id_calls_verify_household_member(
        self, mock_get_subs, mock_get_summary, mock_verify, mock_user, mock_db
    ):
        """Should call verify_household_member when user_id is provided."""
        target_user_id = uuid4()
        mock_get_subs.return_value = []
        mock_get_summary.return_value = {
            "total_count": 0,
            "monthly_cost": 0.0,
            "yearly_cost": 0.0,
        }
        mock_verify.return_value = None

        await get_subscriptions(user_id=target_user_id, current_user=mock_user, db=mock_db)

        mock_verify.assert_awaited_once_with(mock_db, target_user_id, mock_user.organization_id)
        mock_get_subs.assert_awaited_once_with(mock_db, mock_user.organization_id, target_user_id)


@pytest.mark.unit
class TestDeactivateSubscription:
    """Tests for PATCH /subscriptions/{subscription_id}/deactivate."""

    @pytest.mark.asyncio
    async def test_deactivates_subscription(self, mock_user, mock_db):
        """Should mark subscription as inactive and commit."""
        sub = _make_subscription(org_id=mock_user.organization_id)
        subscription_id = sub.id

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sub
        mock_db.execute.return_value = mock_result

        result = await deactivate_subscription(
            subscription_id=subscription_id, current_user=mock_user, db=mock_db
        )

        assert sub.is_active is False
        mock_db.commit.assert_awaited_once()
        assert result == {"success": True, "message": "Subscription marked as inactive"}

    @pytest.mark.asyncio
    async def test_returns_404_for_nonexistent_subscription(self, mock_user, mock_db):
        """Should raise 404 when subscription is not found."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await deactivate_subscription(
                subscription_id=uuid4(), current_user=mock_user, db=mock_db
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Subscription not found"
        mock_db.commit.assert_not_awaited()
