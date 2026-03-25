"""Unit tests for NetWorthAttributionService.

Covers:
- Empty attribution when no accounts exist
- Savings credited for checking account deposits
- History returns the correct number of monthly buckets
- Month label formatting (e.g. March 2026)
"""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest

# ---------------------------------------------------------------------------
# Celery stub — must come before any app import
# ---------------------------------------------------------------------------
_celery_stub = MagicMock()
sys.modules.setdefault("celery", _celery_stub)
sys.modules.setdefault("app.workers.celery_app", _celery_stub)

from app.models.account import Account, AccountType  # noqa: E402
from app.models.transaction import Transaction  # noqa: E402
from app.services.net_worth_attribution_service import (  # noqa: E402
    NetWorthAttributionService,
    _empty_attribution,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_account(account_type: AccountType, org_id=None, user_id=None) -> Account:
    acct = Account()
    acct.id = uuid4()
    acct.organization_id = org_id or uuid4()
    acct.user_id = user_id or uuid4()
    acct.account_type = account_type
    acct.is_active = True
    acct.name = "Test Account"
    return acct


def _make_transaction(account_id, amount: Decimal, txn_date: date, org_id=None) -> Transaction:
    txn = Transaction()
    txn.id = uuid4()
    txn.organization_id = org_id or uuid4()
    txn.account_id = account_id
    txn.amount = amount
    txn.date = txn_date
    txn.is_pending = False
    return txn


def _mock_db_with_accounts_and_transactions(accounts, transactions):
    """Return an AsyncMock db session returning the given accounts and transactions."""
    db = AsyncMock()

    acct_result = Mock()
    acct_result.scalars.return_value.all.return_value = accounts

    txn_result = Mock()
    txn_result.scalars.return_value.all.return_value = transactions

    # First call → accounts, second call → transactions
    db.execute.side_effect = [acct_result, txn_result]
    return db


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNetWorthAttributionService:

    @pytest.mark.asyncio
    async def test_empty_attribution_no_accounts(self):
        """When there are no active accounts, all values should be zero."""
        db = AsyncMock()
        acct_result = Mock()
        acct_result.scalars.return_value.all.return_value = []
        db.execute.return_value = acct_result

        result = await NetWorthAttributionService.calculate_monthly_attribution(
            db=db,
            organization_id=uuid4(),
            user_id=None,
            month=3,
            year=2026,
        )

        assert result["savings"] == 0.0
        assert result["investment_contributions"] == 0.0
        assert result["debt_paydown"] == 0.0
        assert result["month"] == 3
        assert result["year"] == 2026
        assert "No accounts found" in result["attribution_note"]

    @pytest.mark.asyncio
    async def test_savings_deposits_credited(self):
        """A deposit into a CHECKING account should increase the savings bucket."""
        org_id = uuid4()
        user_id = uuid4()

        acct = _make_account(AccountType.CHECKING, org_id=org_id, user_id=user_id)
        txn = _make_transaction(
            account_id=acct.id,
            amount=Decimal("500.00"),
            txn_date=date(2026, 3, 15),
            org_id=org_id,
        )

        db = _mock_db_with_accounts_and_transactions([acct], [txn])

        result = await NetWorthAttributionService.calculate_monthly_attribution(
            db=db,
            organization_id=org_id,
            user_id=user_id,
            month=3,
            year=2026,
        )

        assert result["savings"] == 500.0
        assert result["investment_contributions"] == 0.0

    @pytest.mark.asyncio
    async def test_savings_account_deposit_credited(self):
        """A deposit into a SAVINGS account should also increase the savings bucket."""
        org_id = uuid4()
        user_id = uuid4()

        acct = _make_account(AccountType.SAVINGS, org_id=org_id, user_id=user_id)
        txn = _make_transaction(
            account_id=acct.id,
            amount=Decimal("1000.00"),
            txn_date=date(2026, 3, 10),
            org_id=org_id,
        )

        db = _mock_db_with_accounts_and_transactions([acct], [txn])

        result = await NetWorthAttributionService.calculate_monthly_attribution(
            db=db,
            organization_id=org_id,
            user_id=user_id,
            month=3,
            year=2026,
        )

        assert result["savings"] == 1000.0

    @pytest.mark.asyncio
    async def test_investment_contributions_credited(self):
        """A positive transaction in a BROKERAGE account counts as investment contribution."""
        org_id = uuid4()
        user_id = uuid4()

        acct = _make_account(AccountType.BROKERAGE, org_id=org_id, user_id=user_id)
        txn = _make_transaction(
            account_id=acct.id,
            amount=Decimal("2000.00"),
            txn_date=date(2026, 3, 1),
            org_id=org_id,
        )

        db = _mock_db_with_accounts_and_transactions([acct], [txn])

        result = await NetWorthAttributionService.calculate_monthly_attribution(
            db=db,
            organization_id=org_id,
            user_id=user_id,
            month=3,
            year=2026,
        )

        assert result["investment_contributions"] == 2000.0
        assert result["savings"] == 0.0

    @pytest.mark.asyncio
    async def test_history_returns_correct_months(self):
        """get_attribution_history with months=6 should return exactly 6 entries."""
        org_id = uuid4()

        # Each call to calculate_monthly_attribution needs 2 db.execute calls:
        # one for accounts (returns []), one skipped because account_ids is empty.
        # With an empty account list, only 1 execute call happens per month.
        db = AsyncMock()
        empty_result = Mock()
        empty_result.scalars.return_value.all.return_value = []
        db.execute.return_value = empty_result

        results = await NetWorthAttributionService.get_attribution_history(
            db=db,
            organization_id=org_id,
            user_id=None,
            months=6,
        )

        assert len(results) == 6

    @pytest.mark.asyncio
    async def test_month_labels_correct(self):
        """March 2026 should produce period_label 'March 2026'."""
        db = AsyncMock()
        empty_result = Mock()
        empty_result.scalars.return_value.all.return_value = []
        db.execute.return_value = empty_result

        result = await NetWorthAttributionService.calculate_monthly_attribution(
            db=db,
            organization_id=uuid4(),
            user_id=None,
            month=3,
            year=2026,
        )

        assert result["period_label"] == "March 2026"

    @pytest.mark.asyncio
    async def test_negative_savings_for_withdrawal(self):
        """A negative transaction (withdrawal) from a CHECKING account reduces savings bucket."""
        org_id = uuid4()
        user_id = uuid4()

        acct = _make_account(AccountType.CHECKING, org_id=org_id, user_id=user_id)
        txn = _make_transaction(
            account_id=acct.id,
            amount=Decimal("-300.00"),
            txn_date=date(2026, 3, 20),
            org_id=org_id,
        )

        db = _mock_db_with_accounts_and_transactions([acct], [txn])

        result = await NetWorthAttributionService.calculate_monthly_attribution(
            db=db,
            organization_id=org_id,
            user_id=user_id,
            month=3,
            year=2026,
        )

        assert result["savings"] == -300.0
