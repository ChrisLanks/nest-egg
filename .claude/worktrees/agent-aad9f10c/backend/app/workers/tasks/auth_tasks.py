"""Celery tasks for authentication maintenance and audit log persistence."""

import logging
from typing import Optional

from sqlalchemy import delete, func, or_

from app.models.user import RefreshToken
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="cleanup_expired_refresh_tokens")
def cleanup_expired_refresh_tokens_task():
    """
    Delete expired and revoked refresh tokens from the database.
    Runs daily at 3am to keep the refresh_tokens table lean.
    """
    import asyncio

    asyncio.run(_cleanup_expired_refresh_tokens_async())


async def _cleanup_expired_refresh_tokens_async():
    """Async implementation of refresh token cleanup."""
    from app.workers.utils import get_celery_session

    async with get_celery_session() as db:
        try:
            result = await db.execute(
                delete(RefreshToken).where(
                    or_(
                        RefreshToken.expires_at < func.now(),
                        RefreshToken.revoked_at.is_not(None),
                    )
                )
            )
            await db.commit()

            deleted_count = result.rowcount
            logger.info(
                f"Refresh token cleanup complete. Deleted {deleted_count} expired/revoked tokens."
            )

        except Exception as e:
            logger.error(f"Error cleaning up refresh tokens: {str(e)}", exc_info=True)
            raise


@celery_app.task(
    name="persist_audit_log",
    max_retries=5,
    default_retry_delay=2,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def persist_audit_log_task(
    request_id: str,
    action: str,
    method: str,
    path: str,
    status_code: int,
    user_id: Optional[str],
    ip_address: str,
    duration_ms: Optional[int],
) -> None:
    """Persist an audit log entry to the database.

    Called by AuditLogMiddleware via .delay() so the HTTP response is never
    blocked waiting for the DB write.  Celery retries on transient failures
    (up to 5 times with exponential backoff), so logs are not silently lost
    when the database is momentarily unavailable.
    """
    import asyncio

    asyncio.run(
        _persist_audit_log_async(
            request_id=request_id,
            action=action,
            method=method,
            path=path,
            status_code=status_code,
            user_id=user_id,
            ip_address=ip_address,
            duration_ms=duration_ms,
        )
    )


def _safe_uuid(value: Optional[str]):
    from uuid import UUID as _UUID

    if not value or value in ("N/A", "unknown", "anonymous"):
        return None
    try:
        return _UUID(value)
    except (ValueError, AttributeError):
        return None


async def _persist_audit_log_async(
    request_id: str,
    action: str,
    method: str,
    path: str,
    status_code: int,
    user_id: Optional[str],
    ip_address: str,
    duration_ms: Optional[int],
) -> None:
    """Async implementation — writes one AuditLog row per call."""
    from app.models.audit_log import AuditLog
    from app.workers.utils import get_celery_session

    async with get_celery_session() as session:
        entry = AuditLog(
            request_id=request_id,
            action=action,
            method=method,
            path=path,
            status_code=status_code,
            user_id=_safe_uuid(user_id),
            ip_address=ip_address,
            duration_ms=duration_ms,
        )
        session.add(entry)
        await session.commit()
        logger.debug("audit_log persisted: action=%s request_id=%s", action, request_id)
