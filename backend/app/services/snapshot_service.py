"""
Portfolio snapshot service for historical tracking.

Captures daily portfolio snapshots for performance analysis and trend tracking.
"""

import logging
from datetime import date
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.portfolio_snapshot import PortfolioSnapshot
from app.schemas.holding import PortfolioSummary
from app.utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)


class SnapshotService:
    """Service for managing portfolio snapshots."""

    async def capture_snapshot(
        self,
        db: AsyncSession,
        organization_id: UUID,
        portfolio: PortfolioSummary,
        snapshot_date: Optional[date] = None,
    ) -> PortfolioSnapshot:
        """
        Capture a portfolio snapshot for the given organization.

        Uses upsert (INSERT ... ON CONFLICT UPDATE) to ensure one snapshot per day.

        Args:
            db: Database session
            organization_id: Organization ID
            portfolio: Portfolio summary data to snapshot
            snapshot_date: Date for snapshot (defaults to today)

        Returns:
            Created or updated PortfolioSnapshot
        """
        if snapshot_date is None:
            snapshot_date = utc_now().date()

        # Convert PortfolioSummary to snapshot data (JSON-serializable)
        snapshot_data = {
            "total_value": float(portfolio.total_value),
            "total_cost_basis": (
                float(portfolio.total_cost_basis) if portfolio.total_cost_basis else None
            ),
            "total_gain_loss": (
                float(portfolio.total_gain_loss) if portfolio.total_gain_loss else None
            ),
            "total_gain_loss_percent": (
                float(portfolio.total_gain_loss_percent)
                if portfolio.total_gain_loss_percent
                else None
            ),
            "holdings_by_ticker": [h.model_dump(mode="json") for h in portfolio.holdings_by_ticker],
            "holdings_by_account": [
                h.model_dump(mode="json") for h in portfolio.holdings_by_account
            ],
            "category_breakdown": (
                portfolio.category_breakdown.model_dump(mode="json")
                if portfolio.category_breakdown
                else None
            ),
            "geographic_breakdown": (
                portfolio.geographic_breakdown.model_dump(mode="json")
                if portfolio.geographic_breakdown
                else None
            ),
            "sector_breakdown": (
                [s.model_dump(mode="json") for s in portfolio.sector_breakdown]
                if portfolio.sector_breakdown
                else None
            ),
        }

        # Prepare snapshot values
        values = {
            "organization_id": organization_id,
            "snapshot_date": snapshot_date,
            "total_value": portfolio.total_value,
            "total_cost_basis": portfolio.total_cost_basis,
            "total_gain_loss": portfolio.total_gain_loss,
            "total_gain_loss_percent": portfolio.total_gain_loss_percent,
            "stocks_value": portfolio.stocks_value,
            "bonds_value": portfolio.bonds_value,
            "etf_value": portfolio.etf_value,
            "mutual_funds_value": portfolio.mutual_funds_value,
            "cash_value": portfolio.cash_value,
            "other_value": portfolio.other_value,
            "retirement_value": (
                portfolio.category_breakdown.retirement_value
                if portfolio.category_breakdown
                else Decimal("0")
            ),
            "taxable_value": (
                portfolio.category_breakdown.taxable_value
                if portfolio.category_breakdown
                else Decimal("0")
            ),
            "domestic_value": (
                portfolio.geographic_breakdown.domestic_value
                if portfolio.geographic_breakdown
                else Decimal("0")
            ),
            "international_value": (
                portfolio.geographic_breakdown.international_value
                if portfolio.geographic_breakdown
                else Decimal("0")
            ),
            "snapshot_data": snapshot_data,
        }

        # Upsert snapshot (insert or update if exists)
        stmt = pg_insert(PortfolioSnapshot).values(**values)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_org_snapshot_date",
            set_={
                "total_value": stmt.excluded.total_value,
                "total_cost_basis": stmt.excluded.total_cost_basis,
                "total_gain_loss": stmt.excluded.total_gain_loss,
                "total_gain_loss_percent": stmt.excluded.total_gain_loss_percent,
                "stocks_value": stmt.excluded.stocks_value,
                "bonds_value": stmt.excluded.bonds_value,
                "etf_value": stmt.excluded.etf_value,
                "mutual_funds_value": stmt.excluded.mutual_funds_value,
                "cash_value": stmt.excluded.cash_value,
                "other_value": stmt.excluded.other_value,
                "retirement_value": stmt.excluded.retirement_value,
                "taxable_value": stmt.excluded.taxable_value,
                "domestic_value": stmt.excluded.domestic_value,
                "international_value": stmt.excluded.international_value,
                "snapshot_data": stmt.excluded.snapshot_data,
            },
        ).returning(PortfolioSnapshot)

        result = await db.execute(stmt)
        await db.commit()
        snapshot = result.scalar_one()

        logger.info(
            f"Captured snapshot for org {organization_id} on {snapshot_date}: ${snapshot.total_value}"
        )
        return snapshot

    async def get_snapshots(
        self,
        db: AsyncSession,
        organization_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: Optional[int] = None,
    ) -> List[PortfolioSnapshot]:
        """
        Get historical snapshots for an organization.

        Args:
            db: Database session
            organization_id: Organization ID
            start_date: Start date (inclusive)
            end_date: End date (inclusive, defaults to today)
            limit: Maximum number of snapshots to return

        Returns:
            List of PortfolioSnapshot objects ordered by date ascending
        """
        query = select(PortfolioSnapshot).where(
            PortfolioSnapshot.organization_id == organization_id
        )

        if start_date:
            query = query.where(PortfolioSnapshot.snapshot_date >= start_date)

        if end_date:
            query = query.where(PortfolioSnapshot.snapshot_date <= end_date)

        query = query.order_by(PortfolioSnapshot.snapshot_date.asc())

        if limit:
            query = query.limit(limit)

        result = await db.execute(query)
        snapshots = result.scalars().all()

        logger.info(f"Retrieved {len(snapshots)} snapshots for org {organization_id}")
        return list(snapshots)

    async def get_latest_snapshot(
        self, db: AsyncSession, organization_id: UUID
    ) -> Optional[PortfolioSnapshot]:
        """
        Get the most recent snapshot for an organization.

        Args:
            db: Database session
            organization_id: Organization ID

        Returns:
            Latest PortfolioSnapshot or None if no snapshots exist
        """
        query = (
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.organization_id == organization_id)
            .order_by(PortfolioSnapshot.snapshot_date.desc())
            .limit(1)
        )

        result = await db.execute(query)
        return result.scalar_one_or_none()


# Singleton instance
snapshot_service = SnapshotService()
