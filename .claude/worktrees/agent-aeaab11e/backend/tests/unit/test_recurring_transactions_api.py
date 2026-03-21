"""Unit tests for recurring transactions API endpoints."""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.recurring_transactions import (
    create_recurring_transaction,
    delete_recurring_transaction,
    detect_recurring_patterns,
    get_upcoming_bills,
    list_recurring_transactions,
    update_recurring_transaction,
)
from app.models.recurring_transaction import RecurringFrequency, RecurringTransaction
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

        with patch("app.api.v1.recurring_transactions.recurring_detection_service") as mock_svc:
            mock_svc.detect_recurring_patterns = AsyncMock(return_value=patterns)

            result = await detect_recurring_patterns(
                min_occurrences=3,
                lookback_days=180,
                user_id=None,
                current_user=mock_user,
                db=mock_db,
            )

        assert result["detected_patterns"] == 3
        assert len(result["patterns"]) == 3

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_patterns(self, mock_user, mock_db):
        """Should return zero count when no patterns detected."""
        with patch("app.api.v1.recurring_transactions.recurring_detection_service") as mock_svc:
            mock_svc.detect_recurring_patterns = AsyncMock(return_value=[])

            result = await detect_recurring_patterns(
                min_occurrences=3,
                lookback_days=180,
                user_id=None,
                current_user=mock_user,
                db=mock_db,
            )

        assert result["detected_patterns"] == 0
        assert result["patterns"] == []

    @pytest.mark.asyncio
    async def test_passes_params_to_service(self, mock_user, mock_db):
        """Should pass min_occurrences and lookback_days through to service."""
        with patch("app.api.v1.recurring_transactions.recurring_detection_service") as mock_svc:
            mock_svc.detect_recurring_patterns = AsyncMock(return_value=[])

            await detect_recurring_patterns(
                min_occurrences=5,
                lookback_days=365,
                user_id=None,
                current_user=mock_user,
                db=mock_db,
            )

            mock_svc.detect_recurring_patterns.assert_called_once_with(
                db=mock_db,
                user=mock_user,
                min_occurrences=5,
                lookback_days=365,
                account_ids=None,
            )

    @pytest.mark.asyncio
    async def test_user_id_filtering_calls_verify_and_passes_account_ids(self, mock_user, mock_db):
        """Should call verify_household_member, get_user_accounts, pass account_ids."""
        target_user_id = uuid4()
        acc1 = Mock()
        acc1.id = uuid4()
        acc2 = Mock()
        acc2.id = uuid4()

        with patch(
            "app.api.v1.recurring_transactions.verify_household_member",
            new_callable=AsyncMock,
        ) as mock_verify:
            with patch(
                "app.api.v1.recurring_transactions.get_user_accounts",
                new_callable=AsyncMock,
                return_value=[acc1, acc2],
            ) as mock_get_accs:
                with patch(
                    "app.api.v1.recurring_transactions.recurring_detection_service"
                ) as mock_svc:
                    mock_svc.detect_recurring_patterns = AsyncMock(return_value=[])

                    await detect_recurring_patterns(
                        min_occurrences=3,
                        lookback_days=180,
                        user_id=target_user_id,
                        current_user=mock_user,
                        db=mock_db,
                    )

        mock_verify.assert_awaited_once_with(mock_db, target_user_id, mock_user.organization_id)
        mock_get_accs.assert_awaited_once_with(mock_db, target_user_id, mock_user.organization_id)
        call_kwargs = mock_svc.detect_recurring_patterns.call_args.kwargs
        assert call_kwargs["account_ids"] == {acc1.id, acc2.id}


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

        with patch("app.api.v1.recurring_transactions.recurring_detection_service") as mock_svc:
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

        with patch("app.api.v1.recurring_transactions.recurring_detection_service") as mock_svc:
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

        with patch("app.api.v1.recurring_transactions.recurring_detection_service") as mock_svc:
            mock_svc.get_recurring_transactions = AsyncMock(return_value=patterns)

            result = await list_recurring_transactions(
                is_active=None,
                user_id=None,
                current_user=mock_user,
                db=mock_db,
            )

        assert len(result) == 4

    @pytest.mark.asyncio
    async def test_passes_is_active_filter(self, mock_user, mock_db):
        """Should pass is_active filter through to service."""
        with patch("app.api.v1.recurring_transactions.recurring_detection_service") as mock_svc:
            mock_svc.get_recurring_transactions = AsyncMock(return_value=[])

            await list_recurring_transactions(
                is_active=True,
                user_id=None,
                current_user=mock_user,
                db=mock_db,
            )

            mock_svc.get_recurring_transactions.assert_called_once_with(
                db=mock_db,
                user=mock_user,
                is_active=True,
                account_ids=None,
            )

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_none(self, mock_user, mock_db):
        """Should return empty list when user has no patterns."""
        with patch("app.api.v1.recurring_transactions.recurring_detection_service") as mock_svc:
            mock_svc.get_recurring_transactions = AsyncMock(return_value=[])

            result = await list_recurring_transactions(
                is_active=None,
                user_id=None,
                current_user=mock_user,
                db=mock_db,
            )

        assert result == []

    @pytest.mark.asyncio
    async def test_user_id_filtering_calls_verify_and_passes_account_ids(self, mock_user, mock_db):
        """Should call verify_household_member, get_user_accounts, pass account_ids."""
        target_user_id = uuid4()
        acc1 = Mock()
        acc1.id = uuid4()

        with patch(
            "app.api.v1.recurring_transactions.verify_household_member",
            new_callable=AsyncMock,
        ) as mock_verify:
            with patch(
                "app.api.v1.recurring_transactions.get_user_accounts",
                new_callable=AsyncMock,
                return_value=[acc1],
            ) as mock_get_accs:
                with patch(
                    "app.api.v1.recurring_transactions.recurring_detection_service"
                ) as mock_svc:
                    mock_svc.get_recurring_transactions = AsyncMock(return_value=[])

                    await list_recurring_transactions(
                        is_active=None,
                        user_id=target_user_id,
                        current_user=mock_user,
                        db=mock_db,
                    )

        mock_verify.assert_awaited_once_with(mock_db, target_user_id, mock_user.organization_id)
        mock_get_accs.assert_awaited_once_with(mock_db, target_user_id, mock_user.organization_id)
        call_kwargs = mock_svc.get_recurring_transactions.call_args.kwargs
        assert call_kwargs["account_ids"] == {acc1.id}


