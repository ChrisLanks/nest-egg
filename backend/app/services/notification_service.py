"""Service for managing user notifications."""

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationType, NotificationPriority
from app.models.user import User
from app.utils.datetime_utils import utc_now


class NotificationService:
    """Service for creating and managing notifications."""

    @staticmethod
    async def create_notification(
        db: AsyncSession,
        organization_id: UUID,
        type: NotificationType,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        user_id: Optional[UUID] = None,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[UUID] = None,
        action_url: Optional[str] = None,
        action_label: Optional[str] = None,
        expires_in_days: Optional[int] = None,
    ) -> Notification:
        """
        Create a new notification.

        Args:
            db: Database session
            organization_id: Organization ID
            type: Notification type
            title: Short title
            message: Detailed message
            priority: Priority level
            user_id: Optional specific user (None = all org users)
            related_entity_type: Type of related entity ('account', 'transaction', etc.)
            related_entity_id: ID of related entity
            action_url: Optional URL for user action
            action_label: Label for action button
            expires_in_days: Auto-expire after N days

        Returns:
            Created notification
        """
        expires_at = None
        if expires_in_days:
            expires_at = utc_now() + timedelta(days=expires_in_days)

        notification = Notification(
            organization_id=organization_id,
            user_id=user_id,
            type=type,
            priority=priority,
            title=title,
            message=message,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            action_url=action_url,
            action_label=action_label,
            expires_at=expires_at,
        )

        db.add(notification)
        await db.commit()
        await db.refresh(notification)

        return notification

    @staticmethod
    async def get_user_notifications(
        db: AsyncSession,
        user: User,
        include_read: bool = False,
        limit: int = 50,
    ) -> List[Notification]:
        """
        Get notifications for a user.

        Args:
            db: Database session
            user: Current user
            include_read: Include already-read notifications
            limit: Maximum number to return

        Returns:
            List of notifications
        """
        query = select(Notification).where(
            and_(
                Notification.organization_id == user.organization_id,
                or_(
                    Notification.user_id == user.id,
                    Notification.user_id.is_(None)  # Org-wide notifications
                ),
                Notification.is_dismissed == False,
                or_(
                    Notification.expires_at.is_(None),
                    Notification.expires_at > utc_now()
                )
            )
        )

        if not include_read:
            query = query.where(Notification.is_read == False)

        query = query.order_by(
            Notification.priority.desc(),
            Notification.created_at.desc()
        ).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def mark_as_read(
        db: AsyncSession,
        notification_id: UUID,
        user: User,
    ) -> Optional[Notification]:
        """Mark notification as read."""
        result = await db.execute(
            select(Notification).where(
                and_(
                    Notification.id == notification_id,
                    Notification.organization_id == user.organization_id,
                )
            )
        )
        notification = result.scalar_one_or_none()

        if notification:
            notification.is_read = True
            notification.read_at = utc_now()
            await db.commit()
            await db.refresh(notification)

        return notification

    @staticmethod
    async def mark_as_dismissed(
        db: AsyncSession,
        notification_id: UUID,
        user: User,
    ) -> Optional[Notification]:
        """Dismiss notification."""
        result = await db.execute(
            select(Notification).where(
                and_(
                    Notification.id == notification_id,
                    Notification.organization_id == user.organization_id,
                )
            )
        )
        notification = result.scalar_one_or_none()

        if notification:
            notification.is_dismissed = True
            notification.dismissed_at = utc_now()
            await db.commit()
            await db.refresh(notification)

        return notification

    @staticmethod
    async def mark_all_as_read(
        db: AsyncSession,
        user: User,
    ) -> int:
        """Mark all user notifications as read."""
        from sqlalchemy import update

        stmt = (
            update(Notification)
            .where(
                and_(
                    Notification.organization_id == user.organization_id,
                    or_(
                        Notification.user_id == user.id,
                        Notification.user_id.is_(None)
                    ),
                    Notification.is_read == False,
                )
            )
            .values(is_read=True, read_at=utc_now())
        )

        result = await db.execute(stmt)
        await db.commit()

        return result.rowcount

    @staticmethod
    async def get_unread_count(
        db: AsyncSession,
        user: User,
    ) -> int:
        """Get count of unread notifications."""
        from sqlalchemy import func

        query = select(func.count()).select_from(Notification).where(
            and_(
                Notification.organization_id == user.organization_id,
                or_(
                    Notification.user_id == user.id,
                    Notification.user_id.is_(None)
                ),
                Notification.is_read == False,
                Notification.is_dismissed == False,
                or_(
                    Notification.expires_at.is_(None),
                    Notification.expires_at > utc_now()
                )
            )
        )

        result = await db.execute(query)
        return result.scalar() or 0

    @staticmethod
    async def create_account_sync_notification(
        db: AsyncSession,
        organization_id: UUID,
        account_id: UUID,
        account_name: str,
        error_message: str,
        needs_reauth: bool = False,
    ) -> Notification:
        """
        Create notification for account sync issue.

        Args:
            db: Database session
            organization_id: Organization ID
            account_id: Account with sync issue
            account_name: Account display name
            error_message: Error description
            needs_reauth: Whether reauth is required

        Returns:
            Created notification
        """
        if needs_reauth:
            type = NotificationType.REAUTH_REQUIRED
            title = f"Reconnect {account_name}"
            message = f"Your connection to {account_name} has expired. Please reconnect to continue syncing."
            action_label = "Reconnect Account"
            priority = NotificationPriority.HIGH
        else:
            type = NotificationType.SYNC_FAILED
            title = f"Sync Failed: {account_name}"
            message = f"Unable to sync {account_name}. {error_message}"
            action_label = "View Account"
            priority = NotificationPriority.MEDIUM

        return await NotificationService.create_notification(
            db=db,
            organization_id=organization_id,
            type=type,
            title=title,
            message=message,
            priority=priority,
            related_entity_type="account",
            related_entity_id=account_id,
            action_url=f"/accounts/{account_id}",
            action_label=action_label,
            expires_in_days=7,
        )


notification_service = NotificationService()
