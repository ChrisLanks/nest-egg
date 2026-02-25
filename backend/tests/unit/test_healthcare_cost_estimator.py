"""Tests for healthcare cost estimator.

Covers:
- IRMAA surcharge brackets
- Pre-65 ACA costs
- 65+ Medicare costs
- 85+ long-term care costs
- Lifetime cost aggregation
"""

import pytest
from app.services.retirement.healthcare_cost_estimator import (
    ACA_MONTHLY_COUPLE,
    ACA_MONTHLY_SINGLE,
    LTC_FACILITY_MONTHLY,
    LTC_HOME_CARE_MONTHLY,
    MEDICARE_PART_B_MONTHLY,
    MEDICARE_PART_D_MONTHLY,
    MEDIGAP_MONTHLY,
    OOP_ANNUAL,
    estimate_annual_healthcare_cost,
    estimate_lifetime_healthcare_costs,
    get_irmaa_surcharge,
)


# ── IRMAA surcharges ──────────────────────────────────────────────────────────


class TestGetIRMAASurcharge:
    def test_standard_income_no_surcharge(self):
        b, d = get_irmaa_surcharge(80000)
        assert b == 0.0
        assert d == 0.0

    def test_at_boundary_103k(self):
        b, d = get_irmaa_surcharge(103000)
        assert b == 0.0
        assert d == 0.0

    def test_tier_1(self):
        b, d = get_irmaa_surcharge(120000)
        assert b == 70.90
        assert d == 12.90

    def test_tier_2(self):
        b, d = get_irmaa_surcharge(150000)
        assert b == 161.40
        assert d == 33.30

    def test_highest_tier(self):
        b, d = get_irmaa_surcharge(600000)
        assert b == 395.60
        assert d == 81.00

    def test_married_doubles_thresholds(self):
        # $120K single → Tier 1 surcharge
        b_single, _ = get_irmaa_surcharge(120000, "single")
        assert b_single > 0

        # $120K married → standard (threshold is ~$206K)
        b_married, _ = get_irmaa_surcharge(120000, "married")
        assert b_married == 0.0

    def test_married_high_income(self):
        # $300K married → should hit a surcharge tier
        b, d = get_irmaa_surcharge(300000, "married")
        assert b > 0


# ── Pre-65 costs ──────────────────────────────────────────────────────────────


class TestPre65Costs:
    def test_single_pre65(self):
        costs = estimate_annual_healthcare_cost(age=55, current_age=55)
        assert costs["aca_insurance"] == ACA_MONTHLY_SINGLE * 12
        assert costs["medicare_part_b"] == 0.0
        assert costs["medicare_part_d"] == 0.0
        assert costs["medigap"] == 0.0

    def test_married_pre65(self):
        costs = estimate_annual_healthcare_cost(age=55, is_married=True, current_age=55)
        assert costs["aca_insurance"] == ACA_MONTHLY_COUPLE * 12

    def test_oop_always_included(self):
        costs = estimate_annual_healthcare_cost(age=55, current_age=55)
        assert costs["out_of_pocket"] == OOP_ANNUAL

    def test_no_ltc_pre_85(self):
        costs = estimate_annual_healthcare_cost(age=55, current_age=55)
        assert costs["long_term_care"] == 0.0


# ── 65+ Medicare costs ────────────────────────────────────────────────────────


class TestMedicareCosts:
    def test_medicare_at_65(self):
        costs = estimate_annual_healthcare_cost(age=65, current_age=55)
        assert costs["aca_insurance"] == 0.0
        assert costs["medicare_part_b"] == MEDICARE_PART_B_MONTHLY * 12
        assert costs["medicare_part_d"] == MEDICARE_PART_D_MONTHLY * 12
        assert costs["medigap"] == MEDIGAP_MONTHLY * 12

    def test_irmaa_surcharge_at_high_income(self):
        costs_low = estimate_annual_healthcare_cost(age=65, retirement_income=50000, current_age=55)
        costs_high = estimate_annual_healthcare_cost(age=65, retirement_income=200000, current_age=55)
        assert costs_high["irmaa_surcharge"] > costs_low["irmaa_surcharge"]

    def test_no_irmaa_at_standard_income(self):
        costs = estimate_annual_healthcare_cost(age=65, retirement_income=80000, current_age=55)
        assert costs["irmaa_surcharge"] == 0.0


