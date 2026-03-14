"""Unit tests for TransactionSplitService."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import uuid4

import pytest

from app.models.user import User
from app.services.transaction_split_service import TransactionSplitService


@pytest.fixture
def mock_user():
    user = Mock(spec=User)
    user.id = uuid4()
    user.organization_id = uuid4()
    return user


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.commit = AsyncMock()
    db.add = MagicMock()
    db.refresh = AsyncMock()
    db.flush = AsyncMock()
    db.rollback = AsyncMock()
    return db


def _make_transaction(org_id, amount=Decimal("-100.00")):
    txn = MagicMock()
    txn.id = uuid4()
    txn.organization_id = org_id
    txn.amount = amount
    txn.is_split = False
    return txn


class TestCreateSplits:
    """Tests for create_splits."""

    @pytest.mark.asyncio
    async def test_too_many_splits_raises_error(self, mock_user, mock_db):
        splits = [{"amount": "1.00"}] * 51
        with pytest.raises(ValueError, match="Maximum 50"):
            await TransactionSplitService.create_splits(mock_db, uuid4(), splits, mock_user)

    @pytest.mark.asyncio
    async def test_transaction_not_found_raises_error(self, mock_user, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="Transaction not found"):
            await TransactionSplitService.create_splits(
                mock_db, uuid4(), [{"amount": "100.00"}], mock_user
            )

    @pytest.mark.asyncio
    async def test_split_amounts_mismatch_raises_error(self, mock_user, mock_db):
        txn = _make_transaction(mock_user.organization_id, amount=Decimal("-100.00"))
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = txn
        mock_db.execute = AsyncMock(return_value=mock_result)

        splits = [{"amount": "60.00"}, {"amount": "30.00"}]  # sum=90, not 100
        with pytest.raises(ValueError, match="must equal"):
            await TransactionSplitService.create_splits(mock_db, txn.id, splits, mock_user)

    @pytest.mark.asyncio
    async def test_successful_split_creation(self, mock_user, mock_db):
        txn = _make_transaction(mock_user.organization_id, amount=Decimal("-100.00"))
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = txn

        # The method calls execute multiple times: find txn, delete old splits (2x), then commit
        mock_db.execute = AsyncMock(return_value=mock_result)

        splits_data = [
            {"amount": "60.00", "description": "Groceries"},
            {"amount": "40.00", "description": "Household"},
        ]
        result = await TransactionSplitService.create_splits(
            mock_db, txn.id, splits_data, mock_user
        )

        assert len(result) == 2
        assert txn.is_split is True
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_split_with_category_id(self, mock_user, mock_db):
        txn = _make_transaction(mock_user.organization_id, amount=Decimal("-50.00"))
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = txn
        mock_db.execute = AsyncMock(return_value=mock_result)

        cat_id = uuid4()
        splits_data = [{"amount": "50.00", "category_id": cat_id}]
        result = await TransactionSplitService.create_splits(
            mock_db, txn.id, splits_data, mock_user
        )

        assert len(result) == 1


class TestGetTransactionSplits:
    """Tests for get_transaction_splits."""

    @pytest.mark.asyncio
    async def test_returns_splits(self, mock_user, mock_db):
        split1 = MagicMock()
        split2 = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [split1, split2]
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await TransactionSplitService.get_transaction_splits(mock_db, uuid4(), mock_user)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_returns_empty_list(self, mock_user, mock_db):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await TransactionSplitService.get_transaction_splits(mock_db, uuid4(), mock_user)
        assert result == []


class TestDeleteSplits:
    """Tests for delete_splits."""

    @pytest.mark.asyncio
    async def test_transaction_not_found_returns_false(self, mock_user, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await TransactionSplitService.delete_splits(mock_db, uuid4(), mock_user)
        assert result is False

    @pytest.mark.asyncio
    async def test_successful_deletion(self, mock_user, mock_db):
        txn = _make_transaction(mock_user.organization_id)
        txn.is_split = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = txn
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await TransactionSplitService.delete_splits(mock_db, txn.id, mock_user)
        assert result is True
        assert txn.is_split is False
        mock_db.commit.assert_called_once()


class TestUpdateSplit:
    """Tests for update_split."""

    @pytest.mark.asyncio
    async def test_split_not_found_returns_none(self, mock_user, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await TransactionSplitService.update_split(
            mock_db, uuid4(), amount=Decimal("25.00"), user=mock_user
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_update_description_only(self, mock_user, mock_db):
        split = MagicMock()
        split.id = uuid4()
        split.organization_id = mock_user.organization_id
        split.description = "Old desc"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = split
        mock_db.execute = AsyncMock(return_value=mock_result)

        await TransactionSplitService.update_split(
            mock_db, split.id, description="New desc", user=mock_user
        )
        assert split.description == "New desc"
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_amount_validates_sum(self, mock_user, mock_db):
        split = MagicMock()
        split.id = uuid4()
        split.organization_id = mock_user.organization_id
        split.parent_transaction_id = uuid4()

        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = split

        # After flush, sum query returns total that matches parent
        mock_sum_result = MagicMock()
        mock_sum_result.scalar.return_value = Decimal("100.00")

        mock_parent_result = MagicMock()
        mock_parent_result.scalar.return_value = Decimal("-100.00")

        mock_db.execute = AsyncMock(side_effect=[mock_result1, mock_sum_result, mock_parent_result])

        await TransactionSplitService.update_split(
            mock_db, split.id, amount=Decimal("50.00"), user=mock_user
        )
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_amount_mismatch_raises_error(self, mock_user, mock_db):
        split = MagicMock()
        split.id = uuid4()
        split.organization_id = mock_user.organization_id
        split.parent_transaction_id = uuid4()

        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = split

        mock_sum_result = MagicMock()
        mock_sum_result.scalar.return_value = Decimal("80.00")  # doesn't match

        mock_parent_result = MagicMock()
        mock_parent_result.scalar.return_value = Decimal("-100.00")

        mock_db.execute = AsyncMock(side_effect=[mock_result1, mock_sum_result, mock_parent_result])

        with pytest.raises(ValueError, match="must equal"):
            await TransactionSplitService.update_split(
                mock_db, split.id, amount=Decimal("30.00"), user=mock_user
            )
        mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_category_id(self, mock_user, mock_db):
        split = MagicMock()
        split.id = uuid4()
        split.organization_id = mock_user.organization_id
        split.category_id = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = split
        mock_db.execute = AsyncMock(return_value=mock_result)

        new_cat = uuid4()
        await TransactionSplitService.update_split(
            mock_db, split.id, category_id=new_cat, user=mock_user
        )
        assert split.category_id == new_cat
