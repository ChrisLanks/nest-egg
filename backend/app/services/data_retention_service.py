"""Data retention service for enterprise compliance.

Purges transactions older than a configurable retention period.
Designed to be called by a Celery beat task (daily at 3 AM).
"""

import logging
from datetime import date, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction
from app.models.user import User

logger = logging.getLogger(__name__)


class DataRetentionService:
    """Purge old data per configurable retention policy."""

    @staticmethod
    async def purge_old_data(
        db: AsyncSession,
        org_id,
        retention_days: int,
        *,
        dry_run: bool = True,
    ) -> int:
        """
        Delete transactions older than *retention_days* for the given org.

        Args:
            db: Async database session.
            org_id: Organization UUID to scope the purge.
            retention_days: Keep transactions newer than this many days.
            dry_run: If True, count rows but don't delete (safe default).

        Returns:
            Number of rows affected (deleted or would-be-deleted in dry-run).
        """
        cutoff = date.today() - timedelta(days=retention_days)

        if dry_run:
            result = await db.execute(
                select(func.count())
                .select_from(Transaction)
                .where(
                    Transaction.organization_id == org_id,
                    Transaction.date < cutoff,
                )
            )
            count = result.scalar() or 0
            logger.info(
                "Data retention DRY RUN: org=%s would delete %d transactions older than %s",
                org_id,
                count,
                cutoff.isoformat(),
            )
            return count

        result = await db.execute(
            delete(Transaction).where(
                Transaction.organization_id == org_id,
                Transaction.date < cutoff,
            )
        )
        await db.commit()
        deleted = result.rowcount
        logger.info(
            "Data retention: org=%s deleted %d transactions older than %s",
            org_id,
            deleted,
            cutoff.isoformat(),
        )
        return deleted

    @staticmethod
    async def purge_all_orgs(
        db: AsyncSession,
        retention_days: int,
        *,
        dry_run: bool = True,
    ) -> dict:
        """
        Run retention purge for every organization.

        Returns:
            Dict mapping org_id → rows affected.
        """
        orgs = await db.execute(
            select(User.organization_id).distinct()
        )
        org_ids = [row[0] for row in orgs.all()]

        results = {}
        for org_id in org_ids:
            count = await DataRetentionService.purge_old_data(
                db, org_id, retention_days, dry_run=dry_run
            )
            results[str(org_id)] = count

        total = sum(results.values())
        logger.info(
            "Data retention complete: %d orgs processed, %d total rows %s",
            len(org_ids),
            total,
            "would be deleted (dry run)" if dry_run else "deleted",
        )
        return results
