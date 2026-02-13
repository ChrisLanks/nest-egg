"""Dashboard service for financial summary calculations."""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.account import Account, AccountType
from app.models.transaction import Transaction, TransactionLabel


class DashboardService:
    """Service for calculating dashboard metrics."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_net_worth(self, organization_id: str) -> Decimal:
        """Calculate net worth (assets - debts)."""
        # Get all accounts
        result = await self.db.execute(
            select(Account).where(
                Account.organization_id == organization_id
            )
        )
        accounts = result.scalars().all()

        total = Decimal(0)
        for account in accounts:
            balance = account.current_balance or Decimal(0)

            # Asset accounts add to net worth
            if account.account_type in [AccountType.CHECKING, AccountType.SAVINGS, AccountType.BROKERAGE,
                                       AccountType.RETIREMENT_401K, AccountType.RETIREMENT_IRA,
                                       AccountType.HSA, AccountType.MANUAL]:
                total += balance
            # Debt accounts subtract from net worth (credit cards)
            elif account.account_type == AccountType.CREDIT_CARD:
                total -= abs(balance)

        return total

    async def get_total_assets(self, organization_id: str) -> Decimal:
        """Calculate total assets."""
        result = await self.db.execute(
            select(Account).where(
                Account.organization_id == organization_id,
                Account.account_type.in_([
                    AccountType.CHECKING, AccountType.SAVINGS, AccountType.BROKERAGE,
                    AccountType.RETIREMENT_401K, AccountType.RETIREMENT_IRA,
                    AccountType.HSA, AccountType.MANUAL
                ])
            )
        )
        accounts = result.scalars().all()

        return sum((account.current_balance or Decimal(0) for account in accounts), Decimal(0))

    async def get_total_debts(self, organization_id: str) -> Decimal:
        """Calculate total debts (accounts with negative balances)."""
        result = await self.db.execute(
            select(Account).where(
                Account.organization_id == organization_id,
                Account.account_type == AccountType.CREDIT_CARD
            )
        )
        accounts = result.scalars().all()

        # For credit cards, return absolute value of negative balances
        return sum((abs(account.current_balance or Decimal(0)) for account in accounts), Decimal(0))

    async def get_monthly_spending(
        self, 
        organization_id: str, 
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Decimal:
        """Calculate total spending for the period (negative transactions)."""
        if not start_date:
            # Default to current month
            now = datetime.utcnow()
            start_date = date(now.year, now.month, 1)
        
        if not end_date:
            end_date = date.today()

        result = await self.db.execute(
            select(func.sum(Transaction.amount)).where(
                Transaction.organization_id == organization_id,
                Transaction.date >= start_date,
                Transaction.date <= end_date,
                Transaction.amount < 0  # Expenses are negative
            )
        )
        total = result.scalar()
        return abs(total) if total else Decimal(0)

    async def get_monthly_income(
        self, 
        organization_id: str, 
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Decimal:
        """Calculate total income for the period (positive transactions)."""
        if not start_date:
            # Default to current month
            now = datetime.utcnow()
            start_date = date(now.year, now.month, 1)
        
        if not end_date:
            end_date = date.today()

        result = await self.db.execute(
            select(func.sum(Transaction.amount)).where(
                Transaction.organization_id == organization_id,
                Transaction.date >= start_date,
                Transaction.date <= end_date,
                Transaction.amount > 0  # Income is positive
            )
        )
        total = result.scalar()
        return total if total else Decimal(0)

    async def get_expense_by_category(
        self,
        organization_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 10
    ) -> List[Dict]:
        """Get top expense categories."""
        if not start_date:
            now = datetime.utcnow()
            start_date = date(now.year, now.month, 1)
        
        if not end_date:
            end_date = date.today()

        result = await self.db.execute(
            select(
                Transaction.category_primary,
                func.sum(Transaction.amount).label('total'),
                func.count(Transaction.id).label('count')
            )
            .where(
                Transaction.organization_id == organization_id,
                Transaction.date >= start_date,
                Transaction.date <= end_date,
                Transaction.amount < 0,
                Transaction.category_primary.isnot(None)
            )
            .group_by(Transaction.category_primary)
            .order_by(func.sum(Transaction.amount).asc())  # Most negative first
            .limit(limit)
        )
        
        categories = []
        for row in result:
            categories.append({
                'category': row.category_primary,
                'total': abs(float(row.total)),
                'count': row.count
            })
        
        return categories

    async def get_recent_transactions(
        self,
        organization_id: str,
        limit: int = 10
    ) -> List[Transaction]:
        """Get recent transactions."""
        result = await self.db.execute(
            select(Transaction)
            .options(
                joinedload(Transaction.labels).joinedload(TransactionLabel.label),
                joinedload(Transaction.account)
            )
            .where(Transaction.organization_id == organization_id)
            .order_by(Transaction.date.desc(), Transaction.created_at.desc())
            .limit(limit)
        )
        return result.unique().scalars().all()

    async def get_cash_flow_trend(
        self,
        organization_id: str,
        months: int = 6
    ) -> List[Dict]:
        """Get income vs expenses trend over time."""
        end_date = date.today()
        start_date = end_date - timedelta(days=months * 30)

        # Get transactions grouped by month
        month_expr = func.date_trunc('month', Transaction.date)

        result = await self.db.execute(
            select(
                month_expr.label('month'),
                func.sum(
                    case((Transaction.amount > 0, Transaction.amount), else_=0)
                ).label('income'),
                func.sum(
                    case((Transaction.amount < 0, Transaction.amount), else_=0)
                ).label('expenses')
            )
            .where(
                Transaction.organization_id == organization_id,
                Transaction.date >= start_date,
                Transaction.date <= end_date
            )
            .group_by(month_expr)
            .order_by(month_expr)
        )

        trend = []
        for row in result:
            trend.append({
                'month': row.month.strftime('%Y-%m') if row.month else '',
                'income': float(row.income or 0),
                'expenses': abs(float(row.expenses or 0))
            })

        return trend

    async def get_account_balances(self, organization_id: str) -> List[Dict]:
        """Get all account balances."""
        result = await self.db.execute(
            select(Account).where(
                Account.organization_id == organization_id
            ).order_by(Account.account_type, Account.name)
        )
        accounts = result.scalars().all()

        balances = []
        for account in accounts:
            balances.append({
                'id': str(account.id),
                'name': account.name,
                'type': account.account_type,
                'balance': float(account.current_balance or 0),
                'institution': account.institution_name
            })

        return balances
