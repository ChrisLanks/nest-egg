"""Auto-revoke expired guest access."""

import logging

from sqlalchemy import select

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="auto_revoke_expired_guests")
def auto_revoke_expired_guests():
    """
    Revoke guest access records past their expires_at date.
    Runs daily at 2am UTC.
    """
    import asyncio

    asyncio.run(_auto_revoke_expired_guests_async())


async def _auto_revoke_expired_guests_async():
    """Async implementation of expired-guest revocation."""
    from app.models.user import HouseholdGuest
    from app.utils.datetime_utils import utc_now
    from app.workers.utils import get_celery_session

    async with get_celery_session() as db:
        try:
            now = utc_now()

            result = await db.execute(
                select(HouseholdGuest).where(
                    HouseholdGuest.is_active.is_(True),
                    HouseholdGuest.expires_at.isnot(None),
                    HouseholdGuest.expires_at < now,
                )
            )
            expired_guests = result.scalars().all()

            if not expired_guests:
                logger.info("auto_revoke_expired_guests: no expired guests found")
                return

            logger.info(
                "auto_revoke_expired_guests: revoking %d expired guest record(s)",
                len(expired_guests),
            )

            for guest in expired_guests:
                guest.is_active = False
                guest.revoked_at = now
                logger.info(
                    "Revoked expired guest: user=%s org=%s expires_at=%s",
                    guest.user_id,
                    guest.organization_id,
                    guest.expires_at,
                )

            await db.commit()
            logger.info(
                "auto_revoke_expired_guests: committed %d revocations",
                len(expired_guests),
            )

        except Exception as e:
            logger.error(
                "auto_revoke_expired_guests: error during revocation: %s",
                e,
                exc_info=True,
            )
            raise
