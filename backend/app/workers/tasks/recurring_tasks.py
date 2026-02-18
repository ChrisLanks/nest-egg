"""Celery tasks for recurring transaction detection."""

import logging
from sqlalchemy import select

from app.workers.celery_app import celery_app
from app.core.database import async_session_factory
from app.services.recurring_detection_service import RecurringDetectionService
from app.models.user import User

logger = logging.getLogger(__name__)


@celery_app.task(name="detect_recurring_patterns")
def detect_recurring_patterns_task():
    """
    Auto-detect recurring transactions for all organizations.
    Runs weekly on Monday at 2am.
    """
    import asyncio

    asyncio.run(_detect_recurring_async())


async def _detect_recurring_async():
    """Async implementation of recurring pattern detection."""
    async with async_session_factory() as db:
        try:
            # Get all unique organization IDs
            result = await db.execute(select(User.organization_id).distinct())
            org_ids = [row[0] for row in result.all()]

            logger.info(f"Detecting recurring patterns for {len(org_ids)} organizations")

            total_patterns = 0
            for org_id in org_ids:
                # Get any user from org for auth context
                user_result = await db.execute(
                    select(User).where(User.organization_id == org_id).limit(1)
                )
                user = user_result.scalar_one_or_none()

                if user:
                    # Detect patterns using existing service
                    # Look back 180 days, require 3+ occurrences
                    patterns = await RecurringDetectionService.detect_recurring_patterns(
                        db, user, min_occurrences=3, lookback_days=180
                    )
                    total_patterns += len(patterns)
                    logger.info(f"Detected {len(patterns)} recurring patterns for org {org_id}")

            logger.info(
                f"Recurring pattern detection complete. Total patterns detected: {total_patterns}"
            )

        except Exception as e:
            logger.error(f"Error detecting recurring patterns: {str(e)}", exc_info=True)
            raise
