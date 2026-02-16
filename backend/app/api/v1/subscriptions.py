"""Subscriptions API endpoints."""

from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import (
    get_current_user,
    verify_household_member,
)
from app.models.user import User
from app.models.recurring_transaction import RecurringTransaction
from app.services.recurring_detection_service import RecurringDetectionService
from app.services.deduplication_service import DeduplicationService

router = APIRouter()

# Initialize deduplication service
deduplication_service = DeduplicationService()


class SubscriptionItem(BaseModel):
    """Individual subscription item."""
    id: UUID
    merchant_name: str
    average_amount: float
    frequency: str
    next_expected_date: Optional[date] = None
    confidence_score: float
    account_id: UUID
    occurrence_count: int


class SubscriptionSummary(BaseModel):
    """Summary of all subscriptions."""
    subscriptions: List[SubscriptionItem]
    total_count: int
    monthly_cost: float
    yearly_cost: float


@router.get("/", response_model=SubscriptionSummary)
async def get_subscriptions(
    user_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all active subscriptions."""
    # Verify household member if user_id provided
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)

    # Get subscriptions
    subscriptions = await RecurringDetectionService.get_subscriptions(
        db, current_user.organization_id, user_id
    )

    # Get summary
    summary = await RecurringDetectionService.get_subscription_summary(
        db, current_user.organization_id, user_id
    )

    # Convert to response model
    return SubscriptionSummary(
        subscriptions=[
            SubscriptionItem(
                id=sub.id,
                merchant_name=sub.merchant_name,
                average_amount=float(abs(sub.average_amount)),
                frequency=sub.frequency.value,
                next_expected_date=sub.next_expected_date,
                confidence_score=float(sub.confidence_score),
                account_id=sub.account_id,
                occurrence_count=sub.occurrence_count,
            )
            for sub in subscriptions
        ],
        **summary,
    )


@router.patch("/{subscription_id}/deactivate")
async def deactivate_subscription(
    subscription_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark subscription as inactive (not a subscription)."""
    # Get subscription
    result = await db.execute(
        select(RecurringTransaction).where(
            and_(
                RecurringTransaction.id == subscription_id,
                RecurringTransaction.organization_id == current_user.organization_id,
            )
        )
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    # Deactivate
    subscription.is_active = False
    await db.commit()

    return {"success": True, "message": "Subscription marked as inactive"}
