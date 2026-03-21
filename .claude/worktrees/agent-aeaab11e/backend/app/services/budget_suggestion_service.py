"""Service for generating smart budget suggestions based on spending history."""

import math
from datetime import date, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.budget import Budget, BudgetPeriod
from app.models.transaction import Category, Transaction
from app.models.user import User


def _round_up_nice(amount: float) -> float:
    """Round a dollar amount up to a 'nice' budget number.

    Examples: 247 → 250, 83 → 100, 1247 → 1300, 14 → 15, 510 → 550
    """
    if amount <= 0:
        return 0
    if amount < 10:
        return math.ceil(amount)
    if amount < 25:
        return math.ceil(amount / 5) * 5
    if amount < 100:
        return math.ceil(amount / 10) * 10
    if amount < 500:
        return math.ceil(amount / 25) * 25
    if amount < 1000:
        return math.ceil(amount / 50) * 50
    return math.ceil(amount / 100) * 100


def _suggest_period(
    avg_monthly: float,
    month_count: int,
    spending_by_month: dict[str, float],
) -> BudgetPeriod:
    """Suggest the best budget period based on spending pattern.

    Looks at how many months have spending to detect infrequent expenses
    (e.g., car insurance every 6 months, annual subscriptions).
    """
    if month_count == 0:
        return BudgetPeriod.MONTHLY

    months_with_spending = sum(1 for v in spending_by_month.values() if v > 0)
    ratio = months_with_spending / month_count

    # If spending appears in < 25% of months, it's likely annual
    if ratio <= 0.25 and month_count >= 6:
        return BudgetPeriod.YEARLY
    # If spending appears in 25-50% of months, suggest semi-annual
    if ratio <= 0.50 and month_count >= 4:
        return BudgetPeriod.SEMI_ANNUAL
    # If spending appears in 50-70% of months, quarterly
    if ratio <= 0.70 and month_count >= 3:
        return BudgetPeriod.QUARTERLY

    return BudgetPeriod.MONTHLY


