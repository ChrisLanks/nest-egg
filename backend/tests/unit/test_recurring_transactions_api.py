"""Unit tests for recurring transactions API endpoints."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4
from datetime import date, datetime
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.recurring_transactions import (
    detect_recurring_patterns,
    create_recurring_transaction,
    list_recurring_transactions,
    update_recurring_transaction,
    delete_recurring_transaction,
    get_upcoming_bills,
)
from app.models.recurring_transaction import RecurringTransaction, RecurringFrequency
from app.models.user import User
from app.schemas.recurring_transaction import (
    RecurringTransactionCreate,
    RecurringTransactionUpdate,
)


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


def _make_pattern(org_id=None, **kwargs):
    """Return a minimal RecurringTransaction-like Mock."""
    p = Mock(spec=RecurringTransaction)
    p.id = uuid4()
    p.organization_id = org_id or uuid4()
    p.account_id = uuid4()
    p.merchant_name = kwargs.get("merchant_name", "Netflix")
    p.frequency = kwargs.get("frequency", RecurringFrequency.MONTHLY)
    p.average_amount = kwargs.get("average_amount", Decimal("15.99"))
    p.amount_variance = Decimal("0.00")
    p.confidence_score = kwargs.get("confidence_score", Decimal("0.85"))
    p.is_user_created = kwargs.get("is_user_created", False)
    p.is_active = kwargs.get("is_active", True)
    p.is_archived = False
    p.is_no_longer_found = False
    p.is_bill = kwargs.get("is_bill", False)
    p.reminder_days_before = 3
    p.category_id = None
    p.label_id = None
    p.description_pattern = None
    p.first_occurrence = date(2024, 1, 1)
    p.last_occurrence = date(2024, 6, 1)
    p.next_expected_date = date(2024, 7, 1)
    p.occurrence_count = 6
    p.created_at = datetime(2024, 1, 1)
    p.updated_at = datetime(2024, 6, 1)
    return p


@pytest.mark.unit
class TestDetectRecurringPatterns:
    """Tests for POST /recurring-transactions/detect."""

    @pytest.mark.asyncio
    async def test_returns_detected_count_and_patterns(self, mock_user, mock_db):
        """Should return detected_patterns count and patterns list."""
        patterns = [_make_pattern(org_id=mock_user.organization_id) for _ in range(3)]

        with patch(
            "app.api.v1.recurring_transactions.recurring_detection_service"
        ) as mock_svc:
            mock_svc.detect_recurring_patterns = AsyncMock(return_value=patterns)

            result = await detect_recurring_patterns(
                min_occurrences=3,
                lookback_days=180,
                current_user=mock_user,
                db=mock_db,
            )

        assert result["detected_patterns"] == 3
        assert len(result["patterns"]) == 3

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_patterns(self, mock_user, mock_db):
        """Should return zero count when no patterns detected."""
        with patch(
            "app.api.v1.recurring_transactions.recurring_detection_service"
        ) as mock_svc:
            mock_svc.detect_recurring_patterns = AsyncMock(return_value=[])

            result = await detect_recurring_patterns(
                min_occurrences=3,
                lookback_days=180,
                current_user=mock_user,
                db=mock_db,
            )

        assert result["detected_patterns"] == 0
        assert result["patterns"] == []

    @pytest.mark.asyncio
    async def test_passes_params_to_service(self, mock_user, mock_db):
        """Should pass min_occurrences and lookback_days through to service."""
        with patch(
            "app.api.v1.recurring_transactions.recurring_detection_service"
        ) as mock_svc:
            mock_svc.detect_recurring_patterns = AsyncMock(return_value=[])

            await detect_recurring_patterns(
                min_occurrences=5,
                lookback_days=365,
                current_user=mock_user,
                db=mock_db,
            )

            mock_svc.detect_recurring_patterns.assert_called_once_with(
                db=mock_db,
                user=mock_user,
                min_occurrences=5,
                lookback_days=365,
            )


@pytest.mark.unit
class TestCreateRecurringTransaction:
    """Tests for POST /recurring-transactions/."""

    @pytest.mark.asyncio
    async def test_creates_manual_pattern(self, mock_user, mock_db):
        """Should create a manual recurring pattern via the service."""
        account_id = uuid4()
        pattern = _make_pattern(
            org_id=mock_user.organization_id,
            merchant_name="Spotify",
            is_user_created=True,
        )
        pattern.account_id = account_id

        create_data = RecurringTransactionCreate(
            merchant_name="Spotify",
            account_id=account_id,
            frequency=RecurringFrequency.MONTHLY,
            average_amount=Decimal("9.99"),
        )

        with patch(
            "app.api.v1.recurring_transactions.recurring_detection_service"
        ) as mock_svc:
            mock_svc.create_manual_recurring = AsyncMock(return_value=pattern)

            result = await create_recurring_transaction(
                recurring_data=create_data,
                current_user=mock_user,
                db=mock_db,
            )

        assert result.merchant_name == "Spotify"
        mock_svc.create_manual_recurring.assert_called_once()

    @pytest.mark.asyncio
    async def test_passes_all_fields_to_service(self, mock_user, mock_db):
        """Should pass all create fields through to service."""
        account_id = uuid4()
        pattern = _make_pattern(org_id=mock_user.organization_id, is_bill=True)

        create_data = RecurringTransactionCreate(
            merchant_name="Electric Bill",
            account_id=account_id,
            frequency=RecurringFrequency.MONTHLY,
            average_amount=Decimal("120.00"),
            is_bill=True,
            reminder_days_before=5,
        )

        with patch(
            "app.api.v1.recurring_transactions.recurring_detection_service"
        ) as mock_svc:
            mock_svc.create_manual_recurring = AsyncMock(return_value=pattern)

            await create_recurring_transaction(
                recurring_data=create_data,
                current_user=mock_user,
                db=mock_db,
            )

            call_kwargs = mock_svc.create_manual_recurring.call_args.kwargs
            assert call_kwargs["merchant_name"] == "Electric Bill"
            assert call_kwargs["frequency"] == RecurringFrequency.MONTHLY
            assert call_kwargs["average_amount"] == Decimal("120.00")
            assert call_kwargs["is_bill"] is True
            assert call_kwargs["reminder_days_before"] == 5


@pytest.mark.unit
class TestListRecurringTransactions:
    """Tests for GET /recurring-transactions/."""

    @pytest.mark.asyncio
    async def test_returns_all_patterns(self, mock_user, mock_db):
        """Should return all recurring patterns for the user's org."""
        patterns = [_make_pattern(org_id=mock_user.organization_id) for _ in range(4)]

        with patch(
            "app.api.v1.recurring_transactions.recurring_detection_service"
        ) as mock_svc:
            mock_svc.get_recurring_transactions = AsyncMock(return_value=patterns)

            result = await list_recurring_transactions(
                is_active=None,
                current_user=mock_user,
                db=mock_db,
            )

        assert len(result) == 4

    @pytest.mark.asyncio
    async def test_passes_is_active_filter(self, mock_user, mock_db):
        """Should pass is_active filter through to service."""
        with patch(
            "app.api.v1.recurring_transactions.recurring_detection_service"
        ) as mock_svc:
            mock_svc.get_recurring_transactions = AsyncMock(return_value=[])

            await list_recurring_transactions(
                is_active=True,
                current_user=mock_user,
                db=mock_db,
            )

            mock_svc.get_recurring_transactions.assert_called_once_with(
                db=mock_db,
                user=mock_user,
                is_active=True,
            )

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_none(self, mock_user, mock_db):
        """Should return empty list when user has no patterns."""
        with patch(
            "app.api.v1.recurring_transactions.recurring_detection_service"
        ) as mock_svc:
            mock_svc.get_recurring_transactions = AsyncMock(return_value=[])

            result = await list_recurring_transactions(
                is_active=None,
                current_user=mock_user,
                db=mock_db,
            )

        assert result == []


