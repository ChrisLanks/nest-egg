"""Enhanced trends service — net worth history, investment performance, spending velocity.

Provides time-series data for charts and insights beyond basic income/expense trends.
"""

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.dividend import DividendIncome
from app.models.holding import Holding
from app.models.net_worth_snapshot import NetWorthSnapshot
from app.models.transaction import Transaction

logger = logging.getLogger(__name__)


class EnhancedTrendsService:
    """Service for advanced financial trend analysis and charting data."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # NET WORTH HISTORY
    # ------------------------------------------------------------------

    async def get_net_worth_history(
        self,
        organization_id: UUID,
        user_id: Optional[UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Get net worth history time series from snapshots.

        Returns daily data points with asset/liability breakdown.
        """
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=365)

        conditions = [
            NetWorthSnapshot.organization_id == organization_id,
            NetWorthSnapshot.snapshot_date >= start_date,
            NetWorthSnapshot.snapshot_date <= end_date,
        ]
        if user_id:
            conditions.append(NetWorthSnapshot.user_id == user_id)
        else:
            conditions.append(NetWorthSnapshot.user_id.is_(None))

        result = await self.db.execute(
            select(NetWorthSnapshot)
            .where(and_(*conditions))
            .order_by(NetWorthSnapshot.snapshot_date)
        )
        snapshots = list(result.scalars().all())

        data_points = []
        for s in snapshots:
            data_points.append(
                {
                    "date": s.snapshot_date.isoformat(),
                    "total_net_worth": float(s.total_net_worth),
                    "total_assets": float(s.total_assets),
                    "total_liabilities": float(s.total_liabilities),
                    "cash": float((s.cash_and_checking or 0) + (s.savings or 0)),
                    "investments": float(s.investments or 0),
                    "retirement": float(s.retirement or 0),
                    "property": float(getattr(s, "property", 0) or 0),
                    "credit_cards": float(s.credit_cards or 0),
                    "loans": float((s.loans or 0) + (s.student_loans or 0)),
                    "mortgages": float(s.mortgages or 0),
                }
            )

        # Calculate period change
        period_change = None
        if len(data_points) >= 2:
            first = data_points[0]["total_net_worth"]
            last = data_points[-1]["total_net_worth"]
            period_change = {
                "absolute": round(last - first, 2),
                "percentage": round((last - first) / abs(first) * 100, 2) if first != 0 else None,
                "start_value": first,
                "end_value": last,
            }

        return {
            "data_points": data_points,
            "period_change": period_change,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "snapshot_count": len(data_points),
        }

    # ------------------------------------------------------------------
    # INVESTMENT PERFORMANCE
    # ------------------------------------------------------------------

    async def get_investment_performance(
        self,
        organization_id: UUID,
        account_ids: Optional[List[UUID]] = None,
    ) -> Dict[str, Any]:
        """Get investment portfolio performance metrics.

        Computes total gain/loss, weighted return, and per-holding performance.
        """
        conditions = [
            Holding.organization_id == organization_id,
            Holding.current_total_value.isnot(None),
        ]
        if account_ids:
            conditions.append(Holding.account_id.in_(account_ids))

        result = await self.db.execute(select(Holding).where(and_(*conditions)))
        holdings = list(result.scalars().all())

        total_cost_basis = Decimal("0")
        total_current_value = Decimal("0")
        holding_performance = []

        for h in holdings:
            cost = h.total_cost_basis or Decimal("0")
            current = h.current_total_value or Decimal("0")
            gain = current - cost

            total_cost_basis += cost
            total_current_value += current

            gain_pct = None
            if cost > 0:
                gain_pct = float((gain / cost * 100).quantize(Decimal("0.01")))

            holding_performance.append(
                {
                    "ticker": h.ticker,
                    "name": h.name,
                    "shares": float(h.shares),
                    "cost_basis": float(cost),
                    "current_value": float(current),
                    "gain_loss": float(gain),
                    "gain_loss_pct": gain_pct,
                    "asset_type": h.asset_type,
                    "sector": h.sector,
                }
            )

        # Sort by gain/loss (biggest winners first)
        holding_performance.sort(key=lambda x: x["gain_loss"], reverse=True)

        total_gain = total_current_value - total_cost_basis
        total_return_pct = None
        if total_cost_basis > 0:
            total_return_pct = float(
                (total_gain / total_cost_basis * 100).quantize(Decimal("0.01"))
            )

        # Winners / losers
        winners = [h for h in holding_performance if h["gain_loss"] > 0][:5]
        losers = [h for h in reversed(holding_performance) if h["gain_loss"] < 0][:5]

        return {
            "total_cost_basis": float(total_cost_basis),
            "total_current_value": float(total_current_value),
            "total_gain_loss": float(total_gain),
            "total_return_pct": total_return_pct,
            "holding_count": len(holdings),
            "holdings": holding_performance,
            "top_winners": winners,
            "top_losers": losers,
        }

    # ------------------------------------------------------------------
    # SPENDING VELOCITY (rate of spending change over time)
    # ------------------------------------------------------------------

    async def get_spending_velocity(
        self,
        organization_id: UUID,
        months: int = 12,
        user_id: Optional[UUID] = None,
        account_ids: Optional[List[UUID]] = None,
    ) -> Dict[str, Any]:
        """Analyze spending acceleration/deceleration over time.

        Shows month-over-month spending change and identifies trends
        (spending speeding up or slowing down).
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=months * 31)

        conditions = [
            Transaction.organization_id == organization_id,
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            Transaction.amount < 0,  # Expenses only
            Transaction.is_transfer.is_(False),
            Account.is_active.is_(True),
            Account.exclude_from_cash_flow.is_(False),
        ]

        if user_id:
            conditions.append(Account.user_id == user_id)
        if account_ids:
            conditions.append(Transaction.account_id.in_(account_ids))

        month_expr = func.to_char(Transaction.date, "YYYY-MM")

        result = await self.db.execute(
            select(
                month_expr.label("month"),
                func.sum(func.abs(Transaction.amount)).label("total"),
                func.count(Transaction.id).label("txn_count"),
                func.avg(func.abs(Transaction.amount)).label("avg_txn"),
            )
            .select_from(Transaction)
            .join(Account, Transaction.account_id == Account.id)
            .where(and_(*conditions))
            .group_by(month_expr)
            .order_by(month_expr)
        )

        monthly = []
        for row in result.all():
            monthly.append(
                {
                    "month": row.month,
                    "total_spending": float(row.total or 0),
                    "transaction_count": row.txn_count,
                    "avg_transaction": float(row.avg_txn or 0),
                }
            )

        # Compute month-over-month velocity
        for i in range(1, len(monthly)):
            prev = monthly[i - 1]["total_spending"]
            curr = monthly[i]["total_spending"]
            if prev > 0:
                monthly[i]["mom_change_pct"] = round((curr - prev) / prev * 100, 1)
            else:
                monthly[i]["mom_change_pct"] = None
            monthly[i]["mom_change_abs"] = round(curr - prev, 2)

        if monthly:
            monthly[0]["mom_change_pct"] = None
            monthly[0]["mom_change_abs"] = None

        # Compute trend direction (linear regression slope on monthly totals)
        trend_direction = "stable"
        if len(monthly) >= 3:
            totals = [m["total_spending"] for m in monthly]
            first_half_avg = sum(totals[: len(totals) // 2]) / max(len(totals) // 2, 1)
            second_half_avg = sum(totals[len(totals) // 2 :]) / max(
                len(totals) - len(totals) // 2, 1
            )
            pct_change = (
                (second_half_avg - first_half_avg) / first_half_avg * 100
                if first_half_avg > 0
                else 0
            )

            if pct_change > 5:
                trend_direction = "accelerating"
            elif pct_change < -5:
                trend_direction = "decelerating"

        avg_monthly = sum(m["total_spending"] for m in monthly) / max(len(monthly), 1)

        return {
            "monthly_data": monthly,
            "trend_direction": trend_direction,
            "avg_monthly_spending": round(avg_monthly, 2),
            "months_analyzed": len(monthly),
        }

    # ------------------------------------------------------------------
    # CASH FLOW SUMMARY (income vs expenses stacked over time)
    # ------------------------------------------------------------------

    async def get_cash_flow_history(
        self,
        organization_id: UUID,
        months: int = 12,
        user_id: Optional[UUID] = None,
        account_ids: Optional[List[UUID]] = None,
    ) -> Dict[str, Any]:
        """Get monthly cash flow (income vs expenses) time series for chart data."""
        end_date = date.today()
        start_date = end_date - timedelta(days=months * 31)

        conditions = [
            Transaction.organization_id == organization_id,
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            Transaction.is_transfer.is_(False),
            Account.is_active.is_(True),
            Account.exclude_from_cash_flow.is_(False),
        ]

        if user_id:
            conditions.append(Account.user_id == user_id)
        if account_ids:
            conditions.append(Transaction.account_id.in_(account_ids))

        month_expr = func.to_char(Transaction.date, "YYYY-MM")

        result = await self.db.execute(
            select(
                month_expr.label("month"),
                func.sum(case((Transaction.amount > 0, Transaction.amount), else_=0)).label(
                    "income"
                ),
                func.sum(
                    case((Transaction.amount < 0, func.abs(Transaction.amount)), else_=0)
                ).label("expenses"),
            )
            .select_from(Transaction)
            .join(Account, Transaction.account_id == Account.id)
            .where(and_(*conditions))
            .group_by(month_expr)
            .order_by(month_expr)
        )

        data = []
        total_income = Decimal("0")
        total_expenses = Decimal("0")

        for row in result.all():
            inc = Decimal(str(row.income or 0))
            exp = Decimal(str(row.expenses or 0))
            total_income += inc
            total_expenses += exp
            data.append(
                {
                    "month": row.month,
                    "income": float(inc),
                    "expenses": float(exp),
                    "net": float(inc - exp),
                    "savings_rate": float((inc - exp) / inc * 100) if inc > 0 else 0,
                }
            )

        avg_savings_rate = None
        if total_income > 0:
            avg_savings_rate = float((total_income - total_expenses) / total_income * 100)

        return {
            "monthly_data": data,
            "total_income": float(total_income),
            "total_expenses": float(total_expenses),
            "total_net": float(total_income - total_expenses),
            "avg_savings_rate": round(avg_savings_rate, 1)
            if avg_savings_rate is not None
            else None,
            "months_analyzed": len(data),
        }

    # ------------------------------------------------------------------
    # INVESTMENT INCOME TREND (dividends over time)
    # ------------------------------------------------------------------

    async def get_investment_income_trend(
        self,
        organization_id: UUID,
        months: int = 24,
        account_ids: Optional[List[UUID]] = None,
    ) -> Dict[str, Any]:
        """Get monthly investment income (dividends/interest) trend for charting."""
        end_date = date.today()
        start_date = end_date - timedelta(days=months * 31)

        conditions = [
            DividendIncome.organization_id == organization_id,
            DividendIncome.ex_date >= start_date,
            DividendIncome.ex_date <= end_date,
        ]
        if account_ids:
            conditions.append(DividendIncome.account_id.in_(account_ids))

        month_expr = func.to_char(DividendIncome.ex_date, "YYYY-MM")

        result = await self.db.execute(
            select(
                month_expr.label("month"),
                func.sum(DividendIncome.amount).label("total"),
                func.count().label("count"),
            )
            .where(and_(*conditions))
            .group_by(month_expr)
            .order_by(month_expr)
        )

        data = []
        cumulative = Decimal("0")
        for row in result.all():
            amt = Decimal(str(row.total or 0))
            cumulative += amt
            data.append(
                {
                    "month": row.month,
                    "income": float(amt),
                    "payment_count": row.count,
                    "cumulative": float(cumulative),
                }
            )

        return {
            "monthly_data": data,
            "total_income": float(cumulative),
            "months_analyzed": len(data),
        }
