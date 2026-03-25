"""Net worth attribution API endpoints.

Explains monthly net worth changes by attributing them to:
savings, investment contributions, debt paydown, and other flows.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.net_worth_attribution_service import NetWorthAttributionService

router = APIRouter()


@router.get("/monthly")
async def get_monthly_attribution(
    month: int = Query(..., ge=1, le=12, description="Month (1-12)"),
    year: int = Query(..., ge=2000, le=2100, description="Year"),
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get net worth attribution breakdown for a specific month.

    Returns how much of the net worth change came from:
    - savings (net deposits into cash/savings accounts)
    - investment_contributions (deposits into brokerage/retirement accounts)
    - debt_paydown (principal paid off)
    """
    result = await NetWorthAttributionService.calculate_monthly_attribution(
        db=db,
        organization_id=current_user.organization_id,
        user_id=user_id,
        month=month,
        year=year,
    )
    return result


@router.get("/history")
async def get_attribution_history(
    months: int = Query(12, ge=1, le=60, description="Number of months of history to return"),
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get net worth attribution history for the last N months.

    Returns a list of monthly attribution breakdowns, oldest first.
    """
    results = await NetWorthAttributionService.get_attribution_history(
        db=db,
        organization_id=current_user.organization_id,
        user_id=user_id,
        months=months,
    )
    return results
