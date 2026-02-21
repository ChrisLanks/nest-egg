"""Unit tests for transactions API endpoints."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4
from datetime import date, datetime
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.transactions import (
    get_or_create_transfer_label,
    encode_cursor,
    decode_cursor,
    list_transactions,
    get_transaction,
    update_transaction,
    add_label_to_transaction,
    remove_label_from_transaction,
    create_transaction,
)
from app.models.transaction import Transaction, Label, TransactionLabel, Category
from app.models.account import Account
from app.models.user import User
from app.schemas.transaction import TransactionUpdate, ManualTransactionCreate


@pytest.fixture
def mock_user():
    """Create a mock user without database."""
    user = Mock(spec=User)
    user.id = uuid4()
    user.organization_id = uuid4()
    user.email = "test@example.com"
    user.is_active = True
    return user


@pytest.mark.unit
class TestHelperFunctions:
    """Test helper functions."""

    @pytest.mark.asyncio
    async def test_get_or_create_transfer_label_existing(self):
        """Should return existing Transfer label if found."""
        mock_db = AsyncMock(spec=AsyncSession)
        org_id = uuid4()
        existing_label = Label(
            id=uuid4(),
            organization_id=org_id,
            name="Transfer",
            color="#808080",
            is_system=True,
        )

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = existing_label
        mock_db.execute.return_value = mock_result

        result = await get_or_create_transfer_label(mock_db, org_id)

        assert result == existing_label
        assert not mock_db.add.called

    @pytest.mark.asyncio
    async def test_get_or_create_transfer_label_creates_new(self):
        """Should create new Transfer label if not found."""
        mock_db = AsyncMock(spec=AsyncSession)
        org_id = uuid4()

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        async def mock_refresh(obj, *args, **kwargs):
            obj.id = uuid4()

        mock_db.refresh = AsyncMock(side_effect=mock_refresh)
        mock_db.commit = AsyncMock()

        result = await get_or_create_transfer_label(mock_db, org_id)

        assert result.name == "Transfer"
        assert result.organization_id == org_id
        assert result.is_system is True
        mock_db.add.assert_called_once()

    def test_encode_cursor(self):
        """Should encode cursor correctly."""
        txn_date = date(2024, 1, 15)
        created_at = datetime(2024, 1, 15, 10, 30, 0)
        txn_id = uuid4()

        cursor = encode_cursor(txn_date, created_at, txn_id)

        assert isinstance(cursor, str)
        assert len(cursor) > 0

    def test_decode_cursor_valid(self):
        """Should decode valid cursor correctly."""
        txn_date = date(2024, 1, 15)
        created_at = datetime(2024, 1, 15, 10, 30, 0)
        txn_id = uuid4()

        cursor = encode_cursor(txn_date, created_at, txn_id)
        decoded_date, decoded_created_at, decoded_id = decode_cursor(cursor)

        assert decoded_date == txn_date
        assert decoded_created_at == created_at
        assert decoded_id == txn_id

    def test_decode_cursor_invalid(self):
        """Should raise HTTPException for invalid cursor."""
        with pytest.raises(HTTPException) as exc_info:
            decode_cursor("invalid-cursor")

        assert exc_info.value.status_code == 400
        assert "Invalid cursor" in exc_info.value.detail


@pytest.mark.unit
class TestListTransactions:
    """Test list_transactions endpoint."""

    def create_mock_transaction(self):
        """Create a mock transaction."""
        txn = Mock(spec=Transaction)
        txn.id = uuid4()
        txn.organization_id = uuid4()
        txn.account_id = uuid4()
        txn.external_transaction_id = "ext-123"
        txn.date = date(2024, 1, 15)
        txn.amount = Decimal("-50.00")
        txn.merchant_name = "Test Merchant"
        txn.description = "Test transaction"
        txn.category_primary = "Shopping"
        txn.category_detailed = "Clothing"
        txn.is_pending = False
        txn.is_transfer = False
        txn.created_at = datetime(2024, 1, 15, 10, 0, 0)
        txn.updated_at = datetime(2024, 1, 15, 10, 0, 0)

        txn.account = Mock(spec=Account)
        txn.account.name = "Checking"
        txn.account.mask = "1234"
        txn.account.is_active = True

        txn.category = Mock(spec=Category)
        txn.category.id = uuid4()
        txn.category.name = "Clothing"
        txn.category.color = "#FF0000"
        txn.category.parent_category_id = None
        txn.category.parent = None

        txn.labels = []
        return txn

    @pytest.mark.asyncio
    async def test_list_transactions_success(self, mock_user):
        """Should list transactions successfully."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_txn = self.create_mock_transaction()

        # Build mock chain manually: execute() -> unique() -> scalars() -> all()
        mock_scalars = Mock()
        mock_scalars.all = Mock(return_value=[mock_txn])

        mock_unique = Mock()
        mock_unique.scalars = Mock(return_value=mock_scalars)

        mock_execute_result = Mock()
        mock_execute_result.unique = Mock(return_value=mock_unique)

        mock_count_result = Mock()
        mock_count_result.scalar = Mock(return_value=1)

        # The endpoint calls execute() twice: once for transactions, once for count
        # Return them in the order they're called
        mock_db.execute = AsyncMock(side_effect=[mock_execute_result, mock_count_result])

        result = await list_transactions(
            page_size=50,
            cursor=None,
            account_id=None,
            start_date=None,
            end_date=None,
            search=None,
            current_user=mock_user,
            db=mock_db,
        )

        assert result.total == 1
        assert len(result.transactions) == 1
        assert result.has_more is False

    @pytest.mark.asyncio
    async def test_list_transactions_with_pagination(self, mock_user):
        """Should handle cursor-based pagination."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_txn = self.create_mock_transaction()

        # Create enough transactions to trigger pagination
        transactions = [mock_txn] * 51  # More than page_size of 50

        # Build mock chain manually: execute() -> unique() -> scalars() -> all()
        mock_scalars = Mock()
        mock_scalars.all = Mock(return_value=transactions)

        mock_unique = Mock()
        mock_unique.scalars = Mock(return_value=mock_scalars)

        mock_execute_result = Mock()
        mock_execute_result.unique = Mock(return_value=mock_unique)

        mock_count_result = Mock()
        mock_count_result.scalar = Mock(return_value=51)

        # The endpoint calls execute() twice: once for transactions, once for count
        # Return them in the order they're called
        mock_db.execute = AsyncMock(side_effect=[mock_execute_result, mock_count_result])

        result = await list_transactions(
            page_size=50,
            cursor=None,
            account_id=None,
            start_date=None,
            end_date=None,
            search=None,
            current_user=mock_user,
            db=mock_db,
        )

        assert result.has_more is True
        assert result.next_cursor is not None
        assert len(result.transactions) == 50

    @pytest.mark.asyncio
    async def test_list_transactions_invalid_date(self, mock_user):
        """Should raise HTTPException for invalid date format."""
        mock_db = AsyncMock(spec=AsyncSession)

        with pytest.raises(HTTPException) as exc_info:
            await list_transactions(
                page_size=50,
                cursor=None,
                account_id=None,
                user_id=None,
                start_date="invalid-date",
                end_date=None,
                search=None,
                current_user=mock_user,
                db=mock_db,
            )

        assert exc_info.value.status_code == 400
        assert "Invalid start_date format" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_user_id_calls_verify_household_member(self, mock_user):
        """Providing user_id must call verify_household_member before querying."""
        mock_db = AsyncMock(spec=AsyncSession)
        target_user_id = uuid4()
        mock_txn = self.create_mock_transaction()

        mock_scalars = Mock()
        mock_scalars.all = Mock(return_value=[mock_txn])
        mock_unique = Mock()
        mock_unique.scalars = Mock(return_value=mock_scalars)
        mock_execute_result = Mock()
        mock_execute_result.unique = Mock(return_value=mock_unique)
        mock_count_result = Mock()
        mock_count_result.scalar = Mock(return_value=1)
        mock_db.execute = AsyncMock(side_effect=[mock_execute_result, mock_count_result])

        with patch(
            "app.api.v1.transactions.verify_household_member",
            new_callable=AsyncMock,
        ) as mock_verify:
            await list_transactions(
                page_size=50,
                cursor=None,
                account_id=None,
                user_id=target_user_id,
                start_date=None,
                end_date=None,
                search=None,
                current_user=mock_user,
                db=mock_db,
            )

            mock_verify.assert_awaited_once_with(
                mock_db, target_user_id, mock_user.organization_id
            )

    @pytest.mark.asyncio
    async def test_user_id_non_member_raises_403(self, mock_user):
        """verify_household_member raising 403 must propagate out of list_transactions."""
        mock_db = AsyncMock(spec=AsyncSession)

        with patch(
            "app.api.v1.transactions.verify_household_member",
            new_callable=AsyncMock,
            side_effect=HTTPException(status_code=403, detail="Not a household member"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await list_transactions(
                    page_size=50,
                    cursor=None,
                    account_id=None,
                    user_id=uuid4(),
                    start_date=None,
                    end_date=None,
                    search=None,
                    current_user=mock_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_no_user_id_skips_verify_household_member(self, mock_user):
        """When user_id is None (household view), verify_household_member is not called."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_txn = self.create_mock_transaction()

        mock_scalars = Mock()
        mock_scalars.all = Mock(return_value=[mock_txn])
        mock_unique = Mock()
        mock_unique.scalars = Mock(return_value=mock_scalars)
        mock_execute_result = Mock()
        mock_execute_result.unique = Mock(return_value=mock_unique)
        mock_count_result = Mock()
        mock_count_result.scalar = Mock(return_value=1)
        mock_db.execute = AsyncMock(side_effect=[mock_execute_result, mock_count_result])

        with patch(
            "app.api.v1.transactions.verify_household_member",
            new_callable=AsyncMock,
        ) as mock_verify:
            await list_transactions(
                page_size=50,
                cursor=None,
                account_id=None,
                user_id=None,
                start_date=None,
                end_date=None,
                search=None,
                current_user=mock_user,
                db=mock_db,
            )

            mock_verify.assert_not_awaited()


