"""Unit tests for transaction notes and flagged_for_review features."""

from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.transactions import (
    create_transaction,
    list_flagged_transactions,
    update_transaction,
)
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.transaction import (
    ManualTransactionCreate,
    TransactionUpdate,
)


def _make_user(org_id=None):
    user = Mock(spec=User)
    user.id = uuid4()
    user.organization_id = org_id or uuid4()
    return user


def _make_account(user):
    acct = Mock(spec=Account)
    acct.id = uuid4()
    acct.organization_id = user.organization_id
    acct.user_id = user.id
    acct.name = "Test Checking"
    acct.mask = "1234"
    acct.is_active = True
    return acct


def _make_transaction_obj(
    user,
    account,
    notes=None,
    flagged=False,
    amount=-50.00,
    merchant="Coffee Shop",
):
    txn = Mock(spec=Transaction)
    txn.id = uuid4()
    txn.organization_id = user.organization_id
    txn.account_id = account.id
    txn.date = date(2024, 3, 15)
    txn.amount = Decimal(str(amount))
    txn.merchant_name = merchant
    txn.description = "Test transaction"
    txn.category_primary = "Dining"
    txn.category_detailed = None
    txn.external_transaction_id = None
    txn.is_pending = False
    txn.is_transfer = False
    txn.notes = notes
    txn.flagged_for_review = flagged
    txn.created_at = datetime(2024, 3, 15, 12, 0, 0, tzinfo=timezone.utc)
    txn.updated_at = datetime(2024, 3, 15, 12, 0, 0, tzinfo=timezone.utc)
    txn.account = account
    txn.category = None
    txn.labels = []
    txn.is_split = False
    txn.deduplication_hash = str(uuid4())
    return txn


