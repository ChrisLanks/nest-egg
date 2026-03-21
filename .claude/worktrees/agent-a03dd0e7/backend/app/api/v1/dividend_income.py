"""Dividend and investment income API endpoints."""

import logging
from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import (
    get_current_user,
    get_user_accounts,
    verify_household_member,
)
from app.models.dividend import IncomeType
from app.models.user import User
from app.schemas.dividend import (
    DividendIncomeCreate,
)
from app.services.dividend_detection_service import DividendDetectionService
from app.services.dividend_income_service import DividendIncomeService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/summary")
async def get_dividend_summary(
    user_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get portfolio-wide dividend income summary with trends."""
    account_ids = None
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)
        user_accounts = await get_user_accounts(db, user_id, current_user.organization_id)
        account_ids = [acc.id for acc in user_accounts]

    service = DividendIncomeService(db)
    return await service.get_summary(
        organization_id=current_user.organization_id,
        account_ids=account_ids,
    )


@router.get("/")
async def list_dividend_income(
    account_id: Optional[UUID] = None,
    user_id: Optional[UUID] = None,
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
    user_account_ids = None
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)
        user_accounts = await get_user_accounts(db, user_id, current_user.organization_id)
        user_account_ids = [acc.id for acc in user_accounts]

    service = DividendIncomeService(db)
    records = await service.list_income(
        organization_id=current_user.organization_id,
        account_id=account_id,
        account_ids=user_account_ids,
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


@router.post("/detect", status_code=200)
async def detect_dividend_transactions(
    user_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Scan all existing transactions and auto-label dividend income.

    This is a backfill operation — useful after first linking accounts.
    Newly synced transactions are auto-detected during sync.
    If user_id is provided, only scans that user's accounts.
    """
    account_ids = None
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)
        user_accounts = await get_user_accounts(db, user_id, current_user.organization_id)
        account_ids = {acc.id for acc in user_accounts}

    detector = DividendDetectionService(db)
    count = await detector.backfill_organization(
        organization_id=current_user.organization_id,
        account_ids=account_ids,
    )
    await db.commit()
    return {"labeled_count": count}


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
