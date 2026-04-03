"""Service for managing transaction splits."""

from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_, func
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
        if len(splits_data) > 50:
            raise ValueError("Maximum 50 splits per transaction")

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
                assigned_user_id=split_data.get("assigned_user_id"),
            )
            db.add(split)
            splits.append(split)

        # Mark transaction as split
        transaction.is_split = True
        transaction.updated_at = utc_now()

        await db.commit()

        # Reload all splits in a single query instead of N individual refreshes
        split_ids = [s.id for s in splits]
        result = await db.execute(
            select(TransactionSplit).where(TransactionSplit.id.in_(split_ids))
        )
        return list(result.scalars().all())

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
        assigned_user_id: Optional[UUID] = None,
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
        if assigned_user_id is not None:
            split.assigned_user_id = assigned_user_id

        split.updated_at = utc_now()

        # If the amount was changed, validate that all splits still sum to
        # the parent transaction amount (same check used in create_splits)
        if amount is not None:
            # Flush so the updated amount is visible to the sum query
            await db.flush()

            all_splits_result = await db.execute(
                select(func.sum(TransactionSplit.amount)).where(
                    TransactionSplit.parent_transaction_id == split.parent_transaction_id
                )
            )
            total = all_splits_result.scalar() or Decimal("0")

            parent_result = await db.execute(
                select(Transaction.amount).where(Transaction.id == split.parent_transaction_id)
            )
            parent_amount = parent_result.scalar()

            if abs(Decimal(str(total)) - abs(Decimal(str(parent_amount)))) > Decimal("0.01"):
                await db.rollback()
                raise ValueError(
                    f"Split amounts ({total}) must equal transaction amount ({abs(parent_amount)})"
                )

        await db.commit()
        await db.refresh(split)

        return split

    @staticmethod
    async def get_member_balances(
        db: AsyncSession,
        organization_id: UUID,
        since_date=None,
    ) -> List[dict]:
        """
        Return per-member expense totals from assigned splits.

        Each entry: {member_id, member_name, total_assigned, net_owed}
        net_owed = total_assigned - their_fair_share (fair share = total / member_count).
        Positive net_owed means the member spent more than their share (household owes them).
        Negative net_owed means they underpaid (they owe the household).
        """
        conditions = [
            TransactionSplit.organization_id == organization_id,
            TransactionSplit.assigned_user_id.isnot(None),
        ]
        if since_date is not None:
            conditions.append(
                TransactionSplit.parent_transaction_id.in_(
                    select(Transaction.id).where(
                        Transaction.organization_id == organization_id,
                        Transaction.date >= since_date,
                    )
                )
            )

        # Sum splits per assigned member
        agg_result = await db.execute(
            select(
                TransactionSplit.assigned_user_id,
                func.sum(TransactionSplit.amount).label("total"),
            )
            .where(and_(*conditions))
            .group_by(TransactionSplit.assigned_user_id)
        )
        rows = agg_result.all()

        if not rows:
            return []

        user_ids = [r.assigned_user_id for r in rows]
        users_result = await db.execute(
            select(User.id, User.display_name, User.email).where(
                User.id.in_(user_ids)
            )
        )
        users_map = {u.id: (u.display_name or u.email or str(u.id)) for u in users_result.all()}

        total_all = sum(float(r.total) for r in rows)
        member_count = len(rows)
        fair_share = total_all / member_count if member_count else 0.0

        return [
            {
                "member_id": r.assigned_user_id,
                "member_name": users_map.get(r.assigned_user_id, str(r.assigned_user_id)),
                "total_assigned": float(r.total),
                "net_owed": float(r.total) - fair_share,
            }
            for r in rows
        ]


transaction_split_service = TransactionSplitService()
