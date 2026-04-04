"""Education planning API endpoints."""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user, get_filtered_accounts, verify_household_member
from app.services.rate_limit_service import rate_limit_service
from app.models.user import User
from app.services.education_planning_service import education_planning_service
from app.services.permission_service import permission_service

logger = logging.getLogger(__name__)



async def _rate_limit(http_request: Request, current_user: User = Depends(get_current_user)):
    """Shared rate-limit dependency for all endpoints in this module."""
    await rate_limit_service.check_rate_limit(
        request=http_request, max_requests=30, window_seconds=60, identifier=str(current_user.id)
    )

router = APIRouter(dependencies=[Depends(_rate_limit)])


# ------------------------------------------------------------------
# Response schemas
# ------------------------------------------------------------------


class EducationPlanAccount(BaseModel):
    """Summary of a 529 account for education planning."""

    account_id: str
    account_name: str
    current_balance: float
    monthly_contribution: float
    user_id: str


class EducationPlansResponse(BaseModel):
    """List of 529 accounts with basic info."""

    plans: List[EducationPlanAccount]
    total_529_savings: float


class ProjectionDataPoint(BaseModel):
    """A single year in the projection."""

    year: int
    projected_savings: float


class EducationProjectionResponse(BaseModel):
    """Full 529 projection result."""

    current_balance: float
    monthly_contribution: float
    years_until_college: int
    college_type: str
    annual_return: float
    projected_balance: float
    total_college_cost: float
    funding_percentage: float
    funding_gap: float
    funding_surplus: float
    recommended_monthly_to_close_gap: float
    projections: List[ProjectionDataPoint]


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------


@router.get("/plans", response_model=EducationPlansResponse)
async def list_education_plans(
    user_id: Optional[UUID] = Query(None, description="Filter by household member"),
    user_ids: Optional[List[UUID]] = Query(None, description="Multi-user filter"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all 529 accounts with education planning info for the organization."""
    target_user_id = None
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)
        await permission_service.require(
            db,
            actor=current_user,
            action="read",
            resource_type="education_plan",
            owner_id=user_id,
        )
        target_user_id = user_id

    plans = await education_planning_service.get_education_plans(
        db=db,
        organization_id=current_user.organization_id,
        user_id=target_user_id,
    )

    total_savings = sum(p["current_balance"] for p in plans)

    return EducationPlansResponse(
        plans=[EducationPlanAccount(**p) for p in plans],
        total_529_savings=round(total_savings, 2),
    )


@router.get("/projection", response_model=EducationProjectionResponse)
async def get_education_projection(
    current_balance: float = Query(..., ge=0, description="Current 529 balance"),
    monthly_contribution: float = Query(0, ge=0, description="Monthly contribution amount"),
    years_until_college: int = Query(..., ge=1, le=30, description="Years until college starts"),
    college_type: str = Query(
        "public_in_state",
        description="College type: public_in_state, public_out_of_state, private",
    ),
    annual_return: float = Query(
        0.06, ge=0, le=0.20, description="Expected annual return (decimal)"
    ),
    current_user: User = Depends(get_current_user),
):
    """
    Project 529 growth vs estimated college costs.

    Returns year-by-year projections, funding percentage, gap/surplus,
    and recommended monthly contribution to close any gap.
    """
    if college_type not in ("public_in_state", "public_out_of_state", "private"):
        college_type = "public_in_state"

    result = await education_planning_service.project_529(
        current_balance=current_balance,
        monthly_contribution=monthly_contribution,
        years_until_college=years_until_college,
        college_type=college_type,
        annual_return=annual_return,
    )

    return EducationProjectionResponse(**result)
