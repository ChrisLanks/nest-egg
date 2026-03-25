"""
Tax bucket analysis API endpoints.
"""
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.tax_bucket_service import TaxBucketService

router = APIRouter(prefix="/tax-buckets", tags=["Tax Buckets"])


@router.get("/summary")
async def get_bucket_summary(
    user_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await TaxBucketService.get_bucket_summary(
        db, current_user.organization_id, user_id
    )


@router.get("/rmd-projection")
async def get_rmd_projection(
    pre_tax_balance: float = Query(...),
    current_age: int = Query(...),
    growth_rate: float = Query(0.06),
    current_user: User = Depends(get_current_user),
):
    return TaxBucketService.project_rmd_schedule(
        Decimal(str(pre_tax_balance)),
        current_age,
        Decimal(str(growth_rate)),
    )


@router.get("/roth-headroom")
async def get_roth_headroom(
    current_income: float = Query(...),
    filing_status: str = Query("single"),
    current_user: User = Depends(get_current_user),
):
    return TaxBucketService.get_roth_conversion_headroom(
        Decimal(str(current_income)),
        filing_status,
    )
