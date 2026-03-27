"""IRMAA & Medicare cost projection API."""

import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.financial import MEDICARE
from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter(tags=["IRMAA Projection"])


class IrmaaYearPoint(BaseModel):
    calendar_year: int
    age: Optional[int]
    projected_magi: float
    irmaa_tier: int  # 0 = base, 1-5 = surcharge tiers
    tier_label: str
    part_b_monthly: float
    part_d_monthly: float
    irmaa_surcharge_monthly: float
    total_monthly_premium: float
    total_annual_premium: float


class IrmaaProjectionResponse(BaseModel):
    current_tier: int
    current_tier_label: str
    years_until_medicare: int
    current_age: Optional[int]
    assumed_magi: float
    filing_status: str
    projection: List[IrmaaYearPoint]
    lifetime_premium_estimate: float
    optimization_tip: Optional[str]
    data_source: Optional[dict] = None  # DataSourceMeta — static/cached/live indicator


def _irmaa_tier(magi: float, brackets: list, married: bool, married_brackets: list | None = None) -> tuple[int, str, float, float]:
    """Return (tier_index, label, part_b_surcharge, part_d_surcharge)."""
    # Use proper married brackets when available, otherwise fall back to 2x single
    if married and married_brackets:
        effective_brackets = married_brackets
    elif married:
        effective_brackets = [(t * 2.0, b, d) for t, b, d in brackets]
    else:
        effective_brackets = brackets
    tier_labels = ["Base (no IRMAA)", "Tier 1", "Tier 2", "Tier 3", "Tier 4", "Tier 5"]
    for i, (threshold, b_surcharge, d_surcharge) in enumerate(effective_brackets):
        if magi <= threshold:
            return i, tier_labels[i], b_surcharge, d_surcharge
    # Above last bracket
    last = effective_brackets[-1]
    return len(effective_brackets) - 1, tier_labels[len(effective_brackets) - 1], last[1], last[2]


@router.get("/irmaa-projection", response_model=IrmaaProjectionResponse)
async def get_irmaa_projection(
    current_magi: float = Query(..., description="Current Modified Adjusted Gross Income"),
    filing_status: str = Query(default="single", description="single or married"),
    income_growth_rate: float = Query(default=0.03, ge=0.0, le=0.20),
    projection_years: int = Query(default=15, ge=1, le=40),
    user_id: Optional[str] = Query(default=None, description="Household member user ID; defaults to current user"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Project Medicare Part B/D premiums including IRMAA surcharges based on income trajectory."""
    import uuid as _uuid
    today = datetime.date.today()
    current_year = today.year

    # Resolve subject user
    subject_user = current_user
    if user_id and user_id != str(current_user.id):
        member_result = await db.execute(
            select(User).where(
                User.id == _uuid.UUID(user_id),
                User.organization_id == current_user.organization_id,
            )
        )
        member = member_result.scalar_one_or_none()
        if member:
            subject_user = member

    current_age: Optional[int] = None
    if subject_user.birthdate:
        bd = subject_user.birthdate
        current_age = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))

    married = filing_status.lower() in ("married", "mfj")
    years_until_medicare = max(0, MEDICARE.ELIGIBILITY_AGE - current_age) if current_age else 0

    # Current tier based on current MAGI
    med = MEDICARE.for_year(current_year)
    brackets = med["IRMAA_BRACKETS_SINGLE"]
    base_b = med["PART_B_MONTHLY"]
    base_d = med["PART_D_MONTHLY"]

    married_brackets = med.get("IRMAA_BRACKETS_MARRIED")
    tier_idx, tier_label, _, _ = _irmaa_tier(current_magi, brackets, married, married_brackets)

    projection: List[IrmaaYearPoint] = []
    lifetime_total = 0.0

    for i in range(projection_years + 1):
        proj_year = current_year + i
        age = (current_age + i) if current_age is not None else None

        # IRMAA uses income from 2 years prior
        income_year = proj_year - 2
        magi = current_magi * ((1 + income_growth_rate) ** max(0, income_year - current_year))

        med_y = MEDICARE.for_year(proj_year)
        br_y = med_y["IRMAA_BRACKETS_SINGLE"]
        mbr_y = med_y.get("IRMAA_BRACKETS_MARRIED")
        b_base_y = med_y["PART_B_MONTHLY"]
        d_base_y = med_y["PART_D_MONTHLY"]

        t_idx, t_label, b_surcharge, d_surcharge = _irmaa_tier(magi, br_y, married, mbr_y)

        total_b = b_base_y + b_surcharge
        total_d = d_base_y + d_surcharge
        surcharge = b_surcharge + d_surcharge
        total_monthly = total_b + total_d
        total_annual = total_monthly * 12

        # Only count years user is on Medicare
        if age is None or age >= MEDICARE.ELIGIBILITY_AGE:
            lifetime_total += total_annual

        projection.append(IrmaaYearPoint(
            calendar_year=proj_year,
            age=age,
            projected_magi=round(magi, 0),
            irmaa_tier=t_idx,
            tier_label=t_label,
            part_b_monthly=round(total_b, 2),
            part_d_monthly=round(total_d, 2),
            irmaa_surcharge_monthly=round(surcharge, 2),
            total_monthly_premium=round(total_monthly, 2),
            total_annual_premium=round(total_annual, 2),
        ))

    # Optimization tip
    tip = None
    if tier_idx >= 2:
        tip = "Roth conversions before Medicare eligibility can permanently reduce your MAGI and lower IRMAA surcharges."
    elif tier_idx == 1:
        tip = "You are in IRMAA Tier 1. Strategic Roth conversions or tax-loss harvesting may reduce MAGI below the threshold."

    return IrmaaProjectionResponse(
        current_tier=tier_idx,
        current_tier_label=tier_label,
        years_until_medicare=years_until_medicare,
        current_age=current_age,
        assumed_magi=current_magi,
        filing_status=filing_status,
        projection=projection,
        lifetime_premium_estimate=round(lifetime_total, 2),
        optimization_tip=tip,
    )