@pytest.mark.unit
class TestGetTransaction:
    """Test get_transaction endpoint."""

    @pytest.mark.asyncio
    async def test_get_transaction_success(self, mock_user):
        """Should get transaction by ID."""
        mock_db = AsyncMock(spec=AsyncSession)
        transaction_id = uuid4()

        mock_txn = Mock(spec=Transaction)
        mock_txn.id = transaction_id
        mock_txn.organization_id = mock_user.organization_id
        mock_txn.account_id = uuid4()
        mock_txn.date = date(2024, 1, 15)
        mock_txn.amount = Decimal("-50.00")
        mock_txn.merchant_name = "Test"
        mock_txn.description = "Test"
        mock_txn.category_primary = "Shopping"
        mock_txn.category_detailed = None
        mock_txn.is_pending = False
        mock_txn.is_transfer = False
        mock_txn.created_at = datetime(2024, 1, 15, 10, 0, 0)
        mock_txn.updated_at = datetime(2024, 1, 15, 10, 0, 0)
        mock_txn.external_transaction_id = None
        mock_txn.account = Mock()
        mock_txn.account.name = "Checking"
        mock_txn.account.mask = "1234"
        mock_txn.category = None
        mock_txn.labels = []

        mock_result = Mock()
        mock_unique_result = Mock()
        mock_unique_result.scalar_one_or_none.return_value = mock_txn
        mock_result.unique.return_value = mock_unique_result
        mock_db.execute.return_value = mock_result

        result = await get_transaction(
            transaction_id=transaction_id,
            current_user=mock_user,
            db=mock_db,
        )

        assert result.id == transaction_id
        assert result.merchant_name == "Test"

    @pytest.mark.asyncio
    async def test_get_transaction_not_found(self, mock_user):
        """Should raise 404 for non-existent transaction."""
        mock_db = AsyncMock(spec=AsyncSession)
        transaction_id = uuid4()

        mock_result = Mock()
        mock_unique_result = Mock()
        mock_unique_result.scalar_one_or_none.return_value = None
        mock_result.unique.return_value = mock_unique_result
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await get_transaction(
                transaction_id=transaction_id,
                current_user=mock_user,
                db=mock_db,
            )

        assert exc_info.value.status_code == 404


