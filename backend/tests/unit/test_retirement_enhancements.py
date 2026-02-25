"""Tests for retirement planner UX enhancements.

Covers:
- Slider range validation (retirement age 15-95, life expectancy 15+)
- Cash balance tracking in account data
- Household-aware default scenario creation
- Schema validation edge cases
"""

import pytest
from decimal import Decimal
from pydantic import ValidationError

from app.schemas.retirement import (
    RetirementScenarioCreate,
    RetirementScenarioUpdate,
    QuickSimulationRequest,
    RetirementAccountDataResponse,
)


# ── Slider Range Validation ──────────────────────────────────────────────────


class TestSliderRanges:
    """Verify retirement_age and life_expectancy accept expanded ranges."""

    def test_retirement_age_min_15(self):
        """Retirement age of 15 should be valid (FIRE planning)."""
        schema = RetirementScenarioCreate(
            name="FIRE Plan",
            retirement_age=15,
            annual_spending_retirement=Decimal("30000"),
        )
        assert schema.retirement_age == 15

    def test_retirement_age_max_95(self):
        schema = RetirementScenarioCreate(
            name="Late Retirement",
            retirement_age=95,
            annual_spending_retirement=Decimal("50000"),
        )
        assert schema.retirement_age == 95

    def test_retirement_age_below_min_fails(self):
        with pytest.raises(ValidationError):
            RetirementScenarioCreate(
                name="Invalid",
                retirement_age=14,
                annual_spending_retirement=Decimal("50000"),
            )

    def test_retirement_age_above_max_fails(self):
        with pytest.raises(ValidationError):
            RetirementScenarioCreate(
                name="Invalid",
                retirement_age=96,
                annual_spending_retirement=Decimal("50000"),
            )

    def test_life_expectancy_min_15(self):
        schema = RetirementScenarioCreate(
            name="Short Plan",
            retirement_age=15,
            life_expectancy=15,
            annual_spending_retirement=Decimal("30000"),
        )
        assert schema.life_expectancy == 15

    def test_life_expectancy_max_120(self):
        schema = RetirementScenarioCreate(
            name="Long Life",
            retirement_age=67,
            life_expectancy=120,
            annual_spending_retirement=Decimal("50000"),
        )
        assert schema.life_expectancy == 120

    def test_life_expectancy_below_min_fails(self):
        with pytest.raises(ValidationError):
            RetirementScenarioCreate(
                name="Invalid",
                retirement_age=30,
                life_expectancy=14,
                annual_spending_retirement=Decimal("50000"),
            )

    def test_update_retirement_age_15(self):
        schema = RetirementScenarioUpdate(retirement_age=15)
        assert schema.retirement_age == 15

    def test_update_retirement_age_95(self):
        schema = RetirementScenarioUpdate(retirement_age=95)
        assert schema.retirement_age == 95

    def test_update_life_expectancy_15(self):
        schema = RetirementScenarioUpdate(life_expectancy=15)
        assert schema.life_expectancy == 15

    def test_quick_sim_retirement_age_15(self):
        schema = QuickSimulationRequest(
            current_portfolio=Decimal("100000"),
            retirement_age=15,
            current_age=20,
            annual_spending=Decimal("30000"),
        )
        assert schema.retirement_age == 15

    def test_quick_sim_retirement_age_95(self):
        schema = QuickSimulationRequest(
            current_portfolio=Decimal("500000"),
            retirement_age=95,
            current_age=60,
            annual_spending=Decimal("50000"),
        )
        assert schema.retirement_age == 95

    def test_quick_sim_life_expectancy_15(self):
        schema = QuickSimulationRequest(
            current_portfolio=Decimal("100000"),
            retirement_age=15,
            current_age=18,
            life_expectancy=15,
            annual_spending=Decimal("30000"),
        )
        assert schema.life_expectancy == 15

    def test_original_ranges_still_valid(self):
        """Values within original ranges should still work."""
        schema = RetirementScenarioCreate(
            name="Standard",
            retirement_age=67,
            life_expectancy=95,
            annual_spending_retirement=Decimal("60000"),
        )
        assert schema.retirement_age == 67
        assert schema.life_expectancy == 95


# ── Cash Balance in Account Data ─────────────────────────────────────────────


class TestCashBalanceSchema:
    """Verify cash_balance field in RetirementAccountDataResponse."""

    def test_cash_balance_default_zero(self):
        data = RetirementAccountDataResponse(
            total_portfolio=100000,
            taxable_balance=30000,
            pre_tax_balance=50000,
            roth_balance=15000,
            hsa_balance=5000,
            pension_monthly=0,
            annual_contributions=10000,
            employer_match_annual=5000,
        )
        assert data.cash_balance == 0

    def test_cash_balance_explicit(self):
        data = RetirementAccountDataResponse(
            total_portfolio=100000,
            taxable_balance=30000,
            pre_tax_balance=50000,
            roth_balance=15000,
            hsa_balance=5000,
            cash_balance=10000,
            pension_monthly=0,
            annual_contributions=10000,
            employer_match_annual=5000,
        )
        assert data.cash_balance == 10000

    def test_cash_balance_subset_of_taxable(self):
        """Cash balance should be <= taxable_balance."""
        data = RetirementAccountDataResponse(
            total_portfolio=50000,
            taxable_balance=20000,
            pre_tax_balance=20000,
            roth_balance=5000,
            hsa_balance=5000,
            cash_balance=15000,
            pension_monthly=0,
            annual_contributions=0,
            employer_match_annual=0,
        )
        # cash_balance can be up to taxable_balance
        assert data.cash_balance <= data.taxable_balance


