"""Celery tasks for data retention policy enforcement."""

import logging

from app.workers.celery_app import celery_app
from app.core.database import AsyncSessionLocal as async_session_factory

logger = logging.getLogger(__name__)


@celery_app.task(name="run_data_retention")
def run_data_retention_task():
    """
    Purge transactions older than DATA_RETENTION_DAYS for all organizations.

    Only runs if DATA_RETENTION_DAYS is configured (non-None).
    Respects DATA_RETENTION_DRY_RUN (default True = log-only).
    """
    import asyncio

    asyncio.run(_run_data_retention_async())


async def _run_data_retention_async():
    """Async implementation of data retention purge."""
    from app.config import settings
    from app.services.data_retention_service import DataRetentionService

    retention_days = settings.DATA_RETENTION_DAYS
    if retention_days is None:
        logger.info("Data retention skipped: DATA_RETENTION_DAYS is not configured.")
        return

    dry_run = settings.DATA_RETENTION_DRY_RUN

    async with async_session_factory() as db:
        try:
            results = await DataRetentionService.purge_all_orgs(
                db,
                retention_days,
                dry_run=dry_run,
            )
            logger.info(
                "Data retention task complete: retention_days=%d, dry_run=%s, results=%s",
                retention_days,
                dry_run,
                results,
            )
        except Exception as e:
            logger.error("Data retention task failed: %s", str(e), exc_info=True)
            raise
