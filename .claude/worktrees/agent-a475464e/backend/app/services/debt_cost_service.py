"""
Debt Cost Service — true monthly interest cost breakdown across all debt accounts.

Uses account-level interest_rate and current_balance to compute:
  monthly_interest = |balance| * (annual_rate / 12)

For credit cards: estimates interest only on revolving (non-zero) balances.
"""

from __future__ import annotations

import logging
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account, AccountType

logger = logging.getLogger(__name__)

DEBT_ACCOUNT_TYPES = {
    AccountType.CREDIT_CARD,
    AccountType.LOAN,
    AccountType.STUDENT_LOAN,
    AccountType.MORTGAGE,
}


class DebtAccountCost(BaseModel):
    account_id: str
    account_name: str
    account_type: str
    balance: float
    interest_rate: Optional[float]  # annual, e.g. 0.0699
    monthly_interest_cost: float
    annual_interest_cost: float
    minimum_payment: Optional[float]


class DebtCostSummary(BaseModel):
    total_debt: float
    total_monthly_interest: float
    total_annual_interest: float
    accounts: List[DebtAccountCost]
    weighted_avg_rate: Optional[float]


class DebtCostService:
    """Calculate true interest cost across all debt accounts."""

    @staticmethod
    async def get_debt_cost(
        db: AsyncSession,
        organization_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> DebtCostSummary:
        """
        Return monthly interest cost breakdown for debt accounts.

        Scoped to user_id when provided (individual view) or all household
        accounts when None (combined view).
        """
        conditions = [
            Account.organization_id == organization_id,
            Account.account_type.in_(list(DEBT_ACCOUNT_TYPES)),
            Account.is_active.is_(True),
        ]
        if user_id:
            conditions.append(Account.user_id == user_id)

        result = await db.execute(
            select(Account).where(and_(*conditions)).order_by(Account.current_balance)
        )
        accounts = result.scalars().all()

        account_costs: List[DebtAccountCost] = []
        total_debt = 0.0
        total_monthly_interest = 0.0
        weighted_rate_numerator = 0.0

        for acct in accounts:
            balance = float(acct.current_balance or 0)
            abs_balance = abs(balance)
            rate = float(acct.interest_rate) if acct.interest_rate else None

            monthly_interest = (abs_balance * (rate / 12)) if rate and abs_balance > 0 else 0.0
            annual_interest = monthly_interest * 12

            account_costs.append(
                DebtAccountCost(
                    account_id=str(acct.id),
                    account_name=acct.name,
                    account_type=acct.account_type.value,
                    balance=round(balance, 2),
                    interest_rate=rate,
                    monthly_interest_cost=round(monthly_interest, 2),
                    annual_interest_cost=round(annual_interest, 2),
                    minimum_payment=(float(acct.minimum_payment) if acct.minimum_payment else None),
                )
            )

            total_debt += abs_balance
            total_monthly_interest += monthly_interest
            if rate and abs_balance > 0:
                weighted_rate_numerator += abs_balance * rate

        weighted_avg_rate = (
            round(weighted_rate_numerator / total_debt, 6) if total_debt > 0 else None
        )

        return DebtCostSummary(
            total_debt=round(total_debt, 2),
            total_monthly_interest=round(total_monthly_interest, 2),
            total_annual_interest=round(total_monthly_interest * 12, 2),
            accounts=account_costs,
            weighted_avg_rate=weighted_avg_rate,
        )
