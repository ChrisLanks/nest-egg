"""Tax-loss harvesting suggestion service."""

import logging
from collections import defaultdict
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account, TaxTreatment
from app.models.holding import Holding

logger = logging.getLogger(__name__)

# Default tax rates for estimation
FEDERAL_TAX_RATE = Decimal("0.22")  # 22% marginal
STATE_TAX_RATE = Decimal("0.05")  # 5% average state
COMBINED_TAX_RATE = FEDERAL_TAX_RATE + STATE_TAX_RATE


class TaxLossOpportunity:
    """A single tax-loss harvesting opportunity."""

    def __init__(
        self,
        holding_id: UUID,
        ticker: str,
        name: Optional[str],
        shares: Decimal,
        cost_basis: Decimal,
        current_value: Decimal,
        unrealized_loss: Decimal,
        loss_percentage: Decimal,
        estimated_tax_savings: Decimal,
        wash_sale_risk: bool,
        wash_sale_reason: Optional[str],
        sector: Optional[str],
        suggested_replacements: List[str],
    ):
        self.holding_id = holding_id
        self.ticker = ticker
        self.name = name
        self.shares = shares
        self.cost_basis = cost_basis
        self.current_value = current_value
        self.unrealized_loss = unrealized_loss
        self.loss_percentage = loss_percentage
        self.estimated_tax_savings = estimated_tax_savings
        self.wash_sale_risk = wash_sale_risk
        self.wash_sale_reason = wash_sale_reason
        self.sector = sector
        self.suggested_replacements = suggested_replacements


class TaxLossHarvestingService:
    """Identifies tax-loss harvesting opportunities from user holdings."""

    async def get_opportunities(
        self,
        db: AsyncSession,
        organization_id: UUID,
    ) -> List[TaxLossOpportunity]:
        """Find holdings with unrealized losses in taxable accounts only.

        Tax-loss harvesting only applies to taxable accounts (brokerage, etc.).
        Losses in retirement accounts (401k, IRA, HSA, 529) cannot be claimed.
        """
        # Get taxable account IDs — only these are eligible for tax-loss harvesting
        acct_result = await db.execute(
            select(Account.id).where(
                Account.organization_id == organization_id,
                Account.is_active.is_(True),
                Account.tax_treatment == TaxTreatment.TAXABLE,
            )
        )
        taxable_account_ids = {row[0] for row in acct_result.all()}

        # Also include accounts with NULL tax_treatment that look taxable (brokerage, crypto)
        from app.models.account import AccountType
        fallback_result = await db.execute(
            select(Account.id).where(
                Account.organization_id == organization_id,
                Account.is_active.is_(True),
                Account.tax_treatment.is_(None),
                Account.account_type.in_([AccountType.BROKERAGE, AccountType.CRYPTO]),
            )
        )
        taxable_account_ids.update(row[0] for row in fallback_result.all())

        if not taxable_account_ids:
            return []

        # Get holdings in taxable accounts with cost basis data
        result = await db.execute(
            select(Holding).where(
                Holding.organization_id == organization_id,
                Holding.account_id.in_(taxable_account_ids),
                Holding.total_cost_basis.isnot(None),
                Holding.current_total_value.isnot(None),
            )
        )
        holdings = result.scalars().all()

        # Build sector -> tickers map for replacement suggestions
        sector_tickers: dict[Optional[str], list[str]] = defaultdict(list)
        for h in holdings:
            if h.sector:
                sector_tickers[h.sector].append(h.ticker)

        opportunities = []
        for h in holdings:
            if h.total_cost_basis is None or h.current_total_value is None:
                continue

            unrealized_loss = h.current_total_value - h.total_cost_basis
            if unrealized_loss >= 0:
                continue  # No loss = no harvesting opportunity

            loss_pct = (
                (unrealized_loss / h.total_cost_basis * 100).quantize(Decimal("0.01"))
                if h.total_cost_basis > 0
                else Decimal("0")
            )
            tax_savings = (abs(unrealized_loss) * COMBINED_TAX_RATE).quantize(
                Decimal("0.01")
            )

            # Suggest same-sector replacements (excluding current ticker)
            replacements = []
            if h.sector and h.sector in sector_tickers:
                replacements = [
                    t for t in sector_tickers[h.sector] if t != h.ticker
                ]

            opportunities.append(
                TaxLossOpportunity(
                    holding_id=h.id,
                    ticker=h.ticker,
                    name=h.name,
                    shares=h.shares,
                    cost_basis=h.total_cost_basis,
                    current_value=h.current_total_value,
                    unrealized_loss=abs(unrealized_loss),
                    loss_percentage=abs(loss_pct),
                    estimated_tax_savings=tax_savings,
                    wash_sale_risk=False,  # Simplified -- would need transaction history for full check
                    wash_sale_reason=None,
                    sector=h.sector,
                    suggested_replacements=replacements[:3],
                )
            )

        # Sort by largest tax savings
        opportunities.sort(key=lambda o: o.estimated_tax_savings, reverse=True)
        return opportunities


tax_loss_harvesting_service = TaxLossHarvestingService()
