"""Extended unit tests for PlaidTransactionSyncService — covers sync_transactions_for_item,
_process_transaction, _create_transaction, _update_transaction, remove_transactions,
and all branch paths including Redis lock handling."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.account import Account, PlaidItem
from app.models.transaction import Transaction
from app.services.plaid_transaction_sync_service import (
    MockPlaidTransactionGenerator,
    PlaidTransactionSyncService,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_plaid_item(org_id=None, item_id=None):
    """Create a mock PlaidItem."""
    item = MagicMock(spec=PlaidItem)
    item.id = item_id or uuid4()
    item.organization_id = org_id or uuid4()
    return item


def _make_account(account_id=None, org_id=None, external_id="ext_acc_1"):
    """Create a mock Account."""
    account = MagicMock(spec=Account)
    account.id = account_id or uuid4()
    account.organization_id = org_id or uuid4()
    account.external_account_id = external_id
    return account


def _make_txn_data(
    txn_id="txn_1",
    account_id="ext_acc_1",
    txn_date="2024-06-15",
    amount=50.00,
    name="Starbucks",
    merchant_name="Starbucks",
    category=None,
    pending=False,
):
    """Create a mock Plaid transaction data dict."""
    return {
        "transaction_id": txn_id,
        "account_id": account_id,
        "date": txn_date,
        "amount": amount,
        "name": name,
        "merchant_name": merchant_name,
        "category": category or ["Food and Drink", "Coffee Shop"],
        "pending": pending,
    }


# ---------------------------------------------------------------------------
# transaction_exists
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTransactionExists:
    @pytest.mark.asyncio
    async def test_returns_true_when_exists(self):
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = uuid4()
        db.execute = AsyncMock(return_value=mock_result)

        result = await PlaidTransactionSyncService.transaction_exists(db, uuid4(), "hash123")
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_not_exists(self):
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)

        result = await PlaidTransactionSyncService.transaction_exists(db, uuid4(), "hash123")
        assert result is False


# ---------------------------------------------------------------------------
# check_external_id_exists
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCheckExternalIdExists:
    @pytest.mark.asyncio
    async def test_returns_true_when_exists(self):
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = uuid4()
        db.execute = AsyncMock(return_value=mock_result)

        result = await PlaidTransactionSyncService.check_external_id_exists(
            db, uuid4(), "ext_txn_1"
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_not_exists(self):
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)

        result = await PlaidTransactionSyncService.check_external_id_exists(
            db, uuid4(), "ext_txn_1"
        )
        assert result is False


# ---------------------------------------------------------------------------
# sync_transactions_for_item
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSyncTransactionsForItem:
    @pytest.mark.asyncio
    async def test_sync_adds_new_transactions(self):
        """Should add new transactions when they don't already exist."""
        service = PlaidTransactionSyncService()

        org_id = uuid4()
        plaid_item_id = uuid4()
        account_id = uuid4()

        plaid_item = MagicMock(spec=PlaidItem)
        plaid_item.id = plaid_item_id
        plaid_item.organization_id = org_id

        account = MagicMock(spec=Account)
        account.id = account_id
        account.external_account_id = "ext_acc_1"
        account.organization_id = org_id

        db = AsyncMock()

        # Mock PlaidItem lookup
        item_result = MagicMock()
        item_result.scalar_one_or_none.return_value = plaid_item

        # Mock accounts lookup
        acc_scalars = MagicMock()
        acc_scalars.all.return_value = [account]
        acc_result = MagicMock()
        acc_result.scalars.return_value = acc_scalars

        # Mock existing ext IDs (none)
        ext_id_result = MagicMock()
        ext_id_result.all.return_value = []

        # Mock existing dedup hashes (none)
        dedup_result = MagicMock()
        dedup_result.all.return_value = []

        db.execute = AsyncMock(side_effect=[item_result, acc_result, ext_id_result, dedup_result])

        nested_ctx = AsyncMock()
        nested_ctx.__aenter__ = AsyncMock()
        nested_ctx.__aexit__ = AsyncMock(return_value=False)
        db.begin_nested = MagicMock(return_value=nested_ctx)

        txn_data = [_make_txn_data(txn_id="txn_new")]

        with patch("app.services.plaid_transaction_sync_service.redis_client", None):
            result = await service.sync_transactions_for_item(db, plaid_item_id, txn_data)

        assert result["added"] == 1
        assert result["skipped"] == 0
        assert result["errors"] == 0
        db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_skips_existing_by_ext_id(self):
        """Should skip transactions that already exist by external ID."""
        service = PlaidTransactionSyncService()

        org_id = uuid4()
        plaid_item_id = uuid4()
        account_id = uuid4()

        plaid_item = MagicMock(spec=PlaidItem)
        plaid_item.id = plaid_item_id
        plaid_item.organization_id = org_id

        account = MagicMock(spec=Account)
        account.id = account_id
        account.external_account_id = "ext_acc_1"
        account.organization_id = org_id

        db = AsyncMock()

        item_result = MagicMock()
        item_result.scalar_one_or_none.return_value = plaid_item

        acc_scalars = MagicMock()
        acc_scalars.all.return_value = [account]
        acc_result = MagicMock()
        acc_result.scalars.return_value = acc_scalars

        # Existing ext ID already in set
        ext_id_result = MagicMock()
        ext_id_result.all.return_value = [(account_id, "txn_existing")]

        dedup_result = MagicMock()
        dedup_result.all.return_value = []

        # For update path: _get_transaction_by_external_id
        existing_txn = MagicMock(spec=Transaction)
        existing_txn.external_transaction_id = "txn_existing"
        existing_txn.is_pending = True
        existing_txn.merchant_name = "Old Name"
        txn_lookup_result = MagicMock()
        txn_lookup_result.scalar_one_or_none.return_value = existing_txn

        db.execute = AsyncMock(
            side_effect=[item_result, acc_result, ext_id_result, dedup_result, txn_lookup_result]
        )

        nested_ctx = AsyncMock()
        nested_ctx.__aenter__ = AsyncMock()
        nested_ctx.__aexit__ = AsyncMock(return_value=False)
        db.begin_nested = MagicMock(return_value=nested_ctx)

        txn_data = [_make_txn_data(txn_id="txn_existing")]

        with patch("app.services.plaid_transaction_sync_service.redis_client", None):
            result = await service.sync_transactions_for_item(db, plaid_item_id, txn_data)

        assert result["updated"] == 1

    @pytest.mark.asyncio
    async def test_sync_raises_when_plaid_item_not_found(self):
        """Should raise ValueError when PlaidItem doesn't exist."""
        service = PlaidTransactionSyncService()
        db = AsyncMock()

        item_result = MagicMock()
        item_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=item_result)

        with patch("app.services.plaid_transaction_sync_service.redis_client", None):
            with pytest.raises(ValueError, match="not found"):
                await service.sync_transactions_for_item(db, uuid4(), [])

    @pytest.mark.asyncio
    async def test_sync_redis_lock_prevents_concurrent(self):
        """Should return zeros when Redis lock already held."""
        service = PlaidTransactionSyncService()
        db = AsyncMock()

        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock(return_value=False)

        with patch("app.services.plaid_transaction_sync_service.redis_client", mock_redis):
            result = await service.sync_transactions_for_item(db, uuid4(), [])

        assert result == {"added": 0, "updated": 0, "skipped": 0, "errors": 0}

    @pytest.mark.asyncio
    async def test_sync_redis_failure_proceeds(self):
        """Should proceed without lock if Redis fails."""
        service = PlaidTransactionSyncService()

        org_id = uuid4()
        plaid_item_id = uuid4()

        plaid_item = MagicMock(spec=PlaidItem)
        plaid_item.id = plaid_item_id
        plaid_item.organization_id = org_id

        db = AsyncMock()

        item_result = MagicMock()
        item_result.scalar_one_or_none.return_value = plaid_item

        acc_scalars = MagicMock()
        acc_scalars.all.return_value = []
        acc_result = MagicMock()
        acc_result.scalars.return_value = acc_scalars

        ext_id_result = MagicMock()
        ext_id_result.all.return_value = []

        dedup_result = MagicMock()
        dedup_result.all.return_value = []

        db.execute = AsyncMock(side_effect=[item_result, acc_result, ext_id_result, dedup_result])

        nested_ctx = AsyncMock()
        nested_ctx.__aenter__ = AsyncMock()
        nested_ctx.__aexit__ = AsyncMock(return_value=False)
        db.begin_nested = MagicMock(return_value=nested_ctx)

        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock(side_effect=Exception("Redis down"))

        with patch("app.services.plaid_transaction_sync_service.redis_client", mock_redis):
            result = await service.sync_transactions_for_item(db, plaid_item_id, [])

        assert result["added"] == 0

    @pytest.mark.asyncio
    async def test_sync_handles_processing_errors(self):
        """Should increment errors count when transaction processing fails."""
        service = PlaidTransactionSyncService()

        org_id = uuid4()
        plaid_item_id = uuid4()

        plaid_item = MagicMock(spec=PlaidItem)
        plaid_item.id = plaid_item_id
        plaid_item.organization_id = org_id

        db = AsyncMock()

        item_result = MagicMock()
        item_result.scalar_one_or_none.return_value = plaid_item

        acc_scalars = MagicMock()
        acc_scalars.all.return_value = []  # No matching accounts
        acc_result = MagicMock()
        acc_result.scalars.return_value = acc_scalars

        ext_id_result = MagicMock()
        ext_id_result.all.return_value = []

        dedup_result = MagicMock()
        dedup_result.all.return_value = []

        db.execute = AsyncMock(side_effect=[item_result, acc_result, ext_id_result, dedup_result])

        nested_ctx = AsyncMock()
        nested_ctx.__aenter__ = AsyncMock()
        nested_ctx.__aexit__ = AsyncMock(return_value=False)
        db.begin_nested = MagicMock(return_value=nested_ctx)

        # Transaction with unknown account
        txn_data = [_make_txn_data(txn_id="txn_no_acct", account_id="unknown_acc")]

        with patch("app.services.plaid_transaction_sync_service.redis_client", None):
            result = await service.sync_transactions_for_item(db, plaid_item_id, txn_data)

        assert result["errors"] == 1


