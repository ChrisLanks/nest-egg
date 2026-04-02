"""Capital gains harvesting analysis service.

Identifies opportunities to realize long-term capital gains at 0% federal rate
during low-income years by analyzing available LTCG bracket room.
"""
from __future__ import annotations

import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.financial import TAX


def _ltcg_0pct_ceiling(tax_year: int | None = None) -> dict[str, Decimal]:
    """Derive 0% LTCG ceilings from TAX constants for the given year.

    The 0% LTCG rate applies up to the first bracket threshold in
    LTCG_BRACKETS_SINGLE / LTCG_BRACKETS_MARRIED.
    """
    year = tax_year or datetime.date.today().year
    tax_data = TAX.for_year(year)
    single_ceiling = Decimal(str(tax_data["LTCG_BRACKETS_SINGLE"][0][0]))
    married_ceiling = Decimal(str(tax_data["LTCG_BRACKETS_MARRIED"][0][0]))
    # HoH is approximately midpoint; use single as conservative fallback
    hoh_ceiling = Decimal(str(int((float(single_ceiling) + float(married_ceiling)) / 2)))
    return {
        "single": single_ceiling,
        "married_filing_jointly": married_ceiling,
        "married_filing_separately": single_ceiling,
        "head_of_household": hoh_ceiling,
    }


class CapitalGainsHarvestingService:
    """Provides capital gains harvesting analysis against the 0% LTCG bracket."""

    @staticmethod
    async def get_ltcg_bracket_fill(
        db: AsyncSession,
        organization_id: UUID,
        current_taxable_income: Decimal,
        filing_status: str = "single",
        tax_year: int | None = None,
    ) -> dict:
        """Returns how much LTCG can be realized at 0% federal rate.

        The 0% LTCG bracket applies up to the top of the 12% ordinary income bracket.

        Returns:
            dict with available_0pct_room, current_income, bracket_ceiling,
            suggested_harvest_amount
        """
        ceilings = _ltcg_0pct_ceiling(tax_year)
        ceiling = ceilings.get(filing_status.lower(), ceilings["single"])
        available = max(Decimal("0"), ceiling - current_taxable_income)
        return {
            "filing_status": filing_status,
            "ltcg_0pct_ceiling": float(ceiling),
            "current_taxable_income": float(current_taxable_income),
            "available_0pct_room": float(available),
            "suggested_harvest_amount": float(min(available, Decimal("50000"))),
        }

    @staticmethod
    async def get_harvest_candidates(
        db: AsyncSession,
        organization_id: UUID,
        user_id: UUID | None,
        min_gain: Decimal = Decimal("500"),
    ) -> list[dict]:
        """Returns tax lots with unrealized long-term gains eligible for harvesting.

        Filters: held > 365 days, unrealized gain > min_gain.
        TaxLot uses acquisition_date, total_cost_basis, sale_proceeds, is_closed,
        realized_gain_loss, and closed_at fields.
        """
        from app.models.tax_lot import TaxLot
        from datetime import date, timedelta

        ltcg_cutoff = date.today() - timedelta(days=366)  # Must hold > 1 year (366 days)

        # TaxLot doesn't have a user_id — filter via account join if user_id given
        if user_id:
            from app.models.account import Account

            stmt = (
                select(TaxLot)
                .join(Account, TaxLot.account_id == Account.id)
                .where(
                    TaxLot.organization_id == organization_id,
                    TaxLot.is_closed == False,
                    TaxLot.acquisition_date <= ltcg_cutoff,
                    Account.user_id == user_id,
                )
            )
        else:
            stmt = select(TaxLot).where(
                TaxLot.organization_id == organization_id,
                TaxLot.is_closed == False,
                TaxLot.acquisition_date <= ltcg_cutoff,
            )

        result = await db.execute(stmt)
        lots = result.scalars().all()

        candidates = []
        for lot in lots:
            # Use total_cost_basis; current_value must be estimated from holding price
            # since TaxLot doesn't store current_value directly.
            # We require total_cost_basis to compute gain; skip if missing.
            if not lot.total_cost_basis:
                continue

            # Fetch current value from the associated holding
            from app.models.holding import Holding
            from app.models.account import Account, AccountType

            holding_result = await db.execute(
                select(Holding).where(Holding.id == lot.holding_id)
            )
            holding = holding_result.scalar_one_or_none()
            if not holding or not holding.current_total_value:
                continue

            # Compute per-lot current value proportional to remaining quantity
            if not holding.shares or holding.shares == 0:
                continue
            lot_fraction = lot.remaining_quantity / holding.shares
            lot_current_value = holding.current_total_value * lot_fraction
            lot_cost_basis = lot.total_cost_basis * (lot.remaining_quantity / lot.quantity)

            gain = lot_current_value - lot_cost_basis
            if gain < min_gain:
                continue

            # Fetch account type to determine crypto-specific tax treatment
            acct_result = await db.execute(
                select(Account.account_type).where(Account.id == lot.account_id)
            )
            account_type = acct_result.scalar_one_or_none()
            is_crypto = account_type == AccountType.CRYPTO

            holding_period_days = (date.today() - lot.acquisition_date).days
            candidates.append(
                {
                    "tax_lot_id": str(lot.id),
                    "ticker": holding.ticker,
                    "shares": float(lot.remaining_quantity),
                    "cost_basis": float(lot_cost_basis),
                    "current_value": float(lot_current_value),
                    "unrealized_gain": float(gain),
                    "acquisition_date": lot.acquisition_date.isoformat(),
                    "holding_period_days": holding_period_days,
                    "is_long_term": True,
                    "is_crypto": is_crypto,
                    "no_wash_sale_rule": is_crypto,
                    "crypto_wash_sale_note": (
                        "Crypto is currently treated as property (no wash-sale rule applies). "
                        "This may change if crypto is reclassified as a security."
                    ) if is_crypto else None,
                }
            )

        candidates.sort(key=lambda x: x["unrealized_gain"], reverse=True)
        return candidates

    @staticmethod
    async def get_ytd_realized_gains(
        db: AsyncSession,
        organization_id: UUID,
        user_id: UUID | None,
        tax_year: int | None = None,
    ) -> dict:
        """Returns YTD realized short-term and long-term gains from closed tax lots."""
        from app.models.tax_lot import TaxLot
        from datetime import date

        if tax_year is None:
            tax_year = date.today().year

        if user_id:
            from app.models.account import Account

            stmt = (
                select(TaxLot)
                .join(Account, TaxLot.account_id == Account.id)
                .where(
                    TaxLot.organization_id == organization_id,
                    TaxLot.is_closed == True,
                    Account.user_id == user_id,
                )
            )
        else:
            stmt = select(TaxLot).where(
                TaxLot.organization_id == organization_id,
                TaxLot.is_closed == True,
            )

        result = await db.execute(stmt)
        lots = result.scalars().all()

        stcg = Decimal("0")
        ltcg = Decimal("0")
        for lot in lots:
            # closed_at is a DateTime; check if it's in the target tax year
            if not lot.closed_at or lot.closed_at.year != tax_year:
                continue
            if not lot.realized_gain_loss:
                continue
            held_days = (lot.closed_at.date() - lot.acquisition_date).days
            if held_days > 365:
                ltcg += lot.realized_gain_loss
            else:
                stcg += lot.realized_gain_loss

        return {
            "tax_year": tax_year,
            "realized_stcg": float(stcg),
            "realized_ltcg": float(ltcg),
            "total_realized": float(stcg + ltcg),
        }
