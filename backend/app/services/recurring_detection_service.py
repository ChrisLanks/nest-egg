"""Service for detecting recurring transaction patterns."""

from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional, Dict
from uuid import UUID
from collections import defaultdict

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recurring_transaction import RecurringTransaction, RecurringFrequency
from app.models.transaction import Transaction
from app.models.user import User
from app.utils.datetime_utils import utc_now


class RecurringDetectionService:
    """Service for detecting and managing recurring transactions."""

    @staticmethod
    def _calculate_frequency(
        dates: List[date],
    ) -> Optional[RecurringFrequency]:
        """
        Calculate frequency from a list of dates.

        Returns:
            RecurringFrequency or None if no pattern detected
        """
        if len(dates) < 2:
            return None

        # Calculate gaps between dates
        sorted_dates = sorted(dates)
        gaps = []
        for i in range(len(sorted_dates) - 1):
            gap = (sorted_dates[i + 1] - sorted_dates[i]).days
            gaps.append(gap)

        if not gaps:
            return None

        # Calculate average gap
        avg_gap = sum(gaps) / len(gaps)

        # Determine frequency based on average gap (with tolerance)
        if 5 <= avg_gap <= 9:  # Weekly (7 days ± 2)
            return RecurringFrequency.WEEKLY
        elif 12 <= avg_gap <= 16:  # Biweekly (14 days ± 2)
            return RecurringFrequency.BIWEEKLY
        elif 25 <= avg_gap <= 35:  # Monthly (30 days ± 5)
            return RecurringFrequency.MONTHLY
        elif 85 <= avg_gap <= 95:  # Quarterly (90 days ± 5)
            return RecurringFrequency.QUARTERLY
        elif 350 <= avg_gap <= 380:  # Yearly (365 days ± 15)
            return RecurringFrequency.YEARLY

        return None

    @staticmethod
    def _calculate_confidence_score(
        transaction_count: int,
        amount_variance: Decimal,
        date_consistency: float,
    ) -> Decimal:
        """
        Calculate confidence score for recurring pattern.

        Args:
            transaction_count: Number of transactions in pattern
            amount_variance: Variance in amounts
            date_consistency: How consistent the dates are (0-1)

        Returns:
            Confidence score 0.00-1.00
        """
        # Base score from transaction count
        count_score = min(transaction_count / 5, 1.0)  # Max at 5 transactions

        # Amount consistency (lower variance = higher score)
        amount_score = max(0, 1.0 - float(amount_variance) / 50.0)  # $50 variance = 0 score

        # Date consistency directly
        date_score = date_consistency

        # Weighted average
        confidence = (count_score * 0.4 + amount_score * 0.3 + date_score * 0.3)

        return Decimal(str(round(confidence, 2)))

    @staticmethod
    async def detect_recurring_patterns(
        db: AsyncSession,
        user: User,
        min_occurrences: int = 3,
        lookback_days: int = 180,
    ) -> List[RecurringTransaction]:
        """
        Auto-detect recurring transaction patterns.

        Args:
            db: Database session
            user: Current user
            min_occurrences: Minimum transactions to consider a pattern
            lookback_days: Days to look back for patterns

        Returns:
            List of detected recurring patterns
        """
        # Get recent transactions
        cutoff_date = date.today() - timedelta(days=lookback_days)

        result = await db.execute(
            select(Transaction).where(
                and_(
                    Transaction.organization_id == user.organization_id,
                    Transaction.date >= cutoff_date,
                    Transaction.merchant_name.isnot(None),
                )
            ).order_by(Transaction.date)
        )
        transactions = list(result.scalars().all())

        # Group by merchant name and account
        grouped: Dict[tuple, List[Transaction]] = defaultdict(list)
        for txn in transactions:
            key = (txn.merchant_name, txn.account_id)
            grouped[key].append(txn)

        # Detect patterns
        patterns = []

        for (merchant_name, account_id), txns in grouped.items():
            if len(txns) < min_occurrences:
                continue

            # Calculate frequency
            dates = [txn.date for txn in txns]
            frequency = RecurringDetectionService._calculate_frequency(dates)

            if frequency is None:
                continue

            # Calculate average amount and variance
            amounts = [abs(txn.amount) for txn in txns]
            avg_amount = sum(amounts) / len(amounts)
            amount_variance = max(amounts) - min(amounts)

            # Calculate date consistency
            sorted_dates = sorted(dates)
            gaps = [(sorted_dates[i + 1] - sorted_dates[i]).days for i in range(len(sorted_dates) - 1)]
            avg_gap = sum(gaps) / len(gaps)
            gap_variance = sum(abs(gap - avg_gap) for gap in gaps) / len(gaps)
            date_consistency = max(0, 1.0 - (gap_variance / avg_gap))

            # Calculate confidence score
            confidence_score = RecurringDetectionService._calculate_confidence_score(
                len(txns),
                amount_variance,
                date_consistency,
            )

            # Skip low confidence patterns
            if confidence_score < Decimal("0.60"):
                continue

            # Calculate next expected date
            last_date = sorted_dates[-1]
            if frequency == RecurringFrequency.WEEKLY:
                next_expected = last_date + timedelta(days=7)
            elif frequency == RecurringFrequency.BIWEEKLY:
                next_expected = last_date + timedelta(days=14)
            elif frequency == RecurringFrequency.MONTHLY:
                next_expected = last_date + timedelta(days=30)
            elif frequency == RecurringFrequency.QUARTERLY:
                next_expected = last_date + timedelta(days=90)
            elif frequency == RecurringFrequency.YEARLY:
                next_expected = last_date + timedelta(days=365)
            else:
                next_expected = None

            # Check if pattern already exists
            existing_result = await db.execute(
                select(RecurringTransaction).where(
                    and_(
                        RecurringTransaction.organization_id == user.organization_id,
                        RecurringTransaction.account_id == account_id,
                        RecurringTransaction.merchant_name == merchant_name,
                    )
                )
            )
            existing = existing_result.scalar_one_or_none()

            if existing:
                # Update existing pattern
                existing.frequency = frequency
                existing.average_amount = avg_amount
                existing.amount_variance = amount_variance
                existing.confidence_score = confidence_score
                existing.last_occurrence = sorted_dates[-1]
                existing.next_expected_date = next_expected
                existing.occurrence_count = len(txns)
                existing.updated_at = utc_now()
                patterns.append(existing)
            else:
                # Create new pattern
                pattern = RecurringTransaction(
                    organization_id=user.organization_id,
                    account_id=account_id,
                    merchant_name=merchant_name,
                    frequency=frequency,
                    average_amount=avg_amount,
                    amount_variance=amount_variance,
                    confidence_score=confidence_score,
                    first_occurrence=sorted_dates[0],
                    last_occurrence=sorted_dates[-1],
                    next_expected_date=next_expected,
                    occurrence_count=len(txns),
                    is_user_created=False,
                )
                db.add(pattern)
                patterns.append(pattern)

        await db.commit()

        # Refresh all patterns
        for pattern in patterns:
            await db.refresh(pattern)

        return patterns

    @staticmethod
    async def create_manual_recurring(
        db: AsyncSession,
        user: User,
        merchant_name: str,
        account_id: UUID,
        frequency: RecurringFrequency,
        average_amount: Decimal,
        category_id: Optional[UUID] = None,
        amount_variance: Decimal = Decimal("5.00"),
    ) -> RecurringTransaction:
        """Create a manually defined recurring transaction."""
        pattern = RecurringTransaction(
            organization_id=user.organization_id,
            account_id=account_id,
            merchant_name=merchant_name,
            frequency=frequency,
            average_amount=average_amount,
            amount_variance=amount_variance,
            category_id=category_id,
            is_user_created=True,
            confidence_score=Decimal("1.00"),  # Manual patterns have perfect confidence
            first_occurrence=date.today(),
            occurrence_count=1,
        )

        db.add(pattern)
        await db.commit()
        await db.refresh(pattern)

        return pattern

    @staticmethod
    async def get_recurring_transactions(
        db: AsyncSession,
        user: User,
        is_active: Optional[bool] = None,
    ) -> List[RecurringTransaction]:
        """Get all recurring transaction patterns."""
        query = select(RecurringTransaction).where(
            RecurringTransaction.organization_id == user.organization_id
        )

        if is_active is not None:
            query = query.where(RecurringTransaction.is_active == is_active)

        query = query.order_by(RecurringTransaction.confidence_score.desc())

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def update_recurring_transaction(
        db: AsyncSession,
        recurring_id: UUID,
        user: User,
        **kwargs,
    ) -> Optional[RecurringTransaction]:
        """Update a recurring transaction pattern."""
        result = await db.execute(
            select(RecurringTransaction).where(
                and_(
                    RecurringTransaction.id == recurring_id,
                    RecurringTransaction.organization_id == user.organization_id,
                )
            )
        )
        pattern = result.scalar_one_or_none()

        if not pattern:
            return None

        for key, value in kwargs.items():
            if hasattr(pattern, key):
                setattr(pattern, key, value)

        pattern.updated_at = utc_now()

        await db.commit()
        await db.refresh(pattern)

        return pattern

    @staticmethod
    async def delete_recurring_transaction(
        db: AsyncSession,
        recurring_id: UUID,
        user: User,
    ) -> bool:
        """Delete a recurring transaction pattern."""
        result = await db.execute(
            select(RecurringTransaction).where(
                and_(
                    RecurringTransaction.id == recurring_id,
                    RecurringTransaction.organization_id == user.organization_id,
                )
            )
        )
        pattern = result.scalar_one_or_none()

        if not pattern:
            return False

        await db.delete(pattern)
        await db.commit()

        return True


recurring_detection_service = RecurringDetectionService()