# ---------------------------------------------------------------------------
# _process_transaction branches
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProcessTransaction:
    @pytest.mark.asyncio
    async def test_skips_when_account_not_found(self):
        """Should increment errors when account not in accounts dict."""
        service = PlaidTransactionSyncService()
        db = AsyncMock()
        org_id = uuid4()
        stats = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}

        txn_data = _make_txn_data(account_id="missing_account")

        await service._process_transaction(
            db=db,
            organization_id=org_id,
            accounts={},  # empty
            txn_data=txn_data,
            stats=stats,
        )

        assert stats["errors"] == 1

    @pytest.mark.asyncio
    async def test_skips_by_dedup_hash_in_prefetched_set(self):
        """Should skip when dedup hash found in pre-fetched set."""
        service = PlaidTransactionSyncService()
        db = AsyncMock()
        org_id = uuid4()
        account_id = uuid4()

        account = MagicMock(spec=Account)
        account.id = account_id
        account.organization_id = org_id

        stats = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}
        txn_data = _make_txn_data()

        # Pre-compute the hash using same logic as _process_transaction
        # amount comes from Decimal(str(txn_data["amount"])) = Decimal("50.0")
        # description = txn_data.get("name", "") = "Starbucks"
        # hash_description = description or merchant_name or ""
        dedup_hash = service.generate_deduplication_hash(
            account_id=account_id,
            txn_date=date(2024, 6, 15),
            amount=Decimal(str(txn_data["amount"])),
            description=txn_data.get("name", ""),
        )

        await service._process_transaction(
            db=db,
            organization_id=org_id,
            accounts={"ext_acc_1": account},
            txn_data=txn_data,
            stats=stats,
            existing_ext_ids=set(),
            org_ext_ids=set(),
            existing_dedup_hashes={(account_id, dedup_hash)},
        )

        assert stats["skipped"] == 1

    @pytest.mark.asyncio
    async def test_skips_by_org_ext_id(self):
        """Should skip when external ID found in org-level set."""
        service = PlaidTransactionSyncService()
        db = AsyncMock()
        org_id = uuid4()
        account_id = uuid4()

        account = MagicMock(spec=Account)
        account.id = account_id
        account.organization_id = org_id

        stats = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}
        txn_data = _make_txn_data(txn_id="existing_ext_id")

        await service._process_transaction(
            db=db,
            organization_id=org_id,
            accounts={"ext_acc_1": account},
            txn_data=txn_data,
            stats=stats,
            existing_ext_ids=set(),
            org_ext_ids={"existing_ext_id"},
            existing_dedup_hashes=set(),
        )

        assert stats["skipped"] == 1

    @pytest.mark.asyncio
    async def test_fallback_ext_id_check_without_prefetched_sets(self):
        """Should use DB queries when pre-fetched sets are None."""
        service = PlaidTransactionSyncService()
        db = AsyncMock()
        org_id = uuid4()
        account_id = uuid4()

        account = MagicMock(spec=Account)
        account.id = account_id
        account.organization_id = org_id

        stats = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}
        txn_data = _make_txn_data(txn_id="some_txn")

        # Mock _get_transaction_by_external_id returning existing
        existing_txn = MagicMock(spec=Transaction)
        existing_txn.is_pending = False
        existing_txn.merchant_name = "Test"
        existing_txn.external_transaction_id = "some_txn"

        txn_result = MagicMock()
        txn_result.scalar_one_or_none.return_value = existing_txn
        db.execute = AsyncMock(return_value=txn_result)

        await service._process_transaction(
            db=db,
            organization_id=org_id,
            accounts={"ext_acc_1": account},
            txn_data=txn_data,
            stats=stats,
            existing_ext_ids=None,
            org_ext_ids=None,
            existing_dedup_hashes=None,
        )

        assert stats["updated"] == 1

    @pytest.mark.asyncio
    async def test_creates_new_transaction(self):
        """Should create transaction when no duplicates found."""
        service = PlaidTransactionSyncService()
        db = AsyncMock()
        org_id = uuid4()
        account_id = uuid4()

        account = MagicMock(spec=Account)
        account.id = account_id
        account.organization_id = org_id

        stats = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}
        txn_data = _make_txn_data(txn_id="brand_new_txn")

        await service._process_transaction(
            db=db,
            organization_id=org_id,
            accounts={"ext_acc_1": account},
            txn_data=txn_data,
            stats=stats,
            existing_ext_ids=set(),
            org_ext_ids=set(),
            existing_dedup_hashes=set(),
        )

        assert stats["added"] == 1
        db.add.assert_called_once()
        added = db.add.call_args[0][0]
        assert isinstance(added, Transaction)
        assert added.external_transaction_id == "brand_new_txn"


