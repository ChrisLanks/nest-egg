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

from sqlalchemy import delete, select

from app.core.database import AsyncSessionLocal
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.models.user import EmailVerificationToken, Organization, PasswordResetToken, User
from app.services.snapshot_service import snapshot_service
from app.utils.datetime_utils import utc_now
from app.workers.celery_app import celery_app

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
    return offset_minutes * 60  # convert to seconds


def _fetch_all_organizations():
    """
    Fetch all organisation IDs synchronously in batches.

    Runs the async DB query in a fresh event loop (Celery worker context).
    Only fetches IDs (not full ORM objects) to minimise memory usage.
    """

    async def _inner():
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Organization.id))
            return result.scalars().all()

    return asyncio.run(_inner())


def _dispatch_snapshot_tasks(org_ids) -> int:
    """
    Enqueue per-org snapshot tasks with staggered countdowns.

    Extracted so tests can call this with a pre-built org ID list without
    needing to patch the DB fetch or asyncio.run.

    Returns the number of tasks dispatched.
    """
    logger.info("orchestrate_portfolio_snapshots: dispatching tasks for %d orgs", len(org_ids))
    for org_id in org_ids:
        countdown = _calculate_offset_seconds(org_id)
        capture_org_portfolio_snapshot.apply_async(
            args=[str(org_id)],
            countdown=countdown,
        )
    return len(org_ids)


@celery_app.task(name="orchestrate_portfolio_snapshots")
def orchestrate_portfolio_snapshots():
    """
    Celery Beat entry point (fires at midnight UTC).

    Fetches all organisation IDs and dispatches per-org snapshot tasks with
    staggered countdowns to avoid a thundering herd.
    """
    org_ids = _fetch_all_organizations()
    _dispatch_snapshot_tasks(org_ids)


@celery_app.task(name="capture_org_portfolio_snapshot")
def capture_org_portfolio_snapshot(organization_id: str):
    """
    Capture the daily net-worth snapshot for a single organisation.

    Idempotent: skips if a snapshot for today already exists.
    """

    async def _run():
        async with AsyncSessionLocal() as db:
            today = utc_now().date()

            # Idempotency check for household snapshot
            existing = await db.execute(
                select(PortfolioSnapshot).where(
                    PortfolioSnapshot.organization_id == organization_id,
                    PortfolioSnapshot.snapshot_date == today,
                    PortfolioSnapshot.user_id.is_(None),
                )
            )
            if existing.scalar_one_or_none():
                logger.debug(
                    "capture_org_portfolio_snapshot: snapshot already exists for org=%s date=%s",
                    organization_id,
                    today,
                )
                return

            # Get all active users in the organization
            users_result = await db.execute(
                select(User).where(
                    User.organization_id == organization_id,
                    User.is_active.is_(True),
                )
            )
            users = users_result.scalars().all()
            if not users:
                logger.warning(
                    "capture_org_portfolio_snapshot: no users for org=%s, skipping",
                    organization_id,
                )
                return

            # Use the first user as auth context for household snapshot
            user = users[0]

            # Imported here to avoid circular dependency (holdings → services → tasks)
            from app.api.v1.holdings import get_portfolio_summary

            # 1. Capture household-level snapshot (user_id=None)
            portfolio = await get_portfolio_summary(user_id=None, current_user=user, db=db)
            await snapshot_service.capture_snapshot(
                db=db, organization_id=organization_id, portfolio=portfolio
            )
            logger.info(
                "capture_org_portfolio_snapshot: captured household snapshot for org=%s total=$%s",
                organization_id,
                portfolio.total_value,
            )

            # 2. Capture per-user snapshots for each household member
            for member in users:
                try:
                    user_portfolio = await get_portfolio_summary(
                        user_id=member.id, current_user=member, db=db
                    )
                    await snapshot_service.capture_snapshot(
                        db=db,
                        organization_id=organization_id,
                        portfolio=user_portfolio,
                        user_id=member.id,
                    )
                    logger.info(
                        "capture_org_portfolio_snapshot: captured user snapshot "
                        "for org=%s user=%s total=$%s",
                        organization_id,
                        member.id,
                        user_portfolio.total_value,
                    )
                except Exception as e:
                    logger.error(
                        "capture_org_portfolio_snapshot: failed to capture user snapshot "
                        "for org=%s user=%s: %s",
                        organization_id,
                        member.id,
                        e,
                    )

            # Capture net worth snapshot and check milestones
            try:
                from app.services.milestone_service import check_milestones
                from app.services.net_worth_service import net_worth_service

                nw_snapshot = await net_worth_service.capture_snapshot(
                    db=db, organization_id=organization_id
                )
                milestones = await check_milestones(
                    db=db,
                    organization_id=organization_id,
                    current_net_worth=nw_snapshot.total_net_worth,
                )
                if milestones:
                    logger.info(
                        "capture_org_portfolio_snapshot: %d milestone(s) hit for org=%s",
                        len(milestones),
                        organization_id,
                    )
            except Exception as e:
                logger.error(
                    "capture_org_portfolio_snapshot: milestone check failed for org=%s: %s",
                    organization_id,
                    e,
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
                "cleanup_expired_auth_tokens: deleted %d password-reset"
                " and %d email-verification tokens",
                r1.rowcount,
                r2.rowcount,
            )

    asyncio.run(_run())
