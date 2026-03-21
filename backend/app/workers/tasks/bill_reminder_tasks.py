"""Celery task for bill payment reminders.

Runs daily at 8 AM UTC. For each active org, finds recurring transactions
marked as bills where the next expected date is within the reminder window,
then creates a LARGE_TRANSACTION notification (used as a bill reminder) unless
an identical reminder was already sent today (deduplication guard).
"""

import asyncio
import logging
from datetime import timedelta

from sqlalchemy import and_, func, select

from app.models.notification import Notification, NotificationPriority, NotificationType
from app.models.recurring_transaction import RecurringTransaction
from app.models.user import Organization, User
from app.services.notification_service import NotificationService
from app.utils.datetime_utils import utc_now
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

# Use LARGE_TRANSACTION as the closest available type for bill reminders
# (a dedicated BILL_REMINDER type does not exist in the current enum).
_BILL_REMINDER_TYPE = NotificationType.LARGE_TRANSACTION


@celery_app.task(name="send_bill_reminders")
def send_bill_reminders_task():
    """Send bill payment reminders to all active households. Runs at 8 AM daily."""
    asyncio.run(_send_bill_reminders_async())


async def _send_bill_reminders_async():
    """Async implementation of the bill reminder task."""
    from app.workers.utils import get_celery_session

    async with get_celery_session() as db:
        # Iterate all active organizations (same pattern as recap_tasks)
        orgs_result = await db.execute(
            select(Organization).where(Organization.is_active.is_(True))
        )
        orgs = orgs_result.scalars().all()

        for org in orgs:
            try:
                await _process_org_bills(db, org)
            except Exception as exc:
                logger.error(
                    "bill_reminder_failed",
                    extra={"org_id": str(org.id), "error": str(exc)},
                )

        await db.commit()


async def _process_org_bills(db, org) -> None:
    """Create bill reminder notifications for one organization."""
    today = utc_now().date()

    # Find active bills where next_expected_date is set
    bills_result = await db.execute(
        select(RecurringTransaction).where(
            and_(
                RecurringTransaction.organization_id == org.id,
                RecurringTransaction.is_bill.is_(True),
                RecurringTransaction.is_active.is_(True),
                RecurringTransaction.next_expected_date.isnot(None),
            )
        )
    )
    bills = bills_result.scalars().all()

    if not bills:
        return

    # Fetch any active org member to use as notification recipient
    users_result = await db.execute(
        select(User).where(
            User.organization_id == org.id,
            User.is_active.is_(True),
        )
    )
    org_users = users_result.scalars().all()
    if not org_users:
        return

    # Prefer org admin for the notification user_id so emails fire
    alert_user = next(
        (u for u in org_users if u.is_org_admin), org_users[0]
    )

    for bill in bills:
        days_until_due = (bill.next_expected_date - today).days

        # Should we remind? Trigger when we're within the reminder window
        # (days_until_due <= reminder_days_before) or overdue
        should_remind = days_until_due <= bill.reminder_days_before

        if not should_remind and days_until_due >= 0:
            continue

        # Deduplication: skip if a bill reminder notification for this recurring
        # transaction already exists today for this org (same entity_id + type + date)
        today_str = today.isoformat()
        existing_result = await db.execute(
            select(Notification.id)
            .where(
                and_(
                    Notification.organization_id == org.id,
                    Notification.type == _BILL_REMINDER_TYPE,
                    Notification.related_entity_id == bill.id,
                    func.date(Notification.created_at) == today_str,
                )
            )
            .limit(1)
        )
        if existing_result.scalar_one_or_none() is not None:
            logger.debug(
                "bill_reminder_skipped_duplicate",
                extra={"org_id": str(org.id), "bill_id": str(bill.id)},
            )
            continue

        # Build the notification
        if days_until_due < 0:
            urgency = "overdue"
            priority = NotificationPriority.HIGH
            due_label = f"{abs(days_until_due)} day(s) overdue"
        elif days_until_due == 0:
            urgency = "due today"
            priority = NotificationPriority.HIGH
            due_label = "due today"
        else:
            urgency = f"due in {days_until_due} day(s)"
            priority = NotificationPriority.MEDIUM
            due_label = f"due in {days_until_due} day(s)"

        title = f"Bill Reminder: {bill.merchant_name}"
        message = (
            f"Your bill to {bill.merchant_name} is {due_label}. "
            f"Expected amount: ${float(bill.average_amount):.2f} "
            f"(due {bill.next_expected_date.strftime('%b %d, %Y')})."
        )

        await NotificationService.create_notification(
            db=db,
            organization_id=org.id,
            user_id=alert_user.id,
            type=_BILL_REMINDER_TYPE,
            title=title,
            message=message,
            priority=priority,
            related_entity_type="recurring_transaction",
            related_entity_id=bill.id,
            action_url="/bills",
            action_label="View Bills",
            expires_in_days=3,
        )

        logger.info(
            "bill_reminder_created",
            extra={
                "org_id": str(org.id),
                "bill_id": str(bill.id),
                "merchant": bill.merchant_name,
                "urgency": urgency,
            },
        )