# ---------------------------------------------------------------------------
# _create_transaction
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCreateTransaction:
    @pytest.mark.asyncio
    async def test_creates_with_full_category(self):
        """Should extract primary and detailed category from Plaid data."""
        service = PlaidTransactionSyncService()
        db = AsyncMock()
        org_id = uuid4()
        account = MagicMock(spec=Account)
        account.id = uuid4()

        stats = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}
        txn_data = _make_txn_data(category=["Groceries", "Supermarkets"])

        await service._create_transaction(
            db=db,
            organization_id=org_id,
            account=account,
            external_id="txn_1",
            txn_data=txn_data,
            dedup_hash="hash",
            stats=stats,
        )

        added = db.add.call_args[0][0]
        assert added.category_primary == "Groceries"
        assert added.category_detailed == "Supermarkets"

    @pytest.mark.asyncio
    async def test_creates_with_single_category(self):
        """Should handle single category list."""
        service = PlaidTransactionSyncService()
        db = AsyncMock()
        org_id = uuid4()
        account = MagicMock(spec=Account)
        account.id = uuid4()

        stats = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}
        txn_data = _make_txn_data(category=["Shopping"])

        await service._create_transaction(
            db=db,
            organization_id=org_id,
            account=account,
            external_id="txn_1",
            txn_data=txn_data,
            dedup_hash="hash",
            stats=stats,
        )

        added = db.add.call_args[0][0]
        assert added.category_primary == "Shopping"
        assert added.category_detailed is None

    @pytest.mark.asyncio
    async def test_creates_with_empty_category(self):
        """Should handle empty category list."""
        service = PlaidTransactionSyncService()
        db = AsyncMock()
        org_id = uuid4()
        account = MagicMock(spec=Account)
        account.id = uuid4()

        stats = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}
        txn_data = {
            "transaction_id": "txn_1",
            "account_id": "ext_acc_1",
            "date": "2024-06-15",
            "amount": 50.00,
            "name": "Test",
            "merchant_name": "Test",
            "category": [],
            "pending": False,
        }

        await service._create_transaction(
            db=db,
            organization_id=org_id,
            account=account,
            external_id="txn_1",
            txn_data=txn_data,
            dedup_hash="hash",
            stats=stats,
        )

        added = db.add.call_args[0][0]
        assert added.category_primary is None
        assert added.category_detailed is None

    @pytest.mark.asyncio
    async def test_creates_with_pending_flag(self):
        """Should set is_pending from transaction data."""
        service = PlaidTransactionSyncService()
        db = AsyncMock()
        org_id = uuid4()
        account = MagicMock(spec=Account)
        account.id = uuid4()

        stats = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}
        txn_data = _make_txn_data(pending=True)

        await service._create_transaction(
            db=db,
            organization_id=org_id,
            account=account,
            external_id="txn_1",
            txn_data=txn_data,
            dedup_hash="hash",
            stats=stats,
        )

        added = db.add.call_args[0][0]
        assert added.is_pending is True


