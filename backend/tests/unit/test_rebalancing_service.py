"""Unit tests for RebalancingService — presets, drift calculation, DB operations."""

from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.schemas.target_allocation import AllocationSlice
from app.services.rebalancing_service import (
    PRESET_PORTFOLIOS,
    RebalancingService,
)

# ── get_presets ──────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestGetPresets:
    """Test preset portfolio retrieval."""

    def test_returns_all_presets(self):
        presets = RebalancingService.get_presets()
        assert len(presets) == 5
        assert "bogleheads_3fund" in presets
        assert "balanced_60_40" in presets
        assert "target_date_2050" in presets
        assert "conservative_30_70" in presets
        assert "all_weather" in presets

    def test_preset_allocations_sum_to_100(self):
        for key, preset in PRESET_PORTFOLIOS.items():
            total = sum(a["target_percent"] for a in preset["allocations"])
            assert total == 100, f"{key} allocations sum to {total}, expected 100"

    def test_preset_has_name_and_allocations(self):
        for key, preset in PRESET_PORTFOLIOS.items():
            assert "name" in preset
            assert "allocations" in preset
            assert len(preset["allocations"]) > 0


# ── get_active_allocation ────────────────────────────────────────────────────


@pytest.mark.unit
class TestGetActiveAllocation:
    """Test active allocation retrieval."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_returns_active_allocation(self, mock_db):
        alloc = Mock()
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = alloc
        mock_db.execute.return_value = result_mock

        result = await RebalancingService.get_active_allocation(mock_db, uuid4())
        assert result == alloc

    @pytest.mark.asyncio
    async def test_returns_none_when_no_active(self, mock_db):
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock

        result = await RebalancingService.get_active_allocation(mock_db, uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_with_user_id_filter(self, mock_db):
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock

        await RebalancingService.get_active_allocation(mock_db, uuid4(), user_id=uuid4())
        mock_db.execute.assert_awaited_once()


# ── deactivate_other_allocations ─────────────────────────────────────────────


@pytest.mark.unit
class TestDeactivateOtherAllocations:
    """Test deactivation of other allocations."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_deactivates_without_exclude(self, mock_db):
        await RebalancingService.deactivate_other_allocations(mock_db, uuid4(), uuid4())
        assert mock_db.execute.await_count == 2  # SELECT FOR UPDATE + UPDATE

    @pytest.mark.asyncio
    async def test_deactivates_with_exclude_id(self, mock_db):
        await RebalancingService.deactivate_other_allocations(
            mock_db, uuid4(), uuid4(), exclude_id=uuid4()
        )
        assert mock_db.execute.await_count == 2


# ── calculate_drift ──────────────────────────────────────────────────────────


