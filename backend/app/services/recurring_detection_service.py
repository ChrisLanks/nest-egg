"""Service for detecting recurring transaction patterns."""

from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional, Dict
from uuid import UUID
from collections import defaultdict

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.recurring_transaction import RecurringTransaction, RecurringFrequency
from app.models.transaction import Transaction, Label, TransactionLabel
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
        confidence = count_score * 0.4 + amount_score * 0.3 + date_score * 0.3

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

        # Fetch only needed columns, not full ORM objects
        result = await db.execute(
            select(
                Transaction.merchant_name,
                Transaction.account_id,
                Transaction.date,
                Transaction.amount,
                Transaction.id,
            )
            .where(
                and_(
                    Transaction.organization_id == user.organization_id,
                    Transaction.date >= cutoff_date,
                    Transaction.merchant_name.isnot(None),
                )
            )
            .order_by(Transaction.merchant_name, Transaction.account_id, Transaction.date)
        )
        rows = result.all()

        # Group by merchant name and account
        grouped: Dict[tuple, List] = defaultdict(list)
        for row in rows:
            key = (row.merchant_name, row.account_id)
            grouped[key].append(row)

        # Detect patterns
        patterns = []

        for (merchant_name, account_id), txns in grouped.items():
            if len(txns) < min_occurrences:
                continue

            # Calculate frequency
            dates = [row.date for row in txns]
            frequency = RecurringDetectionService._calculate_frequency(dates)

            if frequency is None:
                continue

            # Calculate average amount and variance
            amounts = [abs(row.amount) for row in txns]
            avg_amount = sum(amounts) / len(amounts)
            amount_variance = max(amounts) - min(amounts)

            # Calculate date consistency
            sorted_dates = sorted(dates)
            gaps = [
                (sorted_dates[i + 1] - sorted_dates[i]).days for i in range(len(sorted_dates) - 1)
            ]
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
                existing.is_no_longer_found = False  # Re-found — clear the flag
                # Auto-reactivate if deactivated but transactions are still occurring
                if not existing.is_active:
                    existing.is_active = True
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

        # Ensure "Recurring Bill" label exists and label all matched transactions
        recurring_bill_label = await RecurringDetectionService.ensure_recurring_bill_label(
            db, user.organization_id
        )
        for pattern in patterns:
            if pattern.label_id is None:
                pattern.label_id = recurring_bill_label.id
            await RecurringDetectionService.apply_label_to_matching_transactions(
                db,
                organization_id=user.organization_id,
                merchant_name=pattern.merchant_name,
                account_id=pattern.account_id,
                label_id=pattern.label_id,
            )

        # Mark auto-detected patterns not seen in this run as "no longer found"
        detected_keys = {(merchant_name, str(account_id)) for (merchant_name, account_id) in grouped.keys()}
        all_auto_result = await db.execute(
            select(RecurringTransaction).where(
                and_(
                    RecurringTransaction.organization_id == user.organization_id,
                    RecurringTransaction.is_user_created.is_(False),
                    RecurringTransaction.is_archived.is_(False),
                )
            )
        )
        for auto_pattern in all_auto_result.scalars().all():
            key = (auto_pattern.merchant_name, str(auto_pattern.account_id))
            if key not in detected_keys:
                auto_pattern.is_no_longer_found = True
                auto_pattern.updated_at = utc_now()

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
        is_bill: bool = False,
        reminder_days_before: int = 3,
        label_id: Optional[UUID] = None,
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
            is_bill=is_bill,
            reminder_days_before=reminder_days_before,
            label_id=label_id,
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

    @staticmethod
    async def get_upcoming_bills(
        db: AsyncSession,
        user: User,
        days_ahead: int = 30,
    ) -> List[Dict]:
        """
        Get upcoming bills that are due within the specified time window.

        Args:
            db: Database session
            user: Current user
            days_ahead: Days to look ahead for upcoming bills

        Returns:
            List of upcoming bills with due dates and details
        """
        today = date.today()
        future_date = today + timedelta(days=days_ahead)

        # Query for recurring transactions marked as bills
        result = await db.execute(
            select(RecurringTransaction)
            .where(
                and_(
                    RecurringTransaction.organization_id == user.organization_id,
                    RecurringTransaction.is_bill.is_(True),
                    RecurringTransaction.is_active.is_(True),
                    RecurringTransaction.next_expected_date.isnot(None),
                    RecurringTransaction.next_expected_date <= future_date,
                )
            )
            .order_by(RecurringTransaction.next_expected_date)
        )
        bills = list(result.scalars().all())

        # Format response
        upcoming_bills = []
        for bill in bills:
            days_until_due = (bill.next_expected_date - today).days

            # Check if we should send a reminder (based on reminder_days_before)
            should_remind = days_until_due <= bill.reminder_days_before

            if should_remind or days_until_due < 0:  # Include overdue bills
                upcoming_bills.append(
                    {
                        "recurring_transaction_id": bill.id,
                        "merchant_name": bill.merchant_name,
                        "average_amount": bill.average_amount,
                        "next_expected_date": bill.next_expected_date,
                        "days_until_due": days_until_due,
                        "is_overdue": days_until_due < 0,
                        "account_id": bill.account_id,
                        "category_id": bill.category_id,
                    }
                )

        return upcoming_bills

    @staticmethod
    async def get_subscriptions(
        db: AsyncSession,
        organization_id: UUID,
        user_id: Optional[UUID] = None,
        is_active: bool = True,
    ) -> List[RecurringTransaction]:
        """
        Get subscription-like recurring transactions.
        Filters for monthly/yearly frequency with high confidence (>0.70).

        Args:
            db: Database session
            organization_id: Organization ID
            user_id: Optional user ID for filtering
            is_active: Filter for active subscriptions only

        Returns:
            List of subscription-like recurring transactions
        """
        query = select(RecurringTransaction).where(
            and_(
                RecurringTransaction.organization_id == organization_id,
                RecurringTransaction.frequency.in_(
                    [RecurringFrequency.MONTHLY, RecurringFrequency.YEARLY]
                ),
                RecurringTransaction.confidence_score >= Decimal("0.70"),
                RecurringTransaction.is_active == is_active,
            )
        )

        # Apply user filter if provided
        if user_id:
            query = query.join(Account).where(Account.user_id == user_id)

        query = query.order_by(RecurringTransaction.average_amount.desc())

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_subscription_summary(
        db: AsyncSession, organization_id: UUID, user_id: Optional[UUID] = None
    ) -> Dict:
        """
        Calculate total monthly cost of subscriptions.

        Args:
            db: Database session
            organization_id: Organization ID
            user_id: Optional user ID for filtering

        Returns:
            Dict with total_count, monthly_cost, yearly_cost
        """
        subscriptions = await RecurringDetectionService.get_subscriptions(
            db, organization_id, user_id
        )

        monthly_total = Decimal(0)
        for sub in subscriptions:
            if sub.frequency == RecurringFrequency.MONTHLY:
                monthly_total += abs(sub.average_amount)
            elif sub.frequency == RecurringFrequency.YEARLY:
                monthly_total += abs(sub.average_amount) / 12

        return {
            "total_count": len(subscriptions),
            "monthly_cost": float(monthly_total),
            "yearly_cost": float(monthly_total * 12),
        }

    # ── Label helpers ────────────────────────────────────────────────────────

    @staticmethod
    async def ensure_recurring_bill_label(db: AsyncSession, organization_id: UUID) -> Label:
        """
        Return the org's 'Recurring Bill' label, creating it if it doesn't exist.
        """
        result = await db.execute(
            select(Label).where(
                and_(
                    Label.organization_id == organization_id,
                    Label.name == "Recurring Bill",
                )
            )
        )
        label = result.scalar_one_or_none()
        if label is None:
            label = Label(
                organization_id=organization_id,
                name="Recurring Bill",
                color="#3182CE",  # Chakra blue.500
                is_system=False,
            )
            db.add(label)
            await db.flush()  # get the id without committing
        return label

    @staticmethod
    async def apply_label_to_matching_transactions(
        db: AsyncSession,
        organization_id: UUID,
        merchant_name: str,
        account_id: UUID,
        label_id: UUID,
    ) -> int:
        """
        Apply a label to all transactions matching the given merchant + account.
        Skips transactions that already have the label.
        Returns the count of newly labelled transactions.
        """
        # Fetch only IDs, not full ORM objects
        result = await db.execute(
            select(Transaction.id).where(
                and_(
                    Transaction.organization_id == organization_id,
                    Transaction.account_id == account_id,
                    Transaction.merchant_name == merchant_name,
                )
            )
        )
        transaction_ids = [row[0] for row in result.all()]

        # Collect existing labelled transaction ids to avoid duplicates
        if not transaction_ids:
            return 0

        existing_result = await db.execute(
            select(TransactionLabel.transaction_id).where(
                and_(
                    TransactionLabel.transaction_id.in_(transaction_ids),
                    TransactionLabel.label_id == label_id,
                )
            )
        )
        already_labelled = set(existing_result.scalars().all())

        count = 0
        for txn_id in transaction_ids:
            if txn_id not in already_labelled:
                db.add(TransactionLabel(
                    transaction_id=txn_id,
                    label_id=label_id,
                ))
                count += 1

        return count

    @staticmethod
    async def count_matching_transactions(
        db: AsyncSession,
        organization_id: UUID,
        merchant_name: str,
        account_id: UUID,
    ) -> int:
        """Count transactions matching the given merchant + account (for UI preview)."""
        result = await db.execute(
            select(func.count(Transaction.id)).where(
                and_(
                    Transaction.organization_id == organization_id,
                    Transaction.account_id == account_id,
                    Transaction.merchant_name == merchant_name,
                )
            )
        )
        return result.scalar() or 0


recurring_detection_service = RecurringDetectionService()
