"""Recurring transactions API endpoints."""

from datetime import date, timedelta
from typing import List, Optional
from uuid import UUID

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db, get_user_accounts, verify_household_member
from app.models.account import Account
from app.models.recurring_transaction import RecurringFrequency, RecurringTransaction
from app.models.user import User
from app.schemas.recurring_transaction import (
    RecurringTransactionCreate,
    RecurringTransactionResponse,
    RecurringTransactionUpdate,
    UpcomingBillResponse,
)
from app.services.input_sanitization_service import input_sanitization_service
from app.services.rate_limit_service import rate_limit_service
from app.services.recurring_detection_service import (
    RecurringDetectionService,
    recurring_detection_service,
)
from app.utils.datetime_utils import utc_now


async def _rate_limit(http_request: Request, current_user: User = Depends(get_current_user)):
    """Shared rate-limit dependency for all endpoints in this module."""
    await rate_limit_service.check_rate_limit(
        request=http_request, max_requests=30, window_seconds=60, identifier=str(current_user.id)
    )


router = APIRouter(dependencies=[Depends(_rate_limit)])


class DetectResponse(BaseModel):
    detected_patterns: int
    patterns: list


class ApplyLabelResponse(BaseModel):
    applied_count: int
    label_id: str


class PreviewLabelResponse(BaseModel):
    matching_transactions: int


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


