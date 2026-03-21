"""
Savings Rate Service — monthly savings rate trend with user_id scoping.

Savings rate = (income - |expenses|) / income for each month.
Income = positive transactions. Expenses = absolute value of negative transactions.
Uses the same account-scoping pattern as other services.
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from dateutil.relativedelta import relativedelta
from pydantic import BaseModel
from sqlalchemy import and_, case, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.transaction import Transaction

logger = logging.getLogger(__name__)

SS_MINIMUM_PLANNING_AGE = 50  # default hide below this age


class MonthlySavingsRate(BaseModel):
    month: str  # "YYYY-MM"
    income: float
    expenses: float
    savings: float
    savings_rate: float  # 0.0–1.0; negative when spending > income


class SavingsRateSummary(BaseModel):
    current_month_rate: Optional[float]
    trailing_3m_rate: Optional[float]
    trailing_12m_rate: Optional[float]
    monthly_trend: List[MonthlySavingsRate]
    avg_monthly_savings: float
    best_month: Optional[str]
    worst_month: Optional[str]


class SavingsRateService:
    """Calculate monthly savings rate trend scoped by org/user."""

    @staticmethod
    async def get_savings_trend(
        db: AsyncSession,
        organization_id: UUID,
        user_id: Optional[UUID] = None,
        months: int = 12,
    ) -> SavingsRateSummary:
        """
        Return savings rate trend for the last `months` calendar months.

        When user_id is provided only transactions belonging to that user's
        accounts are included (individual view). When None, all household
        accounts are aggregated.
        """
        today = date.today()
        # Start from the 1st of the month `months` ago
        start_date = today.replace(day=1) - relativedelta(months=months - 1)

        # Build base query filtering by org and date range
        base_filter = [
            Transaction.organization_id == organization_id,
            Transaction.date >= start_date,
            Transaction.date <= today,
            Transaction.is_pending.is_(False),
        ]

        # Join to Account for user_id scoping when requested
        if user_id:
            stmt = (
                select(
                    extract("year", Transaction.date).label("yr"),
                    extract("month", Transaction.date).label("mo"),
                    func.sum(
                        case((Transaction.amount > 0, Transaction.amount), else_=Decimal("0"))
                    ).label("income"),
                    func.sum(
                        case(
                            (Transaction.amount < 0, func.abs(Transaction.amount)),
                            else_=Decimal("0"),
                        )
                    ).label("expenses"),
                )
                .join(Account, Transaction.account_id == Account.id)
                .where(
                    and_(
                        *base_filter,
                        Account.user_id == user_id,
                        Account.exclude_from_cash_flow.is_(False),
                    )
                )
                .group_by("yr", "mo")
                .order_by("yr", "mo")
            )
        else:
            stmt = (
                select(
                    extract("year", Transaction.date).label("yr"),
                    extract("month", Transaction.date).label("mo"),
                    func.sum(
                        case((Transaction.amount > 0, Transaction.amount), else_=Decimal("0"))
                    ).label("income"),
                    func.sum(
                        case(
                            (Transaction.amount < 0, func.abs(Transaction.amount)),
                            else_=Decimal("0"),
                        )
                    ).label("expenses"),
                )
                .join(Account, Transaction.account_id == Account.id)
                .where(
                    and_(
                        *base_filter,
                        Account.exclude_from_cash_flow.is_(False),
                    )
                )
                .group_by("yr", "mo")
                .order_by("yr", "mo")
            )

        result = await db.execute(stmt)
        rows = result.all()

        monthly: List[MonthlySavingsRate] = []
        for row in rows:
            yr = int(row.yr)
            mo = int(row.mo)
            income = float(row.income or 0)
            expenses = float(row.expenses or 0)
            savings = income - expenses
            rate = (savings / income) if income > 0 else 0.0
            monthly.append(
                MonthlySavingsRate(
                    month=f"{yr:04d}-{mo:02d}",
                    income=round(income, 2),
                    expenses=round(expenses, 2),
                    savings=round(savings, 2),
                    savings_rate=round(rate, 4),
                )
            )

        if not monthly:
            return SavingsRateSummary(
                current_month_rate=None,
                trailing_3m_rate=None,
                trailing_12m_rate=None,
                monthly_trend=[],
                avg_monthly_savings=0.0,
                best_month=None,
                worst_month=None,
            )

        # Current month (last entry)
        current_month_rate = monthly[-1].savings_rate if monthly else None

        # Trailing averages (weighted by income)
        def _avg_rate(window: List[MonthlySavingsRate]) -> Optional[float]:
            total_income = sum(m.income for m in window)
            total_savings = sum(m.savings for m in window)
            if total_income <= 0:
                return None
            return round(total_savings / total_income, 4)

        trailing_3 = monthly[-3:] if len(monthly) >= 3 else monthly
        trailing_12 = monthly[-12:] if len(monthly) >= 12 else monthly

        avg_monthly_savings = sum(m.savings for m in monthly) / len(monthly) if monthly else 0.0
        best = max(monthly, key=lambda m: m.savings_rate, default=None)
        worst = min(monthly, key=lambda m: m.savings_rate, default=None)

        return SavingsRateSummary(
            current_month_rate=current_month_rate,
            trailing_3m_rate=_avg_rate(trailing_3),
            trailing_12m_rate=_avg_rate(trailing_12),
            monthly_trend=monthly,
            avg_monthly_savings=round(avg_monthly_savings, 2),
            best_month=best.month if best else None,
            worst_month=worst.month if worst else None,
        )
