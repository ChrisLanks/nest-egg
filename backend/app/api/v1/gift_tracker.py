"""Gift tax annual exclusion tracker API endpoints."""

import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.financial import ESTATE
from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.gift_record import GiftRecord
from app.models.user import User
from app.services.rate_limit_service import rate_limit_service


async def _rate_limit(http_request: Request, current_user: User = Depends(get_current_user)):
    """Shared rate-limit dependency for gift tracker endpoints."""
    await rate_limit_service.check_rate_limit(
        request=http_request, max_requests=30, window_seconds=60, identifier=str(current_user.id)
    )


router = APIRouter(tags=["Gift Tracker"], dependencies=[Depends(_rate_limit)])


# ── Schemas ──────────────────────────────────────────────────────────────────

class GiftRecordCreate(BaseModel):
    recipient_name: str = Field(..., min_length=1, max_length=200)
    recipient_relationship: Optional[str] = Field(None, max_length=100)
    amount: float = Field(..., gt=0)
    date: str = Field(..., description="ISO date string YYYY-MM-DD")
    is_529_superfunding: bool = Field(False)
    notes: Optional[str] = None


class GiftRecordOut(BaseModel):
    id: str
    year: int
    recipient_name: str
    recipient_relationship: Optional[str]
    amount: float
    date: str
    is_529_superfunding: bool
    notes: Optional[str]


class RecipientSummary(BaseModel):
    recipient_name: str
    total_gifted: float
    remaining_exclusion: float
    gift_count: int


class GiftSummaryResponse(BaseModel):
    year: int
    annual_exclusion_limit: int
    total_gifts: float
    recipients: List[RecipientSummary]
    superfunding_active: bool
    superfunding_total: float
    lifetime_exemption_usage: float
    notes: List[str]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/gifts", response_model=GiftRecordOut, status_code=201)
async def create_gift(
    gift: GiftRecordCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record a new gift."""
    gift_date = datetime.date.fromisoformat(gift.date)
    record = GiftRecord(
        organization_id=current_user.organization_id,
        donor_user_id=current_user.id,
        year=gift_date.year,
        recipient_name=gift.recipient_name,
        recipient_relationship=gift.recipient_relationship,
        amount=Decimal(str(gift.amount)),
        date=gift_date,
        is_529_superfunding=gift.is_529_superfunding,
        notes=gift.notes,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return GiftRecordOut(
        id=str(record.id),
        year=record.year,
        recipient_name=record.recipient_name,
        recipient_relationship=record.recipient_relationship,
        amount=float(record.amount),
        date=record.date.isoformat(),
        is_529_superfunding=record.is_529_superfunding,
        notes=record.notes,
    )


@router.get("/gifts", response_model=List[GiftRecordOut])
async def list_gifts(
    year: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all gifts for the current user's organization."""
    conditions = [GiftRecord.organization_id == current_user.organization_id]
    if year:
        conditions.append(GiftRecord.year == year)
    result = await db.execute(
        select(GiftRecord).where(and_(*conditions)).order_by(GiftRecord.date.desc())
    )
    records = result.scalars().all()
    return [
        GiftRecordOut(
            id=str(r.id),
            year=r.year,
            recipient_name=r.recipient_name,
            recipient_relationship=r.recipient_relationship,
            amount=float(r.amount),
            date=r.date.isoformat(),
            is_529_superfunding=r.is_529_superfunding,
            notes=r.notes,
        )
        for r in records
    ]


@router.delete("/gifts/{gift_id}", status_code=204)
async def delete_gift(
    gift_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a gift record."""
    result = await db.execute(
        select(GiftRecord).where(
            GiftRecord.id == UUID(gift_id),
            GiftRecord.organization_id == current_user.organization_id,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Gift record not found")
    await db.delete(record)
    await db.commit()


@router.get("/gifts/summary", response_model=GiftSummaryResponse)
async def gift_summary(
    year: int = Query(default=None, description="Tax year; defaults to current year"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Summarize gifts for a year with remaining exclusion per recipient."""
    effective_year = year or datetime.date.today().year

    estate_data = ESTATE.for_year(effective_year)
    annual_limit = int(estate_data["ANNUAL_GIFT_EXCLUSION"])

    result = await db.execute(
        select(GiftRecord).where(
            GiftRecord.organization_id == current_user.organization_id,
            GiftRecord.year == effective_year,
        )
    )
    records = result.scalars().all()

    # Group by recipient
    by_recipient: dict[str, list] = {}
    superfunding_total = 0.0
    for r in records:
        by_recipient.setdefault(r.recipient_name, []).append(r)
        if r.is_529_superfunding:
            superfunding_total += float(r.amount)

    recipients = []
    total_gifts = 0.0
    lifetime_usage = 0.0
    for name, gifts in by_recipient.items():
        total = sum(float(g.amount) for g in gifts)
        total_gifts += total
        remaining = max(0, annual_limit - total)
        excess = max(0, total - annual_limit)
        lifetime_usage += excess
        recipients.append(RecipientSummary(
            recipient_name=name,
            total_gifted=round(total, 2),
            remaining_exclusion=round(remaining, 2),
            gift_count=len(gifts),
        ))

    superfunding_active = any(r.is_529_superfunding for r in records)

    notes = []
    if superfunding_active:
        notes.append(
            "529 superfunding election active: up to 5x annual exclusion "
            f"(${annual_limit * 5:,}) spread over 5 years."
        )
    if lifetime_usage > 0:
        notes.append(
            f"${lifetime_usage:,.0f} exceeds annual exclusion and counts against "
            "lifetime estate/gift tax exemption."
        )

    return GiftSummaryResponse(
        year=effective_year,
        annual_exclusion_limit=annual_limit,
        total_gifts=round(total_gifts, 2),
        recipients=recipients,
        superfunding_active=superfunding_active,
        superfunding_total=round(superfunding_total, 2),
        lifetime_exemption_usage=round(lifetime_usage, 2),
        notes=notes,
    )
