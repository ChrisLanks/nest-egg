"""Service for syncing Plaid investment holdings into the holdings table."""

import logging
from decimal import Decimal
from typing import List, Dict, Tuple
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.holding import Holding
from app.models.account import Account
from app.utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)


class PlaidHoldingsSyncService:
    """Syncs Plaid investment holdings into the local holdings table."""

    async def sync_holdings(
        self,
        db: AsyncSession,
        account: Account,
        plaid_holdings: List[dict],
        plaid_securities: List[dict],
    ) -> int:
        """
        Sync Plaid holdings data into the holdings table.

        Returns number of holdings synced.
        """
        # Build security lookup: security_id -> security dict
        sec_map: Dict[str, dict] = {}
        for sec in plaid_securities:
            sec_map[sec["security_id"]] = sec

        # Get existing holdings for this account
        result = await db.execute(
            select(Holding).where(Holding.account_id == account.id)
        )
        existing = {h.ticker: h for h in result.scalars().all()}

        synced_tickers = set()
        total_value = Decimal("0")

        for h in plaid_holdings:
            security = sec_map.get(h.get("security_id", ""))
            if not security:
                continue

            ticker = security.get("ticker_symbol") or security.get("name", "UNKNOWN")
            ticker = ticker.upper()
            synced_tickers.add(ticker)

            shares = Decimal(str(h.get("quantity", 0)))
            price = Decimal(str(security.get("close_price", 0)))
            cost_basis = (
                Decimal(str(h.get("cost_basis", 0))) if h.get("cost_basis") else None
            )
            value = Decimal(str(h.get("institution_value", 0)))
            total_value += value

            asset_type = self._map_security_type(security.get("type", ""))

            if ticker in existing:
                # Update existing holding
                holding = existing[ticker]
                holding.shares = shares
                holding.current_price_per_share = price
                holding.current_total_value = value
                holding.total_cost_basis = cost_basis
                if cost_basis and shares > 0:
                    holding.cost_basis_per_share = (cost_basis / shares).quantize(
                        Decimal("0.01")
                    )
                holding.asset_type = asset_type
                holding.name = security.get("name")
                holding.price_as_of = utc_now()
            else:
                # Create new holding
                new_holding = Holding(
                    account_id=account.id,
                    organization_id=account.organization_id,
                    ticker=ticker,
                    name=security.get("name"),
                    shares=shares,
                    current_price_per_share=price,
                    current_total_value=value,
                    total_cost_basis=cost_basis,
                    cost_basis_per_share=(cost_basis / shares).quantize(
                        Decimal("0.01")
                    )
                    if cost_basis and shares > 0
                    else None,
                    asset_type=asset_type,
                    price_as_of=utc_now(),
                )
                db.add(new_holding)

        # Remove holdings that are no longer in Plaid
        for ticker, holding in existing.items():
            if ticker not in synced_tickers:
                await db.delete(holding)

        # Update account balance
        account.current_balance = total_value
        account.last_synced_at = utc_now()

        await db.commit()
        return len(synced_tickers)

    @staticmethod
    def _map_security_type(plaid_type: str) -> str:
        """Map Plaid security type to our asset_type."""
        mapping = {
            "equity": "stock",
            "etf": "etf",
            "mutual fund": "mutual_fund",
            "fixed income": "bond",
            "cash": "cash",
            "derivative": "other",
            "cryptocurrency": "crypto",
        }
        return mapping.get(plaid_type.lower(), "other")


plaid_holdings_sync_service = PlaidHoldingsSyncService()
