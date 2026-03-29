"""Credit score tracking API endpoints."""

import logging
from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.credit_score import CreditScore
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

SCORE_MIN = 300
SCORE_MAX = 850

PROVIDERS = ["Equifax", "TransUnion", "Experian", "FICO", "Other"]


# ── FICO score bands ──────────────────────────────────────────────────────────
def _score_band(score: int) -> str:
    """Return FICO credit score band label."""
    if score >= 800:
        return "Exceptional"
    if score >= 740:
        return "Very Good"
    if score >= 670:
        return "Good"
    if score >= 580:
        return "Fair"
    return "Poor"


# ── Schemas ───────────────────────────────────────────────────────────────────
class CreditScoreCreate(BaseModel):
    score: int = Field(..., ge=SCORE_MIN, le=SCORE_MAX, description="Credit score (300–850)")
    score_date: date = Field(..., description="Date the score was pulled")
    provider: str = Field(..., max_length=50, description="Bureau or scoring model")
    notes: Optional[str] = Field(None, max_length=500)


class CreditScoreResponse(BaseModel):
    id: UUID
    score: int
    score_date: date
    provider: str
    notes: Optional[str]
    band: str
    created_at: date

    class Config:
        from_attributes = True


class CreditScoreHistory(BaseModel):
    entries: List[CreditScoreResponse]
    latest_score: Optional[int]
    latest_band: Optional[str]
    change_from_previous: Optional[int]  # points change since second-to-last entry


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.get("/credit-scores", response_model=CreditScoreHistory)
async def get_credit_score_history(
    user_id: Optional[str] = Query(default=None, description="Household member user ID; defaults to current user"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get credit score history for the current user or a household member."""
    target_user_id = current_user.id
    if user_id and user_id != str(current_user.id):
        # Verify the target user belongs to this org
        member_result = await db.execute(
            select(User).where(
                User.id == UUID(user_id),
                User.organization_id == current_user.organization_id,
            )
        )
        member = member_result.scalar_one_or_none()
        if not member:
            raise HTTPException(status_code=404, detail="Household member not found")
        target_user_id = member.id

    result = await db.execute(
        select(CreditScore)
        .where(
            and_(
                CreditScore.organization_id == current_user.organization_id,
                CreditScore.user_id == target_user_id,
            )
        )
        .order_by(CreditScore.score_date.desc())
    )
    scores = result.scalars().all()

    entries = [
        CreditScoreResponse(
            id=s.id,
            score=s.score,
            score_date=s.score_date,
            provider=s.provider,
            notes=s.notes,
            band=_score_band(s.score),
            created_at=s.created_at.date(),
        )
        for s in scores
    ]

    latest_score = entries[0].score if entries else None
    latest_band = entries[0].band if entries else None
    change_from_previous = None
    if len(entries) >= 2:
        change_from_previous = entries[0].score - entries[1].score

    return CreditScoreHistory(
        entries=entries,
        latest_score=latest_score,
        latest_band=latest_band,
        change_from_previous=change_from_previous,
    )


@router.post("/credit-scores", response_model=CreditScoreResponse, status_code=201)
async def add_credit_score(
    body: CreditScoreCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a new credit score entry."""
    entry = CreditScore(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        score=body.score,
        score_date=body.score_date,
        provider=body.provider,
        notes=body.notes,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)

    return CreditScoreResponse(
        id=entry.id,
        score=entry.score,
        score_date=entry.score_date,
        provider=entry.provider,
        notes=entry.notes,
        band=_score_band(entry.score),
        created_at=entry.created_at.date(),
    )


@router.delete("/credit-scores/{score_id}", status_code=204)
async def delete_credit_score(
    score_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a credit score entry."""
    result = await db.execute(
        select(CreditScore).where(
            CreditScore.id == score_id,
            CreditScore.organization_id == current_user.organization_id,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Credit score entry not found")

    await db.delete(entry)
    await db.commit()
