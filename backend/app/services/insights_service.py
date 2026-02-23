"""Insights service for generating smart spending insights and anomaly detection."""

from datetime import date, timedelta
from typing import Dict, List
from uuid import UUID

from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction
from app.models.account import Account
from app.utils.datetime_utils import utc_now


class InsightsService:
    """Service for generating spending insights and detecting anomalies."""

    @staticmethod
    async def generate_insights(
        db: AsyncSession, organization_id: UUID, account_ids: List[UUID], max_insights: int = 5
    ) -> List[Dict]:
        """
        Generate prioritized insights for dashboard display.

        Args:
            db: Database session
            organization_id: Organization ID
            account_ids: List of account IDs to analyze
            max_insights: Maximum number of insights to return

        Returns:
            List of insight dictionaries with type, title, message, priority, icon
        """
        insights = []

        # Detect category trends (month-over-month changes)
        trends = await InsightsService._detect_category_trends(db, organization_id, account_ids)
        insights.extend(trends)

        # Detect spending anomalies
        anomalies = await InsightsService._detect_anomalies(db, organization_id, account_ids)
        insights.extend(anomalies)

        # Sort by priority score (high priority first) and limit
        insights.sort(key=lambda x: x["priority_score"], reverse=True)
        return insights[:max_insights]

    @staticmethod
    async def _detect_category_trends(
        db: AsyncSession, organization_id: UUID, account_ids: List[UUID]
    ) -> List[Dict]:
        """
        Calculate month-over-month category spending changes.

        Returns insights for categories with >20% change.
        """
        if not account_ids:
            return []

        # Calculate current month (this month)
        now = utc_now()
        current_month_start = date(now.year, now.month, 1)

        # Calculate previous month
        if now.month == 1:
            previous_month_start = date(now.year - 1, 12, 1)
            previous_month_end = date(now.year - 1, 12, 31)
        else:
            previous_month_start = date(now.year, now.month - 1, 1)
            # Last day of previous month
            previous_month_end = current_month_start - timedelta(days=1)

        current_month_end = date.today()

        # Single query for both months using conditional aggregation
        combined_result = await db.execute(
            select(
                Transaction.category_primary,
                func.sum(
                    case(
                        (
                            and_(
                                Transaction.date >= current_month_start,
                                Transaction.date <= current_month_end,
                            ),
                            func.abs(Transaction.amount),
                        ),
                        else_=0,
                    )
                ).label("current_total"),
                func.sum(
                    case(
                        (
                            and_(
                                Transaction.date >= previous_month_start,
                                Transaction.date <= previous_month_end,
                            ),
                            func.abs(Transaction.amount),
                        ),
                        else_=0,
                    )
                ).label("previous_total"),
            )
            .select_from(Transaction)
            .join(Account)
            .where(
                and_(
                    Transaction.organization_id == organization_id,
                    Account.is_active.is_(True),
                    Account.exclude_from_cash_flow.is_(False),
                    Transaction.is_transfer.is_(False),
                    Transaction.account_id.in_(account_ids),
                    Transaction.date >= previous_month_start,
                    Transaction.date <= current_month_end,
                    Transaction.amount < 0,  # Expenses only
                    Transaction.category_primary.isnot(None),
                )
            )
            .group_by(Transaction.category_primary)
        )
        current_month_data = {}
        previous_month_data = {}
        for row in combined_result:
            if row.current_total:
                current_month_data[row.category_primary] = float(row.current_total)
            if row.previous_total:
                previous_month_data[row.category_primary] = float(row.previous_total)

        # Calculate trends
        insights = []
        all_categories = set(current_month_data.keys()) | set(previous_month_data.keys())

        for category in all_categories:
            current = current_month_data.get(category, 0)
            previous = previous_month_data.get(category, 0)

            # Skip if amounts are too small to be meaningful
            if current < 10 and previous < 10:
                continue

            # Calculate percentage change
            if previous > 0:
                change_pct = ((current - previous) / previous) * 100
            elif current > 0:
                # New category spending
                change_pct = 100
            else:
                continue

            # Only report significant changes (>20%)
            if abs(change_pct) >= 20:
                if change_pct > 0:
                    # Spending increased
                    insights.append(
                        {
                            "type": "category_increase",
                            "title": f"{category} spending up",
                            "message": f"You spent ${current:.0f} on {category} this month, {change_pct:.0f}% more than last month (${previous:.0f})",
                            "category": category,
                            "amount": current,
                            "percentage_change": change_pct,
                            "priority": "high" if change_pct > 50 else "medium",
                            "icon": "📈",
                            "priority_score": change_pct,  # Higher changes = higher priority
                        }
                    )
                else:
                    # Spending decreased (positive trend)
                    insights.append(
                        {
                            "type": "category_decrease",
                            "title": f"{category} spending down",
                            "message": f"Great job! You spent ${current:.0f} on {category} this month, {abs(change_pct):.0f}% less than last month (${previous:.0f})",
                            "category": category,
                            "amount": current,
                            "percentage_change": change_pct,
                            "priority": "low",
                            "icon": "📉",
                            "priority_score": abs(change_pct)
                            * 0.8,  # Lower priority than increases
                        }
                    )

        return insights

    @staticmethod
    async def _detect_anomalies(
        db: AsyncSession, organization_id: UUID, account_ids: List[UUID]
    ) -> List[Dict]:
        """
        Find unusual transactions (>2 standard deviations from merchant average).

        Returns insights for anomalous transactions in the last 30 days.
        """
        if not account_ids:
            return []

        # Look at last 30 days for anomalies
        lookback_date = date.today() - timedelta(days=30)

        # Get all transactions with merchant info
        transactions_result = await db.execute(
            select(
                Transaction.id,
                Transaction.merchant_name,
                Transaction.amount,
                Transaction.date,
                Transaction.category_primary,
            )
            .select_from(Transaction)
            .join(Account)
            .where(
                and_(
                    Transaction.organization_id == organization_id,
                    Account.is_active.is_(True),
                    Account.exclude_from_cash_flow.is_(False),
                    Transaction.is_transfer.is_(False),
                    Transaction.account_id.in_(account_ids),
                    Transaction.date >= lookback_date,
                    Transaction.amount < 0,  # Expenses only
                    Transaction.merchant_name.isnot(None),
                )
            )
        )
        transactions = transactions_result.all()

        # Group by merchant and calculate statistics
        merchant_data: Dict[str, List[float]] = {}
        for txn in transactions:
            merchant = txn.merchant_name
            amount = abs(float(txn.amount))
            if merchant not in merchant_data:
                merchant_data[merchant] = []
            merchant_data[merchant].append(amount)

        # Find anomalies using leave-one-out: exclude the candidate from its own stats
        insights = []
        for txn in transactions:
            merchant = txn.merchant_name
            amount = abs(float(txn.amount))
            merchant_transactions = merchant_data[merchant]

            # Need at least 4 transactions (3 others + the candidate) to establish a pattern
            if len(merchant_transactions) < 4:
                continue

            # Leave-one-out: compute stats from all OTHER transactions for this merchant
            others = [x for x in merchant_transactions if x != amount]
            if not others:
                others = merchant_transactions[:-1]  # fallback for duplicates

            mean = sum(others) / len(others)
            variance = sum((x - mean) ** 2 for x in others) / len(others)
            std_dev = variance**0.5

            # Check if this transaction is >2 standard deviations from mean
            if std_dev > 0:
                z_score = (amount - mean) / std_dev
                if z_score > 2:  # More than 2 std devs above mean
                    insights.append(
                        {
                            "type": "anomaly",
                            "title": f"Unusual {merchant} charge",
                            "message": f"You spent ${amount:.0f} at {merchant}, which is unusually high compared to your typical ${mean:.0f}",
                            "category": txn.category_primary,
                            "amount": amount,
                            "priority": "high" if z_score > 3 else "medium",
                            "icon": "⚠️",
                            "priority_score": z_score * 30,  # z_score of 3 = priority 90
                        }
                    )

        return insights