@pytest.mark.unit
class TestUpdateRecurringTransaction:
    """Tests for PATCH /recurring-transactions/{recurring_id}."""

    @pytest.mark.asyncio
    async def test_updates_pattern_fields(self, mock_user, mock_db):
        """Should update and return the modified pattern."""
        recurring_id = uuid4()
        updated = _make_pattern(org_id=mock_user.organization_id, merchant_name="Hulu")

        update_data = RecurringTransactionUpdate(merchant_name="Hulu")

        with patch("app.api.v1.recurring_transactions.recurring_detection_service") as mock_svc:
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

        with patch("app.api.v1.recurring_transactions.recurring_detection_service") as mock_svc:
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

        with patch("app.api.v1.recurring_transactions.recurring_detection_service") as mock_svc:
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

        with patch("app.api.v1.recurring_transactions.recurring_detection_service") as mock_svc:
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

        with patch("app.api.v1.recurring_transactions.recurring_detection_service") as mock_svc:
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

        with patch("app.api.v1.recurring_transactions.recurring_detection_service") as mock_svc:
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

        with patch("app.api.v1.recurring_transactions.recurring_detection_service") as mock_svc:
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
        with patch("app.api.v1.recurring_transactions.recurring_detection_service") as mock_svc:
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
        with patch("app.api.v1.recurring_transactions.recurring_detection_service") as mock_svc:
            mock_svc.get_upcoming_bills = AsyncMock(return_value=[])

            await get_upcoming_bills(
                days_ahead=14,
                user_id=None,
                current_user=mock_user,
                db=mock_db,
            )

            mock_svc.get_upcoming_bills.assert_called_once_with(
                db=mock_db,
                user=mock_user,
                days_ahead=14,
                user_id=None,
            )


# ---------------------------------------------------------------------------
# _expand_occurrences helper
# ---------------------------------------------------------------------------

