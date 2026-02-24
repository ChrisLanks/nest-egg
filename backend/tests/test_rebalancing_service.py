"""Tests for the rebalancing service drift calculations and schema validation."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.target_allocation import (
    AllocationSlice,
    TargetAllocationCreate,
    TargetAllocationUpdate,
)
from app.services.rebalancing_service import PRESET_PORTFOLIOS, RebalancingService


# ── Presets ──────────────────────────────────────────────────────────────────


class TestPresets:
    """Verify preset portfolio definitions are valid."""

    def test_all_presets_sum_to_100(self):
        for key, preset in PRESET_PORTFOLIOS.items():
            total = sum(a["target_percent"] for a in preset["allocations"])
            assert total == 100, f"Preset '{key}' allocations sum to {total}, expected 100"

    def test_bogleheads_has_three_slices(self):
        bg = PRESET_PORTFOLIOS["bogleheads_3fund"]
        assert len(bg["allocations"]) == 3
        classes = {a["asset_class"] for a in bg["allocations"]}
        assert classes == {"domestic", "international", "bond"}

    def test_all_presets_have_name(self):
        for key, preset in PRESET_PORTFOLIOS.items():
            assert "name" in preset and len(preset["name"]) > 0, f"Preset '{key}' missing name"

    def test_get_presets_returns_dict(self):
        presets = RebalancingService.get_presets()
        assert isinstance(presets, dict)
        assert "bogleheads_3fund" in presets
        assert "balanced_60_40" in presets
        assert "all_weather" in presets


# ── Drift calculation ────────────────────────────────────────────────────────


class TestCalculateDrift:
    """Test pure drift calculation logic."""

    def _make_slices(self, data: list[tuple[str, int, str]]) -> list[AllocationSlice]:
        return [
            AllocationSlice(asset_class=ac, target_percent=Decimal(str(tp)), label=label)
            for ac, tp, label in data
        ]

    def test_perfectly_balanced_portfolio(self):
        """When current matches target, no drift and no trades."""
        slices = self._make_slices([
            ("domestic", 60, "US Stocks"),
            ("international", 30, "Intl"),
            ("bond", 10, "Bonds"),
        ])
        current = {
            "domestic": Decimal("60000"),
            "international": Decimal("30000"),
            "bond": Decimal("10000"),
        }
        total = Decimal("100000")

        drift_items, trade_recs, needs_rebalancing, max_drift = (
            RebalancingService.calculate_drift(slices, current, total, Decimal("5"))
        )

        assert len(drift_items) == 3
        assert not needs_rebalancing
        assert len(trade_recs) == 0
        for item in drift_items:
            assert item.status == "on_target"
            assert abs(item.drift_percent) <= Decimal("1")

    def test_overweight_underweight_detection(self):
        """Detects overweight and underweight positions."""
        slices = self._make_slices([
            ("domestic", 60, "US Stocks"),
            ("bond", 40, "Bonds"),
        ])
        # Domestic is 80%, should be 60% → overweight
        # Bonds is 20%, should be 40% → underweight
        current = {
            "domestic": Decimal("80000"),
            "bond": Decimal("20000"),
        }
        total = Decimal("100000")

        drift_items, trade_recs, needs_rebalancing, max_drift = (
            RebalancingService.calculate_drift(slices, current, total, Decimal("5"))
        )

        domestic = next(d for d in drift_items if d.asset_class == "domestic")
        bond = next(d for d in drift_items if d.asset_class == "bond")

        assert domestic.status == "overweight"
        assert domestic.drift_percent == Decimal("20.00")
        assert bond.status == "underweight"
        assert bond.drift_percent == Decimal("-20.00")

    def test_trade_recommendations_generated_when_drift_exceeds_threshold(self):
        """Trade recommendations are generated for positions beyond threshold."""
        slices = self._make_slices([
            ("domestic", 60, "US Stocks"),
            ("bond", 40, "Bonds"),
        ])
        current = {
            "domestic": Decimal("75000"),
            "bond": Decimal("25000"),
        }
        total = Decimal("100000")

        drift_items, trade_recs, needs_rebalancing, max_drift = (
            RebalancingService.calculate_drift(slices, current, total, Decimal("5"))
        )

        assert needs_rebalancing
        assert len(trade_recs) == 2

        sell_rec = next(r for r in trade_recs if r.action == "SELL")
        buy_rec = next(r for r in trade_recs if r.action == "BUY")

        assert sell_rec.asset_class == "domestic"
        assert sell_rec.amount == Decimal("15000.00")
        assert buy_rec.asset_class == "bond"
        assert buy_rec.amount == Decimal("15000.00")

    def test_no_trades_when_within_threshold(self):
        """No trade recommendations when drift is within threshold."""
        slices = self._make_slices([
            ("domestic", 60, "US Stocks"),
            ("bond", 40, "Bonds"),
        ])
        # 62/38 split — 2% drift, below 5% threshold
        current = {
            "domestic": Decimal("62000"),
            "bond": Decimal("38000"),
        }
        total = Decimal("100000")

        _, trade_recs, needs_rebalancing, _ = (
            RebalancingService.calculate_drift(slices, current, total, Decimal("5"))
        )

        assert not needs_rebalancing
        assert len(trade_recs) == 0

    def test_missing_asset_class_treated_as_zero(self):
        """Asset class with target but no holdings is underweight."""
        slices = self._make_slices([
            ("domestic", 60, "US Stocks"),
            ("international", 30, "Intl"),
            ("bond", 10, "Bonds"),
        ])
        # No international holdings at all
        current = {
            "domestic": Decimal("80000"),
            "bond": Decimal("20000"),
        }
        total = Decimal("100000")

        drift_items, _, _, _ = (
            RebalancingService.calculate_drift(slices, current, total, Decimal("5"))
        )

        intl = next(d for d in drift_items if d.asset_class == "international")
        assert intl.current_percent == Decimal("0")
        assert intl.current_value == Decimal("0")
        assert intl.status == "underweight"

    def test_zero_portfolio_total(self):
        """Handles empty portfolio gracefully — drift is 0 when portfolio total is 0."""
        slices = self._make_slices([("domestic", 100, "US Stocks")])
        drift_items, trade_recs, needs_rebalancing, max_drift = (
            RebalancingService.calculate_drift(slices, {}, Decimal("0"), Decimal("5"))
        )
        assert len(drift_items) == 1
        assert drift_items[0].current_percent == Decimal("0")
        # target_value is 0 when portfolio is 0, so drift_value is 0
        assert drift_items[0].drift_value == Decimal("0")
        # No meaningful trades on an empty portfolio
        assert len(trade_recs) == 0 or all(r.amount == Decimal("0") for r in trade_recs)

    def test_max_drift_tracks_largest_absolute_drift(self):
        """max_drift returns the largest absolute drift percentage."""
        slices = self._make_slices([
            ("domestic", 50, "US"),
            ("bond", 50, "Bonds"),
        ])
        current = {
            "domestic": Decimal("70000"),
            "bond": Decimal("30000"),
        }
        total = Decimal("100000")

        _, _, _, max_drift = (
            RebalancingService.calculate_drift(slices, current, total, Decimal("5"))
        )

        assert max_drift == Decimal("20.00")


# ── Schema validation ────────────────────────────────────────────────────────


class TestSchemaValidation:
    """Test Pydantic schema validators for target allocations."""

    def test_create_valid_allocation(self):
        """Valid allocation passes validation."""
        alloc = TargetAllocationCreate(
            name="Test",
            allocations=[
                AllocationSlice(asset_class="domestic", target_percent=Decimal("60"), label="US"),
                AllocationSlice(asset_class="bond", target_percent=Decimal("40"), label="Bonds"),
            ],
        )
        assert alloc.name == "Test"
        assert len(alloc.allocations) == 2

    def test_create_rejects_sum_not_100(self):
        """Allocations that don't sum to 100 are rejected."""
        with pytest.raises(ValidationError, match="must sum to 100"):
            TargetAllocationCreate(
                name="Bad",
                allocations=[
                    AllocationSlice(asset_class="domestic", target_percent=Decimal("60"), label="US"),
                    AllocationSlice(asset_class="bond", target_percent=Decimal("30"), label="Bonds"),
                ],
            )

    def test_create_rejects_duplicate_asset_class(self):
        """Duplicate asset_class entries are rejected."""
        with pytest.raises(ValidationError, match="Duplicate asset_class"):
            TargetAllocationCreate(
                name="Duped",
                allocations=[
                    AllocationSlice(asset_class="domestic", target_percent=Decimal("50"), label="US A"),
                    AllocationSlice(asset_class="domestic", target_percent=Decimal("50"), label="US B"),
                ],
            )

    def test_update_rejects_duplicate_asset_class(self):
        """Duplicate asset_class in update payload is rejected."""
        with pytest.raises(ValidationError, match="Duplicate asset_class"):
            TargetAllocationUpdate(
                allocations=[
                    AllocationSlice(asset_class="bond", target_percent=Decimal("50"), label="Bonds A"),
                    AllocationSlice(asset_class="bond", target_percent=Decimal("50"), label="Bonds B"),
                ],
            )

    def test_create_rejects_too_many_allocations(self):
        """More than 20 allocation slices are rejected."""
        slices = [
            AllocationSlice(
                asset_class=f"class_{i}",
                target_percent=Decimal("4") if i < 20 else Decimal("0"),
                label=f"Class {i}",
            )
            for i in range(21)
        ]
        with pytest.raises(ValidationError):
            TargetAllocationCreate(name="TooMany", allocations=slices)

    def test_asset_class_max_length(self):
        """asset_class longer than 50 chars is rejected."""
        with pytest.raises(ValidationError):
            AllocationSlice(
                asset_class="x" * 51,
                target_percent=Decimal("100"),
                label="Test",
            )

    def test_label_max_length(self):
        """label longer than 100 chars is rejected."""
        with pytest.raises(ValidationError):
            AllocationSlice(
                asset_class="domestic",
                target_percent=Decimal("100"),
                label="x" * 101,
            )

    def test_update_allows_partial_without_allocations(self):
        """Update with only drift_threshold is valid (no allocation validation)."""
        update = TargetAllocationUpdate(drift_threshold=Decimal("3.0"))
        assert update.drift_threshold == Decimal("3.0")
        assert update.allocations is None

    def test_presets_have_no_duplicate_asset_classes(self):
        """All preset portfolios have unique asset classes."""
        for key, preset in PRESET_PORTFOLIOS.items():
            classes = [a["asset_class"] for a in preset["allocations"]]
            assert len(classes) == len(set(classes)), (
                f"Preset '{key}' has duplicate asset_class entries"
            )