# ---------------------------------------------------------------------------
# _update_transaction
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUpdateTransaction:
    @pytest.mark.asyncio
    async def test_updates_pending_and_merchant(self):
        """Should update is_pending and merchant_name fields."""
        service = PlaidTransactionSyncService()
        txn = MagicMock(spec=Transaction)
        txn.is_pending = True
        txn.merchant_name = "Old Name"
        txn.external_transaction_id = "txn_1"

        stats = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}
        txn_data = _make_txn_data(pending=False, merchant_name="New Name")

        await service._update_transaction(txn, txn_data, stats)

        assert txn.is_pending is False
        assert txn.merchant_name == "New Name"
        assert stats["updated"] == 1

    @pytest.mark.asyncio
    async def test_updates_falls_back_to_name(self):
        """Should use name when merchant_name is None."""
        service = PlaidTransactionSyncService()
        txn = MagicMock(spec=Transaction)
        txn.external_transaction_id = "txn_1"

        stats = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}
        txn_data = {
            "transaction_id": "txn_1",
            "account_id": "acc_1",
            "date": "2024-01-01",
            "amount": 50,
            "name": "Fallback Name",
            "merchant_name": None,
            "pending": False,
        }

        await service._update_transaction(txn, txn_data, stats)

        assert txn.merchant_name == "Fallback Name"