class BudgetSuggestionService:
    """Generates budget suggestions from spending history."""

    @staticmethod
    async def get_suggestions(
        db: AsyncSession,
        user: User,
        months: int = 6,
        max_suggestions: int = 8,
    ) -> List[dict]:
        """Analyze spending history and suggest budgets.

        Args:
            db: Database session
            user: Current user
            months: How many months of history to analyze (default 6)
            max_suggestions: Maximum number of suggestions to return

        Returns:
            List of suggestion dicts with: category_name, category_id,
            suggested_amount, suggested_period, avg_monthly_spend,
            total_spend, month_count, transaction_count
        """
        lookback = date.today() - timedelta(days=months * 31)

        # Get account IDs for this org
        acct_result = await db.execute(
            select(Account.id).where(
                Account.organization_id == user.organization_id,
            )
        )
        account_ids = [row[0] for row in acct_result.all()]
        if not account_ids:
            return []

        # Get existing budget category IDs to exclude
        budget_result = await db.execute(
            select(Budget.category_id).where(
                and_(
                    Budget.organization_id == user.organization_id,
                    Budget.is_active.is_(True),
                    Budget.category_id.isnot(None),
                )
            )
        )
        existing_category_ids = {row[0] for row in budget_result.all()}

        # Aggregate spending by category (custom categories)
        custom_cat_query = (
            select(
                Category.id,
                Category.name,
                func.abs(func.sum(Transaction.amount)).label("total"),
                func.count(Transaction.id).label("txn_count"),
                func.min(Transaction.date).label("first_date"),
                func.max(Transaction.date).label("last_date"),
            )
            .join(Category, Transaction.category_id == Category.id)
            .where(
                and_(
                    Transaction.account_id.in_(account_ids),
                    Transaction.amount < 0,  # expenses only
                    Transaction.date >= lookback,
                    Category.parent_category_id.is_(None),  # top-level only
                )
            )
            .group_by(Category.id, Category.name)
            .having(func.count(Transaction.id) >= 3)  # at least 3 transactions
            .order_by(func.abs(func.sum(Transaction.amount)).desc())
        )
        custom_results = (await db.execute(custom_cat_query)).all()

        # Also get spending by category_primary (provider categories without custom mapping)
        provider_cat_query = (
            select(
                func.lower(Transaction.category_primary).label("cat_name"),
                func.abs(func.sum(Transaction.amount)).label("total"),
                func.count(Transaction.id).label("txn_count"),
                func.min(Transaction.date).label("first_date"),
                func.max(Transaction.date).label("last_date"),
            )
            .where(
                and_(
                    Transaction.account_id.in_(account_ids),
                    Transaction.amount < 0,
                    Transaction.date >= lookback,
                    Transaction.category_id.is_(None),
                    Transaction.category_primary.isnot(None),
                    Transaction.category_primary != "",
                )
            )
            .group_by(func.lower(Transaction.category_primary))
            .having(func.count(Transaction.id) >= 3)
            .order_by(func.abs(func.sum(Transaction.amount)).desc())
        )
        provider_results = (await db.execute(provider_cat_query)).all()

        # Merge results, prioritizing custom categories
        seen_names: set[str] = set()
        candidates: list[dict] = []

        for row in custom_results:
            cat_id, cat_name, total, txn_count, first_date, last_date = row
            if cat_id in existing_category_ids:
                continue
            name_lower = cat_name.lower()
            if name_lower in seen_names:
                continue
            seen_names.add(name_lower)
            candidates.append(
                {
                    "category_id": str(cat_id),
                    "category_name": cat_name,
                    "total_spend": float(total),
                    "transaction_count": txn_count,
                    "first_date": first_date,
                    "last_date": last_date,
                }
            )

        for row in provider_results:
            cat_name, total, txn_count, first_date, last_date = row
            if cat_name in seen_names:
                continue
            seen_names.add(cat_name)
            candidates.append(
                {
                    "category_id": None,
                    "category_name": cat_name.title(),
                    "total_spend": float(total),
                    "transaction_count": txn_count,
                    "first_date": first_date,
                    "last_date": last_date,
                }
            )

        # For each candidate, compute monthly breakdown and suggest period/amount
        suggestions = []
        for c in candidates[: max_suggestions * 2]:  # over-fetch to filter later
            # Get per-month spending for this category
            spending_by_month = await BudgetSuggestionService._get_monthly_breakdown(
                db,
                account_ids,
                c["category_id"],
                c["category_name"],
                lookback,
            )

            month_count = len(spending_by_month)
            if month_count == 0:
                continue

            total = c["total_spend"]
            avg_monthly = total / month_count

            period = _suggest_period(avg_monthly, month_count, spending_by_month)

            # Calculate suggested amount based on period
            if period == BudgetPeriod.MONTHLY:
                raw_amount = avg_monthly
            elif period == BudgetPeriod.QUARTERLY:
                raw_amount = avg_monthly * 3
            elif period == BudgetPeriod.SEMI_ANNUAL:
                raw_amount = avg_monthly * 6
            else:  # yearly
                raw_amount = total  # use actual total from lookback

            suggested_amount = _round_up_nice(raw_amount * 1.1)  # 10% buffer

            suggestions.append(
                {
                    "category_name": c["category_name"],
                    "category_id": c["category_id"],
                    "suggested_amount": suggested_amount,
                    "suggested_period": period.value,
                    "avg_monthly_spend": round(avg_monthly, 2),
                    "total_spend": round(total, 2),
                    "month_count": month_count,
                    "transaction_count": c["transaction_count"],
                }
            )

        # Sort by total spend descending and limit
        suggestions.sort(key=lambda s: s["total_spend"], reverse=True)
        return suggestions[:max_suggestions]

    @staticmethod
    async def _get_monthly_breakdown(
        db: AsyncSession,
        account_ids: list[UUID],
        category_id: Optional[str],
        category_name: str,
        since: date,
    ) -> dict[str, float]:
        """Get spending broken down by YYYY-MM for a category."""
        month_label = func.to_char(Transaction.date, "YYYY-MM")

        query = (
            select(
                month_label.label("month"),
                func.abs(func.sum(Transaction.amount)).label("total"),
            )
            .where(
                and_(
                    Transaction.account_id.in_(account_ids),
                    Transaction.amount < 0,
                    Transaction.date >= since,
                )
            )
            .group_by(month_label)
        )

        if category_id:
            # Include child categories
            children_result = await db.execute(
                select(Category.id).where(Category.parent_category_id == category_id)
            )
            child_ids = [row[0] for row in children_result.all()]
            all_ids = [category_id] + [str(cid) for cid in child_ids]
            query = query.where(Transaction.category_id.in_(all_ids))
        else:
            query = query.where(func.lower(Transaction.category_primary) == category_name.lower())

        result = await db.execute(query)
        return {row.month: float(row.total) for row in result.all()}


budget_suggestion_service = BudgetSuggestionService()
