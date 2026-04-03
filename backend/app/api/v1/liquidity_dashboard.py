"""Liquidity dashboard API endpoint — emergency fund coverage analysis."""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.financial import LIQUIDITY
from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.account import Account, AccountType
from app.models.user import User
from app.services.rate_limit_service import rate_limit_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Liquidity Dashboard"])

# Account types considered liquid
_LIQUID_TYPES = frozenset({
    AccountType.CHECKING,
    AccountType.SAVINGS,
    AccountType.MONEY_MARKET,
    AccountType.CD,
})

# Account types that are immediately accessible (not locked)
_IMMEDIATE_TYPES = frozenset({
    AccountType.CHECKING,
    AccountType.SAVINGS,
    AccountType.MONEY_MARKET,
})

_TARGET_MONTHS = LIQUIDITY.TARGET_EMERGENCY_FUND_MONTHS


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class LiquidAccount(BaseModel):
    account_id: str
    account_name: str
    account_type: str
    balance: float
    institution: Optional[str]
    is_accessible: bool


class LiquidityDashboardResponse(BaseModel):
    liquid_accounts: List[LiquidAccount]
    immediately_accessible: float
    total_liquid: float
    monthly_spending_used: float
    emergency_months_immediate: float
    emergency_months_total: float
    target_months: float
    coverage_gap: float
    grade: str
    grade_color: str
    recommendations: List[str]
    spending_is_estimated: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _grade(months_immediate: float) -> tuple[str, str]:
    """Return (letter_grade, color) based on months of immediately accessible funds."""
    if months_immediate >= 6:
        return "A", "green"
    if months_immediate >= 3:
        return "B", "blue"
    if months_immediate >= 1:
        return "C", "yellow"
    if months_immediate >= 0.5:
        return "D", "orange"
    return "F", "red"


def _recommendations(
    grade: str,
    months_immediate: float,
    immediately_accessible: float,
    total_liquid: float,
    monthly_spending: float,
) -> List[str]:
    recs: List[str] = []
    if grade == "A":
        recs.append("Your emergency fund is in excellent shape.")
        if total_liquid > immediately_accessible:
            recs.append(
                "Consider whether any CD or locked funds could be reallocated to higher-yield investments."
            )
    elif grade == "B":
        gap_amount = (6 - months_immediate) * monthly_spending
        recs.append(
            f"Add approximately ${gap_amount:,.0f} to reach 6 months of coverage (grade A)."
        )
        recs.append("Automate a monthly transfer to your savings account to close the gap.")
    elif grade == "C":
        recs.append(
            "Your immediate reserves cover less than 3 months — prioritise building your emergency fund."
        )
        recs.append(
            f"Target at least ${3 * monthly_spending:,.0f} in immediately accessible accounts."
        )
    elif grade == "D":
        recs.append("Critical: you have less than 1 month of immediately accessible savings.")
        recs.append("Pause non-essential spending and redirect cash to a liquid savings account.")
    else:
        recs.append("Emergency fund is critically low — any unexpected expense could require debt.")
        recs.append(
            f"Open a high-yield savings account and deposit at least ${monthly_spending:,.0f} immediately."
        )
    return recs


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.get("/liquidity", response_model=LiquidityDashboardResponse)
async def get_liquidity_dashboard(
    http_request: Request,
    monthly_spending: Optional[float] = Query(
        None,
        ge=0,
        description="Monthly spending estimate (USD). Defaults to configured default if not provided.",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return a liquidity / emergency fund coverage analysis.

    Queries checking, savings, money-market, and CD accounts. Grades
    the user's emergency fund coverage and provides targeted recommendations.
    """
    await rate_limit_service.check_rate_limit(
        request=http_request, max_requests=20, window_seconds=60, identifier=str(current_user.id)
    )
    spending_is_estimated = monthly_spending is None
    effective_spending = (
        monthly_spending if monthly_spending is not None
        else LIQUIDITY.DEFAULT_MONTHLY_SPENDING_ESTIMATE
    )

    result = await db.execute(
        select(Account).where(
            Account.organization_id == current_user.organization_id,
            Account.account_type.in_(list(_LIQUID_TYPES)),
            Account.is_active == True,  # noqa: E712
        )
    )
    raw_accounts = result.scalars().all()

    liquid_accounts: List[LiquidAccount] = []
    immediately_accessible = 0.0
    total_liquid = 0.0

    for acct in raw_accounts:
        balance = float(acct.current_balance or 0)
        is_accessible = acct.account_type in _IMMEDIATE_TYPES

        liquid_accounts.append(
            LiquidAccount(
                account_id=str(acct.id),
                account_name=acct.name,
                account_type=acct.account_type.value,
                balance=round(balance, 2),
                institution=acct.institution_name,
                is_accessible=is_accessible,
            )
        )

        total_liquid += balance
        if is_accessible:
            immediately_accessible += balance

    # Sort: immediately accessible first, then by balance descending
    liquid_accounts.sort(key=lambda a: (not a.is_accessible, -a.balance))

    months_immediate = (
        (immediately_accessible / effective_spending) if effective_spending > 0 else 0.0
    )
    months_total = (total_liquid / effective_spending) if effective_spending > 0 else 0.0
    coverage_gap = _TARGET_MONTHS - months_immediate  # negative means surplus

    grade, grade_color = _grade(months_immediate)
    recs = _recommendations(
        grade,
        months_immediate,
        immediately_accessible,
        total_liquid,
        effective_spending,
    )

    return LiquidityDashboardResponse(
        liquid_accounts=liquid_accounts,
        immediately_accessible=round(immediately_accessible, 2),
        total_liquid=round(total_liquid, 2),
        monthly_spending_used=round(effective_spending, 2),
        emergency_months_immediate=round(months_immediate, 2),
        emergency_months_total=round(months_total, 2),
        target_months=_TARGET_MONTHS,
        coverage_gap=round(coverage_gap, 2),
        grade=grade,
        grade_color=grade_color,
        recommendations=recs,
        spending_is_estimated=spending_is_estimated,
    )
