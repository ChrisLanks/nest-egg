"""Notification schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.models.notification import NotificationType, NotificationPriority


class NotificationBase(BaseModel):
    """Base notification schema."""

    type: NotificationType
    priority: NotificationPriority
    title: str
    message: str
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[UUID] = None
    action_url: Optional[str] = None
    action_label: Optional[str] = None


class NotificationCreate(NotificationBase):
    """Schema for creating a notification."""

    user_id: Optional[UUID] = None
    expires_in_days: Optional[int] = None


class NotificationResponse(NotificationBase):
    """Schema for notification response."""

    id: UUID
    organization_id: UUID
    user_id: Optional[UUID]
    is_read: bool
    is_dismissed: bool
    read_at: Optional[datetime]
    dismissed_at: Optional[datetime]
    created_at: datetime
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


class UnreadCountResponse(BaseModel):
    """Schema for unread count response."""

    count: int
