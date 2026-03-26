"""RMD Planner API — multi-account Required Minimum Distribution projections."""

import datetime
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.financial import RMD as RMD_CONSTANTS, TAX
from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.account import Account
from app.models.user import User
from app.utils.account_type_groups import RMD_ACCOUNT_TYPES
from app.utils.rmd_calculator import calculate_rmd, requires_rmd

router = APIRouter(tags=["RMD Planner"])


class RmdAccountSummary(BaseModel):
    account_id: str
    name: str
    account_type: str
    current_balance: float


class RmdPerAccount(BaseModel):
    account_id: str
    projected_balance: float
    rmd_amount: float


class RmdYearPoint(BaseModel):
    year: int
    age: int
    total_rmd: float
    estimated_tax_on_rmd: float
    effective_rate_on_rmd: float
    per_account: List[RmdPerAccount]


class RmdPlannerResponse(BaseModel):
    current_age: Optional[int]
    rmd_start_age: int
    years_until_rmd: int
    total_current_rmd_balance: float
    accounts: List[RmdAccountSummary]
    projection: List[RmdYearPoint]
    total_lifetime_rmd_estimate: float
    total_lifetime_tax_estimate: float


def _marginal_rate(income: float, filing_status: str, year: int) -> float:
    """Estimate marginal federal rate from income and filing status."""
    tax_data = TAX.for_year(year)
    brackets = tax_data["BRACKETS_MARRIED"] if filing_status.lower() in ("married", "mfj") else tax_data["BRACKETS_SINGLE"]
    for threshold, rate in brackets:
        if income <= threshold:
            return rate
    return brackets[-1][1] if brackets else 0.22


@router.get("/rmd-planner", response_model=RmdPlannerResponse)
async def get_rmd_planner(
    projection_years: int = Query(default=20, ge=1, le=40),
    growth_rate: float = Query(default=0.06, ge=0.0, le=0.20),
    filing_status: str = Query(default="single"),
    other_annual_income: float = Query(default=50_000.0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Project annual RMDs across all pre-tax retirement accounts with tax impact."""
    today = datetime.date.today()
    current_year = today.year

    current_age: Optional[int] = None
    if current_user.birthdate:
        bd = current_user.birthdate
        current_age = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))

    # Fetch RMD-eligible accounts
    result = await db.execute(
        select(Account).where(
            Account.organization_id == current_user.organization_id,
            Account.account_type.in_(list(RMD_ACCOUNT_TYPES)),
            Account.is_active == True,
        )
    )
    accounts = result.scalars().all()

    account_summaries = [
        RmdAccountSummary(
            account_id=str(a.id),
            name=a.name or str(a.account_type.value),
            account_type=a.account_type.value,
            current_balance=float(a.current_balance or 0),
        )
        for a in accounts
    ]
    total_current_balance = sum(float(a.current_balance or 0) for a in accounts)

    rmd_start_age = RMD_CONSTANTS.TRIGGER_AGE
    years_until_rmd = max(0, rmd_start_age - current_age) if current_age else 0

    projection: List[RmdYearPoint] = []
    lifetime_rmd = 0.0
    lifetime_tax = 0.0

    # Track balances per account
    balances = {a.id: float(a.current_balance or 0) for a in accounts}

    for i in range(projection_years):
        year = current_year + i
        age = (current_age + i) if current_age is not None else rmd_start_age + i

        per_account_rmds: List[RmdPerAccount] = []
        total_rmd = 0.0

        for a in accounts:
            proj_bal = balances[a.id] * ((1 + growth_rate) ** i)
            rmd_amount = 0.0
            if requires_rmd(age):
                rmd_dec = calculate_rmd(Decimal(str(proj_bal)), age)
                if rmd_dec:
                    rmd_amount = float(rmd_dec)
            total_rmd += rmd_amount
            per_account_rmds.append(RmdPerAccount(
                account_id=str(a.id),
                projected_balance=round(proj_bal, 2),
                rmd_amount=round(rmd_amount, 2),
            ))

        # Estimate tax on RMD using marginal bracket
        taxable_income = other_annual_income + total_rmd
        rate = _marginal_rate(taxable_income, filing_status, year)
        tax_on_rmd = total_rmd * rate

        lifetime_rmd += total_rmd
        lifetime_tax += tax_on_rmd

        projection.append(RmdYearPoint(
            year=year,
            age=age,
            total_rmd=round(total_rmd, 2),
            estimated_tax_on_rmd=round(tax_on_rmd, 2),
            effective_rate_on_rmd=round(rate, 4),
            per_account=per_account_rmds,
        ))

    return RmdPlannerResponse(
        current_age=current_age,
        rmd_start_age=rmd_start_age,
        years_until_rmd=years_until_rmd,
        total_current_rmd_balance=total_current_balance,
        accounts=account_summaries,
        projection=projection,
        total_lifetime_rmd_estimate=round(lifetime_rmd, 2),
        total_lifetime_tax_estimate=round(lifetime_tax, 2),
    )
