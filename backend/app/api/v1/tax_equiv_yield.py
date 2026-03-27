"""Tax-Equivalent Yield calculator API."""

import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.financial import TAX
from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.account import Account, AccountType
from app.models.user import User

router = APIRouter(tags=["Tax-Equivalent Yield"])

# Account types that carry an interest rate / yield
_YIELD_ACCOUNT_TYPES = frozenset({
    AccountType.CD,
    AccountType.BOND,
    AccountType.I_BOND,
    AccountType.SAVINGS,
    AccountType.MONEY_MARKET,
})

_BOND_TYPES = frozenset({AccountType.BOND, AccountType.I_BOND})


class YieldHolding(BaseModel):
    account_id: str
    account_name: str
    account_type: str
    nominal_yield_pct: float      # As percentage (e.g. 4.5 for 4.5%)
    tax_equivalent_yield_pct: float
    current_balance: float
    annual_interest_income: float
    annual_tax_cost: float
    is_muni: bool


class TaxEquivYieldResponse(BaseModel):
    assumed_federal_rate_pct: float
    assumed_state_rate_pct: float
    combined_marginal_rate_pct: float
    holdings: List[YieldHolding]
    portfolio_blended_nominal_yield_pct: float
    portfolio_blended_tax_equiv_yield_pct: float
    total_fixed_income_value: float
    total_annual_interest: float
    total_annual_tax_cost: float


@router.get("/tax-equivalent-yield", response_model=TaxEquivYieldResponse)
async def get_tax_equivalent_yield(
    federal_rate_pct: Optional[float] = Query(default=None, ge=0, le=50, description="Override federal marginal rate (percent, e.g. 22)"),
    state_rate_pct: float = Query(default=5.0, ge=0, le=20, description="State income tax rate (percent)"),
    filing_status: str = Query(default="single"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Calculate tax-equivalent yield for fixed-income accounts."""
    today = datetime.date.today()

    # Resolve federal rate
    if federal_rate_pct is not None:
        fed_rate = federal_rate_pct / 100
    else:
        fed_rate = float(TAX.FEDERAL_MARGINAL_RATE)

    state_rate = state_rate_pct / 100
    combined_rate = fed_rate + state_rate

    result = await db.execute(
        select(Account).where(
            Account.organization_id == current_user.organization_id,
            Account.account_type.in_([t.value for t in _YIELD_ACCOUNT_TYPES]),
            Account.is_active == True,
        )
    )
    accounts = result.scalars().all()

    holdings: List[YieldHolding] = []
    total_value = 0.0
    total_interest = 0.0
    total_tax = 0.0

    for acct in accounts:
        nominal_pct = float(acct.interest_rate or 0)
        balance = float(acct.current_balance or 0)
        if nominal_pct == 0 or balance == 0:
            continue

        nominal = nominal_pct / 100
        is_muni = False  # Could be enhanced with ticker lookup later

        # Tax-equivalent yield: nominal / (1 - combined_rate)
        # For munis (tax-exempt), use same formula to show what taxable yield would be equivalent
        tax_equiv = nominal / (1 - combined_rate) if combined_rate < 1.0 else nominal
        annual_interest = balance * nominal
        annual_tax = annual_interest * combined_rate

        total_value += balance
        total_interest += annual_interest
        total_tax += annual_tax

        holdings.append(YieldHolding(
            account_id=str(acct.id),
            account_name=acct.name or str(acct.account_type.value),
            account_type=acct.account_type.value,
            nominal_yield_pct=round(nominal_pct, 3),
            tax_equivalent_yield_pct=round(tax_equiv * 100, 3),
            current_balance=round(balance, 2),
            annual_interest_income=round(annual_interest, 2),
            annual_tax_cost=round(annual_tax, 2),
            is_muni=is_muni,
        ))

    # Sort by tax-equivalent yield descending
    holdings.sort(key=lambda h: h.tax_equivalent_yield_pct, reverse=True)

    blended_nominal = (total_interest / total_value * 100) if total_value > 0 else 0.0
    blended_tax_equiv = (blended_nominal / 100 / (1 - combined_rate) * 100) if combined_rate < 1.0 else blended_nominal

    return TaxEquivYieldResponse(
        assumed_federal_rate_pct=round(fed_rate * 100, 2),
        assumed_state_rate_pct=round(state_rate * 100, 2),
        combined_marginal_rate_pct=round(combined_rate * 100, 2),
        holdings=holdings,
        portfolio_blended_nominal_yield_pct=round(blended_nominal, 3),
        portfolio_blended_tax_equiv_yield_pct=round(blended_tax_equiv, 3),
        total_fixed_income_value=round(total_value, 2),
        total_annual_interest=round(total_interest, 2),
        total_annual_tax_cost=round(total_tax, 2),
    )