@pytest.mark.unit
class TestUpdateRecurringTransaction:
    """Tests for PATCH /recurring-transactions/{recurring_id}."""

    @pytest.mark.asyncio
    async def test_updates_pattern_fields(self, mock_user, mock_db):
        """Should update and return the modified pattern."""
        recurring_id = uuid4()
        updated = _make_pattern(org_id=mock_user.organization_id, merchant_name="Hulu")

        update_data = RecurringTransactionUpdate(merchant_name="Hulu")

        with patch(
            "app.api.v1.recurring_transactions.recurring_detection_service"
        ) as mock_svc:
            mock_svc.update_recurring_transaction = AsyncMock(return_value=updated)

            result = await update_recurring_transaction(
                recurring_id=recurring_id,
                recurring_data=update_data,
                current_user=mock_user,
                db=mock_db,
            )

        assert result.merchant_name == "Hulu"

    @pytest.mark.asyncio
    async def test_raises_404_when_not_found(self, mock_user, mock_db):
        """Should raise 404 if pattern not found or belongs to another org."""
        recurring_id = uuid4()
        update_data = RecurringTransactionUpdate(merchant_name="X")

        with patch(
            "app.api.v1.recurring_transactions.recurring_detection_service"
        ) as mock_svc:
            mock_svc.update_recurring_transaction = AsyncMock(return_value=None)

            with pytest.raises(HTTPException) as exc_info:
                await update_recurring_transaction(
                    recurring_id=recurring_id,
                    recurring_data=update_data,
                    current_user=mock_user,
                    db=mock_db,
                )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_only_sends_set_fields(self, mock_user, mock_db):
        """Should only pass fields that were explicitly set (exclude_unset)."""
        recurring_id = uuid4()
        updated = _make_pattern(org_id=mock_user.organization_id)

        update_data = RecurringTransactionUpdate(frequency=RecurringFrequency.YEARLY)

        with patch(
            "app.api.v1.recurring_transactions.recurring_detection_service"
        ) as mock_svc:
            mock_svc.update_recurring_transaction = AsyncMock(return_value=updated)

            await update_recurring_transaction(
                recurring_id=recurring_id,
                recurring_data=update_data,
                current_user=mock_user,
                db=mock_db,
            )

            call_kwargs = mock_svc.update_recurring_transaction.call_args.kwargs
            # Only frequency should have been passed, not other optional fields
            assert "frequency" in call_kwargs
            assert "merchant_name" not in call_kwargs


