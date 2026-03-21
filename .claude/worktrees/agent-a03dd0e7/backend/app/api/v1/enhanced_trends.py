"""Enhanced trends API — net worth history, investment performance, spending velocity."""

import logging
from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import (
    get_current_user,
    get_user_accounts,
    verify_household_member,
)
from app.models.user import User
from app.services.enhanced_trends_service import EnhancedTrendsService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/net-worth-history")
async def get_net_worth_history(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    user_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get net worth history time series with asset/liability breakdown."""
    service = EnhancedTrendsService(db)
    return await service.get_net_worth_history(
        organization_id=current_user.organization_id,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/investment-performance")
async def get_investment_performance(
    user_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get investment portfolio performance: total return, per-holding gains, winners/losers."""
    account_ids = None
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)
        user_accounts = await get_user_accounts(db, user_id, current_user.organization_id)
        account_ids = [acc.id for acc in user_accounts]

    service = EnhancedTrendsService(db)
    return await service.get_investment_performance(
        organization_id=current_user.organization_id,
        account_ids=account_ids,
    )


@router.get("/spending-velocity")
async def get_spending_velocity(
    months: int = Query(12, ge=3, le=60),
    user_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Analyze spending acceleration/deceleration: MoM change, trend direction."""
    service = EnhancedTrendsService(db)
    return await service.get_spending_velocity(
        organization_id=current_user.organization_id,
        months=months,
        user_id=user_id,
    )


@router.get("/cash-flow-history")
async def get_cash_flow_history(
    months: int = Query(12, ge=3, le=60),
    user_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get monthly cash flow (income vs expenses) time series with savings rate."""
    service = EnhancedTrendsService(db)
    return await service.get_cash_flow_history(
        organization_id=current_user.organization_id,
        months=months,
        user_id=user_id,
    )


@router.get("/investment-income-trend")
async def get_investment_income_trend(
    months: int = Query(24, ge=3, le=60),
    user_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get monthly dividend/investment income trend for charting."""
    account_ids = None
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)
        user_accounts = await get_user_accounts(db, user_id, current_user.organization_id)
        account_ids = [acc.id for acc in user_accounts]

    service = EnhancedTrendsService(db)
    return await service.get_investment_income_trend(
        organization_id=current_user.organization_id,
        months=months,
        account_ids=account_ids,
    )
