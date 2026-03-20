"""Tax lot service for per-lot cost basis tracking."""

import logging
from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import extract, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.holding import Holding
from app.models.tax_lot import CostBasisMethod, TaxLot
from app.utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)

# One year threshold for long-term vs short-term holding period
LONG_TERM_DAYS = 366  # > 1 year


def _determine_holding_period(acquisition_date: date, sale_date: date) -> str:
    """Determine if a lot qualifies as long-term or short-term."""
    days_held = (sale_date - acquisition_date).days
    return "LONG_TERM" if days_held >= LONG_TERM_DAYS else "SHORT_TERM"


class TaxLotService:
    """Manages tax lot creation, sales, and gain/loss calculations."""

    async def record_purchase(
        self,
        db: AsyncSession,
        org_id: UUID,
        holding_id: UUID,
        account_id: UUID,
        quantity: Decimal,
        price_per_share: Decimal,
        acquisition_date: date,
    ) -> TaxLot:
        """Create a new open tax lot for a purchase.

        Args:
            db: Database session
            org_id: Organization ID
            holding_id: Holding ID
            account_id: Account ID
            quantity: Number of shares purchased
            price_per_share: Cost per share
            acquisition_date: Date of acquisition

        Returns:
            Newly created TaxLot
        """
        total_cost = (quantity * price_per_share).quantize(Decimal("0.01"))

        lot = TaxLot(
            organization_id=org_id,
            holding_id=holding_id,
            account_id=account_id,
            acquisition_date=acquisition_date,
            quantity=quantity,
            cost_basis_per_share=price_per_share,
            total_cost_basis=total_cost,
            remaining_quantity=quantity,
            is_closed=False,
        )
        db.add(lot)
        await db.flush()
        await db.refresh(lot)
        return lot

    async def record_sale(
        self,
        db: AsyncSession,
        org_id: UUID,
        holding_id: UUID,
        account_id: UUID,
        quantity: Decimal,
        sale_price_per_share: Decimal,
        sale_date: date,
        method: Optional[CostBasisMethod] = None,
        specific_lot_ids: Optional[List[UUID]] = None,
    ) -> dict:
        """Record a sale by selecting lots per the cost basis method.

        Supports FIFO (oldest first), LIFO (newest first), HIFO (highest cost first),
        and specific identification.

        Args:
            db: Database session
            org_id: Organization ID
            holding_id: Holding ID
            account_id: Account ID
            quantity: Number of shares to sell
            sale_price_per_share: Sale price per share
            sale_date: Date of sale
            method: Cost basis method (overrides account default if provided)
            specific_lot_ids: Specific lot IDs for SPECIFIC_ID method

        Returns:
            Dictionary with sale results including gains/losses
        """
        # Determine method -- use account default if not specified
        if method is None:
            result = await db.execute(
                select(Account.cost_basis_method).where(
                    Account.id == account_id,
                    Account.organization_id == org_id,  # defense-in-depth: verify ownership
                )
            )
            account_method = result.scalar_one_or_none()
            method = CostBasisMethod(account_method) if account_method else CostBasisMethod.FIFO

        # Get open lots for this holding
        if method == CostBasisMethod.SPECIFIC_ID and specific_lot_ids:
            lots_result = await db.execute(
                select(TaxLot).where(
                    TaxLot.holding_id == holding_id,
                    TaxLot.organization_id == org_id,
                    TaxLot.is_closed.is_(False),
                    TaxLot.remaining_quantity > 0,
                    TaxLot.id.in_(specific_lot_ids),
                )
            )
        else:
            lots_result = await db.execute(
                select(TaxLot).where(
                    TaxLot.holding_id == holding_id,
                    TaxLot.organization_id == org_id,
                    TaxLot.is_closed.is_(False),
                    TaxLot.remaining_quantity > 0,
                )
            )

        lots = list(lots_result.scalars().all())

        # Sort lots based on method
        if method == CostBasisMethod.FIFO:
            lots.sort(key=lambda lot: lot.acquisition_date)
        elif method == CostBasisMethod.LIFO:
            lots.sort(key=lambda lot: lot.acquisition_date, reverse=True)
        elif method == CostBasisMethod.HIFO:
            lots.sort(key=lambda lot: lot.cost_basis_per_share, reverse=True)
        # SPECIFIC_ID: no sorting needed, use lots as selected

        # Validate sufficient quantity
        total_available = sum(lot.remaining_quantity for lot in lots)
        if total_available < quantity:
            raise ValueError(
                f"Insufficient shares: requested {quantity}, available {total_available}"
            )

        # Allocate sale across lots
        remaining_to_sell = quantity
        total_proceeds = Decimal("0")
        total_cost_basis = Decimal("0")
        short_term_gl = Decimal("0")
        long_term_gl = Decimal("0")
        affected_lots = []
        now = utc_now()

        for lot in lots:
            if remaining_to_sell <= 0:
                break

            sell_from_lot = min(remaining_to_sell, lot.remaining_quantity)
            lot_proceeds = (sell_from_lot * sale_price_per_share).quantize(Decimal("0.01"))
            lot_cost = (sell_from_lot * lot.cost_basis_per_share).quantize(Decimal("0.01"))
            lot_gain_loss = lot_proceeds - lot_cost
            holding_period = _determine_holding_period(lot.acquisition_date, sale_date)

            # Update lot
            lot.remaining_quantity = lot.remaining_quantity - sell_from_lot
            if lot.remaining_quantity == 0:
                lot.is_closed = True
                lot.closed_at = now
            lot.sale_proceeds = (lot.sale_proceeds or Decimal("0")) + lot_proceeds
            lot.realized_gain_loss = (lot.realized_gain_loss or Decimal("0")) + lot_gain_loss
            lot.holding_period = holding_period

            # Accumulate totals
            total_proceeds += lot_proceeds
            total_cost_basis += lot_cost
            if holding_period == "SHORT_TERM":
                short_term_gl += lot_gain_loss
            else:
                long_term_gl += lot_gain_loss

            remaining_to_sell -= sell_from_lot
            affected_lots.append(lot)

        await db.flush()
        # Refresh affected lots so response reflects updated state
        for lot in affected_lots:
            await db.refresh(lot)

        return {
            "total_proceeds": total_proceeds,
            "total_cost_basis": total_cost_basis,
            "realized_gain_loss": total_proceeds - total_cost_basis,
            "short_term_gain_loss": short_term_gl,
            "long_term_gain_loss": long_term_gl,
            "lots_affected": len(affected_lots),
            "lot_details": affected_lots,
        }

    async def get_lots(
        self,
        db: AsyncSession,
        holding_id: UUID,
        include_closed: bool = False,
    ) -> List[TaxLot]:
        """List tax lots for a holding.

        Args:
            db: Database session
            holding_id: Holding ID
            include_closed: Whether to include closed (fully sold) lots

        Returns:
            List of TaxLot objects
        """
        query = select(TaxLot).where(TaxLot.holding_id == holding_id)
        if not include_closed:
            query = query.where(TaxLot.is_closed.is_(False))
        query = query.order_by(TaxLot.acquisition_date)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_unrealized_gains(
        self,
        db: AsyncSession,
        account_id: UUID,
        org_id: Optional[UUID] = None,
    ) -> dict:
        """Calculate per-lot unrealized gains using current holding prices.

        Args:
            db: Database session
            account_id: Account ID

        Returns:
            Dictionary with unrealized gains summary
        """
        # Get open lots for this account
        result = await db.execute(
            select(TaxLot)
            .where(
                TaxLot.account_id == account_id,
                TaxLot.is_closed.is_(False),
                TaxLot.remaining_quantity > 0,
            )
            .order_by(TaxLot.acquisition_date)
        )
        lots = result.scalars().all()

        # Get current prices from holdings — scope to org as defense-in-depth
        holding_ids = {lot.holding_id for lot in lots}
        holdings_query = select(Holding).where(Holding.id.in_(holding_ids))
        if org_id is not None:
            holdings_query = holdings_query.where(Holding.organization_id == org_id)
        holdings_result = await db.execute(holdings_query)
        holdings_map = {h.id: h for h in holdings_result.scalars().all()}

        today = date.today()
        total_unrealized = Decimal("0")
        short_term = Decimal("0")
        long_term = Decimal("0")
        lot_items = []

        for lot in lots:
            holding = holdings_map.get(lot.holding_id)
            current_price = holding.current_price_per_share if holding else None
            unrealized_gl = None

            if current_price is not None:
                current_value = (lot.remaining_quantity * current_price).quantize(Decimal("0.01"))
                lot_cost = (lot.remaining_quantity * lot.cost_basis_per_share).quantize(
                    Decimal("0.01")
                )
                unrealized_gl = current_value - lot_cost
                total_unrealized += unrealized_gl

                period = _determine_holding_period(lot.acquisition_date, today)
                if period == "SHORT_TERM":
                    short_term += unrealized_gl
                else:
                    long_term += unrealized_gl
            else:
                period = _determine_holding_period(lot.acquisition_date, today)

            lot_items.append(
                {
                    "lot_id": lot.id,
                    "holding_id": lot.holding_id,
                    "ticker": holding.ticker if holding else "UNKNOWN",
                    "acquisition_date": lot.acquisition_date,
                    "quantity": lot.remaining_quantity,
                    "cost_basis_per_share": lot.cost_basis_per_share,
                    "current_price_per_share": current_price,
                    "unrealized_gain_loss": unrealized_gl,
                    "holding_period": period,
                }
            )

        return {
            "account_id": account_id,
            "total_unrealized_gain_loss": total_unrealized,
            "short_term_unrealized": short_term,
            "long_term_unrealized": long_term,
            "lots": lot_items,
        }

    async def get_realized_gains_summary(
        self,
        db: AsyncSession,
        org_id: UUID,
        tax_year: int,
    ) -> dict:
        """Get short-term vs long-term realized gains for a tax year.

        Args:
            db: Database session
            org_id: Organization ID
            tax_year: Tax year to summarize

        Returns:
            Dictionary with realized gains summary
        """
        result = await db.execute(
            select(TaxLot).where(
                TaxLot.organization_id == org_id,
                TaxLot.is_closed.is_(True),
                TaxLot.closed_at.isnot(None),
                extract("year", TaxLot.closed_at) == tax_year,
            )
        )
        lots = result.scalars().all()

        total_gl = Decimal("0")
        short_term_gl = Decimal("0")
        long_term_gl = Decimal("0")
        total_proceeds = Decimal("0")
        total_cost = Decimal("0")

        for lot in lots:
            gl = lot.realized_gain_loss or Decimal("0")
            proceeds = lot.sale_proceeds or Decimal("0")
            cost = lot.total_cost_basis or Decimal("0")

            total_gl += gl
            total_proceeds += proceeds
            total_cost += cost

            if lot.holding_period == "SHORT_TERM":
                short_term_gl += gl
            else:
                long_term_gl += gl

        return {
            "tax_year": tax_year,
            "total_realized_gain_loss": total_gl,
            "short_term_gain_loss": short_term_gl,
            "long_term_gain_loss": long_term_gl,
            "total_proceeds": total_proceeds,
            "total_cost_basis": total_cost,
            "lots_closed": len(lots),
        }

    async def import_lots_from_holding(
        self,
        db: AsyncSession,
        holding_id: UUID,
        org_id: Optional[UUID] = None,
    ) -> Optional[TaxLot]:
        """Auto-create a single tax lot from existing holding data (for migration).

        Uses the holding's cost_basis_per_share and shares to create one lot.
        If cost basis data is missing, no lot is created.

        Args:
            db: Database session
            holding_id: Holding ID to import from
            org_id: Organization ID for ownership verification (defense-in-depth)

        Returns:
            Created TaxLot or None if insufficient data
        """
        query = select(Holding).where(Holding.id == holding_id)
        if org_id is not None:
            # Defense-in-depth: verify the holding belongs to the caller's org.
            # The API layer already does this check, but we enforce it here too
            # so the service cannot be misused by future callers.
            query = query.where(Holding.organization_id == org_id)
        result = await db.execute(query)
        holding = result.scalar_one_or_none()

        if not holding:
            return None

        if not holding.cost_basis_per_share or not holding.shares:
            logger.warning(
                "Cannot import lot for holding %s: missing cost basis or shares",
                holding_id,
            )
            return None

        # Check if lots already exist for this holding
        existing = await db.execute(
            select(TaxLot.id).where(TaxLot.holding_id == holding_id).limit(1)
        )
        if existing.scalar_one_or_none():
            logger.info("Lots already exist for holding %s, skipping import", holding_id)
            return None

        lot = await self.record_purchase(
            db=db,
            org_id=holding.organization_id,
            holding_id=holding.id,
            account_id=holding.account_id,
            quantity=holding.shares,
            price_per_share=holding.cost_basis_per_share,
            acquisition_date=holding.created_at.date() if holding.created_at else date.today(),
        )
        return lot


tax_lot_service = TaxLotService()
