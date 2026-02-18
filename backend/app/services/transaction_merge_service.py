"""Service for merging duplicate transactions."""

from typing import List, Optional, Tuple
from uuid import UUID
from decimal import Decimal
from datetime import timedelta

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction
from app.models.transaction_merge import TransactionMerge
from app.models.user import User


class TransactionMergeService:
    """Service for detecting and merging duplicate transactions."""

    @staticmethod
    async def find_potential_duplicates(
        db: AsyncSession,
        transaction_id: UUID,
        user: User,
        date_window_days: int = 3,
        amount_tolerance: Decimal = Decimal("0.01"),
    ) -> List[Transaction]:
        """
        Find potential duplicate transactions.

        Args:
            db: Database session
            transaction_id: Transaction to find duplicates for
            user: Current user
            date_window_days: Look within +/- N days
            amount_tolerance: Amount difference tolerance

        Returns:
            List of potential duplicate transactions
        """
        # Get source transaction
        result = await db.execute(
            select(Transaction).where(
                and_(
                    Transaction.id == transaction_id,
                    Transaction.organization_id == user.organization_id,
                )
            )
        )
        source_txn = result.scalar_one_or_none()
        if not source_txn:
            return []

        # Search for similar transactions
        date_min = source_txn.date - timedelta(days=date_window_days)
        date_max = source_txn.date + timedelta(days=date_window_days)
        amount_min = source_txn.amount - amount_tolerance
        amount_max = source_txn.amount + amount_tolerance

        # Build query
        query = select(Transaction).where(
            and_(
                Transaction.organization_id == user.organization_id,
                Transaction.id != transaction_id,
                Transaction.date >= date_min,
                Transaction.date <= date_max,
                Transaction.amount >= amount_min,
                Transaction.amount <= amount_max,
            )
        )

        # Optional: match merchant name if available
        if source_txn.merchant_name:
            query = query.where(Transaction.merchant_name == source_txn.merchant_name)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def merge_transactions(
        db: AsyncSession,
        primary_transaction_id: UUID,
        duplicate_transaction_ids: List[UUID],
        user: User,
        merge_reason: Optional[str] = None,
        is_auto_merged: bool = False,
    ) -> TransactionMerge:
        """
        Merge duplicate transactions into a primary transaction.

        Args:
            db: Database session
            primary_transaction_id: Transaction to keep
            duplicate_transaction_ids: Transactions to merge/delete
            user: Current user
            merge_reason: Optional reason for merge
            is_auto_merged: Whether this was auto-detected

        Returns:
            TransactionMerge record

        Raises:
            ValueError: If transactions not found or validation fails
        """
        # Validate primary transaction exists
        result = await db.execute(
            select(Transaction).where(
                and_(
                    Transaction.id == primary_transaction_id,
                    Transaction.organization_id == user.organization_id,
                )
            )
        )
        primary_txn = result.scalar_one_or_none()
        if not primary_txn:
            raise ValueError("Primary transaction not found")

        # Create merge records and delete duplicates
        merge_records = []
        for dup_id in duplicate_transaction_ids:
            # Validate duplicate exists
            result = await db.execute(
                select(Transaction).where(
                    and_(
                        Transaction.id == dup_id,
                        Transaction.organization_id == user.organization_id,
                    )
                )
            )
            dup_txn = result.scalar_one_or_none()
            if not dup_txn:
                continue

            # Create merge record
            merge_record = TransactionMerge(
                organization_id=user.organization_id,
                primary_transaction_id=primary_transaction_id,
                duplicate_transaction_id=dup_id,
                merge_reason=merge_reason,
                is_auto_merged=is_auto_merged,
                merged_by_user_id=user.id if not is_auto_merged else None,
            )
            db.add(merge_record)
            merge_records.append(merge_record)

            # Delete duplicate transaction
            await db.delete(dup_txn)

        await db.commit()

        # Return first merge record (for simplicity)
        if merge_records:
            await db.refresh(merge_records[0])
            return merge_records[0]

        raise ValueError("No valid duplicates found to merge")

    @staticmethod
    async def get_merge_history(
        db: AsyncSession,
        transaction_id: UUID,
        user: User,
    ) -> List[TransactionMerge]:
        """Get merge history for a transaction."""
        result = await db.execute(
            select(TransactionMerge).where(
                and_(
                    TransactionMerge.primary_transaction_id == transaction_id,
                    TransactionMerge.organization_id == user.organization_id,
                )
            )
        )
        return list(result.scalars().all())

    @staticmethod
    async def auto_detect_and_merge_duplicates(
        db: AsyncSession,
        user: User,
        date_window_days: int = 3,
        amount_tolerance: Decimal = Decimal("0.01"),
        dry_run: bool = True,
    ) -> List[Tuple[Transaction, List[Transaction]]]:
        """
        Auto-detect and optionally merge duplicate transactions.

        Args:
            db: Database session
            user: Current user
            date_window_days: Date window for matching
            amount_tolerance: Amount tolerance for matching
            dry_run: If True, only return matches without merging

        Returns:
            List of (primary_transaction, duplicate_transactions) tuples
        """
        # Get all transactions for organization
        result = await db.execute(
            select(Transaction)
            .where(Transaction.organization_id == user.organization_id)
            .order_by(Transaction.date.desc())
        )
        transactions = list(result.scalars().all())

        # Track processed transactions
        processed = set()
        matches = []

        for txn in transactions:
            if txn.id in processed:
                continue

            # Find duplicates
            duplicates = await TransactionMergeService.find_potential_duplicates(
                db, txn.id, user, date_window_days, amount_tolerance
            )

            # Filter out already processed
            duplicates = [d for d in duplicates if d.id not in processed]

            if duplicates:
                matches.append((txn, duplicates))
                processed.add(txn.id)
                processed.update(d.id for d in duplicates)

                # Auto-merge if not dry run
                if not dry_run:
                    await TransactionMergeService.merge_transactions(
                        db,
                        txn.id,
                        [d.id for d in duplicates],
                        user,
                        merge_reason="Auto-detected duplicate",
                        is_auto_merged=True,
                    )

        return matches


transaction_merge_service = TransactionMergeService()
