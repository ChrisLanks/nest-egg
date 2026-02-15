"""Recurring transactions API endpoints."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.recurring_transaction import (
    RecurringTransactionCreate,
    RecurringTransactionUpdate,
    RecurringTransactionResponse,
    UpcomingBillResponse,
)
from app.services.recurring_detection_service import recurring_detection_service

router = APIRouter()


@router.post("/detect")
async def detect_recurring_patterns(
    min_occurrences: int = 3,
    lookback_days: int = 180,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Auto-detect recurring transaction patterns."""
    patterns = await recurring_detection_service.detect_recurring_patterns(
        db=db,
        user=current_user,
        min_occurrences=min_occurrences,
        lookback_days=lookback_days,
    )

    return {
        "detected_patterns": len(patterns),
        "patterns": patterns,
    }


@router.post("/", response_model=RecurringTransactionResponse, status_code=201)
async def create_recurring_transaction(
    recurring_data: RecurringTransactionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a manually defined recurring transaction pattern."""
    pattern = await recurring_detection_service.create_manual_recurring(
        db=db,
        user=current_user,
        **recurring_data.model_dump(),
    )
    return pattern


@router.get("/", response_model=List[RecurringTransactionResponse])
async def list_recurring_transactions(
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all recurring transaction patterns."""
    patterns = await recurring_detection_service.get_recurring_transactions(
        db=db,
        user=current_user,
        is_active=is_active,
    )
    return patterns


@router.patch("/{recurring_id}", response_model=RecurringTransactionResponse)
async def update_recurring_transaction(
    recurring_id: UUID,
    recurring_data: RecurringTransactionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a recurring transaction pattern."""
    pattern = await recurring_detection_service.update_recurring_transaction(
        db=db,
        recurring_id=recurring_id,
        user=current_user,
        **recurring_data.model_dump(exclude_unset=True),
    )

    if not pattern:
        raise HTTPException(status_code=404, detail="Recurring pattern not found")

    return pattern


@router.delete("/{recurring_id}", status_code=204)
async def delete_recurring_transaction(
    recurring_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a recurring transaction pattern."""
    success = await recurring_detection_service.delete_recurring_transaction(
        db=db,
        recurring_id=recurring_id,
        user=current_user,
    )

    if not success:
        raise HTTPException(status_code=404, detail="Recurring pattern not found")


@router.get("/bills/upcoming", response_model=List[UpcomingBillResponse])
async def get_upcoming_bills(
    days_ahead: int = 30,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get upcoming bills within the specified time window."""
    bills = await recurring_detection_service.get_upcoming_bills(
        db=db,
        user=current_user,
        days_ahead=days_ahead,
    )
    return bills
