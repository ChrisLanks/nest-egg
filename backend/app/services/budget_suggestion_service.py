"""Service for generating smart budget suggestions based on spending history.

Two modes of operation:
  1. Celery task (daily 2am): calls refresh_for_org() per org → writes rows to
     budget_suggestions table. Also called on-demand when cached data is stale.
  2. API endpoint: calls get_cached_suggestions() → reads from the table instantly.
     Falls back to get_suggestions() (on-demand compute) if no cached rows exist yet.
"""

import logging
import math
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.budget import Budget, BudgetPeriod
from app.models.budget_suggestion import BudgetSuggestion
from app.models.transaction import Category, Transaction
from app.models.user import User
from app.utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)

# Suggestions older than this are considered stale → on-demand refresh
SUGGESTION_STALENESS_HOURS = 25  # slightly over 24h to avoid missing a daily run


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
    """Suggest the best budget period based on spending pattern."""
    if month_count == 0:
        return BudgetPeriod.MONTHLY

    months_with_spending = sum(1 for v in spending_by_month.values() if v > 0)
    ratio = months_with_spending / month_count

    if ratio <= 0.25 and month_count >= 6:
        return BudgetPeriod.YEARLY
    if ratio <= 0.50 and month_count >= 4:
        return BudgetPeriod.SEMI_ANNUAL
    if ratio <= 0.70 and month_count >= 3:
        return BudgetPeriod.QUARTERLY

    return BudgetPeriod.MONTHLY