@pytest.mark.unit
class TestCreateTransactionWithNotes:
    """Test creating transactions with notes and flagged_for_review."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def user(self):
        return _make_user()

    @pytest.mark.asyncio
    @patch("app.api.v1.transactions.input_sanitization_service")
    async def test_create_with_notes(self, mock_sanitize, mock_db, user):
        """Transaction can be created with notes field."""
        account = _make_account(user)
        mock_sanitize.sanitize_html.side_effect = lambda x: x

        txn_data = ManualTransactionCreate(
            account_id=account.id,
            date=date(2024, 3, 15),
            amount=Decimal("-25.00"),
            merchant_name="Coffee Shop",
            notes="Business meeting expense",
        )

        # Mock account lookup
        acct_result = Mock()
        acct_result.scalar_one_or_none.return_value = account

        # Mock the transaction after commit/refresh
        created_txn = _make_transaction_obj(user, account, notes="Business meeting expense")
        txn_result = Mock()
        txn_result.unique.return_value.scalar_one.return_value = created_txn

        mock_db.execute.side_effect = [acct_result, txn_result]

        result = await create_transaction(
            transaction_data=txn_data,
            current_user=user,
            db=mock_db,
        )

        assert result.notes == "Business meeting expense"

    @pytest.mark.asyncio
    @patch("app.api.v1.transactions.input_sanitization_service")
    async def test_create_with_flagged(self, mock_sanitize, mock_db, user):
        """Transaction can be created flagged for review."""
        account = _make_account(user)
        mock_sanitize.sanitize_html.side_effect = lambda x: x

        txn_data = ManualTransactionCreate(
            account_id=account.id,
            date=date(2024, 3, 15),
            amount=Decimal("-25.00"),
            merchant_name="Unknown Merchant",
            flagged_for_review=True,
        )

        acct_result = Mock()
        acct_result.scalar_one_or_none.return_value = account

        created_txn = _make_transaction_obj(user, account, flagged=True)
        txn_result = Mock()
        txn_result.unique.return_value.scalar_one.return_value = created_txn

        mock_db.execute.side_effect = [acct_result, txn_result]

        result = await create_transaction(
            transaction_data=txn_data,
            current_user=user,
            db=mock_db,
        )

        assert result.flagged_for_review is True

    @pytest.mark.asyncio
    @patch("app.api.v1.transactions.input_sanitization_service")
    async def test_create_without_notes_defaults_none(self, mock_sanitize, mock_db, user):
        """Transaction without notes has None for notes field."""
        account = _make_account(user)
        mock_sanitize.sanitize_html.side_effect = lambda x: x

        txn_data = ManualTransactionCreate(
            account_id=account.id,
            date=date(2024, 3, 15),
            amount=Decimal("-10.00"),
            merchant_name="Store",
        )

        acct_result = Mock()
        acct_result.scalar_one_or_none.return_value = account

        created_txn = _make_transaction_obj(user, account, notes=None, flagged=False)
        txn_result = Mock()
        txn_result.unique.return_value.scalar_one.return_value = created_txn

        mock_db.execute.side_effect = [acct_result, txn_result]

        result = await create_transaction(
            transaction_data=txn_data,
            current_user=user,
            db=mock_db,
        )

        assert result.notes is None
        assert result.flagged_for_review is False


@pytest.mark.unit
class TestUpdateTransactionNotes:
    """Test updating notes and flagged_for_review on a transaction."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def user(self):
        return _make_user()

    @pytest.mark.asyncio
    @patch("app.api.v1.transactions.input_sanitization_service")
    async def test_update_notes(self, mock_sanitize, mock_db, user):
        """Can update notes on an existing transaction."""
        mock_sanitize.sanitize_html.side_effect = lambda x: x
        account = _make_account(user)
        txn = _make_transaction_obj(user, account, notes=None)

        result_mock = Mock()
        result_mock.unique.return_value.scalar_one_or_none.return_value = txn

        mock_db.execute.return_value = result_mock

        update_data = TransactionUpdate(notes="Updated note")

        await update_transaction(
            transaction_id=txn.id,
            update_data=update_data,
            current_user=user,
            db=mock_db,
        )

        assert txn.notes == "Updated note"

    @pytest.mark.asyncio
    @patch("app.api.v1.transactions.input_sanitization_service")
    async def test_clear_notes(self, mock_sanitize, mock_db, user):
        """Can clear notes by setting to empty string."""
        mock_sanitize.sanitize_html.side_effect = lambda x: x
        account = _make_account(user)
        txn = _make_transaction_obj(user, account, notes="Old note")

        result_mock = Mock()
        result_mock.unique.return_value.scalar_one_or_none.return_value = txn

        mock_db.execute.return_value = result_mock

        update_data = TransactionUpdate(notes="")

        await update_transaction(
            transaction_id=txn.id,
            update_data=update_data,
            current_user=user,
            db=mock_db,
        )

        # Empty string is treated as falsy so notes becomes None
        assert txn.notes is None

    @pytest.mark.asyncio
    @patch("app.api.v1.transactions.input_sanitization_service")
    async def test_flag_for_review(self, mock_sanitize, mock_db, user):
        """Can flag a transaction for review."""
        mock_sanitize.sanitize_html.side_effect = lambda x: x
        account = _make_account(user)
        txn = _make_transaction_obj(user, account, flagged=False)

        result_mock = Mock()
        result_mock.unique.return_value.scalar_one_or_none.return_value = txn

        mock_db.execute.return_value = result_mock

        update_data = TransactionUpdate(flagged_for_review=True)

        await update_transaction(
            transaction_id=txn.id,
            update_data=update_data,
            current_user=user,
            db=mock_db,
        )

        assert txn.flagged_for_review is True

    @pytest.mark.asyncio
    @patch("app.api.v1.transactions.input_sanitization_service")
    async def test_unflag_for_review(self, mock_sanitize, mock_db, user):
        """Can unflag a previously flagged transaction."""
        mock_sanitize.sanitize_html.side_effect = lambda x: x
        account = _make_account(user)
        txn = _make_transaction_obj(user, account, flagged=True)

        result_mock = Mock()
        result_mock.unique.return_value.scalar_one_or_none.return_value = txn

        mock_db.execute.return_value = result_mock

        update_data = TransactionUpdate(flagged_for_review=False)

        await update_transaction(
            transaction_id=txn.id,
            update_data=update_data,
            current_user=user,
            db=mock_db,
        )

        assert txn.flagged_for_review is False

    @pytest.mark.asyncio
    @patch("app.api.v1.transactions.input_sanitization_service")
    async def test_update_not_found(self, mock_sanitize, mock_db, user):
        """Returns 404 when transaction not found."""
        result_mock = Mock()
        result_mock.unique.return_value.scalar_one_or_none.return_value = None

        mock_db.execute.return_value = result_mock

        update_data = TransactionUpdate(notes="test")

        with pytest.raises(HTTPException) as exc_info:
            await update_transaction(
                transaction_id=uuid4(),
                update_data=update_data,
                current_user=user,
                db=mock_db,
            )

        assert exc_info.value.status_code == 404


