"""Celery tasks for holdings snapshots."""

import logging
from sqlalchemy import select
from datetime import date

from app.workers.celery_app import celery_app
from app.core.database import async_session_factory
from app.models.user import User
from app.services.snapshot_service import snapshot_service
from app.dependencies import get_all_household_accounts
from app.services.deduplication_service import deduplication_service

logger = logging.getLogger(__name__)


@celery_app.task(name="capture_daily_holdings_snapshot")
def capture_daily_holdings_snapshot_task():
    """
    Capture daily holdings snapshot for all organizations.
    Runs daily at 11:59 PM to capture end-of-day values.
    """
    import asyncio
    asyncio.run(_capture_snapshots_async())


async def _capture_snapshots_async():
    """Async implementation of holdings snapshot capture."""
    async with async_session_factory() as db:
        try:
            # Get all organizations
            result = await db.execute(select(User.organization_id).distinct())
            org_ids = [row[0] for row in result.all()]

            logger.info(f"Capturing holdings snapshots for {len(org_ids)} organizations")

            today = date.today()
            total_snapshots = 0

            for org_id in org_ids:
                try:
                    # Get any user from this organization
                    user_result = await db.execute(
                        select(User)
                        .where(User.organization_id == org_id)
                        .limit(1)
                    )
                    user = user_result.scalar_one_or_none()

                    if not user:
                        logger.warning(f"No users found for org {org_id}")
                        continue

                    # Import get_portfolio_summary from holdings API
                    from app.api.v1.holdings import get_portfolio_summary

                    # Get current portfolio summary (this handles all the complex logic)
                    portfolio = await get_portfolio_summary(
                        user_id=None,  # Get combined household view
                        current_user=user,
                        db=db
                    )

                    # Capture snapshot for this organization
                    snapshot = await snapshot_service.capture_snapshot(
                        db=db,
                        organization_id=org_id,
                        portfolio=portfolio,
                        snapshot_date=today
                    )

                    total_snapshots += 1
                    logger.info(f"Created snapshot for org {org_id}: ${snapshot.total_value:,.2f}")

                except Exception as e:
                    logger.error(f"Error creating snapshot for org {org_id}: {str(e)}", exc_info=True)
                    # Continue with other organizations

            logger.info(f"Holdings snapshot capture complete. Total snapshots created: {total_snapshots}")

        except Exception as e:
            logger.error(f"Error in holdings snapshot task: {str(e)}", exc_info=True)
            raise