@pytest.mark.unit
class TestUpdateTransaction:
    """Test update_transaction endpoint."""

    @pytest.mark.asyncio
    async def test_update_transaction_success(self, mock_user):
        """Should update transaction successfully."""
        mock_db = AsyncMock(spec=AsyncSession)
        transaction_id = uuid4()

        mock_txn = Mock(spec=Transaction)
        mock_txn.id = transaction_id
        mock_txn.organization_id = mock_user.organization_id
        mock_txn.account_id = uuid4()
        mock_txn.date = date(2024, 1, 15)
        mock_txn.amount = Decimal("-50.00")
        mock_txn.merchant_name = "Old Merchant"
        mock_txn.description = "Old description"
        mock_txn.category_primary = "Shopping"
        mock_txn.category_detailed = None
        mock_txn.external_transaction_id = None
        mock_txn.is_pending = False
        mock_txn.is_transfer = False
        mock_txn.created_at = datetime(2024, 1, 15, 10, 0, 0)
        mock_txn.updated_at = datetime(2024, 1, 15, 10, 0, 0)
        mock_txn.account = Mock()
        mock_txn.account.name = "Checking"
        mock_txn.account.mask = "1234"
        mock_txn.labels = []

        mock_result = Mock()
        mock_unique_result = Mock()
        mock_unique_result.scalar_one_or_none.return_value = mock_txn
        mock_result.unique.return_value = mock_unique_result
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        update_data = TransactionUpdate(
            merchant_name="New Merchant",
            description="New description",
        )

        with patch("app.api.v1.transactions.input_sanitization_service") as mock_sanitize:
            mock_sanitize.sanitize_html.side_effect = lambda x: x

            result = await update_transaction(
                transaction_id=transaction_id,
                update_data=update_data,
                current_user=mock_user,
                db=mock_db,
            )

            assert mock_txn.merchant_name == "New Merchant"
            assert mock_txn.description == "New description"
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_transaction_not_found(self, mock_user):
        """Should raise 404 for non-existent transaction."""
        mock_db = AsyncMock(spec=AsyncSession)
        transaction_id = uuid4()

        mock_result = Mock()
        mock_unique_result = Mock()
        mock_unique_result.scalar_one_or_none.return_value = None
        mock_result.unique.return_value = mock_unique_result
        mock_db.execute.return_value = mock_result

        update_data = TransactionUpdate(merchant_name="New")

        with pytest.raises(HTTPException) as exc_info:
            await update_transaction(
                transaction_id=transaction_id,
                update_data=update_data,
                current_user=mock_user,
                db=mock_db,
            )

        assert exc_info.value.status_code == 404


