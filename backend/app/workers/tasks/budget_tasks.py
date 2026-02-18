"""Celery tasks for budget alerts."""

import logging
from sqlalchemy import select

from app.workers.celery_app import celery_app
from app.core.database import async_session_factory
from app.services.budget_service import BudgetService
from app.models.user import User
from app.models.budget import Budget

logger = logging.getLogger(__name__)


@celery_app.task(name="check_budget_alerts")
def check_budget_alerts_task():
    """
    Check all active budgets and create notifications.
    Runs daily at midnight.
    """
    import asyncio

    asyncio.run(_check_budget_alerts_async())


async def _check_budget_alerts_async():
    """Async implementation of budget alert checking."""
    async with async_session_factory() as db:
        try:
            # Get all organizations with active budgets
            result = await db.execute(
                select(User.organization_id)
                .distinct()
                .join(Budget, User.organization_id == Budget.organization_id)
                .where(Budget.is_active.is_(True))
            )
            org_ids = [row[0] for row in result.all()]

            logger.info(f"Checking budgets for {len(org_ids)} organizations")

            total_alerts = 0
            for org_id in org_ids:
                # Get any user from org for auth context
                user_result = await db.execute(
                    select(User).where(User.organization_id == org_id).limit(1)
                )
                user = user_result.scalar_one_or_none()

                if user:
                    # This method already exists and creates notifications!
                    alerts = await BudgetService.check_budget_alerts(db, user)
                    total_alerts += len(alerts)
                    logger.info(f"Created {len(alerts)} budget alerts for org {org_id}")

            logger.info(f"Budget alert check complete. Total alerts created: {total_alerts}")

        except Exception as e:
            logger.error(f"Error checking budget alerts: {str(e)}", exc_info=True)
            raise
