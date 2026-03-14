"""Expanded tests for interest accrual tasks — covers the async accrual logic."""

import sys
from unittest.mock import MagicMock

_celery_stub = MagicMock()
sys.modules.setdefault("celery", _celery_stub)
sys.modules.setdefault("app.workers.celery_app", _celery_stub)

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from app.models.account import CompoundingFrequency
from app.workers.tasks.interest_accrual_tasks import _accrue_interest_async, _calculate_interest


def _make_account(
    *,
    balance="10000",
    rate="5",
    frequency=CompoundingFrequency.MONTHLY,
    last_accrued=None,
    maturity_date=None,
    origination_date=None,
    compounding_frequency=None,
    account_id=None,
    org_id=None,
):
    account = Mock()
    account.id = account_id or uuid4()
    account.organization_id = org_id or uuid4()
    account.name = "Test Savings"
    account.current_balance = Decimal(balance)
    account.interest_rate = Decimal(rate)
    account.compounding_frequency = compounding_frequency or frequency
    account.last_interest_accrued_at = last_accrued
    account.maturity_date = maturity_date
    account.origination_date = origination_date
    return account


@pytest.mark.unit
class TestAccrueInterestAsync:
    """Test the async interest accrual task logic."""

    @pytest.mark.asyncio
    async def test_no_eligible_accounts(self):
        """No eligible accounts means no transactions created."""
        mock_db = AsyncMock()
        scalars_mock = Mock()
        scalars_mock.all.return_value = []
        result_mock = Mock()
        result_mock.scalars.return_value = scalars_mock
        mock_db.execute.return_value = result_mock

        with patch("app.workers.tasks.interest_accrual_tasks.AsyncSessionLocal") as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            await _accrue_interest_async()

        mock_db.commit.assert_awaited_once()
        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_already_accrued_this_month_skipped(self):
        """Accounts already accrued this month are skipped."""
        today = date.today()
        first_of_month = today.replace(day=1)
        account = _make_account(last_accrued=first_of_month)

        mock_db = AsyncMock()
        scalars_mock = Mock()
        scalars_mock.all.return_value = [account]
        result_mock = Mock()
        result_mock.scalars.return_value = scalars_mock
        mock_db.execute.return_value = result_mock

        with patch("app.workers.tasks.interest_accrual_tasks.AsyncSessionLocal") as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            await _accrue_interest_async()

        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_account_without_maturity_date_proceeds(self):
        """Accounts without maturity_date (savings, checking) proceed normally."""
        account = _make_account(
            balance="12000",
            rate="6",
            last_accrued=None,
            maturity_date=None,
            frequency=CompoundingFrequency.MONTHLY,
        )

        mock_db = AsyncMock()
        call_count = 0

        def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = Mock()
            if call_count == 1:
                scalars_mock = Mock()
                scalars_mock.all.return_value = [account]
                result.scalars.return_value = scalars_mock
            elif call_count == 2:
                result.scalar_one_or_none.return_value = None
            return result

        mock_db.execute.side_effect = execute_side_effect

        with patch("app.workers.tasks.interest_accrual_tasks.AsyncSessionLocal") as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            await _accrue_interest_async()

        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_tiny_interest_skipped(self):
        """Interest below $0.01 is skipped."""
        account = _make_account(balance="1", rate="0.01")

        mock_db = AsyncMock()
        scalars_mock = Mock()
        scalars_mock.all.return_value = [account]
        result_mock = Mock()
        result_mock.scalars.return_value = scalars_mock
        mock_db.execute.return_value = result_mock

        with patch("app.workers.tasks.interest_accrual_tasks.AsyncSessionLocal") as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            await _accrue_interest_async()

        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_existing_transaction_dedup_skipped(self):
        """If dedup transaction already exists, skip."""
        account = _make_account(balance="10000", rate="5", last_accrued=None)

        mock_db = AsyncMock()
        call_count = 0

        def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = Mock()
            if call_count == 1:
                scalars_mock = Mock()
                scalars_mock.all.return_value = [account]
                result.scalars.return_value = scalars_mock
            elif call_count == 2:
                # Dedup check: existing transaction found
                result.scalar_one_or_none.return_value = Mock()
            return result

        mock_db.execute.side_effect = execute_side_effect

        with patch("app.workers.tasks.interest_accrual_tasks.AsyncSessionLocal") as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            await _accrue_interest_async()

        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_successful_accrual(self):
        """Successful interest accrual creates transaction and updates balance."""
        account = _make_account(balance="12000", rate="6", last_accrued=None)

        mock_db = AsyncMock()
        call_count = 0

        def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = Mock()
            if call_count == 1:
                scalars_mock = Mock()
                scalars_mock.all.return_value = [account]
                result.scalars.return_value = scalars_mock
            elif call_count == 2:
                # Dedup check: no existing transaction
                result.scalar_one_or_none.return_value = None
            return result

        mock_db.execute.side_effect = execute_side_effect

        with patch("app.workers.tasks.interest_accrual_tasks.AsyncSessionLocal") as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            await _accrue_interest_async()

        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_db_error_rolls_back(self):
        """DB errors trigger rollback."""
        mock_db = AsyncMock()
        mock_db.execute.side_effect = Exception("DB error")

        with patch("app.workers.tasks.interest_accrual_tasks.AsyncSessionLocal") as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            with pytest.raises(Exception, match="DB error"):
                await _accrue_interest_async()

        mock_db.rollback.assert_awaited_once()


@pytest.mark.unit
class TestCalculateInterestDefaultBranch:
    """Test the default fallback branch in _calculate_interest."""

    def test_unknown_frequency_defaults_to_monthly(self):
        """Unknown compounding frequency defaults to monthly calculation."""
        # Create a mock with a frequency value that doesn't match any case
        account = Mock()
        account.current_balance = Decimal("12000")
        account.interest_rate = Decimal("6")
        account.compounding_frequency = "unknown_value"
        account.maturity_date = None
        account.origination_date = None

        result = _calculate_interest(account, date(2024, 3, 1))
        # Default: balance * rate / 12 = 12000 * 0.06 / 12 = 60
        assert result == Decimal("60.00")
