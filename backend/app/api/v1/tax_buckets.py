"""
Tax bucket analysis API endpoints.
"""
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.financial import FIRE
from app.core.database import get_db
from app.dependencies import get_current_user, verify_household_member
from app.services.rate_limit_service import rate_limit_service
from app.models.user import User
from app.services.tax_bucket_service import TaxBucketService



async def _rate_limit(http_request: Request, current_user: User = Depends(get_current_user)):
    """Shared rate-limit dependency for all endpoints in this module."""
    await rate_limit_service.check_rate_limit(
        request=http_request, max_requests=30, window_seconds=60, identifier=str(current_user.id)
    )

router = APIRouter(prefix="/tax-buckets", tags=["Tax Buckets"], dependencies=[Depends(_rate_limit)])


@router.get("/summary", response_model=Dict[str, Any])
async def get_bucket_summary(
    user_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if user_id and user_id != current_user.id:
        await verify_household_member(db, user_id, current_user.organization_id)
    return await TaxBucketService.get_bucket_summary(
        db, current_user.organization_id, user_id
    )


@router.get("/rmd-projection", response_model=List[Dict[str, Any]])
async def get_rmd_projection(
    pre_tax_balance: float = Query(..., ge=0, le=50_000_000),
    current_age: int = Query(..., ge=0, le=120),
    growth_rate: float = Query(FIRE.DEFAULT_GROWTH_RATE, ge=0, le=1.0),
    current_user: User = Depends(get_current_user),
):
    return TaxBucketService.project_rmd_schedule(
        Decimal(str(pre_tax_balance)),
        current_age,
        Decimal(str(growth_rate)),
    )


@router.get("/roth-headroom", response_model=Dict[str, Any])
async def get_roth_headroom(
    current_income: float = Query(..., ge=0, le=10_000_000),
    filing_status: str = Query("single"),
    target_bracket_rate: float = Query(
        default=0.22,
        ge=0.0,
        le=0.50,
        description="Target bracket rate to optimize for (e.g. 0.22 for the 22% bracket). "
        "Defaults to 0.22.",
    ),
    current_user: User = Depends(get_current_user),
):
    return TaxBucketService.get_roth_conversion_headroom(
        Decimal(str(current_income)),
        filing_status,
        target_bracket_rate=Decimal(str(target_bracket_rate)),
    )