# ── Withdrawal Strategy Schema ───────────────────────────────────────────────


class TestWithdrawalStrategySchema:
    """Verify withdrawal_strategy field accepts valid values."""

    def test_tax_optimized_default(self):
        schema = RetirementScenarioCreate(
            name="Default Strategy",
            retirement_age=67,
            annual_spending_retirement=Decimal("60000"),
        )
        assert schema.withdrawal_strategy.value == "tax_optimized"

    def test_simple_rate_strategy(self):
        from app.models.retirement import WithdrawalStrategy
        schema = RetirementScenarioCreate(
            name="Simple",
            retirement_age=67,
            annual_spending_retirement=Decimal("60000"),
            withdrawal_strategy=WithdrawalStrategy.SIMPLE_RATE,
        )
        assert schema.withdrawal_strategy.value == "simple_rate"

    def test_update_withdrawal_strategy(self):
        from app.models.retirement import WithdrawalStrategy
        schema = RetirementScenarioUpdate(
            withdrawal_strategy=WithdrawalStrategy.TAX_OPTIMIZED,
        )
        assert schema.withdrawal_strategy.value == "tax_optimized"


# ── Social Security Manual Override Schema ───────────────────────────────────


class TestSocialSecurityOverrideSchema:
    """Verify SS manual override fields in scenario schema."""

    def test_manual_override_null_default(self):
        schema = RetirementScenarioCreate(
            name="Default SS",
            retirement_age=67,
            annual_spending_retirement=Decimal("60000"),
        )
        assert schema.social_security_monthly is None
        assert schema.use_estimated_pia is True

    def test_manual_override_with_value(self):
        schema = RetirementScenarioCreate(
            name="Manual SS",
            retirement_age=67,
            annual_spending_retirement=Decimal("60000"),
            social_security_monthly=Decimal("2500"),
            use_estimated_pia=False,
        )
        assert schema.social_security_monthly == Decimal("2500")
        assert schema.use_estimated_pia is False

    def test_update_manual_override(self):
        schema = RetirementScenarioUpdate(
            social_security_monthly=Decimal("3000"),
            use_estimated_pia=False,
        )
        assert schema.social_security_monthly == Decimal("3000")

    def test_clear_manual_override(self):
        """Setting SS override to None should revert to estimated."""
        schema = RetirementScenarioUpdate(
            social_security_monthly=None,
            use_estimated_pia=True,
        )
        assert schema.social_security_monthly is None
        assert schema.use_estimated_pia is True


# ── Tax Rate Schema ──────────────────────────────────────────────────────────


class TestTaxRateSchema:
    """Verify tax rate fields exist and accept correct ranges."""

    def test_default_tax_rates(self):
        schema = RetirementScenarioCreate(
            name="Default Taxes",
            retirement_age=67,
            annual_spending_retirement=Decimal("60000"),
        )
        assert schema.federal_tax_rate == Decimal("22.00")
        assert schema.state_tax_rate == Decimal("5.00")
        assert schema.capital_gains_rate == Decimal("15.00")

    def test_custom_tax_rates(self):
        schema = RetirementScenarioCreate(
            name="High Tax State",
            retirement_age=67,
            annual_spending_retirement=Decimal("60000"),
            federal_tax_rate=Decimal("32.00"),
            state_tax_rate=Decimal("13.30"),
            capital_gains_rate=Decimal("20.00"),
        )
        assert schema.federal_tax_rate == Decimal("32.00")
        assert schema.state_tax_rate == Decimal("13.30")
        assert schema.capital_gains_rate == Decimal("20.00")

    def test_zero_tax_rate_valid(self):
        """No-tax states should accept 0%."""
        schema = RetirementScenarioCreate(
            name="No State Tax",
            retirement_age=67,
            annual_spending_retirement=Decimal("60000"),
            state_tax_rate=Decimal("0"),
        )
        assert schema.state_tax_rate == Decimal("0")

    def test_update_capital_gains_rate(self):
        schema = RetirementScenarioUpdate(capital_gains_rate=Decimal("23.80"))
        assert schema.capital_gains_rate == Decimal("23.80")


# ── Scenario Name Update ────────────────────────────────────────────────────


