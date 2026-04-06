"""Capital gains harvesting API endpoints."""

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user, get_filtered_accounts
from app.services.rate_limit_service import rate_limit_service
from app.models.user import User
from app.services.capital_gains_harvesting_service import CapitalGainsHarvestingService

logger = logging.getLogger(__name__)



async def _rate_limit(http_request: Request, current_user: User = Depends(get_current_user)):
    """Shared rate-limit dependency for all endpoints in this module."""
    await rate_limit_service.check_rate_limit(
        request=http_request, max_requests=30, window_seconds=60, identifier=str(current_user.id)
    )

router = APIRouter(dependencies=[Depends(_rate_limit)])


@router.get(
    "/bracket-fill",
    summary="LTCG 0% bracket room",
    description=(
        "Returns how much long-term capital gain can be realized at 0% federal rate "
        "given the user's current taxable income and filing status."
    ),
    response_model=Dict[str, Any],
)
async def get_ltcg_bracket_fill(
    current_income: float = Query(..., description="Current taxable income (USD)"),
    filing_status: str = Query("single", description="Filing status: single, married_filing_jointly, etc."),
    tax_year: Optional[int] = Query(None, description="Tax year (defaults to current year)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns 0% LTCG bracket room for the given income and filing status."""
    return await CapitalGainsHarvestingService.get_ltcg_bracket_fill(
        db=db,
        organization_id=current_user.organization_id,
        current_taxable_income=Decimal(str(current_income)),
        filing_status=filing_status,
        tax_year=tax_year,
    )


@router.get(
    "/candidates",
    summary="Long-term gain harvest candidates",
    description=(
        "Returns open tax lots held > 365 days with unrealized gains above min_gain, "
        "sorted by largest gain first."
    ),
    response_model=List[Dict[str, Any]],
)
async def get_harvest_candidates(
    min_gain: float = Query(500.0, description="Minimum unrealized gain threshold (USD)"),
    user_id: Optional[UUID] = Query(None, description="Filter to a specific user (household member)"),
    user_ids: Optional[List[UUID]] = Query(None, description="Multi-user filter"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns tax lots eligible for gain harvesting at the 0% LTCG rate."""
    return await CapitalGainsHarvestingService.get_harvest_candidates(
        db=db,
        organization_id=current_user.organization_id,
        user_id=user_id,
        min_gain=Decimal(str(min_gain)),
    )


@router.get(
    "/ytd-realized",
    summary="Year-to-date realized gains",
    description="Returns realized short-term and long-term gains from closed tax lots for a given tax year.",
    response_model=Dict[str, Any],
)
async def get_ytd_realized_gains(
    tax_year: Optional[int] = Query(None, description="Tax year (defaults to current year)"),
    user_id: Optional[UUID] = Query(None, description="Filter to a specific user (household member)"),
    user_ids: Optional[List[UUID]] = Query(None, description="Multi-user filter"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns YTD realized STCG and LTCG from closed tax lots."""
    return await CapitalGainsHarvestingService.get_ytd_realized_gains(
        db=db,
        organization_id=current_user.organization_id,
        user_id=user_id,
        tax_year=tax_year,
    )