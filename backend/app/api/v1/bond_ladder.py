"""Bond / CD / TIPS Ladder Planning API endpoints."""

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.bond_ladder_service import build_ladder, estimate_cd_rates

router = APIRouter()


class BondLadderRequest(BaseModel):
    total_investment: float = Field(..., gt=0, description="Total amount to invest")
    num_rungs: int = Field(5, ge=1, le=30, description="Number of ladder rungs")
    ladder_type: str = Field("treasury", description="cd, treasury, or tips")
    start_year: int = Field(2026, description="Year ladder starts")
    annual_income_needed: float = Field(0, ge=0, description="Desired annual income")


@router.post("/plan")
async def plan_bond_ladder(
    request: BondLadderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Build a bond/CD/TIPS ladder plan using current Treasury rates."""
    # Fetch current treasury rates
    from app.api.v1.treasury_rates import _fetch_fred_rate, TREASURY_SERIES
    from app.core.cache import get as cache_get

    cached = await cache_get("market_data:treasury_rates")
    if cached:
        treasury_rates = cached.get("rates", {})
    else:
        # Use fallback rates
        treasury_rates = {
            "1_month": 0.0435, "3_month": 0.0430, "6_month": 0.0425,
            "1_year": 0.0420, "2_year": 0.0410, "5_year": 0.0400,
            "10_year": 0.0395, "30_year": 0.0410,
        }

    result = build_ladder(
        total_investment=Decimal(str(request.total_investment)),
        num_rungs=request.num_rungs,
        ladder_type=request.ladder_type.lower(),
        start_year=request.start_year,
        annual_income_needed=Decimal(str(request.annual_income_needed)),
        current_treasury_rates=treasury_rates,
    )

    return result


@router.get("/rates")
async def get_ladder_rates(
    current_user: User = Depends(get_current_user),
):
    """Return current Treasury rates with estimated CD rates."""
    from app.core.cache import get as cache_get

    cached = await cache_get("market_data:treasury_rates")
    if cached:
        treasury_rates = cached.get("rates", {})
    else:
        treasury_rates = {
            "1_year": 0.0420, "2_year": 0.0410, "5_year": 0.0400,
            "10_year": 0.0395, "30_year": 0.0410,
        }

    cd_rates = estimate_cd_rates(treasury_rates)

    return {
        "treasury_rates": treasury_rates,
        "estimated_cd_rates": cd_rates,
        "source": "FRED / U.S. Treasury + CD spread estimates",
    }
