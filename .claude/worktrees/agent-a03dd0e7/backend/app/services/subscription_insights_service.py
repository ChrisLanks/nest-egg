"""Service for subscription/bill insights.

Includes year-over-year comparison and price increase detection.
"""

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.recurring_transaction import RecurringFrequency, RecurringTransaction
from app.models.transaction import Category, Transaction
from app.utils.datetime_utils import utc_now

# Multiplier to annualize a single occurrence based on frequency
FREQUENCY_TO_ANNUAL: Dict[RecurringFrequency, int] = {
    RecurringFrequency.WEEKLY: 52,
    RecurringFrequency.BIWEEKLY: 26,
    RecurringFrequency.MONTHLY: 12,
    RecurringFrequency.QUARTERLY: 4,
    RecurringFrequency.YEARLY: 1,
    RecurringFrequency.ON_DEMAND: 0,  # Cannot annualize irregular
}

FREQUENCY_TO_MONTHLY: Dict[RecurringFrequency, Decimal] = {
    RecurringFrequency.WEEKLY: Decimal("52") / Decimal("12"),
    RecurringFrequency.BIWEEKLY: Decimal("26") / Decimal("12"),
    RecurringFrequency.MONTHLY: Decimal("1"),
    RecurringFrequency.QUARTERLY: Decimal("1") / Decimal("3"),
    RecurringFrequency.YEARLY: Decimal("1") / Decimal("12"),
    RecurringFrequency.ON_DEMAND: Decimal("0"),
}

# Minimum percentage change to flag as a price increase/decrease
PRICE_CHANGE_THRESHOLD_PCT = Decimal("5.00")


