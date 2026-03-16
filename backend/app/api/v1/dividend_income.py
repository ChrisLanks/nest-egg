"""Dividend and investment income API endpoints."""

import logging
from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.dividend import IncomeType
from app.models.user import User
from app.schemas.dividend import (
    DividendIncomeCreate,
)
from app.services.dividend_income_service import DividendIncomeService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/summary")
async def get_dividend_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get portfolio-wide dividend income summary with trends."""
    service = DividendIncomeService(db)
    return await service.get_summary(
        organization_id=current_user.organization_id,
    )


@router.get("/")
async def list_dividend_income(
    account_id: Optional[UUID] = None,
    ticker: Optional[str] = None,
    income_type: Optional[IncomeType] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List dividend income records with optional filters."""
    service = DividendIncomeService(db)
    records = await service.list_income(
        organization_id=current_user.organization_id,
        account_id=account_id,
        ticker=ticker,
        income_type=income_type,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
    return records


@router.post("/", status_code=201)
async def create_dividend_income(
    data: DividendIncomeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record a dividend or investment income event."""
    service = DividendIncomeService(db)
    record = await service.create(
        organization_id=current_user.organization_id,
        data=data.model_dump(),
    )
    await db.commit()
    await db.refresh(record)
    return record


@router.delete("/{record_id}", status_code=204)
async def delete_dividend_income(
    record_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a dividend income record."""
    service = DividendIncomeService(db)
    deleted = await service.delete(
        organization_id=current_user.organization_id,
        record_id=record_id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Record not found")
    await db.commit()
