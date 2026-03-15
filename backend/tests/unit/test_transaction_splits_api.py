"""Unit tests for transaction splits API endpoints."""

from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch
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
                    transaction_id=transaction_id,
                    current_user=mock_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404
            assert "Transaction not found" in exc_info.value.detail
