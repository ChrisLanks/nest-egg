"""
Plaid Transaction Sync Service

Handles syncing transactions from Plaid API with deduplication logic.
Each sync operation is idempotent and atomic (all-or-nothing) using
database savepoints and Redis-based distributed locks.
"""

import hashlib
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import redis_client
from app.models.account import Account, PlaidItem
from app.models.transaction import Transaction
from app.services.dividend_detection_service import DividendDetectionService
from app.utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)

# TTL for sync idempotency locks (seconds)
_SYNC_LOCK_TTL = 300


class PlaidTransactionSyncService:
    """Service for syncing transactions from Plaid with deduplication."""

    @staticmethod
    def generate_deduplication_hash(
        account_id: UUID, txn_date: date, amount: Decimal, description: str
    ) -> str:
        """
        Generate deduplication hash for a transaction.
        Uses same algorithm as CSV import for consistency.

        Formula: SHA256(account_id|date|amount|description)
        """
        hash_input = f"{account_id}|{txn_date.isoformat()}|{amount}|{description}"
        return hashlib.sha256(hash_input.encode()).hexdigest()

    @staticmethod
    async def transaction_exists(
        db: AsyncSession, account_id: UUID, deduplication_hash: str
    ) -> bool:
        """Check if transaction already exists."""
        result = await db.execute(
            select(Transaction.id)
            .where(
                and_(
                    Transaction.account_id == account_id,
                    Transaction.deduplication_hash == deduplication_hash,
                )
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def check_external_id_exists(
        db: AsyncSession, organization_id: UUID, external_transaction_id: str
    ) -> bool:
        """
        Check if a transaction with this external_transaction_id already exists
        in this organization (prevents duplicates across accounts).
        """
        result = await db.execute(
            select(Transaction.id)
            .where(
                and_(
                    Transaction.organization_id == organization_id,
                    Transaction.external_transaction_id == external_transaction_id,
                )
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def sync_transactions_for_item(
        self,
        db: AsyncSession,
        plaid_item_id: UUID,
        transactions_data: List[Dict[str, Any]],
        is_test_mode: bool = False,
    ) -> Dict[str, int]:
        """
        Sync transactions for a Plaid item.

        This operation is atomic (all-or-nothing) using a database savepoint
        and protected by a Redis idempotency lock to prevent concurrent syncs.

        Args:
            db: Database session
            plaid_item_id: PlaidItem ID
            transactions_data: List of transaction dicts from Plaid API
            is_test_mode: Whether this is test data (for test@test.com)

        Returns:
            Dict with counts: {added, updated, skipped, errors}
        """
        # Acquire Redis idempotency lock to prevent concurrent syncs
        lock_key = f"sync:plaid:{plaid_item_id}"
        lock_acquired = False
        if redis_client:
            try:
                lock_acquired = await redis_client.set(lock_key, "1", nx=True, ex=_SYNC_LOCK_TTL)
                if not lock_acquired:
                    logger.info(f"Sync already in progress for PlaidItem {plaid_item_id}, skipping")
                    return {"added": 0, "updated": 0, "skipped": 0, "errors": 0}
            except Exception as e:
                logger.warning(f"Redis lock acquisition failed, proceeding without lock: {e}")

        try:
            # Get PlaidItem with organization
            result = await db.execute(select(PlaidItem).where(PlaidItem.id == plaid_item_id))
            plaid_item = result.scalar_one_or_none()

            if not plaid_item:
                raise ValueError(f"PlaidItem {plaid_item_id} not found")

            organization_id = plaid_item.organization_id

            # Get all accounts for this Plaid item
            accounts_result = await db.execute(
                select(Account).where(Account.plaid_item_id == plaid_item_id)
            )
            accounts = {acc.external_account_id: acc for acc in accounts_result.scalars().all()}

            # Pre-fetch existing external IDs and dedup hashes to avoid N+1 queries
            account_ids = [acc.id for acc in accounts.values()]
            ext_id_result = await db.execute(
                select(
                    Transaction.account_id,
                    Transaction.external_transaction_id,
                ).where(
                    Transaction.account_id.in_(account_ids),
                    Transaction.external_transaction_id.isnot(None),
                )
            )
            existing_ext_ids = {(row[0], row[1]) for row in ext_id_result.all()}
            # Cross-account dedup within this Plaid item
            item_ext_ids = {row[1] for row in existing_ext_ids}

            dedup_result = await db.execute(
                select(
                    Transaction.account_id,
                    Transaction.deduplication_hash,
                ).where(Transaction.account_id.in_(account_ids))
            )
            existing_dedup_hashes = {(row[0], row[1]) for row in dedup_result.all()}

            stats = {"added": 0, "updated": 0, "skipped": 0, "errors": 0}

            # Use a savepoint so the entire batch is all-or-nothing
            new_transactions: List[Transaction] = []
            async with db.begin_nested():
                for txn_data in transactions_data:
                    try:
                        txn = await self._process_transaction(
                            db=db,
                            organization_id=organization_id,
                            accounts=accounts,
                            txn_data=txn_data,
                            stats=stats,
                            existing_ext_ids=existing_ext_ids,
                            item_ext_ids=item_ext_ids,
                            existing_dedup_hashes=existing_dedup_hashes,
                        )
                        if txn is not None:
                            new_transactions.append(txn)
                    except Exception as e:
                        logger.error(
                            f"Error processing transaction {txn_data.get('transaction_id')}: {e}"
                        )
                        stats["errors"] += 1

            # Flush to assign IDs, then auto-detect dividend transactions
            await db.flush()
            if new_transactions:
                try:
                    detector = DividendDetectionService(db)
                    await detector.process_batch(new_transactions, organization_id)
                except Exception as e:
                    logger.warning("Dividend auto-detection failed (non-fatal): %s", e)

            await db.commit()

            logger.info(
                f"Synced transactions for PlaidItem {plaid_item_id}: "
                f"added={stats['added']}, updated={stats['updated']}, "
                f"skipped={stats['skipped']}, errors={stats['errors']}"
            )

            return stats
        finally:
            # Release Redis lock on completion (success or failure)
            if redis_client and lock_acquired:
                try:
                    await redis_client.delete(lock_key)
                except Exception as e:
                    logger.warning(f"Failed to release Redis lock {lock_key}: {e}")

    async def _process_transaction(
        self,
        db: AsyncSession,
        organization_id: UUID,
        accounts: Dict[str, Account],
        txn_data: Dict[str, Any],
        stats: Dict[str, int],
        existing_ext_ids: set = None,
        item_ext_ids: set = None,
        existing_dedup_hashes: set = None,
    ) -> Optional[Transaction]:
        """Process a single transaction from Plaid. Returns created txn or None."""
        # Extract transaction data
        external_id = txn_data["transaction_id"]
        external_account_id = txn_data["account_id"]

        # Find corresponding account
        account = accounts.get(external_account_id)
        if not account:
            logger.warning(f"Account {external_account_id} not found for transaction {external_id}")
            stats["errors"] += 1
            return None

        # Parse transaction fields
        txn_date = datetime.strptime(txn_data["date"], "%Y-%m-%d").date()
        amount = Decimal(str(txn_data["amount"]))
        merchant_name = txn_data.get("merchant_name") or txn_data.get("name", "")
        description = txn_data.get("name", "")

        # Generate deduplication hash
        # Use description as primary field for consistency with other providers (Teller),
        # falling back to merchant_name only if description is empty.
        hash_description = description or merchant_name or ""
        dedup_hash = self.generate_deduplication_hash(
            account_id=account.id, txn_date=txn_date, amount=amount, description=hash_description
        )

        # Check if we need to update existing transaction (by external_id in same account)
        # This must come BEFORE the dedup skip checks so that modified transactions
        # (e.g., pending→cleared, merchant name changes) actually get updated.
        if existing_ext_ids is not None and (account.id, external_id) in existing_ext_ids:
            # Fetch the actual record for update (only when we know it exists)
            existing_txn = await self._get_transaction_by_external_id(db, account.id, external_id)
            if existing_txn:
                await self._update_transaction(existing_txn, txn_data, stats)
                return None
        elif existing_ext_ids is None:
            # Fallback for callers that don't pass pre-fetched sets
            existing_txn = await self._get_transaction_by_external_id(db, account.id, external_id)
            if existing_txn:
                await self._update_transaction(existing_txn, txn_data, stats)
                return None

        # Check if transaction already exists by external_id (cross-account check)
        if item_ext_ids is not None:
            if external_id in item_ext_ids:
                stats["skipped"] += 1
                return None
        elif await self.check_external_id_exists(db, organization_id, external_id):
            stats["skipped"] += 1
            return None

        # Check if transaction exists by deduplication hash
        if existing_dedup_hashes is not None:
            if (account.id, dedup_hash) in existing_dedup_hashes:
                stats["skipped"] += 1
                return None
        elif await self.transaction_exists(db, account.id, dedup_hash):
            stats["skipped"] += 1
            return None

        # Create new transaction
        return await self._create_transaction(
            db=db,
            organization_id=organization_id,
            account=account,
            external_id=external_id,
            txn_data=txn_data,
            dedup_hash=dedup_hash,
            stats=stats,
        )

    async def _get_transaction_by_external_id(
        self, db: AsyncSession, account_id: UUID, external_id: str
    ) -> Optional[Transaction]:
        """Get existing transaction by external_transaction_id."""
        result = await db.execute(
            select(Transaction).where(
                and_(
                    Transaction.account_id == account_id,
                    Transaction.external_transaction_id == external_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def _create_transaction(
        self,
        db: AsyncSession,
        organization_id: UUID,
        account: Account,
        external_id: str,
        txn_data: Dict[str, Any],
        dedup_hash: str,
        stats: Dict[str, int],
    ) -> Transaction:
        """Create a new transaction from Plaid data."""
        txn_date = datetime.strptime(txn_data["date"], "%Y-%m-%d").date()
        amount = Decimal(str(txn_data["amount"]))
        merchant_name = txn_data.get("merchant_name") or txn_data.get("name")
        description = txn_data.get("name", "")

        # Extract category info from Plaid
        category_list = txn_data.get("category", [])
        category_primary = category_list[0] if len(category_list) > 0 else None
        category_detailed = category_list[1] if len(category_list) > 1 else None

        # Create transaction
        transaction = Transaction(
            organization_id=organization_id,
            account_id=account.id,
            external_transaction_id=external_id,
            date=txn_date,
            amount=amount,
            merchant_name=merchant_name,
            description=description,
            category_primary=category_primary,
            category_detailed=category_detailed,
            is_pending=txn_data.get("pending", False),
            is_transfer=False,  # Will be determined by rules or user
            deduplication_hash=dedup_hash,
        )

        db.add(transaction)
        stats["added"] += 1

        logger.debug(
            f"Created transaction: {external_id} for account {account.id} "
            f"({merchant_name}, ${amount})"
        )
        return transaction

    async def _update_transaction(
        self, transaction: Transaction, txn_data: Dict[str, Any], stats: Dict[str, int]
    ) -> None:
        """Update an existing transaction with new data from Plaid."""
        # Update fields that may have changed
        transaction.is_pending = txn_data.get("pending", False)
        transaction.merchant_name = txn_data.get("merchant_name") or txn_data.get("name")
        transaction.updated_at = utc_now()

        stats["updated"] += 1

        logger.debug(f"Updated transaction: {transaction.external_transaction_id}")

    async def remove_transactions(
        self, db: AsyncSession, plaid_item_id: UUID, removed_transaction_ids: List[str]
    ) -> int:
        """
        Handle removed transactions from Plaid.

        This operation is atomic (all-or-nothing) using a database savepoint.

        Args:
            db: Database session
            plaid_item_id: PlaidItem ID
            removed_transaction_ids: List of external transaction IDs to remove

        Returns:
            Number of transactions removed
        """
        if not removed_transaction_ids:
            return 0

        # Get organization_id for this plaid_item
        result = await db.execute(
            select(PlaidItem.organization_id).where(PlaidItem.id == plaid_item_id)
        )
        organization_id = result.scalar_one_or_none()

        if not organization_id:
            logger.error(f"PlaidItem {plaid_item_id} not found")
            return 0

        # Use a savepoint so the entire removal batch is all-or-nothing
        async with db.begin_nested():
            # Delete transactions with these external IDs in this organization
            result = await db.execute(
                select(Transaction).where(
                    and_(
                        Transaction.organization_id == organization_id,
                        Transaction.external_transaction_id.in_(removed_transaction_ids),
                    )
                )
            )
            transactions_to_remove = result.scalars().all()

            count = len(transactions_to_remove)
            for txn in transactions_to_remove:
                await db.delete(txn)

        await db.commit()

        logger.info(f"Removed {count} transactions for PlaidItem {plaid_item_id}")

        return count


# Test data generator for test@test.com
class MockPlaidTransactionGenerator:
    """Generates mock Plaid transaction data for testing."""

    MOCK_MERCHANTS = [
        "Whole Foods Market",
        "Amazon.com",
        "Shell Gas Station",
        "Starbucks",
        "Target",
        "McDonald's",
        "Costco",
        "Home Depot",
        "CVS Pharmacy",
        "Uber",
        "Netflix",
        "Spotify",
        "AT&T",
        "Electric Company",
        "Water Utility",
        "Rent Payment",
    ]

    MOCK_CATEGORIES = [
        ["Groceries", "Supermarkets"],
        ["Shopping", "Online"],
        ["Transportation", "Gas"],
        ["Food and Drink", "Coffee Shop"],
        ["Shopping", "Department Stores"],
        ["Food and Drink", "Fast Food"],
        ["Shopping", "Warehouse Clubs"],
        ["Home Improvement", "Hardware"],
        ["Healthcare", "Pharmacies"],
        ["Transportation", "Rideshare"],
        ["Entertainment", "Streaming"],
        ["Entertainment", "Music"],
        ["Bills", "Phone"],
        ["Bills", "Utilities"],
        ["Bills", "Utilities"],
        ["Bills", "Rent"],
    ]

    @classmethod
    def generate_mock_transactions(
        cls, account_id: str, start_date: date, end_date: date, count: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Generate mock transaction data for testing.

        Args:
            account_id: Plaid account ID
            start_date: Start date for transactions
            end_date: End date for transactions
            count: Number of transactions to generate

        Returns:
            List of transaction dicts in Plaid format
        """
        transactions = []
        date_range = (end_date - start_date).days

        for i in range(count):
            # Random date within range
            days_offset = (i * date_range) // count
            txn_date = start_date + timedelta(days=days_offset)

            # Pick merchant
            merchant_idx = i % len(cls.MOCK_MERCHANTS)
            merchant = cls.MOCK_MERCHANTS[merchant_idx]
            category = cls.MOCK_CATEGORIES[merchant_idx]

            # Generate amount (vary by merchant type)
            if "Rent" in merchant or "Electric" in merchant or "Water" in merchant:
                amount = round(500 + (i * 100) % 1000, 2)
            elif "Gas" in merchant or "Uber" in merchant:
                amount = round(20 + (i * 5) % 50, 2)
            elif "Netflix" in merchant or "Spotify" in merchant:
                amount = round(10 + (i * 2) % 10, 2)
            else:
                amount = round(10 + (i * 10) % 200, 2)

            transaction = {
                "transaction_id": f"mock_txn_{account_id}_{i}_{txn_date.isoformat()}",
                "account_id": account_id,
                "date": txn_date.isoformat(),
                "amount": amount,
                "name": merchant,
                "merchant_name": merchant,
                "category": category,
                "pending": False if i < count - 5 else True,  # Last 5 are pending
            }

            transactions.append(transaction)

        # Sort by date descending (newest first)
        transactions.sort(key=lambda x: x["date"], reverse=True)

        return transactions