@router.post("/detect", response_model=DetectResponse)
async def detect_recurring_patterns(
    http_request: Request,
    min_occurrences: int = Query(3, ge=2, le=50),
    lookback_days: int = Query(180, ge=30, le=730),
    user_id: Optional[UUID] = Query(None, description="Filter by user"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Auto-detect recurring transaction patterns."""
    # Tighter limit for this potentially expensive detection operation
    await rate_limit_service.check_rate_limit(
        request=http_request,
        max_requests=10,
        window_seconds=60,
        identifier=str(current_user.id),
    )
    account_ids = None
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)
        user_accounts = await get_user_accounts(db, user_id, current_user.organization_id)
        account_ids = {acc.id for acc in user_accounts}

    patterns = await recurring_detection_service.detect_recurring_patterns(
        db=db,
        user=current_user,
        min_occurrences=min_occurrences,
        lookback_days=lookback_days,
        account_ids=account_ids,
    )

    return DetectResponse(
        detected_patterns=len(patterns),
        patterns=patterns,
    )


@router.post("/", response_model=RecurringTransactionResponse, status_code=201)
async def create_recurring_transaction(
    recurring_data: RecurringTransactionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a manually defined recurring transaction pattern."""
    # Enforce per-org limit to prevent spam / excessive notifications
    MAX_RECURRING_PER_ORG = 100
    count_result = await db.execute(
        select(func.count(RecurringTransaction.id)).where(
            and_(
                RecurringTransaction.organization_id == current_user.organization_id,
                RecurringTransaction.is_active.is_(True),
            )
        )
    )
    active_count = count_result.scalar_one()
    if active_count >= MAX_RECURRING_PER_ORG:
        raise HTTPException(
            status_code=422,
            detail=f"Organisation limit reached: maximum {MAX_RECURRING_PER_ORG} active recurring patterns allowed.",
        )

    # Sanitize user text input
    sanitized = recurring_data.model_dump()
    if sanitized.get("merchant_name"):
        sanitized["merchant_name"] = input_sanitization_service.sanitize_html(
            sanitized["merchant_name"]
        )
    pattern = await recurring_detection_service.create_manual_recurring(
        db=db,
        user=current_user,
        **sanitized,
    )
    return pattern


@router.get("/", response_model=List[RecurringTransactionResponse])
async def list_recurring_transactions(
    is_active: Optional[bool] = None,
    user_id: Optional[UUID] = Query(None, description="Filter by user"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all recurring transaction patterns."""
    account_ids = None
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)
        user_accounts = await get_user_accounts(db, user_id, current_user.organization_id)
        account_ids = {acc.id for acc in user_accounts}

    patterns = await recurring_detection_service.get_recurring_transactions(
        db=db,
        user=current_user,
        is_active=is_active,
        account_ids=account_ids,
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
    # Sanitize user text input
    sanitized = recurring_data.model_dump(exclude_unset=True)
    if sanitized.get("merchant_name"):
        sanitized["merchant_name"] = input_sanitization_service.sanitize_html(
            sanitized["merchant_name"]
        )
    pattern = await recurring_detection_service.update_recurring_transaction(
        db=db,
        recurring_id=recurring_id,
        user=current_user,
        **sanitized,
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
    user_id: Optional[UUID] = Query(None, description="Filter by user"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Expand all active recurring transactions into individual occurrences within
    the next `days` days. Used by the bill calendar page.
    """
    today = date.today()
    end = today + timedelta(days=days)

    conditions = [
        RecurringTransaction.organization_id == current_user.organization_id,
        RecurringTransaction.is_active.is_(True),
        RecurringTransaction.next_expected_date.isnot(None),
    ]

    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)
        user_accounts = await get_user_accounts(db, user_id, current_user.organization_id)
        account_ids = {acc.id for acc in user_accounts}
        conditions.append(RecurringTransaction.account_id.in_(account_ids))

    result = await db.execute(select(RecurringTransaction).where(and_(*conditions)))
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


@router.post("/{recurring_id}/apply-label", response_model=ApplyLabelResponse)
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
        select(RecurringTransaction)
        .join(Account, Account.id == RecurringTransaction.account_id)
        .where(
            and_(
                RecurringTransaction.id == recurring_id,
                RecurringTransaction.organization_id == current_user.organization_id,
                Account.user_id == current_user.id,
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
    return ApplyLabelResponse(applied_count=applied, label_id=str(pattern.label_id))


@router.get("/{recurring_id}/preview-label", response_model=PreviewLabelResponse)
async def preview_label_matches(
    recurring_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return count of transactions that would be labelled for this recurring pattern."""
    result = await db.execute(
        select(RecurringTransaction)
        .join(Account, Account.id == RecurringTransaction.account_id)
        .where(
            and_(
                RecurringTransaction.id == recurring_id,
                RecurringTransaction.organization_id == current_user.organization_id,
                Account.user_id == current_user.id,
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
    return PreviewLabelResponse(matching_transactions=count)


@router.get("/bills/upcoming", response_model=List[UpcomingBillResponse])
async def get_upcoming_bills(
    days_ahead: int = 30,
    user_id: Optional[UUID] = Query(None, description="Filter by user"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get upcoming bills within the specified time window."""
    bills = await recurring_detection_service.get_upcoming_bills(
        db=db,
        user=current_user,
        days_ahead=days_ahead,
        user_id=user_id,
    )
    return bills


# ── Bill Price Increases ────────────────────────────────────────────────────


class PriceIncreaseItem(BaseModel):
    id: str
    merchant_name: str
    frequency: str
    current_amount: float
    previous_amount: Optional[float]
    amount_change_pct: float
    annual_increase: Optional[float]
    annual_cost: float
    amount_change_detected_at: Optional[str]


class PriceAlertsResponse(BaseModel):
    price_increases: List[PriceIncreaseItem]
    total_annual_increase: float


@router.get("/price-increases", response_model=PriceAlertsResponse)
async def get_price_increases(
    user_id: Optional[UUID] = Query(
        None,
        description="Filter to a specific household member. Omit for combined view.",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return all active recurring transactions where the charge has increased
    by more than 5% compared to approximately 12 months ago.

    Supports household view scoping via user_id.
    """
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)

    from app.services.subscription_insights_service import SubscriptionInsightsService

    increases = await SubscriptionInsightsService.get_price_increases(
        db=db,
        organization_id=current_user.organization_id,
        user_id=user_id,
    )

    total_annual_increase = sum(item.get("annual_increase") or 0.0 for item in increases)

    return PriceAlertsResponse(
        price_increases=[PriceIncreaseItem(**item) for item in increases],
        total_annual_increase=round(total_annual_increase, 2),
    )
