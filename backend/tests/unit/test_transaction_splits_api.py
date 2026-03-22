"""Unit tests for transaction splits API endpoints."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.transaction_splits import (
    create_transaction_splits,
    delete_transaction_splits,
    get_transaction_splits,
    update_split,
)
from app.models.user import User
from app.schemas.transaction_split import (
    CreateSplitsRequest,
    TransactionSplitCreate,
    TransactionSplitUpdate,
)


@pytest.mark.unit
class TestCreateTransactionSplits:
    """Test create_transaction_splits endpoint."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        return user

    @pytest.mark.asyncio
    async def test_creates_splits_successfully(self, mock_db, mock_user):
        """Should create splits and return them."""
        transaction_id = uuid4()
        split_request = CreateSplitsRequest(
            transaction_id=transaction_id,
            splits=[
                TransactionSplitCreate(
                    amount=Decimal("50.00"),
                    description="Groceries",
                    category_id=uuid4(),
                ),
                TransactionSplitCreate(
                    amount=Decimal("25.00"),
                    description="Household",
                ),
            ],
        )

        mock_split1 = Mock()
        mock_split2 = Mock()
        expected_splits = [mock_split1, mock_split2]

        with patch(
            "app.api.v1.transaction_splits.transaction_split_service.create_splits",
            new_callable=AsyncMock,
            return_value=expected_splits,
        ) as mock_create:
            result = await create_transaction_splits(
                http_request=MagicMock(),
                split_request=split_request,
                current_user=mock_user,
                db=mock_db,
            )

            assert result == expected_splits
            assert len(result) == 2
            mock_create.assert_called_once_with(
                db=mock_db,
                transaction_id=transaction_id,
                splits_data=[s.model_dump() for s in split_request.splits],
                user=mock_user,
            )

    @pytest.mark.asyncio
    async def test_raises_400_on_value_error(self, mock_db, mock_user):
        """Should raise 400 when service raises ValueError."""
        split_request = CreateSplitsRequest(
            transaction_id=uuid4(),
            splits=[
                TransactionSplitCreate(
                    amount=Decimal("50.00"),
                    description="Groceries",
                ),
            ],
        )

        with patch(
            "app.api.v1.transaction_splits.transaction_split_service.create_splits",
            new_callable=AsyncMock,
            side_effect=ValueError("Split amounts do not match transaction"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await create_transaction_splits(
                    http_request=MagicMock(),
                    split_request=split_request,
                    current_user=mock_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 400
            assert "Invalid split request" in exc_info.value.detail


@pytest.mark.unit
class TestGetTransactionSplits:
    """Test get_transaction_splits endpoint."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        return user

    @pytest.mark.asyncio
    async def test_returns_splits_list(self, mock_db, mock_user):
        """Should return list of splits for a transaction."""
        transaction_id = uuid4()
        mock_split1 = Mock()
        mock_split2 = Mock()
        expected_splits = [mock_split1, mock_split2]

        with patch(
            "app.api.v1.transaction_splits.transaction_split_service.get_transaction_splits",
            new_callable=AsyncMock,
            return_value=expected_splits,
        ) as mock_get:
            result = await get_transaction_splits(
                transaction_id=transaction_id,
                current_user=mock_user,
                db=mock_db,
            )

            assert result == expected_splits
            assert len(result) == 2
            mock_get.assert_called_once_with(
                db=mock_db,
                transaction_id=transaction_id,
                user=mock_user,
            )

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_splits(self, mock_db, mock_user):
        """Should return empty list when transaction has no splits."""
        transaction_id = uuid4()

        with patch(
            "app.api.v1.transaction_splits.transaction_split_service.get_transaction_splits",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await get_transaction_splits(
                transaction_id=transaction_id,
                current_user=mock_user,
                db=mock_db,
            )

            assert result == []


@pytest.mark.unit
class TestUpdateSplit:
    """Test update_split endpoint."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        return user

    @pytest.mark.asyncio
    async def test_updates_split_successfully(self, mock_db, mock_user):
        """Should update a split and return it."""
        split_id = uuid4()
        update_data = TransactionSplitUpdate(
            amount=Decimal("75.00"),
            description="Updated description",
        )
        mock_split = Mock()

        with patch(
            "app.api.v1.transaction_splits.transaction_split_service.update_split",
            new_callable=AsyncMock,
            return_value=mock_split,
        ) as mock_update:
            result = await update_split(
                http_request=MagicMock(),
                split_id=split_id,
                split_data=update_data,
                current_user=mock_user,
                db=mock_db,
            )

            assert result == mock_split
            mock_update.assert_called_once_with(
                db=mock_db,
                split_id=split_id,
                user=mock_user,
                amount=Decimal("75.00"),
                description="Updated description",
            )

    @pytest.mark.asyncio
    async def test_raises_404_when_split_not_found(self, mock_db, mock_user):
        """Should raise 404 when split doesn't exist."""
        split_id = uuid4()
        update_data = TransactionSplitUpdate(amount=Decimal("50.00"))

        with patch(
            "app.api.v1.transaction_splits.transaction_split_service.update_split",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await update_split(
                    http_request=MagicMock(),
                    split_id=split_id,
                    split_data=update_data,
                    current_user=mock_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404
            assert "Split not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_raises_400_on_value_error(self, mock_db, mock_user):
        """Should raise 400 when service raises ValueError."""
        split_id = uuid4()
        update_data = TransactionSplitUpdate(amount=Decimal("999.99"))

        with patch(
            "app.api.v1.transaction_splits.transaction_split_service.update_split",
            new_callable=AsyncMock,
            side_effect=ValueError("Split amounts exceed transaction total"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await update_split(
                    http_request=MagicMock(),
                    split_id=split_id,
                    split_data=update_data,
                    current_user=mock_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 400
            assert "Split amounts exceed transaction total" in exc_info.value.detail


@pytest.mark.unit
class TestDeleteTransactionSplits:
    """Test delete_transaction_splits endpoint."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        return user

    @pytest.mark.asyncio
    async def test_deletes_splits_successfully(self, mock_db, mock_user):
        """Should delete all splits for a transaction."""
        transaction_id = uuid4()

        with patch(
            "app.api.v1.transaction_splits.transaction_split_service.delete_splits",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_delete:
            result = await delete_transaction_splits(
                http_request=MagicMock(),
                transaction_id=transaction_id,
                current_user=mock_user,
                db=mock_db,
            )

            assert result is None
            mock_delete.assert_called_once_with(
                db=mock_db,
                transaction_id=transaction_id,
                user=mock_user,
            )

    @pytest.mark.asyncio
    async def test_raises_404_when_transaction_not_found(self, mock_db, mock_user):
        """Should raise 404 when delete returns False."""
        transaction_id = uuid4()

        with patch(
            "app.api.v1.transaction_splits.transaction_split_service.delete_splits",
            new_callable=AsyncMock,
            return_value=False,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await delete_transaction_splits(
                    http_request=MagicMock(),
                    transaction_id=transaction_id,
                    current_user=mock_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404
            assert "Transaction not found" in exc_info.value.detail


# ---------------------------------------------------------------------------
# Additional targeted coverage for the task specification
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSplitSumValidation:
    """Explicit validation: splits must sum to transaction total."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        return user

    @pytest.mark.asyncio
    async def test_splits_summing_to_transaction_total_returns_splits(self, mock_db, mock_user):
        """Splits whose amounts sum exactly to the transaction total → service returns list."""
        transaction_id = uuid4()
        mock_split = Mock()
        mock_split.id = uuid4()
        mock_split.parent_transaction_id = transaction_id

        split_request = CreateSplitsRequest(
            transaction_id=transaction_id,
            splits=[
                TransactionSplitCreate(amount=Decimal("75.00")),
                TransactionSplitCreate(amount=Decimal("25.00")),
            ],
        )

        with patch(
            "app.api.v1.transaction_splits.transaction_split_service.create_splits",
            new_callable=AsyncMock,
            return_value=[mock_split, mock_split],
        ):
            result = await create_transaction_splits(
                http_request=MagicMock(),
                split_request=split_request,
                current_user=mock_user,
                db=mock_db,
            )

        # Endpoint returns the service result directly; expect 2 splits
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_splits_not_summing_to_total_returns_400(self, mock_db, mock_user):
        """Splits that don't match the transaction amount → 400 Bad Request."""
        transaction_id = uuid4()

        split_request = CreateSplitsRequest(
            transaction_id=transaction_id,
            splits=[
                TransactionSplitCreate(amount=Decimal("40.00")),
                TransactionSplitCreate(amount=Decimal("40.00")),
            ],
        )

        with patch(
            "app.api.v1.transaction_splits.transaction_split_service.create_splits",
            new_callable=AsyncMock,
            side_effect=ValueError(
                "Split amounts (80.00) must equal transaction amount (100.00)"
            ),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await create_transaction_splits(
                    http_request=MagicMock(),
                    split_request=split_request,
                    current_user=mock_user,
                    db=mock_db,
                )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_split_on_nonexistent_transaction_propagates_as_400(self, mock_db, mock_user):
        """Service raises ValueError('Transaction not found') → endpoint returns 400.

        The endpoint maps *all* ValueErrors to 400. The distinct 404 case lives at
        the delete endpoint (which returns False rather than raising). Creating
        splits for a non-existent transaction surfaces as a 400 via ValueError.
        """
        transaction_id = uuid4()

        split_request = CreateSplitsRequest(
            transaction_id=transaction_id,
            splits=[TransactionSplitCreate(amount=Decimal("50.00"))],
        )

        with patch(
            "app.api.v1.transaction_splits.transaction_split_service.create_splits",
            new_callable=AsyncMock,
            side_effect=ValueError("Transaction not found"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await create_transaction_splits(
                    http_request=MagicMock(),
                    split_request=split_request,
                    current_user=mock_user,
                    db=mock_db,
                )

        assert exc_info.value.status_code == 400
        assert "Invalid split request" in exc_info.value.detail


@pytest.mark.unit
class TestGetSplitsResponseShape:
    """Verify get_transaction_splits returns the expected data shape."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        return user

    @pytest.mark.asyncio
    async def test_get_splits_returns_200_with_correct_fields(self, mock_db, mock_user):
        """GET splits endpoint returns list; each item exposes the transaction_id linkage."""
        from datetime import datetime
        from app.schemas.transaction_split import TransactionSplitResponse

        transaction_id = uuid4()

        # Build a proper response object so field access works
        split = TransactionSplitResponse(
            id=uuid4(),
            parent_transaction_id=transaction_id,
            organization_id=mock_user.organization_id,
            amount=Decimal("60.00"),
            description="Groceries",
            category_id=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        with patch(
            "app.api.v1.transaction_splits.transaction_split_service.get_transaction_splits",
            new_callable=AsyncMock,
            return_value=[split],
        ):
            result = await get_transaction_splits(
                transaction_id=transaction_id,
                current_user=mock_user,
                db=mock_db,
            )

        assert len(result) == 1
        item = result[0]
        assert item.parent_transaction_id == transaction_id
        assert item.amount == Decimal("60.00")
        assert item.description == "Groceries"
        assert item.category_id is None