from app.api.v1.recurring_transactions import _expand_occurrences


@pytest.mark.unit
class TestExpandOccurrences:
    """Tests for the _expand_occurrences helper function."""

    def test_monthly_expansion(self):
        pattern = Mock()
        pattern.next_expected_date = date(2024, 7, 1)
        pattern.frequency = RecurringFrequency.MONTHLY

        start = date(2024, 7, 1)
        end = date(2024, 10, 1)
        result = _expand_occurrences(pattern, start, end)

        assert date(2024, 7, 1) in result
        assert date(2024, 8, 1) in result
        assert date(2024, 9, 1) in result
        assert date(2024, 10, 1) in result

    def test_weekly_expansion(self):
        pattern = Mock()
        pattern.next_expected_date = date(2024, 7, 1)
        pattern.frequency = RecurringFrequency.WEEKLY

        start = date(2024, 7, 1)
        end = date(2024, 7, 22)
        result = _expand_occurrences(pattern, start, end)

        assert len(result) == 4  # 7/1, 7/8, 7/15, 7/22

    def test_biweekly_expansion(self):
        pattern = Mock()
        pattern.next_expected_date = date(2024, 7, 1)
        pattern.frequency = RecurringFrequency.BIWEEKLY

        start = date(2024, 7, 1)
        end = date(2024, 8, 12)
        result = _expand_occurrences(pattern, start, end)

        assert date(2024, 7, 1) in result
        assert date(2024, 7, 15) in result
        assert date(2024, 7, 29) in result
        assert date(2024, 8, 12) in result

    def test_quarterly_expansion(self):
        pattern = Mock()
        pattern.next_expected_date = date(2024, 1, 1)
        pattern.frequency = RecurringFrequency.QUARTERLY

        start = date(2024, 1, 1)
        end = date(2024, 12, 31)
        result = _expand_occurrences(pattern, start, end)

        assert len(result) == 4

    def test_yearly_expansion(self):
        pattern = Mock()
        pattern.next_expected_date = date(2024, 6, 15)
        pattern.frequency = RecurringFrequency.YEARLY

        start = date(2024, 1, 1)
        end = date(2026, 12, 31)
        result = _expand_occurrences(pattern, start, end)

        assert len(result) == 3

    def test_on_demand_returns_empty(self):
        pattern = Mock()
        pattern.next_expected_date = date(2024, 7, 1)
        pattern.frequency = RecurringFrequency.ON_DEMAND

        result = _expand_occurrences(pattern, date(2024, 1, 1), date(2024, 12, 31))
        assert result == []

    def test_no_next_expected_date_returns_empty(self):
        pattern = Mock()
        pattern.next_expected_date = None
        pattern.frequency = RecurringFrequency.MONTHLY

        result = _expand_occurrences(pattern, date(2024, 1, 1), date(2024, 12, 31))
        assert result == []

    def test_anchor_after_end_returns_empty(self):
        """When anchor is far in the future and end is before it."""
        pattern = Mock()
        pattern.next_expected_date = date(2025, 1, 1)
        pattern.frequency = RecurringFrequency.MONTHLY

        start = date(2024, 1, 1)
        end = date(2024, 2, 1)
        result = _expand_occurrences(pattern, start, end)

        # Pattern anchored at 2025, looking at Jan-Feb 2024 window
        # Should walk backward to find occurrences in this window
        assert len(result) >= 1


# ---------------------------------------------------------------------------
# Calendar endpoint
# ---------------------------------------------------------------------------

from app.api.v1.recurring_transactions import get_calendar


