"""Notification API endpoints."""

from collections import defaultdict
from datetime import timedelta
from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_current_user, get_db
from app.models.notification import Notification, NotificationPriority, NotificationType
from app.models.user import User
from app.schemas.notification import (
    NotificationResponse,
    UnreadCountResponse,
)
from app.services.notification_service import NotificationService, notification_service
from app.utils.datetime_utils import utc_now

router = APIRouter()


@router.get("/", response_model=List[NotificationResponse])
async def list_notifications(
    include_read: bool = False,
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all notifications for current user."""
    notifications = await notification_service.get_user_notifications(
        db=db,
        user=current_user,
        include_read=include_read,
        limit=limit,
    )
    return notifications


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get count of unread notifications."""
    count = await notification_service.get_unread_count(db=db, user=current_user)
    return {"count": count}


@router.get("/digest")
async def get_household_digest(
    days: int = Query(default=7, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a household notification digest.

    Returns notifications for the entire organization (not just the current user)
    over the past N days, grouped by notification type.
    """
    cutoff = utc_now() - timedelta(days=days)
    org_id = current_user.organization_id

    result = await db.execute(
        select(Notification)
        .where(
            and_(
                Notification.organization_id == org_id,
                Notification.created_at >= cutoff,
            )
        )
        .order_by(Notification.created_at.desc())
    )
    notifications = result.scalars().all()

    # Group by type
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for n in notifications:
        grouped[n.type.value].append(
            {
                "id": str(n.id),
                "user_id": str(n.user_id) if n.user_id else None,
                "title": n.title,
                "message": n.message,
                "priority": n.priority.value,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat(),
            }
        )

    return {
        "organization_id": str(org_id),
        "days": days,
        "total_notifications": len(notifications),
        "groups": {
            ntype: {
                "count": len(items),
                "notifications": items,
            }
            for ntype, items in grouped.items()
        },
    }


@router.patch("/{notification_id}/read")
async def mark_notification_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a notification as read."""
    notification = await notification_service.mark_as_read(
        db=db,
        notification_id=notification_id,
        user=current_user,
    )

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    return notification


@router.patch("/{notification_id}/dismiss")
async def dismiss_notification(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Dismiss a notification."""
    notification = await notification_service.mark_as_dismissed(
        db=db,
        notification_id=notification_id,
        user=current_user,
    )

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    return notification


@router.post("/mark-all-read")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all notifications as read."""
    count = await notification_service.mark_all_as_read(db=db, user=current_user)
    return {"marked_read": count}


@router.post("/test", response_model=NotificationResponse)
async def create_test_notification(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a test notification (for testing purposes). Disabled in production."""
    if settings.ENVIRONMENT == "production":
        raise HTTPException(status_code=404, detail="Not found")

    notification = await NotificationService.create_notification(
        db=db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        type=NotificationType.BUDGET_ALERT,
        title="Test Notification",
        message=(
            "This is a test notification to verify the"
            " notification system is working correctly."
            " Click to view budgets."
        ),
        priority=NotificationPriority.MEDIUM,
        action_url="/budgets",
        expires_in_days=7,
    )

    return notification