class SubscriptionInsightsService:
    """Analyse recurring transactions for cost insights and price change detection."""

    @staticmethod
    def _annualize(amount: Decimal, frequency: RecurringFrequency) -> Decimal:
        """Return projected annual cost for a single-occurrence amount."""
        multiplier = FREQUENCY_TO_ANNUAL.get(frequency, 0)
        return (abs(amount) * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def _monthlyize(amount: Decimal, frequency: RecurringFrequency) -> Decimal:
        """Return projected monthly cost for a single-occurrence amount."""
        multiplier = FREQUENCY_TO_MONTHLY.get(frequency, Decimal("0"))
        return (abs(amount) * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    async def detect_price_changes(
        db: AsyncSession,
        organization_id: UUID,
    ) -> List[RecurringTransaction]:
        """
        For each active recurring transaction, compare the current average_amount
        against the average amount of the same merchant's transactions from
        approximately 12 months ago.  Populate the new year-over-year fields
        when the change exceeds the threshold.

        Returns the list of recurring transactions that were updated.
        """
        # Fetch all active recurring transactions for the org
        result = await db.execute(
            select(RecurringTransaction).where(
                and_(
                    RecurringTransaction.organization_id == organization_id,
                    RecurringTransaction.is_active.is_(True),
                )
            )
        )
        recurring_txns = list(result.scalars().all())

        updated: List[RecurringTransaction] = []
        now = utc_now()
        today = date.today()

        # Define the "previous year" window: 10-14 months ago to allow variance
        prev_start = today - timedelta(days=14 * 30)  # ~14 months
        prev_end = today - timedelta(days=10 * 30)  # ~10 months

        for rt in recurring_txns:
            # Query historical transactions for this merchant + account in the previous window
            hist_result = await db.execute(
                select(func.avg(func.abs(Transaction.amount))).where(
                    and_(
                        Transaction.organization_id == organization_id,
                        Transaction.account_id == rt.account_id,
                        Transaction.merchant_name == rt.merchant_name,
                        Transaction.date >= prev_start,
                        Transaction.date <= prev_end,
                    )
                )
            )
            prev_avg = hist_result.scalar()

            # Always update annual_cost based on current average_amount
            rt.annual_cost = SubscriptionInsightsService._annualize(rt.average_amount, rt.frequency)

            if prev_avg is not None and prev_avg > 0:
                prev_avg_dec = Decimal(str(prev_avg)).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                current = abs(rt.average_amount)

                if prev_avg_dec != Decimal("0"):
                    change_pct = (
                        (current - prev_avg_dec) / prev_avg_dec * Decimal("100")
                    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

                    if abs(change_pct) >= PRICE_CHANGE_THRESHOLD_PCT:
                        rt.previous_amount = prev_avg_dec
                        rt.amount_change_pct = change_pct
                        rt.amount_change_detected_at = now
                    else:
                        # Below threshold -- clear stale detection data
                        rt.previous_amount = prev_avg_dec
                        rt.amount_change_pct = change_pct
                        rt.amount_change_detected_at = None
                else:
                    rt.previous_amount = None
                    rt.amount_change_pct = None
                    rt.amount_change_detected_at = None

                updated.append(rt)
            else:
                # No historical data -- clear fields but still count as processed
                rt.previous_amount = None
                rt.amount_change_pct = None
                rt.amount_change_detected_at = None

            rt.updated_at = now

        await db.commit()

        # Refresh updated records
        for rt in updated:
            await db.refresh(rt)

        return updated

    @staticmethod
    async def _get_active_subscriptions(
        db: AsyncSession,
        organization_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> List[RecurringTransaction]:
        """Internal helper: fetch active subscriptions, optionally filtered by user."""
        query = select(RecurringTransaction).where(
            and_(
                RecurringTransaction.organization_id == organization_id,
                RecurringTransaction.is_active.is_(True),
                RecurringTransaction.frequency.in_(
                    [
                        RecurringFrequency.WEEKLY,
                        RecurringFrequency.BIWEEKLY,
                        RecurringFrequency.MONTHLY,
                        RecurringFrequency.QUARTERLY,
                        RecurringFrequency.YEARLY,
                    ]
                ),
            )
        )

        if user_id:
            query = query.join(Account).where(Account.user_id == user_id)

        query = query.order_by(RecurringTransaction.average_amount.desc())

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_annual_subscription_total(
        db: AsyncSession,
        organization_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> Decimal:
        """Sum of all recurring transactions annualized."""
        subs = await SubscriptionInsightsService._get_active_subscriptions(
            db, organization_id, user_id
        )

        total = Decimal("0")
        for sub in subs:
            total += SubscriptionInsightsService._annualize(sub.average_amount, sub.frequency)
        return total

    @staticmethod
    async def get_year_over_year_comparison(
        db: AsyncSession,
        organization_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> List[Dict]:
        """
        Return a list of subscriptions with current vs previous year amounts.
        Each item includes merchant_name, current_amount, previous_amount,
        change_pct, frequency, and annual_cost.
        """
        subs = await SubscriptionInsightsService._get_active_subscriptions(
            db, organization_id, user_id
        )

        comparisons = []
        for sub in subs:
            comparisons.append(
                {
                    "id": str(sub.id),
                    "merchant_name": sub.merchant_name,
                    "frequency": sub.frequency.value,
                    "current_amount": float(abs(sub.average_amount)),
                    "previous_amount": float(sub.previous_amount) if sub.previous_amount else None,
                    "amount_change_pct": float(sub.amount_change_pct)
                    if sub.amount_change_pct is not None
                    else None,
                    "annual_cost": float(sub.annual_cost)
                    if sub.annual_cost
                    else float(
                        SubscriptionInsightsService._annualize(sub.average_amount, sub.frequency)
                    ),
                    "account_id": str(sub.account_id),
                }
            )

        return comparisons

    @staticmethod
    async def get_price_increases(
        db: AsyncSession,
        organization_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> List[Dict]:
        """Return only subscriptions with detected price
        increases (positive change >= threshold).
        """
        query = select(RecurringTransaction).where(
            and_(
                RecurringTransaction.organization_id == organization_id,
                RecurringTransaction.is_active.is_(True),
                RecurringTransaction.amount_change_pct >= PRICE_CHANGE_THRESHOLD_PCT,
                RecurringTransaction.amount_change_detected_at.isnot(None),
            )
        )

        if user_id:
            query = query.join(Account).where(Account.user_id == user_id)

        query = query.order_by(RecurringTransaction.amount_change_pct.desc())

        result = await db.execute(query)
        subs = list(result.scalars().all())

        increases = []
        for sub in subs:
            increases.append(
                {
                    "id": str(sub.id),
                    "merchant_name": sub.merchant_name,
                    "frequency": sub.frequency.value,
                    "current_amount": float(abs(sub.average_amount)),
                    "previous_amount": float(sub.previous_amount) if sub.previous_amount else None,
                    "amount_change_pct": float(sub.amount_change_pct),
                    "amount_change_detected_at": sub.amount_change_detected_at.isoformat()
                    if sub.amount_change_detected_at
                    else None,
                    "annual_cost": float(sub.annual_cost)
                    if sub.annual_cost
                    else float(
                        SubscriptionInsightsService._annualize(sub.average_amount, sub.frequency)
                    ),
                    "annual_increase": float(
                        SubscriptionInsightsService._annualize(sub.average_amount, sub.frequency)
                        - SubscriptionInsightsService._annualize(sub.previous_amount, sub.frequency)
                    )
                    if sub.previous_amount
                    else None,
                    "account_id": str(sub.account_id),
                }
            )

        return increases

    @staticmethod
    async def get_subscription_summary(
        db: AsyncSession,
        organization_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> Dict:
        """
        Comprehensive subscription summary:
        - total monthly / annual cost
        - count of active subscriptions
        - top categories (by annual spend)
        - price change summary
        """
        subs = await SubscriptionInsightsService._get_active_subscriptions(
            db, organization_id, user_id
        )

        monthly_total = Decimal("0")
        annual_total = Decimal("0")
        price_increases_count = 0
        price_decreases_count = 0
        total_annual_increase = Decimal("0")

        # Track spending by category
        category_spend: Dict[Optional[str], Decimal] = {}

        # Pre-fetch category names for all category_ids in one query
        cat_ids = {sub.category_id for sub in subs if sub.category_id}
        cat_names: Dict[str, str] = {}
        if cat_ids:
            cat_result = await db.execute(
                select(Category.id, Category.name).where(Category.id.in_(cat_ids))
            )
            for row in cat_result.all():
                cat_names[str(row[0])] = row[1]

        for sub in subs:
            monthly_cost = SubscriptionInsightsService._monthlyize(
                sub.average_amount, sub.frequency
            )
            annual_cost = SubscriptionInsightsService._annualize(sub.average_amount, sub.frequency)
            monthly_total += monthly_cost
            annual_total += annual_cost

            # Track price changes
            if sub.amount_change_pct is not None and sub.amount_change_detected_at is not None:
                if sub.amount_change_pct >= PRICE_CHANGE_THRESHOLD_PCT:
                    price_increases_count += 1
                    if sub.previous_amount:
                        prev_annual = SubscriptionInsightsService._annualize(
                            sub.previous_amount, sub.frequency
                        )
                        total_annual_increase += annual_cost - prev_annual
                elif sub.amount_change_pct <= -PRICE_CHANGE_THRESHOLD_PCT:
                    price_decreases_count += 1

            # Accumulate by category
            cat_key = (
                cat_names.get(str(sub.category_id), "Uncategorized")
                if sub.category_id
                else "Uncategorized"
            )
            category_spend[cat_key] = category_spend.get(cat_key, Decimal("0")) + annual_cost

        # Build top categories list sorted by spend descending
        top_categories = sorted(
            [
                {"category": name, "annual_cost": float(spend)}
                for name, spend in category_spend.items()
            ],
            key=lambda x: x["annual_cost"],
            reverse=True,
        )

        return {
            "total_count": len(subs),
            "monthly_cost": float(monthly_total),
            "annual_cost": float(annual_total),
            "price_increases_count": price_increases_count,
            "price_decreases_count": price_decreases_count,
            "total_annual_increase": float(total_annual_increase),
            "top_categories": top_categories,
        }


subscription_insights_service = SubscriptionInsightsService()
