"""Notification API endpoints."""

from collections import defaultdict
from datetime import timedelta
from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_current_admin_user, get_current_user, get_db
from app.models.notification import Notification, NotificationPriority, NotificationType
from app.models.user import User
from pydantic import BaseModel
from app.schemas.notification import (
    NotificationCreate,
    NotificationResponse,
    UnreadCountResponse,
)


class MarkAllReadResponse(BaseModel):
    marked_read: int
from app.services.notification_service import NotificationService, notification_service
from app.services.rate_limit_service import rate_limit_service as _rate_limit_svc
from app.utils.datetime_utils import utc_now


async def _rate_limit(http_request: Request, current_user: User = Depends(get_current_user)):
    """Shared rate-limit dependency for notification endpoints."""
    await _rate_limit_svc.check_rate_limit(
        request=http_request, max_requests=60, window_seconds=60, identifier=str(current_user.id)
    )


router = APIRouter(dependencies=[Depends(_rate_limit)])


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


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
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


@router.patch("/{notification_id}/dismiss", response_model=NotificationResponse)
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


@router.post("/mark-all-read", response_model=MarkAllReadResponse)
async def mark_all_notifications_read(
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all notifications as read."""
    # Additional tighter limit for this bulk-write operation (10/min vs 60/min default)
    await _rate_limit_svc.check_rate_limit(
        request=http_request,
        max_requests=10,
        window_seconds=60,
        identifier=str(current_user.id),
    )
    count = await notification_service.mark_all_as_read(db=db, user=current_user)
    return MarkAllReadResponse(marked_read=count)


@router.post("/", response_model=NotificationResponse)
async def create_notification(
    payload: NotificationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Persist a notification created by the frontend (e.g. from a toast).

    The notification is scoped to the calling user's organization and attributed
    to the calling user unless ``user_id`` is explicitly provided in the payload
    (in which case the caller must belong to the same organization).
    """
    target_user_id = payload.user_id if payload.user_id is not None else current_user.id

    notification = await NotificationService.create_notification(
        db=db,
        organization_id=current_user.organization_id,
        user_id=target_user_id,
        type=payload.type,
        title=payload.title,
        message=payload.message,
        priority=payload.priority,
        related_entity_type=payload.related_entity_type,
        related_entity_id=payload.related_entity_id,
        action_url=payload.action_url,
        action_label=payload.action_label,
        expires_in_days=payload.expires_in_days,
    )
    return notification


@router.post("/test", response_model=NotificationResponse)
async def create_test_notification(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a test notification (for testing purposes). Admin only; disabled in production."""
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
