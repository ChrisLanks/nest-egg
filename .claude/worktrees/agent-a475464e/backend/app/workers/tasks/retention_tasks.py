"""Celery tasks for data retention policy enforcement and GDPR erasure."""

import logging

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="run_data_retention")
def run_data_retention_task():
    """Purge old records across all orgs per DATA_RETENTION_DAYS policy.

    Skipped when DATA_RETENTION_DAYS is None or -1 (indefinite).
    Respects DATA_RETENTION_DRY_RUN (default True = log-only, no deletes).
    Covers: transactions, net_worth_snapshots, notifications, and optionally
    audit_logs (when AUDIT_LOG_RETENTION_DAYS is configured).
    """
    import asyncio

    asyncio.run(_run_data_retention_async())


async def _run_data_retention_async():
    from app.config import settings
    from app.services.data_retention_service import DataRetentionService, _is_indefinite
    from app.workers.utils import get_celery_session

    retention_days = settings.DATA_RETENTION_DAYS
    if _is_indefinite(retention_days):
        logger.info("Data retention skipped: DATA_RETENTION_DAYS is not configured.")
        return

    dry_run = settings.DATA_RETENTION_DRY_RUN
    audit_retention = getattr(settings, "AUDIT_LOG_RETENTION_DAYS", None)

    async with get_celery_session() as db:
        try:
            results = await DataRetentionService.purge_all_orgs(
                db,
                retention_days,
                dry_run=dry_run,
                audit_log_retention_days=audit_retention,
            )
            logger.info(
                "Data retention task complete: retention_days=%d dry_run=%s results=%s",
                retention_days,
                dry_run,
                results,
            )
        except Exception as e:
            logger.error("Data retention task failed: %s", str(e), exc_info=True)
            raise


@celery_app.task(
    name="gdpr_delete_user",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def gdpr_delete_user_task(user_id: str) -> None:
    """Hard-delete a user and their personal data (GDPR Art. 17 right to erasure).

    Runs asynchronously so the HTTP response returns immediately.
    The user's account is deactivated synchronously at request time;
    the hard delete happens here within 24 hours.

    The user's organisation and shared household data are NOT deleted.
    Only the User row and its cascade-deleted children are removed.
    """
    import asyncio

    asyncio.run(_gdpr_delete_user_async(user_id))


async def _gdpr_delete_user_async(user_id: str) -> None:
    from app.services.data_retention_service import DataRetentionService
    from app.workers.utils import get_celery_session

    async with get_celery_session() as db:
        await DataRetentionService.gdpr_delete_user(db, user_id)