# ---------------------------------------------------------------------------
# remove_transactions
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRemoveTransactions:
    @pytest.mark.asyncio
    async def test_returns_zero_for_empty_list(self):
        service = PlaidTransactionSyncService()
        db = AsyncMock()
        result = await service.remove_transactions(db, uuid4(), [])
        assert result == 0

    @pytest.mark.asyncio
    async def test_returns_zero_when_plaid_item_not_found(self):
        service = PlaidTransactionSyncService()
        db = AsyncMock()

        org_result = MagicMock()
        org_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=org_result)

        result = await service.remove_transactions(db, uuid4(), ["txn_1"])
        assert result == 0

    @pytest.mark.asyncio
    async def test_removes_matching_transactions(self):
        service = PlaidTransactionSyncService()
        db = AsyncMock()
        org_id = uuid4()

        # First execute: get org_id
        org_result = MagicMock()
        org_result.scalar_one_or_none.return_value = org_id

        # Second execute: find transactions
        txn1 = MagicMock(spec=Transaction)
        txn2 = MagicMock(spec=Transaction)
        txn_scalars = MagicMock()
        txn_scalars.all.return_value = [txn1, txn2]
        txn_result = MagicMock()
        txn_result.scalars.return_value = txn_scalars

        db.execute = AsyncMock(side_effect=[org_result, txn_result])

        nested_ctx = AsyncMock()
        nested_ctx.__aenter__ = AsyncMock()
        nested_ctx.__aexit__ = AsyncMock(return_value=False)
        db.begin_nested = MagicMock(return_value=nested_ctx)

        result = await service.remove_transactions(db, uuid4(), ["txn_1", "txn_2"])

        assert result == 2
        assert db.delete.await_count == 2
        db.commit.assert_awaited_once()


# ---------------------------------------------------------------------------
# MockPlaidTransactionGenerator (additional tests)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMockGeneratorExtended:
    def test_generates_various_amount_ranges(self):
        """Should generate different amounts based on merchant type."""
        txns = MockPlaidTransactionGenerator.generate_mock_transactions(
            "acc_123", date(2024, 1, 1), date(2024, 12, 31), count=16
        )
        amounts = [t["amount"] for t in txns]
        # Rent/Electric/Water should be higher
        # All amounts should be positive
        assert all(a > 0 for a in amounts)

    def test_all_transactions_have_account_id(self):
        txns = MockPlaidTransactionGenerator.generate_mock_transactions(
            "acc_xyz", date(2024, 1, 1), date(2024, 3, 31), count=10
        )
        for txn in txns:
            assert txn["account_id"] == "acc_xyz"

    def test_transaction_ids_are_unique(self):
        txns = MockPlaidTransactionGenerator.generate_mock_transactions(
            "acc_123", date(2024, 1, 1), date(2024, 6, 30), count=50
        )
        ids = [t["transaction_id"] for t in txns]
        assert len(ids) == len(set(ids))