@pytest.mark.unit
class TestGetCalendar:
    """Tests for GET /recurring-transactions/calendar."""

    @pytest.mark.asyncio
    async def test_returns_calendar_entries(self, mock_user, mock_db):
        """Should return expanded calendar entries sorted by date."""
        pattern = Mock()
        pattern.id = uuid4()
        pattern.merchant_name = "Netflix"
        pattern.average_amount = Decimal("15.99")
        pattern.frequency = RecurringFrequency.MONTHLY
        pattern.next_expected_date = date.today()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [pattern]
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await get_calendar(days=90, user_id=None, current_user=mock_user, db=mock_db)

        assert len(result) >= 1
        # All entries should be CalendarEntry-like
        for entry in result:
            assert entry.merchant_name == "Netflix"

    @pytest.mark.asyncio
    async def test_empty_when_no_patterns(self, mock_user, mock_db):
        """Should return empty list when no active patterns."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await get_calendar(days=30, user_id=None, current_user=mock_user, db=mock_db)
        assert result == []

    @pytest.mark.asyncio
    async def test_user_id_filtering_calls_verify_and_get_user_accounts(self, mock_user, mock_db):
        """Should call verify_household_member and get_user_accounts when user_id provided."""
        target_user_id = uuid4()
        acc1 = Mock()
        acc1.id = uuid4()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.api.v1.recurring_transactions.verify_household_member",
            new_callable=AsyncMock,
        ) as mock_verify:
            with patch(
                "app.api.v1.recurring_transactions.get_user_accounts",
                new_callable=AsyncMock,
                return_value=[acc1],
            ) as mock_get_accs:
                await get_calendar(
                    days=90,
                    user_id=target_user_id,
                    current_user=mock_user,
                    db=mock_db,
                )

        mock_verify.assert_awaited_once_with(mock_db, target_user_id, mock_user.organization_id)
        mock_get_accs.assert_awaited_once_with(mock_db, target_user_id, mock_user.organization_id)


# ---------------------------------------------------------------------------
# Apply label endpoint
# ---------------------------------------------------------------------------

from app.api.v1.recurring_transactions import ApplyLabelRequest, apply_label_to_recurring


@pytest.mark.unit
class TestApplyLabel:
    """Tests for POST /recurring-transactions/{recurring_id}/apply-label."""

    @pytest.mark.asyncio
    async def test_pattern_not_found_raises_404(self, mock_user, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        body = ApplyLabelRequest(retroactive=True)
        with pytest.raises(HTTPException) as exc_info:
            await apply_label_to_recurring(uuid4(), body, mock_user, mock_db)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @patch("app.api.v1.recurring_transactions.RecurringDetectionService")
    async def test_creates_label_when_none(self, mock_rds_cls, mock_user, mock_db):
        pattern = _make_pattern(org_id=mock_user.organization_id)
        pattern.label_id = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = pattern
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        mock_label = Mock()
        mock_label.id = uuid4()
        mock_rds_cls.ensure_recurring_bill_label = AsyncMock(return_value=mock_label)
        mock_rds_cls.apply_label_to_matching_transactions = AsyncMock(return_value=5)

        body = ApplyLabelRequest(retroactive=True)
        result = await apply_label_to_recurring(uuid4(), body, mock_user, mock_db)

        assert result["applied_count"] == 5
        assert pattern.label_id == mock_label.id

    @pytest.mark.asyncio
    @patch("app.api.v1.recurring_transactions.RecurringDetectionService")
    async def test_no_retroactive_apply(self, mock_rds_cls, mock_user, mock_db):
        pattern = _make_pattern(org_id=mock_user.organization_id)
        pattern.label_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = pattern
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        body = ApplyLabelRequest(retroactive=False)
        result = await apply_label_to_recurring(uuid4(), body, mock_user, mock_db)

        assert result["applied_count"] == 0
        mock_rds_cls.apply_label_to_matching_transactions.assert_not_called()


# ---------------------------------------------------------------------------
# Preview label endpoint
# ---------------------------------------------------------------------------

from app.api.v1.recurring_transactions import preview_label_matches


@pytest.mark.unit
class TestPreviewLabelMatches:
    """Tests for GET /recurring-transactions/{recurring_id}/preview-label."""

    @pytest.mark.asyncio
    async def test_pattern_not_found_raises_404(self, mock_user, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await preview_label_matches(uuid4(), mock_user, mock_db)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @patch("app.api.v1.recurring_transactions.RecurringDetectionService")
    async def test_returns_matching_count(self, mock_rds_cls, mock_user, mock_db):
        pattern = _make_pattern(org_id=mock_user.organization_id)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = pattern
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_rds_cls.count_matching_transactions = AsyncMock(return_value=12)

        result = await preview_label_matches(uuid4(), mock_user, mock_db)
        assert result["matching_transactions"] == 12