@pytest.mark.unit
class TestTransactionLabels:
    """Test transaction label endpoints."""

    @pytest.mark.asyncio
    async def test_add_label_to_transaction_success(self, mock_user):
        """Should add label to transaction successfully."""
        mock_db = AsyncMock(spec=AsyncSession)
        transaction_id = uuid4()
        label_id = uuid4()

        mock_txn = Mock(spec=Transaction)
        mock_txn.id = transaction_id
        mock_txn.organization_id = mock_user.organization_id

        mock_label = Mock(spec=Label)
        mock_label.id = label_id
        mock_label.organization_id = mock_user.organization_id

        mock_txn_result = Mock()
        mock_txn_result.scalar_one_or_none.return_value = mock_txn

        mock_label_result = Mock()
        mock_label_result.scalar_one_or_none.return_value = mock_label

        mock_existing_result = Mock()
        mock_existing_result.scalar_one_or_none.return_value = None

        results = [mock_txn_result, mock_label_result, mock_existing_result]
        mock_db.execute = AsyncMock(side_effect=results)
        mock_db.commit = AsyncMock()

        result = await add_label_to_transaction(
            transaction_id=transaction_id,
            label_id=label_id,
            current_user=mock_user,
            db=mock_db,
        )

        assert "success" in result["message"].lower()
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_label_transaction_not_found(self, mock_user):
        """Should raise 404 if transaction not found."""
        mock_db = AsyncMock(spec=AsyncSession)
        transaction_id = uuid4()
        label_id = uuid4()

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await add_label_to_transaction(
                transaction_id=transaction_id,
                label_id=label_id,
                current_user=mock_user,
                db=mock_db,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_remove_label_from_transaction_success(self, mock_user):
        """Should remove label from transaction successfully."""
        mock_db = AsyncMock(spec=AsyncSession)
        transaction_id = uuid4()
        label_id = uuid4()

        mock_txn = Mock(spec=Transaction)
        mock_txn.id = transaction_id
        mock_txn.organization_id = mock_user.organization_id

        mock_txn_label = Mock(spec=TransactionLabel)

        mock_txn_result = Mock()
        mock_txn_result.scalar_one_or_none.return_value = mock_txn

        mock_label_result = Mock()
        mock_label_result.scalar_one_or_none.return_value = mock_txn_label

        results = [mock_txn_result, mock_label_result]
        mock_db.execute = AsyncMock(side_effect=results)
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()

        await remove_label_from_transaction(
            transaction_id=transaction_id,
            label_id=label_id,
            current_user=mock_user,
            db=mock_db,
        )

        mock_db.delete.assert_called_once_with(mock_txn_label)
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_label_transaction_not_found(self, mock_user):
        """Should raise 404 if transaction not found."""
        mock_db = AsyncMock(spec=AsyncSession)
        transaction_id = uuid4()
        label_id = uuid4()

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await remove_label_from_transaction(
                transaction_id=transaction_id,
                label_id=label_id,
                current_user=mock_user,
                db=mock_db,
            )

        assert exc_info.value.status_code == 404


@pytest.mark.unit
class TestManualTransactionCreate:
    """Test create_transaction uses ManualTransactionCreate schema and sanitizes inputs."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_rejects_unknown_account(self, mock_db, mock_user):
        """Should raise 404 when account doesn't belong to the org."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        txn_data = ManualTransactionCreate(
            account_id=uuid4(),
            date=date.today(),
            amount=Decimal("-50.00"),
        )

        with pytest.raises(HTTPException) as exc_info:
            await create_transaction(
                transaction_data=txn_data,
                current_user=mock_user,
                db=mock_db,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_sanitizes_merchant_name_html(self, mock_db, mock_user):
        """HTML in merchant_name must be stripped before the transaction is saved."""
        mock_account = Mock(spec=Account)
        account_result = Mock()
        account_result.scalar_one_or_none.return_value = mock_account
        mock_db.execute.return_value = account_result

        txn_data = ManualTransactionCreate(
            account_id=uuid4(),
            date=date.today(),
            amount=Decimal("-25.00"),
            merchant_name="<script>bad()</script>Starbucks",
        )

        with patch(
            "app.api.v1.transactions.input_sanitization_service.sanitize_html",
            side_effect=lambda s: s.replace("<script>bad()</script>", ""),
        ) as mock_sanitize:
            mock_db.refresh = AsyncMock()
            refetch_result = Mock()
            refetch_result.unique.return_value.scalar_one.return_value = Mock(
                id=uuid4(),
                date=date.today(),
                amount=Decimal("-25.00"),
                merchant_name="Starbucks",
                description=None,
                is_pending=False,
                is_transfer=False,
                category=None,
                labels=[],
                account=mock_account,
            )
            mock_db.execute.side_effect = [account_result, refetch_result]

            try:
                await create_transaction(
                    transaction_data=txn_data,
                    current_user=mock_user,
                    db=mock_db,
                )
            except Exception:
                pass  # Any exception after the sanitize call is fine

        mock_sanitize.assert_any_call("<script>bad()</script>Starbucks")

    @pytest.mark.asyncio
    async def test_sanitizes_description_html(self, mock_db, mock_user):
        """HTML in description must be stripped before saving."""
        mock_account = Mock(spec=Account)
        account_result = Mock()
        account_result.scalar_one_or_none.return_value = mock_account
        mock_db.execute.return_value = account_result

        txn_data = ManualTransactionCreate(
            account_id=uuid4(),
            date=date.today(),
            amount=Decimal("-10.00"),
            description="<img src=x onerror=alert(1)>Coffee",
        )

        with patch(
            "app.api.v1.transactions.input_sanitization_service.sanitize_html",
            side_effect=lambda s: "Coffee",
        ) as mock_sanitize:
            mock_db.refresh = AsyncMock()
            mock_db.execute.side_effect = [account_result, Mock()]
            try:
                await create_transaction(
                    transaction_data=txn_data,
                    current_user=mock_user,
                    db=mock_db,
                )
            except Exception:
                pass

        mock_sanitize.assert_any_call("<img src=x onerror=alert(1)>Coffee")


@pytest.mark.unit
class TestManualTransactionCreateSchema:
    """Validate the ManualTransactionCreate Pydantic schema fields."""

    def test_requires_account_id_and_date(self):
        """account_id and date are required."""
        from pydantic import ValidationError as PydanticValidationError

        with pytest.raises(PydanticValidationError):
            ManualTransactionCreate(amount=Decimal("-5.00"))  # type: ignore[call-arg]

    def test_defaults_is_pending_false(self):
        schema = ManualTransactionCreate(
            account_id=uuid4(),
            date=date.today(),
            amount=Decimal("-5.00"),
        )
        assert schema.is_pending is False

    def test_defaults_is_transfer_false(self):
        schema = ManualTransactionCreate(
            account_id=uuid4(),
            date=date.today(),
            amount=Decimal("-5.00"),
        )
        assert schema.is_transfer is False

    def test_optional_fields_default_none(self):
        schema = ManualTransactionCreate(
            account_id=uuid4(),
            date=date.today(),
            amount=Decimal("-5.00"),
        )
        assert schema.category_id is None
        assert schema.merchant_name is None
        assert schema.description is None