class BudgetSuggestionService:
    """Generates and caches budget suggestions from spending history."""

    # ---------------------------------------------------------------------------
    # Public: cache-aware entry point used by the API endpoint
    # ---------------------------------------------------------------------------

    @staticmethod
    async def get_cached_suggestions(
        db: AsyncSession,
        user: User,
        scoped_user_id: Optional[UUID] = None,
    ) -> List[dict]:
        """Return suggestions from the pre-computed table.

        If no rows exist or rows are stale (>25h old), falls back to on-demand
        compute AND writes the results to the table for next time.

        Args:
            db: Database session
            user: Requesting user (org context)
            scoped_user_id: If set, return suggestions for this member's spending.
        """
        rows = await BudgetSuggestionService._read_cached(
            db, user.organization_id, scoped_user_id
        )

        if rows:
            return [BudgetSuggestionService._row_to_dict(r) for r in rows]

        # Nothing cached — compute on-demand and persist
        logger.info(
            "No cached suggestions for org %s user %s — computing on-demand",
            user.organization_id,
            scoped_user_id,
        )
        scoped_account_ids = None
        if scoped_user_id:
            acct_result = await db.execute(
                select(Account.id).where(
                    and_(
                        Account.organization_id == user.organization_id,
                        Account.user_id == scoped_user_id,
                    )
                )
            )
            scoped_account_ids = [row[0] for row in acct_result.all()]

        suggestions = await BudgetSuggestionService.get_suggestions(
            db, user, scoped_account_ids=scoped_account_ids
        )

        # Persist so next call is instant
        await BudgetSuggestionService._write_cached(
            db, user.organization_id, scoped_user_id, suggestions
        )

        return suggestions

    # ---------------------------------------------------------------------------
    # Public: Celery task entry point
    # ---------------------------------------------------------------------------

    @staticmethod
    async def refresh_for_org(
        db: AsyncSession,
        organization_id: UUID,
        scoped_user_id: Optional[UUID] = None,
    ) -> int:
        """Recompute suggestions for an org (or a specific member) and persist them.

        Called daily by the Celery task. Also callable on-demand.
        Skips the org entirely if it has no active accounts (nothing to analyze).

        Returns the number of suggestions written.
        """
        # Get a user from the org for context (needed by get_suggestions)
        user_result = await db.execute(
            select(User)
            .where(User.organization_id == organization_id)
            .limit(1)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            return 0

        scoped_account_ids = None
        if scoped_user_id:
            acct_result = await db.execute(
                select(Account.id).where(
                    and_(
                        Account.organization_id == organization_id,
                        Account.user_id == scoped_user_id,
                    )
                )
            )
            scoped_account_ids = [row[0] for row in acct_result.all()]
            if scoped_account_ids is not None and len(scoped_account_ids) == 0:
                # No accounts for this user — clear stale rows and return
                await BudgetSuggestionService._clear_cached(
                    db, organization_id, scoped_user_id
                )
                return 0

        suggestions = await BudgetSuggestionService.get_suggestions(
            db, user, scoped_account_ids=scoped_account_ids
        )

        await BudgetSuggestionService._write_cached(
            db, organization_id, scoped_user_id, suggestions
        )

        logger.info(
            "Refreshed %d suggestions for org %s user %s",
            len(suggestions),
            organization_id,
            scoped_user_id,
        )
        return len(suggestions)

    # ---------------------------------------------------------------------------
    # Core compute logic (unchanged, now also used internally)
    # ---------------------------------------------------------------------------

    @staticmethod
    async def get_suggestions(
        db: AsyncSession,
        user: User,
        months: int = 6,
        max_suggestions: int = 8,
        scoped_account_ids: Optional[list[UUID]] = None,
    ) -> List[dict]:
        """Analyze spending history and return suggestion dicts (no DB writes).

        Returns:
            List of dicts with: category_name, category_id, category_primary_raw,
            suggested_amount, suggested_period, avg_monthly_spend,
            total_spend, month_count, transaction_count
        """
        lookback = date.today() - timedelta(days=months * 31)

        if scoped_account_ids is not None:
            account_ids = scoped_account_ids
        else:
            acct_result = await db.execute(
                select(Account.id).where(
                    Account.organization_id == user.organization_id,
                )
            )
            account_ids = [row[0] for row in acct_result.all()]
        if not account_ids:
            return []

        # Existing active budgets — exclude categories already budgeted
        budget_result = await db.execute(
            select(Budget.category_id, Budget.name).where(
                and_(
                    Budget.organization_id == user.organization_id,
                    Budget.is_active.is_(True),
                )
            )
        )
        existing_budgets = budget_result.all()
        existing_category_ids = {row[0] for row in existing_budgets if row[0] is not None}
        existing_budget_names_lower = {row[1].lower() for row in existing_budgets if row[1]}

        # Custom categories with sufficient spending
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
                    Transaction.amount < 0,
                    Transaction.date >= lookback,
                    Category.parent_category_id.is_(None),
                )
            )
            .group_by(Category.id, Category.name)
            .having(func.count(Transaction.id) >= 3)
            .order_by(func.abs(func.sum(Transaction.amount)).desc())
        )
        custom_results = (await db.execute(custom_cat_query)).all()

        # Provider categories (category_primary) — only uncategorised transactions
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
                    "category_primary_raw": None,
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
            if cat_name.lower() in existing_budget_names_lower:
                continue
            if cat_name.title().lower() in existing_budget_names_lower:
                continue
            seen_names.add(cat_name)
            candidates.append(
                {
                    "category_id": None,
                    "category_name": cat_name.title(),
                    "category_primary_raw": cat_name,
                    "total_spend": float(total),
                    "transaction_count": txn_count,
                    "first_date": first_date,
                    "last_date": last_date,
                }
            )

        suggestions = []
        for c in candidates[: max_suggestions * 2]:
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

            if period == BudgetPeriod.MONTHLY:
                raw_amount = avg_monthly
            elif period == BudgetPeriod.QUARTERLY:
                raw_amount = avg_monthly * 3
            elif period == BudgetPeriod.SEMI_ANNUAL:
                raw_amount = avg_monthly * 6
            else:
                raw_amount = total

            suggested_amount = _round_up_nice(raw_amount * 1.1)

            suggestions.append(
                {
                    "category_name": c["category_name"],
                    "category_id": c["category_id"],
                    "category_primary_raw": c["category_primary_raw"],
                    "suggested_amount": suggested_amount,
                    "suggested_period": period.value,
                    "avg_monthly_spend": round(avg_monthly, 2),
                    "total_spend": round(total, 2),
                    "month_count": month_count,
                    "transaction_count": c["transaction_count"],
                }
            )

        suggestions.sort(key=lambda s: s["total_spend"], reverse=True)
        return suggestions[:max_suggestions]

    # ---------------------------------------------------------------------------
    # Private helpers
    # ---------------------------------------------------------------------------

    @staticmethod
    async def _read_cached(
        db: AsyncSession,
        organization_id: UUID,
        scoped_user_id: Optional[UUID],
    ) -> list[BudgetSuggestion]:
        """Return non-stale cached rows, or [] if missing/stale."""
        stale_cutoff = utc_now() - timedelta(hours=SUGGESTION_STALENESS_HOURS)

        if scoped_user_id is not None:
            user_filter = BudgetSuggestion.user_id == scoped_user_id
        else:
            user_filter = BudgetSuggestion.user_id.is_(None)

        result = await db.execute(
            select(BudgetSuggestion)
            .where(
                and_(
                    BudgetSuggestion.organization_id == organization_id,
                    user_filter,
                    BudgetSuggestion.generated_at >= stale_cutoff,
                )
            )
            .order_by(BudgetSuggestion.total_spend.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def _clear_cached(
        db: AsyncSession,
        organization_id: UUID,
        scoped_user_id: Optional[UUID],
    ) -> None:
        """Delete existing cached rows for this org/user scope."""
        if scoped_user_id is not None:
            user_filter = BudgetSuggestion.user_id == scoped_user_id
        else:
            user_filter = BudgetSuggestion.user_id.is_(None)

        await db.execute(
            delete(BudgetSuggestion).where(
                and_(
                    BudgetSuggestion.organization_id == organization_id,
                    user_filter,
                )
            )
        )

    @staticmethod
    async def _write_cached(
        db: AsyncSession,
        organization_id: UUID,
        scoped_user_id: Optional[UUID],
        suggestions: List[dict],
    ) -> None:
        """Replace cached rows for this org/user scope with fresh suggestions."""
        await BudgetSuggestionService._clear_cached(db, organization_id, scoped_user_id)

        now = utc_now()
        for s in suggestions:
            row = BudgetSuggestion(
                organization_id=organization_id,
                user_id=scoped_user_id,
                category_id=UUID(s["category_id"]) if s.get("category_id") else None,
                category_primary_raw=s.get("category_primary_raw"),
                category_name=s["category_name"],
                suggested_amount=Decimal(str(s["suggested_amount"])),
                suggested_period=s["suggested_period"],
                avg_monthly_spend=Decimal(str(s["avg_monthly_spend"])),
                total_spend=Decimal(str(s["total_spend"])),
                month_count=s["month_count"],
                transaction_count=s["transaction_count"],
                generated_at=now,
            )
            db.add(row)

        await db.commit()

    @staticmethod
    def _row_to_dict(row: BudgetSuggestion) -> dict:
        """Convert a BudgetSuggestion ORM row to the standard suggestion dict."""
        return {
            "category_name": row.category_name,
            "category_id": str(row.category_id) if row.category_id else None,
            "category_primary_raw": row.category_primary_raw,
            "suggested_amount": float(row.suggested_amount),
            "suggested_period": row.suggested_period,
            "avg_monthly_spend": float(row.avg_monthly_spend),
            "total_spend": float(row.total_spend),
            "month_count": row.month_count,
            "transaction_count": row.transaction_count,
        }

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
            children_result = await db.execute(
                select(Category.id).where(Category.parent_category_id == category_id)
            )
            child_ids = [row[0] for row in children_result.all()]
            all_ids = [category_id] + [str(cid) for cid in child_ids]
            query = query.where(Transaction.category_id.in_(all_ids))
        else:
            query = query.where(
                func.lower(Transaction.category_primary) == category_name.lower()
            )

        result = await db.execute(query)
        return {row.month: float(row.total) for row in result.all()}


budget_suggestion_service = BudgetSuggestionService()
