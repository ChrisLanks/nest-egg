"""Celery tasks for cash flow forecast alerts."""

import logging
import random

from sqlalchemy import select

from app.models.user import User
from app.services.forecast_service import ForecastService
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _retry_countdown(retries: int) -> float:
    """Exponential back-off with full jitter (thundering-herd prevention)."""
    base = (2 ** retries) * 60
    return base * (0.5 + random.random())


@celery_app.task(
    name="check_cash_flow_forecast",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=False,
)
def check_cash_flow_forecast_task(self=None):
    """
    Check for negative balance projections and create alerts.
    Runs daily at 6:30am.
    """
    import asyncio

    try:
        asyncio.run(_check_forecast_async())
    except Exception as exc:
        retries = check_cash_flow_forecast_task.request.retries if self else 0
        logger.warning("check_cash_flow_forecast retry %d/3: %s", retries + 1, exc)
        raise check_cash_flow_forecast_task.retry(exc=exc, countdown=_retry_countdown(retries))


async def _check_forecast_async():
    """Async implementation of forecast checking."""
    from app.workers.utils import get_celery_session

    async with get_celery_session() as db:
        try:
            # Get all unique organization IDs
            result = await db.execute(select(User.organization_id).distinct())
            org_ids = [row[0] for row in result.all()]

            logger.info(f"Checking cash flow forecasts for {len(org_ids)} organizations")

            alerts_created = 0
            for org_id in org_ids:
                # Check for negative balance alerts (combined view)
                negative_day = await ForecastService.check_negative_balance_alert(
                    db, org_id, user_id=None
                )

                if negative_day:
                    alerts_created += 1
                    logger.info(
                        f"Created negative balance alert for org {org_id}: "
                        f"projected negative on {negative_day['date']}"
                    )

            logger.info(f"Forecast check complete. Total alerts created: {alerts_created}")

        except Exception as e:
            logger.error(f"Error checking cash flow forecasts: {str(e)}", exc_info=True)
            raise
