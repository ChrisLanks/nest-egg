"""Unit tests for StressTestService."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.constants.financial import STRESS_TEST
from app.services.stress_test_service import StressTestService


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def org_id():
    return uuid4()


def _make_portfolio(equity=0.0, bonds=0.0, other=0.0):
    """Build a portfolio composition dict."""
    return {
        "equity": equity,
        "bonds": bonds,
        "other": other,
        "total": equity + bonds + other,
    }


# ── run_scenario ──────────────────────────────────────────────────────────


class TestRunScenario:
    def test_run_scenario_gfc(self):
        """100% equity portfolio drops ~57% under GFC 2008 scenario."""
        portfolio = _make_portfolio(equity=100_000.0)
        result = StressTestService.run_scenario(portfolio, "gfc_2008")

        assert result["scenario_key"] == "gfc_2008"
        assert result["portfolio_before"] == pytest.approx(100_000.0)
        # equity_drop = -0.57 → 43,000 remaining
        assert result["portfolio_after"] == pytest.approx(43_000.0, abs=1.0)
        assert result["pct_change"] == pytest.approx(-0.57, abs=0.001)

    def test_run_scenario_bond_only(self):
        """Bond-only portfolio barely affected by equity crash (GFC)."""
        portfolio = _make_portfolio(bonds=100_000.0)
        result = StressTestService.run_scenario(portfolio, "gfc_2008")

        # GFC bond_change = +0.08 (flight to safety)
        assert result["portfolio_after"] == pytest.approx(108_000.0, abs=1.0)
        assert result["pct_change"] == pytest.approx(0.08, abs=0.001)
        assert result["by_asset_class"]["equity"]["before"] == pytest.approx(0.0)
        assert result["by_asset_class"]["equity"]["after"] == pytest.approx(0.0)

    def test_run_scenario_invalid_key(self):
        """Raises ValueError for an unknown scenario key."""
        portfolio = _make_portfolio(equity=100_000.0)
        with pytest.raises(ValueError, match="Unknown scenario"):
            StressTestService.run_scenario(portfolio, "nonexistent_scenario_xyz")

    def test_rate_shock_bonds(self):
        """Bonds drop when rates rise in the rate_shock_200bps scenario."""
        portfolio = _make_portfolio(bonds=100_000.0)
        result = StressTestService.run_scenario(portfolio, "rate_shock_200bps")

        # rate_increase_bps=200, avg_duration=6, sensitivity=-0.01/100bps
        # bond_change = 6 * -0.01 * (200/100) = -0.12
        assert result["by_asset_class"]["bonds"]["change_pct"] == pytest.approx(-0.12, abs=0.001)
        assert result["portfolio_after"] < result["portfolio_before"]

    def test_run_scenario_mixed_portfolio(self):
        """Mixed equity+bond portfolio correctly splits scenario impact."""
        portfolio = _make_portfolio(equity=70_000.0, bonds=30_000.0)
        result = StressTestService.run_scenario(portfolio, "market_crash_30")

        # equity_drop=-0.30 → 49,000; bond_change=+0.05 → 31,500
        expected_after = 70_000 * 0.70 + 30_000 * 1.05
        assert result["portfolio_after"] == pytest.approx(expected_after, abs=1.0)

    def test_scenario_label_present(self):
        """Each scenario result includes a human-readable label."""
        portfolio = _make_portfolio(equity=50_000.0)
        result = StressTestService.run_scenario(portfolio, "dot_com_2000")
        assert "Dot-Com" in result["scenario_label"]

    def test_zero_portfolio_pct_change_is_zero(self):
        """Zero portfolio doesn't cause division by zero."""
        portfolio = _make_portfolio()
        result = StressTestService.run_scenario(portfolio, "gfc_2008")
        assert result["pct_change"] == pytest.approx(0.0)


# ── run_all_scenarios ─────────────────────────────────────────────────────


class TestRunAllScenarios:
    @pytest.mark.asyncio
    async def test_run_all_scenarios_returns_all(self, mock_db, org_id):
        """All 6 scenarios are returned."""
        # Mock get_portfolio_composition to return a fixed portfolio
        mock_result = MagicMock()
        mock_result.all.return_value = []  # empty holdings
        mock_db.execute = AsyncMock(return_value=mock_result)

        results = await StressTestService.run_all_scenarios(
            db=mock_db,
            organization_id=org_id,
        )
        expected_count = len(STRESS_TEST.SCENARIOS)
        assert len(results) == expected_count

    @pytest.mark.asyncio
    async def test_run_all_scenarios_sorted_worst_first(self, mock_db, org_id):
        """Results are sorted from worst (most negative) to best pct_change."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        results = await StressTestService.run_all_scenarios(
            db=mock_db,
            organization_id=org_id,
        )
        pct_changes = [r["pct_change"] for r in results]
        assert pct_changes == sorted(pct_changes)


# ── get_portfolio_composition ─────────────────────────────────────────────


class TestGetPortfolioComposition:
    @pytest.mark.asyncio
    async def test_empty_portfolio(self, mock_db, org_id):
        """Empty portfolio returns zeros."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await StressTestService.get_portfolio_composition(
            db=mock_db,
            organization_id=org_id,
        )
        assert result["equity"] == 0.0
        assert result["bonds"] == 0.0
        assert result["other"] == 0.0
        assert result["total"] == 0.0

    @pytest.mark.asyncio
    async def test_classifies_bond_asset_type(self, mock_db, org_id):
        """Holdings with asset_type='bond' go to bonds bucket."""
        from app.models.account import AccountType

        holding = MagicMock()
        holding.current_total_value = Decimal("10000")
        holding.asset_type = "bond"

        account = MagicMock()
        account.account_type = AccountType.BROKERAGE
        account.is_active = True

        mock_result = MagicMock()
        mock_result.all.return_value = [(holding, account)]
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await StressTestService.get_portfolio_composition(
            db=mock_db,
            organization_id=org_id,
        )
        assert result["bonds"] == pytest.approx(10000.0)
        assert result["equity"] == pytest.approx(0.0)

    @pytest.mark.asyncio
    async def test_classifies_stock_as_equity(self, mock_db, org_id):
        """Holdings with asset_type='stock' go to equity bucket."""
        from app.models.account import AccountType

        holding = MagicMock()
        holding.current_total_value = Decimal("25000")
        holding.asset_type = "stock"

        account = MagicMock()
        account.account_type = AccountType.BROKERAGE
        account.is_active = True

        mock_result = MagicMock()
        mock_result.all.return_value = [(holding, account)]
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await StressTestService.get_portfolio_composition(
            db=mock_db,
            organization_id=org_id,
        )
        assert result["equity"] == pytest.approx(25000.0)
        assert result["bonds"] == pytest.approx(0.0)
