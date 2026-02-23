"""Recurring transactions API endpoints."""

from datetime import date, timedelta
from typing import List, Optional
from uuid import UUID

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.recurring_transaction import RecurringTransaction, RecurringFrequency
from app.models.user import User
from app.schemas.recurring_transaction import (
    RecurringTransactionCreate,
    RecurringTransactionUpdate,
    RecurringTransactionResponse,
    UpcomingBillResponse,
)
from app.services.recurring_detection_service import recurring_detection_service, RecurringDetectionService
from app.utils.datetime_utils import utc_now

router = APIRouter()


class CalendarEntry(BaseModel):
    """A single bill occurrence on the calendar."""

    date: date
    merchant_name: str
    amount: float
    recurring_transaction_id: str
    frequency: str


def _expand_occurrences(
    pattern: RecurringTransaction,
    start: date,
    end: date,
) -> list[date]:
    """Generate all occurrence dates for a recurring pattern within [start, end]."""
    anchor = pattern.next_expected_date
    if not anchor:
        return []

    freq = pattern.frequency

    # ON_DEMAND has no predictable schedule — skip calendar expansion
    if freq == RecurringFrequency.ON_DEMAND:
        return []

    occurrences: list[date] = []

    # Walk backward from anchor to find the first occurrence >= start
    # Then walk forward until > end
    def _step(d: date, forward: bool = True) -> date:
        delta = 1 if forward else -1
        if freq == RecurringFrequency.WEEKLY:
            return d + timedelta(weeks=delta)
        if freq == RecurringFrequency.BIWEEKLY:
            return d + timedelta(weeks=2 * delta)
        if freq == RecurringFrequency.MONTHLY:
            return d + relativedelta(months=delta)
        if freq == RecurringFrequency.QUARTERLY:
            return d + relativedelta(months=3 * delta)
        # YEARLY
        return d + relativedelta(years=delta)

    # Walk backward from anchor until before start
    first = anchor
    while first > start:
        first = _step(first, forward=False)
    # Now first <= start, so step forward once to get first >= start
    while first < start:
        first = _step(first, forward=True)

    # Walk forward collecting occurrences
    current = first
    while current <= end:
        occurrences.append(current)
        current = _step(current, forward=True)

    return occurrences


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


@router.get("/calendar", response_model=List[CalendarEntry])
async def get_calendar(
    days: int = Query(90, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Expand all active recurring transactions into individual occurrences within
    the next `days` days. Used by the bill calendar page.
    """
    today = date.today()
    end = today + timedelta(days=days)

    result = await db.execute(
        select(RecurringTransaction).where(
            and_(
                RecurringTransaction.organization_id == current_user.organization_id,
                RecurringTransaction.is_active.is_(True),
                RecurringTransaction.next_expected_date.isnot(None),
            )
        )
    )
    patterns = list(result.scalars().all())

    entries: list[CalendarEntry] = []
    for pattern in patterns:
        for occ_date in _expand_occurrences(pattern, today, end):
            entries.append(
                CalendarEntry(
                    date=occ_date,
                    merchant_name=pattern.merchant_name,
                    amount=float(abs(pattern.average_amount)),
                    recurring_transaction_id=str(pattern.id),
                    frequency=pattern.frequency.value,
                )
            )

    entries.sort(key=lambda e: e.date)
    return entries


class ApplyLabelRequest(BaseModel):
    retroactive: bool = True


@router.post("/{recurring_id}/apply-label")
async def apply_label_to_recurring(
    recurring_id: UUID,
    body: ApplyLabelRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Apply this bill's label to matching transactions.
    Creates the 'Recurring Bill' label for the org if one isn't set on the pattern.
    """
    result = await db.execute(
        select(RecurringTransaction).where(
            and_(
                RecurringTransaction.id == recurring_id,
                RecurringTransaction.organization_id == current_user.organization_id,
            )
        )
    )
    pattern = result.scalar_one_or_none()
    if not pattern:
        raise HTTPException(status_code=404, detail="Recurring pattern not found")

    # Ensure a label is assigned
    if pattern.label_id is None:
        label = await RecurringDetectionService.ensure_recurring_bill_label(
            db, current_user.organization_id
        )
        pattern.label_id = label.id
        pattern.updated_at = utc_now()

    applied = 0
    if body.retroactive:
        applied = await RecurringDetectionService.apply_label_to_matching_transactions(
            db,
            organization_id=current_user.organization_id,
            merchant_name=pattern.merchant_name,
            account_id=pattern.account_id,
            label_id=pattern.label_id,
        )

    await db.commit()
    await db.refresh(pattern)
    return {"applied_count": applied, "label_id": str(pattern.label_id)}


@router.get("/{recurring_id}/preview-label")
async def preview_label_matches(
    recurring_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return count of transactions that would be labelled for this recurring pattern."""
    result = await db.execute(
        select(RecurringTransaction).where(
            and_(
                RecurringTransaction.id == recurring_id,
                RecurringTransaction.organization_id == current_user.organization_id,
            )
        )
    )
    pattern = result.scalar_one_or_none()
    if not pattern:
        raise HTTPException(status_code=404, detail="Recurring pattern not found")

    count = await RecurringDetectionService.count_matching_transactions(
        db,
        organization_id=current_user.organization_id,
        merchant_name=pattern.merchant_name,
        account_id=pattern.account_id,
    )
    return {"matching_transactions": count}


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
