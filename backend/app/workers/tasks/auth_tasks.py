"""Celery tasks for authentication maintenance."""

import logging
from datetime import datetime, timezone
from sqlalchemy import delete, or_

from app.workers.celery_app import celery_app
from app.core.database import async_session_factory
from app.models.user import RefreshToken

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
    async with async_session_factory() as db:
        try:
            now = datetime.now(timezone.utc)

            result = await db.execute(
                delete(RefreshToken).where(
                    or_(
                        RefreshToken.expires_at < now,
                        RefreshToken.revoked_at.is_not(None),
                    )
                )
            )
            await db.commit()

            deleted_count = result.rowcount
            logger.info(f"Refresh token cleanup complete. Deleted {deleted_count} expired/revoked tokens.")

        except Exception as e:
            logger.error(f"Error cleaning up refresh tokens: {str(e)}", exc_info=True)
            raise
