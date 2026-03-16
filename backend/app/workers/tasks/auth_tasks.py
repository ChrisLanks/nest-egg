"""Celery tasks for authentication maintenance."""

import logging

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