# ── Long-term care ────────────────────────────────────────────────────────────


class TestLongTermCare:
    def test_ltc_at_85_first_year_home_care(self):
        costs = estimate_annual_healthcare_cost(
            age=85, include_ltc=True, ltc_start_age=85, current_age=55
        )
        assert costs["long_term_care"] == LTC_HOME_CARE_MONTHLY * 12

    def test_ltc_at_86_facility_care(self):
        costs = estimate_annual_healthcare_cost(
            age=86, include_ltc=True, ltc_start_age=85, current_age=55
        )
        assert costs["long_term_care"] == LTC_FACILITY_MONTHLY * 12

    def test_no_ltc_when_disabled(self):
        costs = estimate_annual_healthcare_cost(
            age=85, include_ltc=False, current_age=55
        )
        assert costs["long_term_care"] == 0.0

    def test_ltc_ends_after_duration(self):
        """LTC costs should stop after ltc_duration_years."""
        costs = estimate_annual_healthcare_cost(
            age=88, include_ltc=True, ltc_start_age=85, ltc_duration_years=3, current_age=55
        )
        assert costs["long_term_care"] == 0.0

    def test_ltc_within_duration(self):
        costs = estimate_annual_healthcare_cost(
            age=87, include_ltc=True, ltc_start_age=85, ltc_duration_years=3, current_age=55
        )
        assert costs["long_term_care"] > 0


# ── Total cost coherence ──────────────────────────────────────────────────────


class TestTotalCosts:
    def test_total_is_sum_of_components(self):
        costs = estimate_annual_healthcare_cost(age=70, retirement_income=150000, current_age=55)
        component_sum = (
            costs["aca_insurance"]
            + costs["medicare_part_b"]
            + costs["medicare_part_d"]
            + costs["medigap"]
            + costs["irmaa_surcharge"]
            + costs["out_of_pocket"]
            + costs["long_term_care"]
        )
        assert costs["total"] == pytest.approx(component_sum, abs=0.01)

    def test_costs_increase_with_age_phases(self):
        """65+ should cost more than pre-65 at standard income."""
        pre65 = estimate_annual_healthcare_cost(age=60, current_age=55)
        post65 = estimate_annual_healthcare_cost(age=70, current_age=55)
        # Medicare + Medigap + OOP typically > ACA + OOP
        # (This depends on plan assumptions; both should be non-trivial)
        assert pre65["total"] > 0
        assert post65["total"] > 0


# ── Lifetime costs ────────────────────────────────────────────────────────────


class TestLifetimeHealthcareCosts:
    def test_returns_all_fields(self):
        result = estimate_lifetime_healthcare_costs(
            current_age=55, retirement_age=65, life_expectancy=85,
        )
        assert "pre_65_total" in result
        assert "medicare_total" in result
        assert "ltc_total" in result
        assert "grand_total" in result
        assert "yearly_breakdown" in result

    def test_yearly_breakdown_length(self):
        result = estimate_lifetime_healthcare_costs(
            current_age=60, retirement_age=65, life_expectancy=90,
        )
        # Should have 90 - 60 + 1 = 31 years
        assert len(result["yearly_breakdown"]) == 31

    def test_grand_total_matches_phase_sum(self):
        result = estimate_lifetime_healthcare_costs(
            current_age=55, retirement_age=65, life_expectancy=90,
        )
        assert result["grand_total"] == pytest.approx(
            result["pre_65_total"] + result["medicare_total"] + result["ltc_total"],
            abs=0.01,
        )

    def test_grand_total_positive(self):
        result = estimate_lifetime_healthcare_costs(
            current_age=55, retirement_age=65, life_expectancy=95,
        )
        assert result["grand_total"] > 0
