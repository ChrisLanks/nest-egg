"""Dashboard service for financial summary calculations."""

import json
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID
from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.account import Account, AccountType
from app.models.transaction import Transaction, TransactionLabel, Category
from app.utils.datetime_utils import utc_now


class DashboardService:
    """Service for calculating dashboard metrics."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_net_worth(
        self, organization_id: str, account_ids: Optional[List[UUID]] = None
    ) -> Decimal:
        """Calculate net worth (assets - debts)."""
        # Get all active accounts
        conditions = [Account.organization_id == organization_id, Account.is_active.is_(True)]
        if account_ids is not None:
            conditions.append(Account.id.in_(account_ids))

        result = await self.db.execute(select(Account).where(and_(*conditions)))
        accounts = result.scalars().all()

        total = Decimal(0)
        for account in accounts:
            # Check if account should be included in net worth
            include = self._should_include_in_networth(account)
            if not include:
                continue

            # Calculate account value (may be vested equity for private equity accounts)
            balance = self._calculate_account_value(account)

            # Use account type's category property to determine how to handle balance
            if account.account_type.is_asset:
                total += balance
            elif account.account_type.is_debt:
                # Use abs() to handle both positive and negative balance representations
                total -= abs(balance)

        return total

    def _should_include_in_networth(self, account: Account) -> bool:
        """
        Determine if account should be included in net worth calculation.

        Returns True if:
        - include_in_networth is explicitly True
        - include_in_networth is None and account is a standard financial account

        Returns False if:
        - include_in_networth is explicitly False
        - include_in_networth is None and account type defaults to excluded:
          - VEHICLE (depreciating asset, opt-in for classics)
          - PRIVATE_EQUITY (illiquid, opt-in for public company equity)
          - COLLECTIBLES (uncertain value, opt-in)
          - OTHER / MANUAL (unknown type, opt-in)
        """
        if account.include_in_networth is not None:
            return account.include_in_networth

        # Auto-determine based on account type
        # Account types that default to excluded from net worth
        EXCLUDED_BY_DEFAULT = {
            AccountType.VEHICLE,  # Depreciating asset; opt-in for classics
            AccountType.COLLECTIBLES,  # Uncertain value; opt-in
            AccountType.OTHER,  # Unknown type; opt-in
            AccountType.MANUAL,  # Unknown type; opt-in
            AccountType.PENSION,  # Future income promise, not a liquid asset; opt-in
        }

        if account.account_type in EXCLUDED_BY_DEFAULT:
            return False

        if account.account_type == AccountType.PRIVATE_EQUITY:
            # Private equity: default to excluding unless public
            return bool(account.company_status and account.company_status.value == "public")

        # All other accounts: default to including
        return True

    def _calculate_account_value(self, account: Account) -> Decimal:
        """
        Calculate the current value of an account.

        For Business Equity accounts, calculates from valuation + percentage or uses direct value.
        For Private Equity accounts with vesting schedules, only counts vested equity.
        For all other accounts, returns current_balance.
        """
        # Handle Business Equity accounts
        if account.account_type == AccountType.BUSINESS_EQUITY:
            # If direct equity value is provided, use it
            if account.equity_value:
                return account.equity_value
            # If company valuation is provided
            elif account.company_valuation:
                # If ownership percentage is also provided, calculate proportional value
                if account.ownership_percentage:
                    return (account.company_valuation * account.ownership_percentage) / Decimal(100)
                # If no percentage provided, assume 100% ownership (use full valuation)
                else:
                    return account.company_valuation
            # Fallback to current_balance
            return account.current_balance or Decimal(0)

        # For non-private-equity accounts, just return the balance
        if account.account_type != AccountType.PRIVATE_EQUITY:
            return account.current_balance or Decimal(0)

        # Private equity without vesting schedule: return full balance
        if not account.vesting_schedule:
            return account.current_balance or Decimal(0)

        # Parse vesting schedule and calculate vested amount
        try:
            vesting_milestones = json.loads(account.vesting_schedule)
            if not isinstance(vesting_milestones, list):
                return account.current_balance or Decimal(0)

            today = utc_now().date()
            vested_quantity = Decimal(0)

            for milestone in vesting_milestones:
                vest_date_str = milestone.get("date")
                quantity = milestone.get("quantity", 0)

                if not vest_date_str:
                    continue

                try:
                    vest_date = datetime.strptime(vest_date_str, "%Y-%m-%d").date()
                    if vest_date <= today:
                        vested_quantity += Decimal(str(quantity))
                except (ValueError, TypeError):
                    continue

            # Calculate value: vested_quantity * share_price
            share_price = account.share_price or Decimal(0)
            vested_value = vested_quantity * share_price

            return vested_value

        except (json.JSONDecodeError, TypeError):
            # If vesting schedule is malformed, return full balance as fallback
            return account.current_balance or Decimal(0)

    async def get_total_assets(
        self, organization_id: str, account_ids: Optional[List[UUID]] = None
    ) -> Decimal:
        """Calculate total assets."""
        conditions = [Account.organization_id == organization_id, Account.is_active.is_(True)]
        if account_ids is not None:
            conditions.append(Account.id.in_(account_ids))

        result = await self.db.execute(select(Account).where(and_(*conditions)))
        accounts = result.scalars().all()

        # Filter for asset accounts using category property and respect include_in_networth
        total = Decimal(0)
        for account in accounts:
            if account.account_type.is_asset and self._should_include_in_networth(account):
                total += self._calculate_account_value(account)

        return total

    async def get_total_debts(
        self, organization_id: str, account_ids: Optional[List[UUID]] = None
    ) -> Decimal:
        """Calculate total debts."""
        conditions = [Account.organization_id == organization_id, Account.is_active.is_(True)]
        if account_ids is not None:
            conditions.append(Account.id.in_(account_ids))

        result = await self.db.execute(select(Account).where(and_(*conditions)))
        accounts = result.scalars().all()

        # Filter for debt accounts using category property and return absolute value for display
        return sum(
            (
                abs(account.current_balance or Decimal(0))
                for account in accounts
                if account.account_type.is_debt
            ),
            Decimal(0),
        )

    async def get_monthly_spending(
        self,
        organization_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        account_ids: Optional[List[UUID]] = None,
    ) -> Decimal:
        """Calculate total spending for the period (negative transactions)."""
        if not start_date:
            # Default to current month
            now = utc_now()
            start_date = date(now.year, now.month, 1)

        if not end_date:
            end_date = date.today()

        conditions = [
            Transaction.organization_id == organization_id,
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            Transaction.amount < 0,  # Expenses are negative
        ]
        if account_ids is not None:
            conditions.append(Transaction.account_id.in_(account_ids))

        result = await self.db.execute(
            select(func.sum(Transaction.amount)).where(and_(*conditions))
        )
        total = result.scalar()
        return abs(total) if total else Decimal(0)

    async def get_monthly_income(
        self,
        organization_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        account_ids: Optional[List[UUID]] = None,
    ) -> Decimal:
        """Calculate total income for the period (positive transactions)."""
        if not start_date:
            # Default to current month
            now = utc_now()
            start_date = date(now.year, now.month, 1)

        if not end_date:
            end_date = date.today()

        conditions = [
            Transaction.organization_id == organization_id,
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            Transaction.amount > 0,  # Income is positive
        ]
        if account_ids is not None:
            conditions.append(Transaction.account_id.in_(account_ids))

        result = await self.db.execute(
            select(func.sum(Transaction.amount)).where(and_(*conditions))
        )
        total = result.scalar()
        return total if total else Decimal(0)

    async def get_expense_by_category(
        self,
        organization_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 10,
        account_ids: Optional[List[UUID]] = None,
    ) -> List[Dict]:
        """Get top expense categories."""
        if not start_date:
            now = utc_now()
            start_date = date(now.year, now.month, 1)

        if not end_date:
            end_date = date.today()

        conditions = [
            Transaction.organization_id == organization_id,
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            Transaction.amount < 0,
            Transaction.category_primary.isnot(None),
        ]
        if account_ids is not None:
            conditions.append(Transaction.account_id.in_(account_ids))

        result = await self.db.execute(
            select(
                Transaction.category_primary,
                func.sum(Transaction.amount).label("total"),
                func.count(Transaction.id).label("count"),
            )
            .where(and_(*conditions))
            .group_by(Transaction.category_primary)
            .order_by(func.sum(Transaction.amount).asc())  # Most negative first
            .limit(limit)
        )

        categories = []
        for row in result:
            categories.append(
                {
                    "category": row.category_primary,
                    "total": abs(row.total),
                    "count": row.count,
                }
            )

        return categories

    async def get_recent_transactions(
        self, organization_id: str, limit: int = 10, account_ids: Optional[List[UUID]] = None
    ) -> List[Transaction]:
        """Get recent transactions."""
        conditions = [Transaction.organization_id == organization_id]
        if account_ids is not None:
            conditions.append(Transaction.account_id.in_(account_ids))

        result = await self.db.execute(
            select(Transaction)
            .options(
                joinedload(Transaction.labels).joinedload(TransactionLabel.label),
                joinedload(Transaction.account),
                joinedload(Transaction.category).joinedload(Category.parent),
            )
            .where(and_(*conditions))
            .order_by(Transaction.date.desc(), Transaction.created_at.desc())
            .limit(limit)
        )
        return result.unique().scalars().all()

    async def get_cash_flow_trend(
        self, organization_id: str, months: int = 6, account_ids: Optional[List[UUID]] = None
    ) -> List[Dict]:
        """Get income vs expenses trend over time."""
        end_date = date.today()
        start_date = end_date - timedelta(days=months * 30)

        # Get transactions grouped by month
        month_expr = func.date_trunc("month", Transaction.date)

        conditions = [
            Transaction.organization_id == organization_id,
            Transaction.date >= start_date,
            Transaction.date <= end_date,
        ]
        if account_ids is not None:
            conditions.append(Transaction.account_id.in_(account_ids))

        result = await self.db.execute(
            select(
                month_expr.label("month"),
                func.sum(case((Transaction.amount > 0, Transaction.amount), else_=0)).label(
                    "income"
                ),
                func.sum(case((Transaction.amount < 0, Transaction.amount), else_=0)).label(
                    "expenses"
                ),
            )
            .where(and_(*conditions))
            .group_by(month_expr)
            .order_by(month_expr)
        )

        trend = []
        for row in result:
            trend.append(
                {
                    "month": row.month.strftime("%Y-%m") if row.month else "",
                    "income": float(row.income or 0),
                    "expenses": abs(float(row.expenses or 0)),
                }
            )

        return trend

    async def get_account_balances(
        self, organization_id: str, account_ids: Optional[List[UUID]] = None
    ) -> List[Dict]:
        """Get all active account balances."""
        conditions = [Account.organization_id == organization_id, Account.is_active.is_(True)]
        if account_ids is not None:
            conditions.append(Account.id.in_(account_ids))

        result = await self.db.execute(
            select(Account).where(and_(*conditions)).order_by(Account.account_type, Account.name)
        )
        accounts = result.scalars().all()

        balances = []
        for account in accounts:
            balances.append(
                {
                    "id": str(account.id),
                    "name": account.name,
                    "type": account.account_type,
                    "balance": float(account.current_balance or 0),
                    "institution": account.institution_name,
                }
            )

        return balances
