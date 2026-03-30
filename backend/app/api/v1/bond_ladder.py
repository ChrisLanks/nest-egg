"""Bond / CD / TIPS Ladder Planning API endpoints."""

import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.financial import BOND_LADDER as BOND_LADDER_CONSTANTS
from app.core.cache import get as cache_get
from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.bond_ladder_service import build_ladder, estimate_cd_rates

router = APIRouter()

# Fallback treasury rates sourced from app.constants.financial.BOND_LADDER
_FALLBACK_TREASURY_RATES = BOND_LADDER_CONSTANTS.FALLBACK_TREASURY_RATES


class BondLadderRequest(BaseModel):
    total_investment: float = Field(..., gt=0, description="Total amount to invest")
    num_rungs: int = Field(5, ge=1, le=30, description="Number of ladder rungs")
    ladder_type: str = Field("treasury", description="cd, treasury, or tips")
    start_year: Optional[int] = Field(default=None, description="Year ladder starts; defaults to current year")
    annual_income_needed: float = Field(0, ge=0, description="Desired annual income")


@router.post("/plan")
async def plan_bond_ladder(
    request: BondLadderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Build a bond/CD/TIPS ladder plan using current Treasury rates."""
    # Resolve start_year dynamically
    start_year = request.start_year or datetime.date.today().year

    # Fetch current treasury rates
    cached = await cache_get("market_data:treasury_rates")
    if cached:
        treasury_rates = cached.get("rates", {})
    else:
        treasury_rates = dict(_FALLBACK_TREASURY_RATES)

    result = build_ladder(
        total_investment=Decimal(str(request.total_investment)),
        num_rungs=request.num_rungs,
        ladder_type=request.ladder_type.lower(),
        start_year=start_year,
        annual_income_needed=Decimal(str(request.annual_income_needed)),
        current_treasury_rates=treasury_rates,
    )

    return result


@router.get("/rates")
async def get_ladder_rates(
    current_user: User = Depends(get_current_user),
):
    """Return current Treasury rates with estimated CD rates."""
    cached = await cache_get("market_data:treasury_rates")
    if cached:
        treasury_rates = cached.get("rates", {})
    else:
        treasury_rates = {k: v for k, v in _FALLBACK_TREASURY_RATES.items()
                          if k in ("1_year", "2_year", "5_year", "10_year", "30_year")}

    cd_rates = estimate_cd_rates(treasury_rates)

    return {
        "treasury_rates": treasury_rates,
        "estimated_cd_rates": cd_rates,
        "source": "FRED / U.S. Treasury + CD spread estimates",
    }