@pytest.mark.unit
class TestCalculateDrift:
    """Test portfolio drift calculation logic."""

    def _make_slice(self, asset_class, target_percent, label=None):
        return AllocationSlice(
            asset_class=asset_class,
            target_percent=Decimal(str(target_percent)),
            label=label or asset_class.title(),
        )

    def test_on_target_within_1_percent(self):
        """Portfolio on target (drift within 1%)."""
        slices = [
            self._make_slice("domestic", 60, "US Stocks"),
            self._make_slice("bond", 40, "Bonds"),
        ]
        current = {
            "domestic": Decimal("6050"),  # 60.5%
            "bond": Decimal("3950"),  # 39.5%
        }

        drift_items, trades, needs_rebalancing, max_drift = RebalancingService.calculate_drift(
            slices, current, Decimal("10000"), Decimal("5")
        )

        assert len(drift_items) == 2
        assert not needs_rebalancing
        assert all(d.status == "on_target" for d in drift_items)
        assert len(trades) == 0

    def test_overweight_detection(self):
        """Detect overweight when current > target + 1%."""
        slices = [
            self._make_slice("domestic", 60, "US Stocks"),
            self._make_slice("bond", 40, "Bonds"),
        ]
        current = {
            "domestic": Decimal("7000"),  # 70%
            "bond": Decimal("3000"),  # 30%
        }

        drift_items, trades, needs_rebalancing, max_drift = RebalancingService.calculate_drift(
            slices, current, Decimal("10000"), Decimal("5")
        )

        domestic = next(d for d in drift_items if d.asset_class == "domestic")
        bond = next(d for d in drift_items if d.asset_class == "bond")

        assert domestic.status == "overweight"
        assert bond.status == "underweight"
        assert needs_rebalancing
        assert max_drift == Decimal("10.00")

    def test_trade_recommendations_generated(self):
        """Trade recommendations when drift exceeds threshold."""
        slices = [
            self._make_slice("domestic", 60, "US Stocks"),
            self._make_slice("bond", 40, "Bonds"),
        ]
        current = {
            "domestic": Decimal("7000"),
            "bond": Decimal("3000"),
        }

        _, trades, _, _ = RebalancingService.calculate_drift(
            slices, current, Decimal("10000"), Decimal("5")
        )

        assert len(trades) == 2
        sell_trade = next(t for t in trades if t.action == "SELL")
        buy_trade = next(t for t in trades if t.action == "BUY")

        assert sell_trade.asset_class == "domestic"
        assert buy_trade.asset_class == "bond"
        assert sell_trade.amount == Decimal("1000.00")
        assert buy_trade.amount == Decimal("1000.00")

    def test_no_trades_below_threshold(self):
        """No trade recommendations when drift is below threshold."""
        slices = [
            self._make_slice("domestic", 60, "US Stocks"),
            self._make_slice("bond", 40, "Bonds"),
        ]
        current = {
            "domestic": Decimal("6200"),  # 62%
            "bond": Decimal("3800"),  # 38%
        }

        _, trades, needs_rebalancing, _ = RebalancingService.calculate_drift(
            slices, current, Decimal("10000"), Decimal("5")
        )

        assert not needs_rebalancing
        assert len(trades) == 0

    def test_zero_portfolio_total(self):
        """Zero portfolio total doesn't cause division by zero."""
        slices = [self._make_slice("domestic", 60, "US Stocks")]
        current = {"domestic": Decimal("0")}

        drift_items, trades, needs_rebalancing, max_drift = RebalancingService.calculate_drift(
            slices, current, Decimal("0"), Decimal("5")
        )

        assert len(drift_items) == 1
        assert drift_items[0].current_percent == Decimal("0")

    def test_missing_asset_class_defaults_to_zero(self):
        """Asset class not in current portfolio defaults to $0."""
        slices = [
            self._make_slice("domestic", 60, "US Stocks"),
            self._make_slice("international", 40, "Intl"),
        ]
        current = {
            "domestic": Decimal("10000"),
            # international missing entirely
        }

        drift_items, trades, needs_rebalancing, max_drift = RebalancingService.calculate_drift(
            slices, current, Decimal("10000"), Decimal("5")
        )

        intl = next(d for d in drift_items if d.asset_class == "international")
        assert intl.current_value == Decimal("0")
        assert intl.current_percent == Decimal("0")
        assert intl.status == "underweight"

    def test_three_fund_portfolio(self):
        """Three-fund portfolio with mixed drift."""
        slices = [
            self._make_slice("domestic", 60, "US Stocks"),
            self._make_slice("international", 30, "Intl"),
            self._make_slice("bond", 10, "Bonds"),
        ]
        current = {
            "domestic": Decimal("55000"),
            "international": Decimal("30000"),
            "bond": Decimal("15000"),
        }
        total = Decimal("100000")

        drift_items, trades, needs_rebalancing, max_drift = RebalancingService.calculate_drift(
            slices, current, total, Decimal("3")
        )

        assert len(drift_items) == 3
        assert needs_rebalancing  # bond is 5% over target

    def test_max_drift_tracks_largest(self):
        """max_drift reflects the largest absolute drift."""
        slices = [
            self._make_slice("domestic", 50, "US"),
            self._make_slice("bond", 50, "Bonds"),
        ]
        current = {
            "domestic": Decimal("7000"),
            "bond": Decimal("3000"),
        }

        _, _, _, max_drift = RebalancingService.calculate_drift(
            slices, current, Decimal("10000"), Decimal("5")
        )

        assert max_drift == Decimal("20.00")