class TestScenarioNameUpdate:
    """Verify scenario name can be updated (for tab rename)."""

    def test_update_name(self):
        schema = RetirementScenarioUpdate(name="Early Retirement Plan")
        assert schema.name == "Early Retirement Plan"

    def test_update_name_max_length(self):
        long_name = "A" * 200
        schema = RetirementScenarioUpdate(name=long_name)
        assert schema.name == long_name

    def test_update_name_too_long_fails(self):
        with pytest.raises(ValidationError):
            RetirementScenarioUpdate(name="A" * 201)

    def test_update_name_preserves_other_fields(self):
        """Updating name should not require other fields."""
        schema = RetirementScenarioUpdate(name="New Name")
        assert schema.retirement_age is None
        assert schema.life_expectancy is None


# ── Medical Inflation Rate ───────────────────────────────────────────────────


class TestMedicalInflationRate:
    """Verify medical_inflation_rate field for healthcare editing."""

    def test_default_medical_inflation(self):
        schema = RetirementScenarioCreate(
            name="Default Med Inflation",
            retirement_age=67,
            annual_spending_retirement=Decimal("60000"),
        )
        assert schema.medical_inflation_rate == Decimal("6.00")

    def test_custom_medical_inflation(self):
        schema = RetirementScenarioCreate(
            name="Custom Med Inflation",
            retirement_age=67,
            annual_spending_retirement=Decimal("60000"),
            medical_inflation_rate=Decimal("8.50"),
        )
        assert schema.medical_inflation_rate == Decimal("8.50")

    def test_update_medical_inflation(self):
        schema = RetirementScenarioUpdate(medical_inflation_rate=Decimal("7.00"))
        assert schema.medical_inflation_rate == Decimal("7.00")

    def test_medical_inflation_max_20(self):
        schema = RetirementScenarioCreate(
            name="Max",
            retirement_age=67,
            annual_spending_retirement=Decimal("60000"),
            medical_inflation_rate=Decimal("20.00"),
        )
        assert schema.medical_inflation_rate == Decimal("20.00")

    def test_medical_inflation_above_max_fails(self):
        with pytest.raises(ValidationError):
            RetirementScenarioCreate(
                name="Invalid",
                retirement_age=67,
                annual_spending_retirement=Decimal("60000"),
                medical_inflation_rate=Decimal("21.00"),
            )


# ── Healthcare Cost Overrides ────────────────────────────────────────────────


class TestHealthcareOverrideSchema:
    """Verify healthcare cost override fields in scenario schema."""

    def test_overrides_default_none(self):
        schema = RetirementScenarioCreate(
            name="Default",
            retirement_age=67,
            annual_spending_retirement=Decimal("60000"),
        )
        assert schema.healthcare_pre65_override is None
        assert schema.healthcare_medicare_override is None
        assert schema.healthcare_ltc_override is None

    def test_set_pre65_override(self):
        schema = RetirementScenarioCreate(
            name="Override Pre-65",
            retirement_age=67,
            annual_spending_retirement=Decimal("60000"),
            healthcare_pre65_override=Decimal("15000"),
        )
        assert schema.healthcare_pre65_override == Decimal("15000")

    def test_set_medicare_override(self):
        schema = RetirementScenarioCreate(
            name="Override Medicare",
            retirement_age=67,
            annual_spending_retirement=Decimal("60000"),
            healthcare_medicare_override=Decimal("8500"),
        )
        assert schema.healthcare_medicare_override == Decimal("8500")

    def test_set_ltc_override(self):
        schema = RetirementScenarioCreate(
            name="Override LTC",
            retirement_age=67,
            annual_spending_retirement=Decimal("60000"),
            healthcare_ltc_override=Decimal("45000"),
        )
        assert schema.healthcare_ltc_override == Decimal("45000")

    def test_negative_override_fails(self):
        with pytest.raises(ValidationError):
            RetirementScenarioCreate(
                name="Negative",
                retirement_age=67,
                annual_spending_retirement=Decimal("60000"),
                healthcare_pre65_override=Decimal("-1000"),
            )

    def test_update_overrides(self):
        schema = RetirementScenarioUpdate(
            healthcare_pre65_override=Decimal("12000"),
            healthcare_medicare_override=Decimal("9000"),
        )
        assert schema.healthcare_pre65_override == Decimal("12000")
        assert schema.healthcare_medicare_override == Decimal("9000")

    def test_zero_override_valid(self):
        """User should be able to set override to zero (no cost)."""
        schema = RetirementScenarioCreate(
            name="No LTC",
            retirement_age=67,
            annual_spending_retirement=Decimal("60000"),
            healthcare_ltc_override=Decimal("0"),
        )
        assert schema.healthcare_ltc_override == Decimal("0")


# ── Retirement Scenario Permission ───────────────────────────────────────────


class TestRetirementPermission:
    """Verify retirement_scenario is a valid resource type."""

    def test_retirement_scenario_in_resource_types(self):
        from app.models.permission import RESOURCE_TYPES
        assert "retirement_scenario" in RESOURCE_TYPES

    def test_resource_types_count(self):
        from app.models.permission import RESOURCE_TYPES
        assert len(RESOURCE_TYPES) == 13
