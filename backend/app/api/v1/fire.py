"""FIRE (Financial Independence, Retire Early) API endpoints."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user, verify_household_member
from app.models.user import User
from app.services.fire_service import FireService
from app.services.permission_service import permission_service

logger = logging.getLogger(__name__)

router = APIRouter()


class FIRatioResponse(BaseModel):
    """FI ratio calculation result."""

    fi_ratio: float
    investable_assets: float
    annual_expenses: float
    fi_number: float


class SavingsRateResponse(BaseModel):
    """Savings rate calculation result."""

    savings_rate: float
    income: float
    spending: float
    savings: float
    months: int


class YearsToFIResponse(BaseModel):
    """Years to FI calculation result."""

    years_to_fi: Optional[float]
    fi_number: float
    investable_assets: float
    annual_savings: float
    withdrawal_rate: float
    expected_return: float
    already_fi: bool


class CoastFIResponse(BaseModel):
    """Coast FI calculation result."""

    coast_fi_number: float
    fi_number: float
    investable_assets: float
    is_coast_fi: bool
    retirement_age: int
    years_until_retirement: int
    expected_return: float


class FireMetricsResponse(BaseModel):
    """Complete FIRE metrics dashboard."""

    fi_ratio: FIRatioResponse
    savings_rate: SavingsRateResponse
    years_to_fi: YearsToFIResponse
    coast_fi: CoastFIResponse


@router.get("/metrics", response_model=FireMetricsResponse)
async def get_fire_metrics(
    user_id: Optional[UUID] = Query(
        None, description="Filter by user. None = combined household view"
    ),
    withdrawal_rate: float = Query(
        0.04, ge=0.01, le=0.10, description="Safe withdrawal rate (default 4%)"
    ),
    expected_return: float = Query(
        0.07, ge=0.0, le=0.20, description="Expected annual return (default 7%)"
    ),
    retirement_age: int = Query(
        65, ge=30, le=100, description="Target retirement age (default 65)"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all FIRE (Financial Independence) metrics.

    Returns FI ratio, savings rate, years to FI, and Coast FI calculations.
    """
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)
        await permission_service.require(
            db,
            actor=current_user,
            action="read",
            resource_type="fire_plan",
            owner_id=user_id,
        )

    service = FireService(db)
    metrics = await service.get_fire_dashboard(
        organization_id=current_user.organization_id,
        user_id=user_id,
        withdrawal_rate=withdrawal_rate,
        expected_return=expected_return,
        retirement_age=retirement_age,
    )

    return FireMetricsResponse(
        fi_ratio=FIRatioResponse(**metrics["fi_ratio"]),
        savings_rate=SavingsRateResponse(**metrics["savings_rate"]),
        years_to_fi=YearsToFIResponse(**metrics["years_to_fi"]),
        coast_fi=CoastFIResponse(**metrics["coast_fi"]),
    )
