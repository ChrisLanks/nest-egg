"""
Celery tasks for portfolio net-worth snapshot capture.

Architecture:
- Beat fires ``orchestrate_portfolio_snapshots`` once at midnight UTC
- The orchestrator queries all orgs and spawns a per-org task with a staggered
  ``countdown`` so organisations are spread across the 24-hour window (same
  deterministic hashing used by the old SnapshotScheduler).
- Each per-org task captures a snapshot idempotently (skips if one already
  exists for today).

This replaces the in-process asyncio SnapshotScheduler loop which caused
duplicate executions when multiple API containers were running.
"""

import asyncio
import hashlib
import logging

from sqlalchemy import select, delete

from app.workers.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.models.user import Organization, User, PasswordResetToken, EmailVerificationToken
from app.services.snapshot_service import snapshot_service
from app.utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)


def _calculate_offset_seconds(organization_id) -> int:
    """
    Return a deterministic spread offset (0 – 86399 s) for an organisation.

    Identical algorithm to SnapshotScheduler.calculate_offset_hours() so that
    existing organisations keep their historical snapshot times.
    """
    hash_bytes = hashlib.sha256(str(organization_id).encode()).digest()
    hash_int = int.from_bytes(hash_bytes[:4], byteorder="big")
    offset_minutes = hash_int % (24 * 60)  # 0–1439 minutes
    return offset_minutes * 60             # convert to seconds


def _fetch_all_organizations():
    """
    Fetch all organisations synchronously. Extracted for testability.

    Runs the async DB query in a fresh event loop (Celery worker context).
    """
    async def _inner():
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Organization))
            return result.scalars().all()

    return asyncio.run(_inner())


def _dispatch_snapshot_tasks(orgs) -> int:
    """
    Enqueue per-org snapshot tasks with staggered countdowns.

    Extracted so tests can call this with a pre-built org list without
    needing to patch the DB fetch or asyncio.run.

    Returns the number of tasks dispatched.
    """
    logger.info("orchestrate_portfolio_snapshots: dispatching tasks for %d orgs", len(orgs))
    for org in orgs:
        countdown = _calculate_offset_seconds(org.id)
        capture_org_portfolio_snapshot.apply_async(
            args=[str(org.id)],
            countdown=countdown,
        )
    return len(orgs)


@celery_app.task(name="orchestrate_portfolio_snapshots")
def orchestrate_portfolio_snapshots():
    """
    Celery Beat entry point (fires at midnight UTC).

    Fetches all organisations and dispatches per-org snapshot tasks with
    staggered countdowns to avoid a thundering herd.
    """
    orgs = _fetch_all_organizations()
    _dispatch_snapshot_tasks(orgs)


@celery_app.task(name="capture_org_portfolio_snapshot")
def capture_org_portfolio_snapshot(organization_id: str):
    """
    Capture the daily net-worth snapshot for a single organisation.

    Idempotent: skips if a snapshot for today already exists.
    """
    async def _run():
        async with AsyncSessionLocal() as db:
            today = utc_now().date()

            # Idempotency check
            existing = await db.execute(
                select(PortfolioSnapshot).where(
                    PortfolioSnapshot.organization_id == organization_id,
                    PortfolioSnapshot.snapshot_date == today,
                )
            )
            if existing.scalar_one_or_none():
                logger.debug(
                    "capture_org_portfolio_snapshot: snapshot already exists for org=%s date=%s",
                    organization_id,
                    today,
                )
                return

            # Need a user for auth context used by get_portfolio_summary
            user_result = await db.execute(
                select(User).where(User.organization_id == organization_id).limit(1)
            )
            user = user_result.scalar_one_or_none()
            if not user:
                logger.warning(
                    "capture_org_portfolio_snapshot: no users for org=%s, skipping",
                    organization_id,
                )
                return

            # Imported here to avoid circular dependency (holdings → services → tasks)
            from app.api.v1.holdings import get_portfolio_summary
            portfolio = await get_portfolio_summary(
                user_id=None, current_user=user, db=db
            )
            await snapshot_service.capture_snapshot(
                db=db, organization_id=organization_id, portfolio=portfolio
            )
            logger.info(
                "capture_org_portfolio_snapshot: captured snapshot for org=%s total=$%s",
                organization_id,
                portfolio.total_value,
            )

    asyncio.run(_run())


@celery_app.task(name="cleanup_expired_auth_tokens")
def cleanup_expired_auth_tokens():
    """
    Delete expired password-reset and email-verification tokens.

    Replaces the token cleanup loop that was inside SnapshotScheduler.
    """
    async def _run():
        async with AsyncSessionLocal() as db:
            now = utc_now()
            r1 = await db.execute(
                delete(PasswordResetToken).where(PasswordResetToken.expires_at < now)
            )
            r2 = await db.execute(
                delete(EmailVerificationToken).where(EmailVerificationToken.expires_at < now)
            )
            await db.commit()
            logger.info(
                "cleanup_expired_auth_tokens: deleted %d password-reset and %d email-verification tokens",
                r1.rowcount,
                r2.rowcount,
            )

    asyncio.run(_run())
