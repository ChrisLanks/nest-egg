"""Data retention service for enterprise compliance.

Purges stale records across multiple tables according to a configurable
retention window.  Designed to be called by a Celery beat task (daily at 3 AM).

Retention policy
----------------
DATA_RETENTION_DAYS controls how many days of data to keep.

  None  — keep data indefinitely (default; safe for self-hosted / small teams)
  -1    — keep data indefinitely (explicit equivalent of None)
  N>0   — hard-delete records older than N days

The dry-run flag (default True) lets operators verify what would be deleted
before committing to a live purge.  Set DATA_RETENTION_DRY_RUN=false only
after confirming the retention window is correct.

Tables covered
--------------
- transactions          — scoped to org, filtered by `date`
- net_worth_snapshots   — scoped to org, filtered by `snapshot_date`
- notifications         — scoped to org, filtered by `created_at`
- audit_logs            — global, filtered by `created_at`
  Note: audit logs are append-only for compliance.  Only include them in
  purges when your policy explicitly requires it.  The default behaviour
  skips audit log purges unless AUDIT_LOG_RETENTION_DAYS is set separately.

GDPR "right to erasure"
-----------------------
`gdpr_delete_user` performs a hard delete of a single user record and all
their personally-identifiable data.  Organisation data shared with other
household members is NOT deleted.
"""

import logging
from datetime import date, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.net_worth_snapshot import NetWorthSnapshot
from app.models.notification import Notification
from app.models.transaction import Transaction
from app.models.user import User

logger = logging.getLogger(__name__)


def _is_indefinite(retention_days) -> bool:
    """Return True when retention_days means "keep forever" (None or -1)."""
    return retention_days is None or retention_days < 0


