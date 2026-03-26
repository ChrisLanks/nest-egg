"""Dividend calendar API endpoint — groups dividend income by month."""

import calendar
import datetime
import logging
from collections import defaultdict
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.account import Account
from app.models.dividend import DividendIncome
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Dividend Calendar"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class DividendEvent(BaseModel):
    id: str
    ticker: Optional[str]
    account_id: str
    account_name: str
    income_type: str
    amount: float
    ex_date: Optional[str]
    pay_date: Optional[str]
    shares: Optional[float]
    per_share: Optional[float]


class MonthlyDividend(BaseModel):
    month: int
    month_name: str
    total: float
    events: List[DividendEvent]


class TickerSummary(BaseModel):
    ticker: str
    annual_total: float
    event_count: int


class DividendCalendarResponse(BaseModel):
    year: int
    months: List[MonthlyDividend]
    annual_total: float
    by_ticker: List[TickerSummary]
    avg_monthly: float
    best_month: Optional[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _assign_month(record: DividendIncome, year: int) -> Optional[int]:
    """Return the month (1-12) for a dividend record within the requested year.

    Priority: pay_date → ex_date → None (record excluded).
    Only returns a month when the chosen date falls in the requested year.
    """
    for dt in (record.pay_date, record.ex_date):
        if dt is not None:
            if dt.year == year:
                return dt.month
            # Date exists but is outside the requested year — skip this date
            # and try the next one
    return None


def _record_in_year(record: DividendIncome, year: int) -> bool:
    """Return True when any date field on the record falls in the requested year."""
    for dt in (record.pay_date, record.ex_date):
        if dt is not None and dt.year == year:
            return True
    return False


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.get("/dividend-calendar", response_model=DividendCalendarResponse)
async def get_dividend_calendar(
    year: Optional[int] = Query(
        None, ge=2000, le=2100, description="Calendar year (default: current year)"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return dividend income grouped by month for the requested year.

    Also provides an annual total, per-ticker summary, and average monthly income.
    """
    target_year = year or datetime.date.today().year

    # Fetch all dividend records for the organisation
    result = await db.execute(
        select(DividendIncome).where(
            DividendIncome.organization_id == current_user.organization_id,
        )
    )
    records = result.scalars().all()

    # Fetch accounts for name lookup
    acct_result = await db.execute(
        select(Account).where(
            Account.organization_id == current_user.organization_id,
        )
    )
    accounts = {str(a.id): a for a in acct_result.scalars().all()}

    # Group by month
    monthly_events: dict[int, list[DividendEvent]] = defaultdict(list)
    ticker_totals: dict[str, float] = defaultdict(float)
    ticker_counts: dict[str, int] = defaultdict(int)

    for rec in records:
        if not _record_in_year(rec, target_year):
            continue

        month = _assign_month(rec, target_year)
        if month is None:
            continue

        account = accounts.get(str(rec.account_id))
        account_name = account.name if account else str(rec.account_id)
        ticker = rec.ticker or ""

        event = DividendEvent(
            id=str(rec.id),
            ticker=rec.ticker,
            account_id=str(rec.account_id),
            account_name=account_name,
            income_type=str(rec.income_type),
            amount=float(rec.amount),
            ex_date=rec.ex_date.isoformat() if rec.ex_date else None,
            pay_date=rec.pay_date.isoformat() if rec.pay_date else None,
            shares=float(rec.shares_held) if rec.shares_held is not None else None,
            per_share=float(rec.per_share_amount) if rec.per_share_amount is not None else None,
        )
        monthly_events[month].append(event)

        if ticker:
            ticker_totals[ticker] += float(rec.amount)
            ticker_counts[ticker] += 1

    # Build all 12 months
    months: List[MonthlyDividend] = []
    annual_total = 0.0
    best_month_name: Optional[str] = None
    best_month_total = 0.0

    for m in range(1, 13):
        events = monthly_events.get(m, [])
        total = sum(e.amount for e in events)
        annual_total += total
        month_name = calendar.month_name[m]

        if events and total > best_month_total:
            best_month_total = total
            best_month_name = month_name

        months.append(
            MonthlyDividend(
                month=m,
                month_name=month_name,
                total=round(total, 2),
                events=sorted(events, key=lambda e: (e.pay_date or e.ex_date or "")),
            )
        )

    months_with_income = sum(1 for m in months if m.total > 0)
    avg_monthly = (annual_total / months_with_income) if months_with_income > 0 else 0.0

    by_ticker = sorted(
        [
            TickerSummary(
                ticker=t,
                annual_total=round(v, 2),
                event_count=ticker_counts[t],
            )
            for t, v in ticker_totals.items()
        ],
        key=lambda x: x.annual_total,
        reverse=True,
    )

    return DividendCalendarResponse(
        year=target_year,
        months=months,
        annual_total=round(annual_total, 2),
        by_ticker=by_ticker,
        avg_monthly=round(avg_monthly, 2),
        best_month=best_month_name,
    )
