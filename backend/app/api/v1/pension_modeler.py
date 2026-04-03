"""Pension modeler API endpoint — lump-sum vs. annuity analysis."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.financial import PENSION_MODELER
from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.account import Account, AccountType
from app.models.user import User
from app.services.rate_limit_service import rate_limit_service

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic response schemas
# ---------------------------------------------------------------------------

class PensionAnalysis(BaseModel):
    account_id: str
    account_name: str
    account_type: str
    monthly_benefit: Optional[float]
    annual_benefit: Optional[float]
    lump_sum_value: Optional[float]
    cola_rate: Optional[float]
    survivor_monthly: Optional[float]
    break_even_years: Optional[float]
    lifetime_value_20yr: Optional[float]
    lifetime_value_25yr: Optional[float]
    years_of_service: Optional[float]
    recommendation: str
    recommendation_reason: str


class PensionModelerResponse(BaseModel):
    pensions: List[PensionAnalysis]
    total_monthly_income: float
    total_annual_income: float
    total_lump_sum_value: float
    has_cola_protection: bool
    summary: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PENSION_TYPES = {AccountType.PENSION, AccountType.ANNUITY}


def _analyze_pension(account: Account) -> PensionAnalysis:
    """Compute lump-sum vs. annuity analytics for a single pension/annuity account."""

    monthly = float(account.monthly_benefit) if account.monthly_benefit else None
    annual = monthly * 12 if monthly is not None else None
    lump_sum = float(account.pension_lump_sum_value) if account.pension_lump_sum_value else None
    cola_rate = float(account.pension_cola_rate) if account.pension_cola_rate else None
    survivor_pct = float(account.pension_survivor_pct) if account.pension_survivor_pct else None
    years_service = (
        float(account.pension_years_of_service) if account.pension_years_of_service else None
    )

    # Survivor monthly benefit
    survivor_monthly: Optional[float] = None
    if monthly is not None and survivor_pct is not None:
        survivor_monthly = monthly * (survivor_pct / 100.0)

    # Break-even years: how long until cumulative annuity > lump sum
    break_even_years: Optional[float] = None
    if monthly is not None and lump_sum is not None and annual and annual > 0:
        break_even_years = lump_sum / annual

    # Lifetime values (simplified — no discounting applied; COLA not compounded)
    lifetime_value_20yr: Optional[float] = None
    lifetime_value_25yr: Optional[float] = None
    if monthly is not None:
        lifetime_value_20yr = monthly * 12 * PENSION_MODELER.LIFETIME_VALUE_WINDOWS[0]
        lifetime_value_25yr = monthly * 12 * PENSION_MODELER.LIFETIME_VALUE_WINDOWS[1]

    # Recommendation logic
    if break_even_years is not None:
        if break_even_years < PENSION_MODELER.BREAK_EVEN_ANNUITY_HURDLE_YEARS:
            recommendation = "Take annuity"
            recommendation_reason = (
                f"Break-even at {break_even_years:.1f} years — the annuity pays off "
                "quickly, making it the better choice for most retirees."
            )
        elif break_even_years > PENSION_MODELER.BREAK_EVEN_LUMP_SUM_HURDLE_YEARS:
            recommendation = "Consider lump sum"
            recommendation_reason = (
                f"Break-even at {break_even_years:.1f} years — investing a lump sum "
                "may outperform the annuity if you have good health and investment options."
            )
        else:
            recommendation = "Borderline — depends on health and other income"
            recommendation_reason = (
                f"Break-even at {break_even_years:.1f} years. Consider longevity, "
                "other income sources, and whether a survivor benefit is needed."
            )
    elif monthly is not None and lump_sum is None:
        recommendation = "Annuity income only"
        recommendation_reason = "No lump-sum value on record — annuity payments are your option."
    elif lump_sum is not None and monthly is None:
        recommendation = "Lump sum available"
        recommendation_reason = (
            "No monthly benefit on record — evaluate rollover or annuitization options."
        )
    else:
        recommendation = "Insufficient data"
        recommendation_reason = (
            "Add monthly_benefit or pension_lump_sum_value to this account for analysis."
        )

    return PensionAnalysis(
        account_id=str(account.id),
        account_name=account.name,
        account_type=account.account_type.value,
        monthly_benefit=monthly,
        annual_benefit=annual,
        lump_sum_value=lump_sum,
        cola_rate=cola_rate,
        survivor_monthly=survivor_monthly,
        break_even_years=round(break_even_years, 2) if break_even_years is not None else None,
        lifetime_value_20yr=lifetime_value_20yr,
        lifetime_value_25yr=lifetime_value_25yr,
        years_of_service=years_service,
        recommendation=recommendation,
        recommendation_reason=recommendation_reason,
    )


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get("/pension-model", response_model=PensionModelerResponse)
async def get_pension_model(
    http_request: Request,
    user_id: Optional[str] = Query(default=None, description="Household member user ID; defaults to current user"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Lump-sum vs. annuity analysis for all PENSION and ANNUITY accounts.

    Returns break-even analysis, lifetime value estimates, and a plain-language
    recommendation for each pension account in the household.
    """
    await rate_limit_service.check_rate_limit(
        request=http_request, max_requests=20, window_seconds=60, identifier=str(current_user.id)
    )
    import uuid as _uuid

    # Resolve subject user
    conditions = [
        Account.organization_id == current_user.organization_id,
        Account.account_type.in_([t.value for t in _PENSION_TYPES]),
        Account.is_active.is_(True),  # noqa: E712
    ]
    if user_id:
        if user_id != str(current_user.id):
            member_result = await db.execute(
                select(User).where(
                    User.id == _uuid.UUID(user_id),
                    User.organization_id == current_user.organization_id,
                )
            )
            member = member_result.scalar_one_or_none()
            if not member:
                raise HTTPException(status_code=404, detail="Household member not found")
            conditions.append(Account.user_id == member.id)
        else:
            conditions.append(Account.user_id == current_user.id)

    result = await db.execute(
        select(Account).where(and_(*conditions))
        .order_by(Account.name)
    )
    accounts = result.scalars().all()

    pensions = [_analyze_pension(acct) for acct in accounts]

    total_monthly = sum(p.monthly_benefit for p in pensions if p.monthly_benefit is not None)
    total_annual = total_monthly * 12
    total_lump_sum = sum(p.lump_sum_value for p in pensions if p.lump_sum_value is not None)
    has_cola = any(p.cola_rate and p.cola_rate > 0 for p in pensions)

    if not pensions:
        summary = (
            "No pension or annuity accounts found. Add a PENSION or ANNUITY account with "
            "monthly_benefit or pension_lump_sum_value to run this analysis."
        )
    elif has_cola:
        summary = (
            f"Household pension income: ${total_monthly:,.0f}/month (${total_annual:,.0f}/yr). "
            "At least one pension includes COLA protection, helping maintain purchasing power."
        )
    else:
        summary = (
            f"Household pension income: ${total_monthly:,.0f}/month (${total_annual:,.0f}/yr). "
            "None of your pensions include COLA — inflation may erode real value over time."
        )

    return PensionModelerResponse(
        pensions=pensions,
        total_monthly_income=total_monthly,
        total_annual_income=total_annual,
        total_lump_sum_value=total_lump_sum,
        has_cola_protection=has_cola,
        summary=summary,
    )
