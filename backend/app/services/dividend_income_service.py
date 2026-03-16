"""Dividend and investment income tracking service."""

import logging
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dividend import DividendIncome, IncomeType
from app.models.holding import Holding

logger = logging.getLogger(__name__)


class DividendIncomeService:
    """Service for tracking and analyzing dividend/investment income."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        organization_id: UUID,
        data: dict,
    ) -> DividendIncome:
        """Create a dividend income record."""
        record = DividendIncome(
            organization_id=organization_id,
            **data,
        )
        self.db.add(record)
        await self.db.flush()
        return record

    async def list_income(
        self,
        organization_id: UUID,
        account_id: Optional[UUID] = None,
        ticker: Optional[str] = None,
        income_type: Optional[IncomeType] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[DividendIncome]:
        """List dividend income with optional filters."""
        conditions = [DividendIncome.organization_id == organization_id]

        if account_id:
            conditions.append(DividendIncome.account_id == account_id)
        if ticker:
            conditions.append(DividendIncome.ticker == ticker.upper())
        if income_type:
            conditions.append(DividendIncome.income_type == income_type)
        if start_date:
            conditions.append(DividendIncome.ex_date >= start_date)
        if end_date:
            conditions.append(DividendIncome.ex_date <= end_date)

        result = await self.db.execute(
            select(DividendIncome)
            .where(and_(*conditions))
            .order_by(DividendIncome.ex_date.desc().nullslast())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_summary(
        self,
        organization_id: UUID,
        account_ids: Optional[List[UUID]] = None,
    ) -> dict:
        """Get portfolio-wide dividend income summary."""
        today = date.today()
        year_start = date(today.year, 1, 1)
        trailing_12m_start = today - timedelta(days=365)

        base_conditions = [DividendIncome.organization_id == organization_id]
        if account_ids:
            base_conditions.append(DividendIncome.account_id.in_(account_ids))

        # YTD total
        ytd_result = await self.db.execute(
            select(func.coalesce(func.sum(DividendIncome.amount), 0)).where(
                and_(*base_conditions, DividendIncome.ex_date >= year_start)
            )
        )
        total_ytd = Decimal(str(ytd_result.scalar()))

        # Trailing 12 months
        t12m_result = await self.db.execute(
            select(func.coalesce(func.sum(DividendIncome.amount), 0)).where(
                and_(*base_conditions, DividendIncome.ex_date >= trailing_12m_start)
            )
        )
        total_12m = Decimal(str(t12m_result.scalar()))

        # All-time total
        all_time_result = await self.db.execute(
            select(func.coalesce(func.sum(DividendIncome.amount), 0)).where(and_(*base_conditions))
        )
        total_all_time = Decimal(str(all_time_result.scalar()))

        # Monthly average (trailing 12m)
        monthly_avg = (total_12m / 12).quantize(Decimal("0.01")) if total_12m > 0 else Decimal("0")

        # Projected annual income based on trailing 12m
        projected_annual = total_12m

        # By ticker (trailing 12m)
        ticker_result = await self.db.execute(
            select(
                DividendIncome.ticker,
                func.max(DividendIncome.name).label("name"),
                func.sum(DividendIncome.amount).label("total"),
                func.count().label("count"),
                func.avg(DividendIncome.per_share_amount).label("avg_per_share"),
                func.max(DividendIncome.ex_date).label("latest_ex_date"),
            )
            .where(and_(*base_conditions, DividendIncome.ex_date >= trailing_12m_start))
            .group_by(DividendIncome.ticker)
            .order_by(func.sum(DividendIncome.amount).desc())
        )
        by_ticker = []
        for row in ticker_result.all():
            by_ticker.append(
                {
                    "ticker": row.ticker,
                    "name": row.name,
                    "total_income": Decimal(str(row.total)).quantize(Decimal("0.01")),
                    "payment_count": row.count,
                    "avg_per_share": Decimal(str(row.avg_per_share)).quantize(Decimal("0.0001"))
                    if row.avg_per_share
                    else None,
                    "latest_ex_date": row.latest_ex_date,
                    "yield_on_cost": None,  # Computed below if holding data available
                }
            )

        # Compute yield-on-cost from holdings
        if by_ticker:
            tickers = [t["ticker"] for t in by_ticker]
            acct_cond = [Holding.organization_id == organization_id, Holding.ticker.in_(tickers)]
            if account_ids:
                acct_cond.append(Holding.account_id.in_(account_ids))
            holding_result = await self.db.execute(
                select(
                    Holding.ticker,
                    func.sum(Holding.total_cost_basis).label("cost_basis"),
                )
                .where(and_(*acct_cond))
                .group_by(Holding.ticker)
            )
            cost_map = {r.ticker: r.cost_basis for r in holding_result.all() if r.cost_basis}

            for entry in by_ticker:
                cb = cost_map.get(entry["ticker"])
                if cb and cb > 0:
                    annual_income = entry["total_income"]
                    entry["yield_on_cost"] = (annual_income / Decimal(str(cb)) * 100).quantize(
                        Decimal("0.01")
                    )

        # By month (last 24 months)
        two_years_ago = today - timedelta(days=730)
        month_result = await self.db.execute(
            select(
                func.to_char(DividendIncome.ex_date, "YYYY-MM").label("month"),
                func.sum(DividendIncome.amount).label("total"),
                func.count().label("count"),
                DividendIncome.income_type,
            )
            .where(and_(*base_conditions, DividendIncome.ex_date >= two_years_ago))
            .group_by("month", DividendIncome.income_type)
            .order_by("month")
        )
        month_data: Dict[str, dict] = defaultdict(
            lambda: {"total": Decimal("0"), "count": 0, "by_type": {}}
        )
        for row in month_result.all():
            m = month_data[row.month]
            m["total"] += Decimal(str(row.total))
            m["count"] += row.count
            m["by_type"][row.income_type.value] = Decimal(str(row.total)).quantize(Decimal("0.01"))

        by_month = [
            {
                "month": k,
                "total_income": v["total"].quantize(Decimal("0.01")),
                "dividend_count": v["count"],
                "by_type": v["by_type"],
            }
            for k, v in sorted(month_data.items())
        ]

        # YoY income growth
        income_growth_pct = None
        if len(by_month) >= 13:
            prev_year_total = sum(
                entry["total_income"]
                for entry in by_month
                if entry["month"][:4] == str(today.year - 1)
            )
            curr_year_total = sum(
                entry["total_income"] for entry in by_month if entry["month"][:4] == str(today.year)
            )
            if prev_year_total > 0:
                income_growth_pct = (
                    (curr_year_total - prev_year_total) / prev_year_total * 100
                ).quantize(Decimal("0.01"))

        return {
            "total_income_ytd": total_ytd,
            "total_income_trailing_12m": total_12m,
            "total_income_all_time": total_all_time,
            "projected_annual_income": projected_annual,
            "monthly_average": monthly_avg,
            "by_ticker": by_ticker,
            "by_month": by_month,
            "top_payers": by_ticker[:10],
            "income_growth_pct": income_growth_pct,
        }

    async def delete(self, organization_id: UUID, record_id: UUID) -> bool:
        """Delete a dividend income record."""
        result = await self.db.execute(
            select(DividendIncome).where(
                and_(
                    DividendIncome.id == record_id,
                    DividendIncome.organization_id == organization_id,
                )
            )
        )
        record = result.scalar_one_or_none()
        if not record:
            return False
        await self.db.delete(record)
        return True