@pytest.mark.unit
class TestDeleteRecurringTransaction:
    """Tests for DELETE /recurring-transactions/{recurring_id}."""

    @pytest.mark.asyncio
    async def test_deletes_successfully(self, mock_user, mock_db):
        """Should return None (204) when deleted successfully."""
        recurring_id = uuid4()

        with patch(
            "app.api.v1.recurring_transactions.recurring_detection_service"
        ) as mock_svc:
            mock_svc.delete_recurring_transaction = AsyncMock(return_value=True)

            result = await delete_recurring_transaction(
                recurring_id=recurring_id,
                current_user=mock_user,
                db=mock_db,
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_raises_404_when_not_found(self, mock_user, mock_db):
        """Should raise 404 if pattern not found."""
        recurring_id = uuid4()

        with patch(
            "app.api.v1.recurring_transactions.recurring_detection_service"
        ) as mock_svc:
            mock_svc.delete_recurring_transaction = AsyncMock(return_value=False)

            with pytest.raises(HTTPException) as exc_info:
                await delete_recurring_transaction(
                    recurring_id=recurring_id,
                    current_user=mock_user,
                    db=mock_db,
                )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_passes_user_for_org_scoping(self, mock_user, mock_db):
        """Should pass the current user so service can scope to their org."""
        recurring_id = uuid4()

        with patch(
            "app.api.v1.recurring_transactions.recurring_detection_service"
        ) as mock_svc:
            mock_svc.delete_recurring_transaction = AsyncMock(return_value=True)

            await delete_recurring_transaction(
                recurring_id=recurring_id,
                current_user=mock_user,
                db=mock_db,
            )

            mock_svc.delete_recurring_transaction.assert_called_once_with(
                db=mock_db,
                recurring_id=recurring_id,
                user=mock_user,
            )


@pytest.mark.unit
class TestGetUpcomingBills:
    """Tests for GET /recurring-transactions/bills/upcoming."""

    @pytest.mark.asyncio
    async def test_returns_upcoming_bills(self, mock_user, mock_db):
        """Should return bills that are due within the window."""
        bills = [
            {
                "recurring_transaction_id": uuid4(),
                "merchant_name": "Rent",
                "average_amount": Decimal("1500.00"),
                "next_expected_date": date(2024, 7, 1),
                "days_until_due": 3,
                "is_overdue": False,
                "account_id": uuid4(),
                "category_id": None,
            }
        ]

        with patch(
            "app.api.v1.recurring_transactions.recurring_detection_service"
        ) as mock_svc:
            mock_svc.get_upcoming_bills = AsyncMock(return_value=bills)

            result = await get_upcoming_bills(
                days_ahead=30,
                current_user=mock_user,
                db=mock_db,
            )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_bills(self, mock_user, mock_db):
        """Should return empty list when no upcoming bills."""
        with patch(
            "app.api.v1.recurring_transactions.recurring_detection_service"
        ) as mock_svc:
            mock_svc.get_upcoming_bills = AsyncMock(return_value=[])

            result = await get_upcoming_bills(
                days_ahead=30,
                current_user=mock_user,
                db=mock_db,
            )

        assert result == []

    @pytest.mark.asyncio
    async def test_passes_days_ahead_to_service(self, mock_user, mock_db):
        """Should pass days_ahead through to service."""
        with patch(
            "app.api.v1.recurring_transactions.recurring_detection_service"
        ) as mock_svc:
            mock_svc.get_upcoming_bills = AsyncMock(return_value=[])

            await get_upcoming_bills(
                days_ahead=14,
                current_user=mock_user,
                db=mock_db,
            )

            mock_svc.get_upcoming_bills.assert_called_once_with(
                db=mock_db,
                user=mock_user,
                days_ahead=14,
            )