@pytest.mark.unit
class TestListFlaggedTransactions:
    """Test the flagged transactions endpoint."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def user(self):
        return _make_user()

    @pytest.mark.asyncio
    async def test_returns_flagged_transactions(self, mock_db, user):
        """Flagged endpoint returns only flagged transactions."""
        account = _make_account(user)
        txn1 = _make_transaction_obj(user, account, flagged=True, notes="Suspicious")
        txn2 = _make_transaction_obj(user, account, flagged=True, notes="Review needed")

        # Main query result
        query_result = Mock()
        query_result.unique.return_value.scalars.return_value.all.return_value = [txn1, txn2]

        # Count query result
        count_result = Mock()
        count_result.scalar.return_value = 2

        mock_db.execute.side_effect = [query_result, count_result]

        result = await list_flagged_transactions(
            page_size=50,
            cursor=None,
            current_user=user,
            db=mock_db,
        )

        assert result.total == 2
        assert len(result.transactions) == 2
        assert all(t.flagged_for_review for t in result.transactions)

    @pytest.mark.asyncio
    async def test_empty_flagged_list(self, mock_db, user):
        """Returns empty list when no flagged transactions."""
        query_result = Mock()
        query_result.unique.return_value.scalars.return_value.all.return_value = []

        count_result = Mock()
        count_result.scalar.return_value = 0

        mock_db.execute.side_effect = [query_result, count_result]

        result = await list_flagged_transactions(
            page_size=50,
            cursor=None,
            current_user=user,
            db=mock_db,
        )

        assert result.total == 0
        assert len(result.transactions) == 0
        assert result.has_more is False


@pytest.mark.unit
class TestTransactionSchemas:
    """Test transaction schema behavior for notes and flagged fields."""

    def test_manual_transaction_create_defaults(self):
        """ManualTransactionCreate defaults: notes=None, flagged=False."""
        txn = ManualTransactionCreate(
            account_id=uuid4(),
            date=date(2024, 1, 1),
            amount=Decimal("-10"),
        )
        assert txn.notes is None
        assert txn.flagged_for_review is False

    def test_manual_transaction_create_with_notes(self):
        """ManualTransactionCreate accepts notes and flagged_for_review."""
        txn = ManualTransactionCreate(
            account_id=uuid4(),
            date=date(2024, 1, 1),
            amount=Decimal("-10"),
            notes="Important",
            flagged_for_review=True,
        )
        assert txn.notes == "Important"
        assert txn.flagged_for_review is True

    def test_transaction_update_partial(self):
        """TransactionUpdate allows partial updates."""
        update = TransactionUpdate(notes="New note")
        assert update.notes == "New note"
        assert update.flagged_for_review is None  # Not set
        assert update.merchant_name is None

    def test_transaction_update_flagged_only(self):
        """TransactionUpdate can update only flagged_for_review."""
        update = TransactionUpdate(flagged_for_review=True)
        assert update.flagged_for_review is True
        assert update.notes is None
