"""Celery tasks for pre-computing budget suggestions."""

import logging

from sqlalchemy import select

from app.models.user import Organization
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="refresh_budget_suggestions")
def refresh_budget_suggestions_task():
    """Recompute budget suggestions for every org and cache them in the DB.

    Runs daily at 2:05am (just after check_budget_alerts at midnight and
    detect_recurring_patterns at 2am). Skips orgs with no transactions.
    Per-member suggestions are NOT pre-computed here — those are computed
    on-demand when a user views a specific member's budget page (and cached
    in the same table).
    """
    import asyncio

    asyncio.run(_refresh_all_async())


async def _refresh_all_async():
    from app.services.budget_suggestion_service import BudgetSuggestionService
    from app.workers.utils import get_celery_session

    async with get_celery_session() as db:
        try:
            result = await db.execute(select(Organization.id))
            org_ids = [row[0] for row in result.all()]

            logger.info("Refreshing budget suggestions for %d orgs", len(org_ids))

            total = 0
            for org_id in org_ids:
                try:
                    count = await BudgetSuggestionService.refresh_for_org(
                        db, org_id, scoped_user_id=None
                    )
                    total += count
                except Exception as exc:
                    # Don't let one bad org kill the whole task
                    logger.error(
                        "Error refreshing suggestions for org %s: %s",
                        org_id,
                        exc,
                        exc_info=True,
                    )

            logger.info("Budget suggestion refresh complete. Total suggestions: %d", total)

        except Exception as exc:
            logger.error("Fatal error in refresh_budget_suggestions: %s", exc, exc_info=True)
            raise