class DataRetentionService:
    """Purge old data per configurable retention policy."""

    # ── Per-table purge methods ───────────────────────────────────────────────

    @staticmethod
    async def purge_transactions(
        db: AsyncSession,
        org_id,
        retention_days: int,
        *,
        dry_run: bool = True,
    ) -> int:
        """Delete transactions older than *retention_days* for the given org."""
        cutoff = date.today() - timedelta(days=retention_days)

        if dry_run:
            result = await db.execute(
                select(func.count())
                .select_from(Transaction)
                .where(Transaction.organization_id == org_id, Transaction.date < cutoff)
            )
            count = result.scalar() or 0
            logger.info(
                "DRY RUN — transactions: org=%s would delete %d rows older than %s",
                org_id,
                count,
                cutoff.isoformat(),
            )
            return count

        result = await db.execute(
            delete(Transaction).where(
                Transaction.organization_id == org_id, Transaction.date < cutoff
            )
        )
        await db.commit()
        deleted = result.rowcount
        logger.info(
            "transactions: org=%s deleted %d rows older than %s",
            org_id,
            deleted,
            cutoff.isoformat(),
        )
        return deleted

    @staticmethod
    async def purge_snapshots(
        db: AsyncSession,
        org_id,
        retention_days: int,
        *,
        dry_run: bool = True,
    ) -> int:
        """Delete net-worth snapshots older than *retention_days* for the given org."""
        cutoff = date.today() - timedelta(days=retention_days)

        if dry_run:
            result = await db.execute(
                select(func.count())
                .select_from(NetWorthSnapshot)
                .where(
                    NetWorthSnapshot.organization_id == org_id,
                    NetWorthSnapshot.snapshot_date < cutoff,
                )
            )
            count = result.scalar() or 0
            logger.info(
                "DRY RUN — snapshots: org=%s would delete %d rows older than %s",
                org_id,
                count,
                cutoff.isoformat(),
            )
            return count

        result = await db.execute(
            delete(NetWorthSnapshot).where(
                NetWorthSnapshot.organization_id == org_id,
                NetWorthSnapshot.snapshot_date < cutoff,
            )
        )
        await db.commit()
        deleted = result.rowcount
        logger.info(
            "snapshots: org=%s deleted %d rows older than %s",
            org_id,
            deleted,
            cutoff.isoformat(),
        )
        return deleted

    @staticmethod
    async def purge_notifications(
        db: AsyncSession,
        org_id,
        retention_days: int,
        *,
        dry_run: bool = True,
    ) -> int:
        """Delete notifications older than *retention_days* for the given org."""
        from datetime import datetime, timezone

        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

        if dry_run:
            result = await db.execute(
                select(func.count())
                .select_from(Notification)
                .where(
                    Notification.organization_id == org_id,
                    Notification.created_at < cutoff,
                )
            )
            count = result.scalar() or 0
            logger.info(
                "DRY RUN — notifications: org=%s would delete %d rows older than %s",
                org_id,
                count,
                cutoff.isoformat(),
            )
            return count

        result = await db.execute(
            delete(Notification).where(
                Notification.organization_id == org_id,
                Notification.created_at < cutoff,
            )
        )
        await db.commit()
        deleted = result.rowcount
        logger.info(
            "notifications: org=%s deleted %d rows older than %s",
            org_id,
            deleted,
            cutoff.isoformat(),
        )
        return deleted

    @staticmethod
    async def purge_audit_logs(
        db: AsyncSession,
        retention_days: int,
        *,
        dry_run: bool = True,
    ) -> int:
        """Delete audit log entries older than *retention_days* (global, not per-org).

        Audit logs are append-only for compliance.  Only purge when your
        policy explicitly requires it (e.g. AUDIT_LOG_RETENTION_DAYS=365).
        """
        from datetime import datetime, timezone

        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

        if dry_run:
            result = await db.execute(
                select(func.count()).select_from(AuditLog).where(AuditLog.created_at < cutoff)
            )
            count = result.scalar() or 0
            logger.info(
                "DRY RUN — audit_logs: would delete %d rows older than %s",
                count,
                cutoff.isoformat(),
            )
            return count

        result = await db.execute(delete(AuditLog).where(AuditLog.created_at < cutoff))
        await db.commit()
        deleted = result.rowcount
        logger.info("audit_logs: deleted %d rows older than %s", deleted, cutoff.isoformat())
        return deleted

    # ── Orchestration ─────────────────────────────────────────────────────────

    @staticmethod
    async def purge_old_data(
        db: AsyncSession,
        org_id,
        retention_days: int,
        *,
        dry_run: bool = True,
    ) -> dict:
        """Run all per-org purges for one organisation.

        Returns:
            Dict with row counts per table: ``{transactions, snapshots, notifications}``.
        """
        if _is_indefinite(retention_days):
            return {"transactions": 0, "snapshots": 0, "notifications": 0}

        transactions = await DataRetentionService.purge_transactions(
            db, org_id, retention_days, dry_run=dry_run
        )
        snapshots = await DataRetentionService.purge_snapshots(
            db, org_id, retention_days, dry_run=dry_run
        )
        notifications = await DataRetentionService.purge_notifications(
            db, org_id, retention_days, dry_run=dry_run
        )
        return {
            "transactions": transactions,
            "snapshots": snapshots,
            "notifications": notifications,
        }

    @staticmethod
    async def purge_all_orgs(
        db: AsyncSession,
        retention_days: int,
        *,
        dry_run: bool = True,
        audit_log_retention_days: int | None = None,
    ) -> dict:
        """Run the retention purge for every organisation.

        Args:
            retention_days: Days of data to keep (None/-1 = indefinite).
            dry_run: If True, count rows but don't delete.
            audit_log_retention_days: If set, also purge audit_logs older than
                this many days (independent of per-org retention).

        Returns:
            Dict mapping org_id → per-table counts, plus an "audit_logs" total.
        """
        if _is_indefinite(retention_days):
            logger.info("Data retention: indefinite policy — skipping purge")
            return {}

        orgs = await db.execute(select(User.organization_id).distinct())
        org_ids = [row[0] for row in orgs.all()]

        results: dict = {}
        for org_id in org_ids:
            counts = await DataRetentionService.purge_old_data(
                db, org_id, retention_days, dry_run=dry_run
            )
            results[str(org_id)] = counts

        # Optional global audit log purge
        audit_deleted = 0
        if not _is_indefinite(audit_log_retention_days):
            audit_deleted = await DataRetentionService.purge_audit_logs(
                db,
                audit_log_retention_days,
                dry_run=dry_run,  # type: ignore[arg-type]
            )

        total_tx = sum(v.get("transactions", 0) for v in results.values())
        total_sn = sum(v.get("snapshots", 0) for v in results.values())
        total_nt = sum(v.get("notifications", 0) for v in results.values())
        logger.info(
            "Data retention complete (%s): %d orgs — "
            "transactions=%d snapshots=%d notifications=%d audit_logs=%d",
            "dry run" if dry_run else "live",
            len(org_ids),
            total_tx,
            total_sn,
            total_nt,
            audit_deleted,
        )

        results["_audit_logs"] = audit_deleted
        return results

    # ── GDPR right to erasure ─────────────────────────────────────────────────

    @staticmethod
    async def gdpr_delete_user(db: AsyncSession, user_id: str) -> None:
        """Hard-delete a user and all their personally-identifiable data.

        The user's organisation is NOT deleted — it may be shared with other
        household members.  Only the User row (and its cascade-deleted children:
        refresh_tokens, mfa, consents, identities) is removed.

        Called by the ``gdpr_delete_user_task`` Celery task after a 24-hour
        grace period following the user's deletion request.
        """
        from uuid import UUID

        from sqlalchemy import delete as sa_delete

        user_uuid = UUID(user_id)
        result = await db.execute(sa_delete(User).where(User.id == user_uuid))
        await db.commit()
        logger.info("GDPR erasure complete: user_id=%s rows_deleted=%d", user_id, result.rowcount)
