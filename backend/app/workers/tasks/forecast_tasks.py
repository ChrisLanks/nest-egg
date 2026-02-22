"""Celery tasks for cash flow forecast alerts."""

import logging
from sqlalchemy import select

from app.workers.celery_app import celery_app
from app.core.database import AsyncSessionLocal as async_session_factory
from app.services.forecast_service import ForecastService
from app.models.user import User

logger = logging.getLogger(__name__)


@celery_app.task(name="check_cash_flow_forecast")
def check_cash_flow_forecast_task():
    """
    Check for negative balance projections and create alerts.
    Runs daily at 6:30am.
    """
    import asyncio

    asyncio.run(_check_forecast_async())


async def _check_forecast_async():
    """Async implementation of forecast checking."""
    async with async_session_factory() as db:
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
