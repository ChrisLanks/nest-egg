"""Portfolio stress testing service.

Models portfolio impact under historical and hypothetical market scenarios
using hardcoded scenario parameters from STRESS_TEST constants.
"""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.financial import STRESS_TEST
from app.models.holding import Holding
from app.models.account import Account, AccountType


# Asset class classification for holdings
EQUITY_ACCOUNT_TYPES = {
    AccountType.BROKERAGE,
    AccountType.RETIREMENT_401K,
    AccountType.RETIREMENT_IRA,
    AccountType.RETIREMENT_ROTH,
    AccountType.RETIREMENT_403B,
    AccountType.RETIREMENT_457B,
    AccountType.CRYPTO,
}

BOND_ASSET_TYPES = {"bond", "fixed_income", "treasury"}  # holding.asset_type values
EQUITY_ASSET_TYPES = {"stock", "etf", "mutual_fund", "equity"}


class StressTestService:
    """Runs historical market stress scenarios against a user's portfolio."""

    @staticmethod
    async def get_portfolio_composition(
        db: AsyncSession,
        organization_id: UUID,
        user_id: UUID | None = None,
    ) -> dict:
        """Returns portfolio split into equity, bond, and other buckets by market value."""
        stmt = (
            select(Holding, Account)
            .join(Account, Holding.account_id == Account.id)
            .where(
                Account.organization_id == organization_id,
                Account.is_active == True,
            )
        )
        if user_id:
            stmt = stmt.where(Account.user_id == user_id)

        result = await db.execute(stmt)
        rows = result.all()

        equity_value = Decimal("0")
        bond_value = Decimal("0")
        other_value = Decimal("0")

        for holding, account in rows:
            # Use current_total_value (the actual Holding field name)
            value = holding.current_total_value or Decimal("0")
            asset_type = (holding.asset_type or "").lower()
            if asset_type in BOND_ASSET_TYPES:
                bond_value += value
            elif asset_type in EQUITY_ASSET_TYPES or account.account_type in EQUITY_ACCOUNT_TYPES:
                equity_value += value
            else:
                other_value += value

        total = equity_value + bond_value + other_value
        return {
            "equity": float(equity_value),
            "bonds": float(bond_value),
            "other": float(other_value),
            "total": float(total),
        }

    @staticmethod
    def run_scenario(
        portfolio: dict,
        scenario_key: str,
    ) -> dict:
        """Applies a named stress scenario to a portfolio composition dict.

        Returns pre/post values and percentage change by asset class.
        """
        scenarios = STRESS_TEST.SCENARIOS
        if scenario_key not in scenarios:
            raise ValueError(
                f"Unknown scenario: {scenario_key}. Valid: {list(scenarios)}"
            )

        scenario = scenarios[scenario_key]
        equity = Decimal(str(portfolio.get("equity", 0)))
        bonds = Decimal(str(portfolio.get("bonds", 0)))
        other = Decimal(str(portfolio.get("other", 0)))
        total_before = equity + bonds + other

        equity_drop = scenario.get("equity_drop", Decimal("0"))
        bond_change = scenario.get("bond_change")
        rate_increase_bps = scenario.get("rate_increase_bps")

        # For rate shock: bond impact = -duration * rate_change
        # Assume avg bond duration of 6 years if bond_change is None
        if rate_increase_bps is not None and bond_change is None:
            avg_duration = Decimal("6")
            bond_change = (
                avg_duration
                * STRESS_TEST.BOND_PRICE_SENSITIVITY_PER_YEAR_PER_100BPS
                * Decimal(str(rate_increase_bps)) / Decimal("100")
            )

        equity_after = equity * (1 + equity_drop)
        bonds_after = bonds * (1 + (bond_change or Decimal("0")))
        other_after = other  # Other assets unchanged
        total_after = equity_after + bonds_after + other_after

        dollar_change = total_after - total_before
        pct_change = (dollar_change / total_before) if total_before > 0 else Decimal("0")

        effective_bond_change = bond_change or Decimal("0")

        return {
            "scenario_key": scenario_key,
            "scenario_label": scenario.get("label", scenario_key),
            "portfolio_before": float(total_before),
            "portfolio_after": float(total_after),
            "dollar_change": float(dollar_change),
            "pct_change": float(pct_change),
            "by_asset_class": {
                "equity": {
                    "before": float(equity),
                    "after": float(equity_after),
                    "change_pct": float(equity_drop),
                },
                "bonds": {
                    "before": float(bonds),
                    "after": float(bonds_after),
                    "change_pct": float(effective_bond_change),
                },
                "other": {
                    "before": float(other),
                    "after": float(other_after),
                    "change_pct": 0.0,
                },
            },
        }

    @staticmethod
    async def run_all_scenarios(
        db: AsyncSession,
        organization_id: UUID,
        user_id: UUID | None = None,
    ) -> list[dict]:
        """Runs all hardcoded scenarios against the current portfolio."""
        portfolio = await StressTestService.get_portfolio_composition(
            db, organization_id, user_id
        )
        results = []
        for key in STRESS_TEST.SCENARIOS:
            try:
                results.append(StressTestService.run_scenario(portfolio, key))
            except Exception:
                pass
        results.sort(key=lambda x: x["pct_change"])
        return results
