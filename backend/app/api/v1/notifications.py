"""Notification API endpoints."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.notification import (
    NotificationResponse,
    UnreadCountResponse,
)
from app.services.notification_service import notification_service

router = APIRouter()


@router.get("/", response_model=List[NotificationResponse])
async def list_notifications(
    include_read: bool = False,
    limit: int = 50,
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
    from app.config import settings

    if settings.ENVIRONMENT == "production":
        raise HTTPException(status_code=404, detail="Not found")

    from app.models.notification import NotificationType, NotificationPriority
    from app.services.notification_service import NotificationService

    notification = await NotificationService.create_notification(
        db=db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        type=NotificationType.BUDGET_ALERT,
        title="Test Notification",
        message="This is a test notification to verify the notification system is working correctly. Click to view budgets.",
        priority=NotificationPriority.MEDIUM,
        action_url="/budgets",
        expires_in_days=7,
    )

    return notification
