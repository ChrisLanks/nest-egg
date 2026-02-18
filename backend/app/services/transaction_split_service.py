"""Service for managing transaction splits."""

from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction, TransactionSplit
from app.models.user import User
from app.utils.datetime_utils import utc_now


class TransactionSplitService:
    """Service for creating and managing transaction splits."""

    @staticmethod
    async def create_splits(
        db: AsyncSession,
        transaction_id: UUID,
        splits_data: List[dict],
        user: User,
    ) -> List[TransactionSplit]:
        """
        Create multiple splits for a transaction.

        Args:
            db: Database session
            transaction_id: Transaction to split
            splits_data: List of dicts with amount, description, category_id
            user: Current user

        Returns:
            List of created splits

        Raises:
            ValueError: If splits don't match transaction amount
        """
        # Get transaction
        result = await db.execute(
            select(Transaction).where(
                and_(
                    Transaction.id == transaction_id,
                    Transaction.organization_id == user.organization_id,
                )
            )
        )
        transaction = result.scalar_one_or_none()
        if not transaction:
            raise ValueError("Transaction not found")

        # Validate split amounts sum to transaction amount
        total_split = sum(Decimal(str(split["amount"])) for split in splits_data)
        if abs(total_split - abs(transaction.amount)) > Decimal("0.01"):
            raise ValueError(
                f"Split amounts ({total_split}) must equal transaction amount ({abs(transaction.amount)})"
            )

        # Delete existing splits if any
        await db.execute(
            select(TransactionSplit).where(TransactionSplit.parent_transaction_id == transaction_id)
        )
        await db.execute(
            TransactionSplit.__table__.delete().where(
                TransactionSplit.parent_transaction_id == transaction_id
            )
        )

        # Create new splits
        splits = []
        for split_data in splits_data:
            split = TransactionSplit(
                parent_transaction_id=transaction_id,
                organization_id=user.organization_id,
                amount=Decimal(str(split_data["amount"])),
                description=split_data.get("description"),
                category_id=split_data.get("category_id"),
            )
            db.add(split)
            splits.append(split)

        # Mark transaction as split
        transaction.is_split = True
        transaction.updated_at = utc_now()

        await db.commit()

        # Refresh all splits
        for split in splits:
            await db.refresh(split)

        return splits

    @staticmethod
    async def get_transaction_splits(
        db: AsyncSession,
        transaction_id: UUID,
        user: User,
    ) -> List[TransactionSplit]:
        """Get all splits for a transaction."""
        result = await db.execute(
            select(TransactionSplit).where(
                and_(
                    TransactionSplit.parent_transaction_id == transaction_id,
                    TransactionSplit.organization_id == user.organization_id,
                )
            )
        )
        return list(result.scalars().all())

    @staticmethod
    async def delete_splits(
        db: AsyncSession,
        transaction_id: UUID,
        user: User,
    ) -> bool:
        """
        Delete all splits for a transaction and mark it as not split.

        Returns:
            True if splits were deleted
        """
        # Get transaction
        result = await db.execute(
            select(Transaction).where(
                and_(
                    Transaction.id == transaction_id,
                    Transaction.organization_id == user.organization_id,
                )
            )
        )
        transaction = result.scalar_one_or_none()
        if not transaction:
            return False

        # Delete splits
        await db.execute(
            TransactionSplit.__table__.delete().where(
                TransactionSplit.parent_transaction_id == transaction_id
            )
        )

        # Mark transaction as not split
        transaction.is_split = False
        transaction.updated_at = utc_now()

        await db.commit()
        return True

    @staticmethod
    async def update_split(
        db: AsyncSession,
        split_id: UUID,
        amount: Optional[Decimal] = None,
        description: Optional[str] = None,
        category_id: Optional[UUID] = None,
        user: User = None,
    ) -> Optional[TransactionSplit]:
        """Update a single split."""
        result = await db.execute(
            select(TransactionSplit).where(
                and_(
                    TransactionSplit.id == split_id,
                    TransactionSplit.organization_id == user.organization_id,
                )
            )
        )
        split = result.scalar_one_or_none()
        if not split:
            return None

        if amount is not None:
            split.amount = amount
        if description is not None:
            split.description = description
        if category_id is not None:
            split.category_id = category_id

        split.updated_at = utc_now()

        await db.commit()
        await db.refresh(split)

        return split


transaction_split_service = TransactionSplitService()
