"""Service for managing user notifications."""

import logging
from datetime import timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, case, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationPriority, NotificationType
from app.models.user import User
from app.services.email_service import email_service
from app.utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)

# Maps preference category keys to the NotificationType values they cover.
# Missing category key in user prefs → all types in that category are shown.
NOTIFICATION_CATEGORY_TYPES: dict[str, list[str]] = {
    "account_syncs": [
        NotificationType.SYNC_FAILED,
        NotificationType.REAUTH_REQUIRED,
        NotificationType.SYNC_STALE,
        NotificationType.ACCOUNT_ERROR,
    ],
    "account_activity": [
        NotificationType.ACCOUNT_CONNECTED,
        NotificationType.LARGE_TRANSACTION,
        NotificationType.TRANSACTION_DUPLICATE,
    ],
    "budget_alerts": [
        NotificationType.BUDGET_ALERT,
        NotificationType.HSA_CONTRIBUTION_LIMIT,
        NotificationType.BILL_DUE_BEFORE_PAYCHECK,
    ],
    "goal_alerts": [
        NotificationType.GOAL_COMPLETED,
        NotificationType.GOAL_FUNDED,
    ],
    "milestones": [
        NotificationType.MILESTONE,
        NotificationType.ALL_TIME_HIGH,
        NotificationType.FIRE_COAST_FI,
        NotificationType.FIRE_INDEPENDENT,
        NotificationType.RMD_TAX_BOMB_WARNING,
        NotificationType.PRO_RATA_WARNING,
        NotificationType.NAV_FEATURE_UNLOCKED,
    ],
    "household": [
        NotificationType.HOUSEHOLD_MEMBER_JOINED,
        NotificationType.HOUSEHOLD_MEMBER_LEFT,
        NotificationType.RETIREMENT_SCENARIO_STALE,
    ],
    "weekly_recap": [
        NotificationType.WEEKLY_RECAP,
    ],
    "equity_alerts": [
        NotificationType.EQUITY_VESTING,
        NotificationType.EQUITY_AMT_WARNING,
    ],
    "crypto_alerts": [
        NotificationType.CRYPTO_PRICE_ALERT,
    ],
    "bond_alerts": [
        NotificationType.BOND_MATURITY_UPCOMING,
    ],
    "planning_alerts": [
        NotificationType.BENEFICIARY_MISSING,
        NotificationType.PENSION_ELECTION_DEADLINE,
        NotificationType.QCD_OPPORTUNITY,
    ],
    "portfolio_alerts": [
        NotificationType.REBALANCE_DRIFT_ALERT,
        NotificationType.TAX_BUCKET_IMBALANCE,
        NotificationType.HARVEST_OPPORTUNITY,
    ],
}


def _muted_types_for_user(prefs: dict | None) -> list[str]:
    """Return the list of NotificationType values the user has muted."""
    if not prefs:
        return []
    muted = []
    for category, types in NOTIFICATION_CATEGORY_TYPES.items():
        if prefs.get(category) is False:
            muted.extend(types)
    return muted


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

        # Email notification — track delivery status on the record
        email_attempted = False
        email_succeeded = False
        try:
            if email_service.is_configured and user_id:
                # Look up the user to check email preference
                user_result = await db.execute(select(User).where(User.id == user_id))
                user = user_result.scalar_one_or_none()
                if user and user.email_notifications_enabled and user.email:
                    email_attempted = True
                    await email_service.send_notification_email(
                        to_email=user.email,
                        title=title,
                        message=message,
                        action_url=action_url,
                        action_label=action_label,
                    )
                    email_succeeded = True
        except Exception as e:
            logger.warning(f"Failed to send notification email: {e}")

        # Persist delivery result so we have an audit trail
        if email_attempted:
            notification.email_sent = email_succeeded
            await db.commit()

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
                    Notification.user_id.is_(None),  # Org-wide notifications
                ),
                Notification.is_dismissed.is_(False),
                or_(Notification.expires_at.is_(None), Notification.expires_at > utc_now()),
            )
        )

        if not include_read:
            query = query.where(Notification.is_read.is_(False))

        # Exclude notification types the user has muted in their preferences
        muted = _muted_types_for_user(user.notification_preferences)
        if muted:
            query = query.where(Notification.type.notin_(muted))

        priority_order = case(
            (Notification.priority == NotificationPriority.URGENT, 0),
            (Notification.priority == NotificationPriority.HIGH, 1),
            (Notification.priority == NotificationPriority.MEDIUM, 2),
            (Notification.priority == NotificationPriority.LOW, 3),
            else_=4,
        )
        query = query.order_by(priority_order, Notification.created_at.desc()).limit(limit)

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
                    or_(Notification.user_id == user.id, Notification.user_id.is_(None)),
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
                    or_(Notification.user_id == user.id, Notification.user_id.is_(None)),
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
        """Mark all of the requesting user's personal notifications as read.

        Org-wide notifications (user_id=NULL) share a single is_read flag across
        all household members. Bulk-updating them here would mark them as read for
        every member, not just the caller. We intentionally scope this to
        user_id == user.id only; org-wide notifications can be dismissed
        individually via the per-notification endpoint.
        """
        stmt = (
            update(Notification)
            .where(
                and_(
                    Notification.organization_id == user.organization_id,
                    or_(Notification.user_id == user.id, Notification.user_id.is_(None)),
                    Notification.is_read.is_(False),
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
        query = (
            select(func.count())
            .select_from(Notification)
            .where(
                and_(
                    Notification.organization_id == user.organization_id,
                    or_(Notification.user_id == user.id, Notification.user_id.is_(None)),
                    Notification.is_read.is_(False),
                    Notification.is_dismissed.is_(False),
                    or_(Notification.expires_at.is_(None), Notification.expires_at > utc_now()),
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
            message = (
                f"Your connection to {account_name} has expired. "
                "Please reconnect to continue syncing."
            )
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
