"""Unit tests for TransactionMergeService."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import uuid4

import pytest

from app.models.user import User
from app.services.transaction_merge_service import TransactionMergeService


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
    db.delete = AsyncMock()
    db.add = MagicMock()
    db.refresh = AsyncMock()
    return db


def _make_transaction(org_id, txn_date=None, amount=Decimal("-50.00"), merchant="Store"):
    txn = MagicMock()
    txn.id = uuid4()
    txn.organization_id = org_id
    txn.date = txn_date or date.today()
    txn.amount = amount
    txn.merchant_name = merchant
    return txn


class TestFindPotentialDuplicates:
    """Tests for find_potential_duplicates."""

    @pytest.mark.asyncio
    async def test_source_not_found_returns_empty(self, mock_user, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await TransactionMergeService.find_potential_duplicates(
            mock_db, uuid4(), mock_user
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_finds_duplicates_by_amount_and_date(self, mock_user, mock_db):
        source = _make_transaction(mock_user.organization_id)
        dup = _make_transaction(mock_user.organization_id)

        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = source
        mock_result2 = MagicMock()
        mock_result2.scalars.return_value.all.return_value = [dup]
        mock_db.execute = AsyncMock(side_effect=[mock_result1, mock_result2])

        result = await TransactionMergeService.find_potential_duplicates(
            mock_db, source.id, mock_user
        )
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_no_merchant_skips_merchant_filter(self, mock_user, mock_db):
        source = _make_transaction(mock_user.organization_id, merchant=None)
        source.merchant_name = None

        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = source
        mock_result2 = MagicMock()
        mock_result2.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(side_effect=[mock_result1, mock_result2])

        result = await TransactionMergeService.find_potential_duplicates(
            mock_db, source.id, mock_user
        )
        assert result == []


class TestMergeTransactions:
    """Tests for merge_transactions."""

    @pytest.mark.asyncio
    async def test_primary_not_found_raises_error(self, mock_user, mock_db):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="Primary transaction not found"):
            await TransactionMergeService.merge_transactions(mock_db, uuid4(), [uuid4()], mock_user)

    @pytest.mark.asyncio
    async def test_merge_creates_record_and_deletes_dup(self, mock_user, mock_db):
        primary = _make_transaction(mock_user.organization_id)
        dup = _make_transaction(mock_user.organization_id)

        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = primary
        mock_result2 = MagicMock()
        mock_result2.scalar_one_or_none.return_value = dup
        mock_db.execute = AsyncMock(side_effect=[mock_result1, mock_result2])

        await TransactionMergeService.merge_transactions(
            mock_db, primary.id, [dup.id], mock_user, merge_reason="manual merge"
        )

        mock_db.add.assert_called()
        mock_db.delete.assert_called_once_with(dup)
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_skip_missing_duplicate(self, mock_user, mock_db):
        primary = _make_transaction(mock_user.organization_id)

        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = primary
        mock_result2 = MagicMock()
        mock_result2.scalar_one_or_none.return_value = None  # dup not found
        mock_db.execute = AsyncMock(side_effect=[mock_result1, mock_result2])

        with pytest.raises(ValueError, match="No valid duplicates"):
            await TransactionMergeService.merge_transactions(
                mock_db, primary.id, [uuid4()], mock_user
            )

    @pytest.mark.asyncio
    async def test_auto_merged_flag(self, mock_user, mock_db):
        primary = _make_transaction(mock_user.organization_id)
        dup = _make_transaction(mock_user.organization_id)

        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = primary
        mock_result2 = MagicMock()
        mock_result2.scalar_one_or_none.return_value = dup
        mock_db.execute = AsyncMock(side_effect=[mock_result1, mock_result2])

        await TransactionMergeService.merge_transactions(
            mock_db, primary.id, [dup.id], mock_user, is_auto_merged=True
        )

        # The merge record should have been added
        add_call = mock_db.add.call_args
        merge_record = add_call[0][0]
        assert merge_record.is_auto_merged is True
        assert merge_record.merged_by_user_id is None


class TestGetMergeHistory:
    """Tests for get_merge_history."""

    @pytest.mark.asyncio
    async def test_returns_history(self, mock_user, mock_db):
        mock_merge = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_merge]
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await TransactionMergeService.get_merge_history(mock_db, uuid4(), mock_user)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_history(self, mock_user, mock_db):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await TransactionMergeService.get_merge_history(mock_db, uuid4(), mock_user)
        assert result == []


class TestAutoDetectAndMergeDuplicates:
    """Tests for auto_detect_and_merge_duplicates."""

    @pytest.mark.asyncio
    async def test_dry_run_returns_matches_without_merging(self, mock_user, mock_db):
        txn1 = _make_transaction(mock_user.organization_id)
        txn2 = _make_transaction(mock_user.organization_id)

        # First execute: get all transactions
        mock_result1 = MagicMock()
        mock_result1.scalars.return_value.all.return_value = [txn1]
        # find_potential_duplicates calls
        mock_result2 = MagicMock()
        mock_result2.scalar_one_or_none.return_value = txn1
        mock_result3 = MagicMock()
        mock_result3.scalars.return_value.all.return_value = [txn2]
        mock_db.execute = AsyncMock(side_effect=[mock_result1, mock_result2, mock_result3])

        result = await TransactionMergeService.auto_detect_and_merge_duplicates(
            mock_db, mock_user, dry_run=True
        )
        assert len(result) == 1
        # Should NOT call merge (dry run)
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_duplicates_returns_empty(self, mock_user, mock_db):
        txn1 = _make_transaction(mock_user.organization_id)

        mock_result1 = MagicMock()
        mock_result1.scalars.return_value.all.return_value = [txn1]
        mock_result2 = MagicMock()
        mock_result2.scalar_one_or_none.return_value = txn1
        mock_result3 = MagicMock()
        mock_result3.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(side_effect=[mock_result1, mock_result2, mock_result3])

        result = await TransactionMergeService.auto_detect_and_merge_duplicates(
            mock_db, mock_user, dry_run=True
        )
        assert len(result) == 0
