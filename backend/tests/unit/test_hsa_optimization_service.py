"""Unit tests for HsaOptimizationService."""
from decimal import Decimal
import pytest
from app.services.hsa_optimization_service import HsaOptimizationService


class TestContributionHeadroom:
    def test_individual_plan_partial_contribution(self):
        result = HsaOptimizationService.calculate_contribution_headroom(
            ytd_contributions=Decimal("2000"),
            is_family_plan=False,
            age=40,
            year=2026,
        )
        assert result["remaining_room"] > 0
        assert result["can_contribute"] is True
        assert result["catch_up_eligible"] is False

    def test_family_plan_higher_limit(self):
        individual = HsaOptimizationService.calculate_contribution_headroom(
            ytd_contributions=Decimal("0"),
            is_family_plan=False,
            age=40,
            year=2026,
        )
        family = HsaOptimizationService.calculate_contribution_headroom(
            ytd_contributions=Decimal("0"),
            is_family_plan=True,
            age=40,
            year=2026,
        )
        assert family["annual_limit"] > individual["annual_limit"]

    def test_catch_up_at_55(self):
        result = HsaOptimizationService.calculate_contribution_headroom(
            ytd_contributions=Decimal("0"),
            is_family_plan=False,
            age=55,
            year=2026,
        )
        assert result["catch_up_eligible"] is True
        assert result["catch_up_amount"] > 0

    def test_medicare_age_cannot_contribute(self):
        result = HsaOptimizationService.calculate_contribution_headroom(
            ytd_contributions=Decimal("0"),
            is_family_plan=False,
            age=65,
            year=2026,
        )
        assert result["can_contribute"] is False

    def test_fully_contributed_no_remaining(self):
        result = HsaOptimizationService.calculate_contribution_headroom(
            ytd_contributions=Decimal("10000"),
            is_family_plan=False,
            age=40,
            year=2026,
        )
        assert result["remaining_room"] == 0.0


class TestInvestStrategy:
    def test_invest_beats_spend_long_term(self):
        result = HsaOptimizationService.project_invest_strategy(
            current_balance=Decimal("5000"),
            annual_contribution=Decimal("4300"),
            annual_medical_expenses=Decimal("2000"),
            years=20,
        )
        assert result["invest_strategy_balance"] > result["spend_strategy_balance"]
        assert result["invest_advantage"] > 0

    def test_short_horizon_still_computes(self):
        result = HsaOptimizationService.project_invest_strategy(
            current_balance=Decimal("0"),
            annual_contribution=Decimal("4300"),
            annual_medical_expenses=Decimal("0"),
            years=1,
        )
        assert result["invest_strategy_balance"] > 0

    def test_lifetime_value_grows(self):
        result = HsaOptimizationService.calculate_lifetime_value(
            current_balance=Decimal("10000"),
            annual_contribution=Decimal("4300"),
            years_until_retirement=25,
        )
        assert result["projected_balance_at_retirement"] > 10000
        assert result["tax_free_for_medical"] is True
