"""Celery tasks for recurring transaction detection."""

import logging
import random

from sqlalchemy import select

from app.models.user import User
from app.services.recurring_detection_service import RecurringDetectionService
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _retry_countdown(retries: int) -> float:
    """Exponential back-off with full jitter: 2^n * 60s ± 50 %.

    Keeps retry bursts from all workers hitting the DB simultaneously
    (thundering-herd prevention).
    """
    base = (2 ** retries) * 60  # 60s, 120s, 240s …
    return base * (0.5 + random.random())  # jitter: 50–150 % of base


@celery_app.task(
    name="detect_recurring_patterns",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=False,  # We apply our own jittered countdown
)
def detect_recurring_patterns_task(self=None):
    """
    Auto-detect recurring transactions for all organizations.
    Runs weekly on Monday at 2am.
    """
    import asyncio

    try:
        asyncio.run(_detect_recurring_async())
    except Exception as exc:
        retries = detect_recurring_patterns_task.request.retries if self else 0
        logger.warning(
            "detect_recurring_patterns retry %d/3: %s",
            retries + 1,
            exc,
        )
        raise detect_recurring_patterns_task.retry(
            exc=exc, countdown=_retry_countdown(retries)
        )


async def _detect_recurring_async():
    """Async implementation of recurring pattern detection."""
    from app.workers.utils import get_celery_session

    async with get_celery_session() as db:
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
