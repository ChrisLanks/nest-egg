"""
Portfolio snapshot scheduler with offset-based periodic execution.

This scheduler ensures snapshots are captured daily with randomized offsets
to avoid all organizations updating simultaneously.
"""

import asyncio
import logging
import hashlib
from datetime import datetime, time, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.models.user import Organization
from app.services.snapshot_service import snapshot_service

logger = logging.getLogger(__name__)


class SnapshotScheduler:
    """
    Background scheduler for portfolio snapshots.

    Features:
    - Runs daily for each organization with a deterministic time offset
    - Offset is based on organization ID hash to ensure consistency
    - Checks on startup if snapshot was missed
    - Spreads execution across 24 hours to avoid load spikes
    """

    def __init__(self):
        self.running = False
        self.task: Optional[asyncio.Task] = None

    def calculate_offset_hours(self, organization_id: UUID) -> float:
        """
        Calculate deterministic offset hours (0-24) for an organization.

        Uses organization ID hash to generate consistent but randomized offset.
        This ensures the same organization always runs at the same time,
        but different organizations are spread across the day.

        Args:
            organization_id: Organization UUID

        Returns:
            Float between 0 and 24 representing hours offset from midnight UTC
        """
        # Hash the organization ID to get a deterministic random value
        hash_bytes = hashlib.sha256(str(organization_id).encode()).digest()
        hash_int = int.from_bytes(hash_bytes[:4], byteorder="big")

        # Map to 0-24 hour range
        offset_hours = (hash_int % (24 * 60)) / 60.0  # Minutes to hours

        logger.debug(f"Org {organization_id} offset: {offset_hours:.2f} hours from midnight UTC")
        return offset_hours

    def get_next_run_time(self, organization_id: UUID, now: Optional[datetime] = None) -> datetime:
        """
        Calculate the next scheduled run time for an organization.

        Args:
            organization_id: Organization UUID
            now: Current datetime (defaults to now)

        Returns:
            Next scheduled run datetime
        """
        if now is None:
            now = datetime.utcnow()

        offset_hours = self.calculate_offset_hours(organization_id)
        offset_delta = timedelta(hours=offset_hours)

        # Calculate today's scheduled time
        today_midnight = datetime.combine(now.date(), time.min)
        today_scheduled = today_midnight + offset_delta

        # If today's time has passed, schedule for tomorrow
        if now >= today_scheduled:
            tomorrow_midnight = today_midnight + timedelta(days=1)
            return tomorrow_midnight + offset_delta
        else:
            return today_scheduled

    async def should_capture_snapshot(
        self, db: AsyncSession, organization_id: UUID, now: Optional[datetime] = None
    ) -> bool:
        """
        Check if a snapshot should be captured for an organization.

        Returns True if:
        1. No snapshot exists for today, AND
        2. The scheduled time has passed (based on offset)

        Args:
            db: Database session
            organization_id: Organization UUID
            now: Current datetime (defaults to now)

        Returns:
            True if snapshot should be captured
        """
        if now is None:
            now = datetime.utcnow()

        today = now.date()

        # Check if snapshot already exists for today
        existing = await db.execute(
            select(PortfolioSnapshot).where(
                PortfolioSnapshot.organization_id == organization_id,
                PortfolioSnapshot.snapshot_date == today,
            )
        )
        if existing.scalar_one_or_none():
            logger.debug(f"Snapshot already exists for org {organization_id} on {today}")
            return False

        # Check if scheduled time has passed
        next_run = self.get_next_run_time(organization_id, now)

        # If next run is in the future, we haven't reached today's window yet
        if next_run.date() > today:
            logger.debug(f"Scheduled time not reached for org {organization_id}")
            return False

        # If next run is tomorrow, today's window has passed - capture now
        return True

    async def capture_organization_snapshot(self, db: AsyncSession, organization_id: UUID) -> bool:
        """
        Capture snapshot for a single organization.

        Args:
            db: Database session
            organization_id: Organization UUID

        Returns:
            True if snapshot was captured successfully
        """
        try:
            # Get portfolio summary (reuse existing holdings API logic)
            from app.api.v1.holdings import get_portfolio_summary
            from app.models.user import User

            # Get first user of organization (for auth context)
            result = await db.execute(
                select(User).where(User.organization_id == organization_id).limit(1)
            )
            user = result.scalar_one_or_none()

            if not user:
                logger.warning(f"No users found for organization {organization_id}")
                return False

            # Get portfolio summary
            portfolio = await get_portfolio_summary(user_id=None, current_user=user, db=db)

            # Capture snapshot
            await snapshot_service.capture_snapshot(
                db=db, organization_id=organization_id, portfolio=portfolio
            )

            logger.info(f"✓ Captured snapshot for org {organization_id}: ${portfolio.total_value}")
            return True

        except Exception as e:
            logger.error(f"Failed to capture snapshot for org {organization_id}: {e}")
            return False

    async def _acquire_lock(self) -> bool:
        """
        Attempt to acquire a distributed lock via Redis SET NX EX.

        Returns True if the lock was acquired, False if another instance
        already holds it.  Falls back to True (always run) when Redis is
        unavailable so that single-instance / dev setups still work.
        """
        try:
            import redis.asyncio as aioredis
            from app.config import settings

            client = aioredis.from_url(
                settings.REDIS_URL, encoding="utf-8", decode_responses=True
            )
            # TTL of 2 hours; a full snapshot run should finish well within that
            acquired = await client.set(
                "scheduler:snapshot:lock", "1", nx=True, ex=7200
            )
            await client.aclose()
            return bool(acquired)
        except Exception as e:
            logger.warning(
                f"Could not acquire snapshot lock via Redis ({e}); running anyway"
            )
            return True  # Run without a lock (safe for dev / single-instance)

    async def check_and_capture_all(self):
        """
        Check all organizations and capture snapshots as needed.

        This is called periodically (every 12 hours) to check if any organization
        needs a snapshot based on their offset schedule.

        A Redis distributed lock prevents multiple server instances from running
        the snapshot loop simultaneously.
        """
        if not await self._acquire_lock():
            logger.info("Snapshot check skipped: another instance holds the lock")
            return

        async with AsyncSessionLocal() as db:
            try:
                # Get all active organizations
                result = await db.execute(select(Organization))
                organizations = result.scalars().all()

                logger.info(f"Checking {len(organizations)} organizations for snapshot capture")

                now = datetime.utcnow()
                captured_count = 0

                for org in organizations:
                    if await self.should_capture_snapshot(db, org.id, now):
                        success = await self.capture_organization_snapshot(db, org.id)
                        if success:
                            captured_count += 1

                        # Small delay between captures to avoid DB lock contention
                        await asyncio.sleep(1)

                if captured_count > 0:
                    logger.info(f"Captured {captured_count} snapshots")

            except Exception as e:
                logger.error(f"Error in snapshot check cycle: {e}")

    async def run_scheduler_loop(self):
        """
        Main scheduler loop that runs continuously.

        Checks every 12 hours if any organizations need snapshots captured.
        Since we only capture one snapshot per day, checking 2x daily is sufficient.
        """
        logger.info("Portfolio snapshot scheduler started (checks every 12 hours)")

        # Run initial check on startup
        await self.check_and_capture_all()

        # Then run every 12 hours
        while self.running:
            try:
                # Wait 12 hours
                await asyncio.sleep(43200)  # 12 hours in seconds

                # Check and capture
                await self.check_and_capture_all()

            except asyncio.CancelledError:
                logger.info("Snapshot scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                # Continue running even if one cycle fails
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    async def cleanup_expired_tokens(self) -> None:
        """Delete expired password-reset and email-verification tokens."""
        from sqlalchemy import delete
        from app.models.user import PasswordResetToken, EmailVerificationToken

        async with AsyncSessionLocal() as db:
            try:
                now = datetime.utcnow()
                r1 = await db.execute(
                    delete(PasswordResetToken).where(PasswordResetToken.expires_at < now)
                )
                r2 = await db.execute(
                    delete(EmailVerificationToken).where(EmailVerificationToken.expires_at < now)
                )
                await db.commit()
                logger.info(
                    "token_cleanup: deleted %d expired password-reset and %d email-verification tokens",
                    r1.rowcount,
                    r2.rowcount,
                )
            except Exception as e:
                logger.error("Error during token cleanup: %s", e)

    async def run_cleanup_loop(self) -> None:
        """Run token cleanup every 24 hours."""
        logger.info("Token cleanup loop started (runs every 24 hours)")
        # Initial run on startup
        await self.cleanup_expired_tokens()
        while self.running:
            try:
                await asyncio.sleep(86400)  # 24 hours
                await self.cleanup_expired_tokens()
            except asyncio.CancelledError:
                logger.info("Token cleanup loop cancelled")
                break
            except Exception as e:
                logger.error("Error in token cleanup loop: %s", e)
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    async def start(self):
        """Start the background scheduler task."""
        if self.running:
            logger.warning("Scheduler already running")
            return

        self.running = True
        self.task = asyncio.create_task(self.run_scheduler_loop())
        self._cleanup_task: Optional[asyncio.Task] = asyncio.create_task(self.run_cleanup_loop())
        logger.info("Snapshot scheduler and token cleanup tasks created")

    async def stop(self):
        """Stop the background scheduler task."""
        if not self.running:
            return

        self.running = False
        for task in (self.task, getattr(self, "_cleanup_task", None)):
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        logger.info("Snapshot scheduler stopped")


# Singleton instance
snapshot_scheduler = SnapshotScheduler()
