"""Tests for centralized financial constants.

Ensures all constants are properly defined, have correct types, and that
services correctly import from the centralized file.
"""

from decimal import Decimal

import pytest

from app.constants.financial import (
    EDUCATION,
    FIRE,
    HEALTH,
    HEALTHCARE,
    MEDICARE,
    PORTFOLIO,
    RETIREMENT,
    RMD,
    SS,
    TAX,
)

# ── TAX constants ──────────────────────────────────────────────────────────


class TestTaxConstants:
    def test_federal_rate_is_decimal(self):
        assert isinstance(TAX.FEDERAL_MARGINAL_RATE, Decimal)
        assert 0 < TAX.FEDERAL_MARGINAL_RATE < 1

    def test_state_rate_is_decimal(self):
        assert isinstance(TAX.STATE_AVERAGE_RATE, Decimal)
        assert 0 < TAX.STATE_AVERAGE_RATE < 1

    def test_combined_rate_equals_sum(self):
        assert TAX.COMBINED_RATE == TAX.FEDERAL_MARGINAL_RATE + TAX.STATE_AVERAGE_RATE

    def test_ltcg_brackets_single_ordered(self):
        brackets = TAX.LTCG_BRACKETS_SINGLE
        assert len(brackets) == 3
        # Thresholds should be ascending
        for i in range(len(brackets) - 1):
            assert brackets[i][0] < brackets[i + 1][0]
        # First bracket is 0%
        assert brackets[0][1] == 0.00
        # Last bracket is 20%
        assert brackets[-1][1] == 0.20

    def test_ltcg_brackets_married_higher_thresholds(self):
        single = TAX.LTCG_BRACKETS_SINGLE
        married = TAX.LTCG_BRACKETS_MARRIED
        assert married[0][0] > single[0][0]  # Married threshold higher

    def test_nii_surtax_rate(self):
        assert TAX.NII_SURTAX_RATE == 0.038
        assert TAX.NII_THRESHOLD_SINGLE == 200_000
        assert TAX.NII_THRESHOLD_MARRIED == 250_000

    def test_standard_deduction_values(self):
        assert TAX.STANDARD_DEDUCTION_SINGLE > 0
        assert TAX.STANDARD_DEDUCTION_MARRIED > TAX.STANDARD_DEDUCTION_SINGLE
        assert TAX.STANDARD_DEDUCTION_OVER_65_EXTRA_SINGLE > 0

    def test_ss_taxation_thresholds_ordered(self):
        for thresholds in [TAX.SS_TAXATION_THRESHOLDS_SINGLE, TAX.SS_TAXATION_THRESHOLDS_MARRIED]:
            for i in range(len(thresholds) - 1):
                assert thresholds[i][0] < thresholds[i + 1][0]
            # First bracket has 0% taxation
            assert thresholds[0][1] == 0.00
            # Last bracket has 85% maximum
            assert thresholds[-1][1] == 0.85


# ── RETIREMENT limits ──────────────────────────────────────────────────────


class TestRetirementConstants:
    def test_401k_limits(self):
        assert RETIREMENT.LIMIT_401K > 0
        assert RETIREMENT.LIMIT_401K_CATCH_UP > 0
        assert RETIREMENT.LIMIT_401K_TOTAL > RETIREMENT.LIMIT_401K

    def test_ira_limits(self):
        assert RETIREMENT.LIMIT_IRA > 0
        assert RETIREMENT.LIMIT_IRA_CATCH_UP > 0

    def test_hsa_limits(self):
        assert RETIREMENT.LIMIT_HSA_FAMILY > RETIREMENT.LIMIT_HSA_INDIVIDUAL
        assert RETIREMENT.LIMIT_HSA_CATCH_UP > 0

    def test_planning_defaults(self):
        assert RETIREMENT.DEFAULT_RETIREMENT_AGE == 67
        assert RETIREMENT.DEFAULT_LIFE_EXPECTANCY == 95
        assert 0 < RETIREMENT.SPENDING_RATIO_HOUSEHOLD <= 1
        assert 0 < RETIREMENT.SPENDING_RATIO_SINGLE <= 1


# ── SS constants ───────────────────────────────────────────────────────────


class TestSSConstants:
    def test_bend_points(self):
        assert SS.BEND_POINT_1 > 0
        assert SS.BEND_POINT_2 > SS.BEND_POINT_1

    def test_replacement_rates(self):
        assert SS.RATE_1 == 0.90
        assert SS.RATE_2 == 0.32
        assert SS.RATE_3 == 0.15

    def test_fra_table(self):
        assert 1937 in SS.FRA_TABLE
        assert 1959 in SS.FRA_TABLE
        assert SS.FRA_TABLE[1937] == (65, 0)

    def test_taxable_max(self):
        assert SS.TAXABLE_MAX > 100_000


# ── MEDICARE constants ─────────────────────────────────────────────────────


class TestMedicareConstants:
    def test_premiums(self):
        assert MEDICARE.PART_B_MONTHLY > 0
        assert MEDICARE.PART_D_MONTHLY > 0
        assert MEDICARE.MEDIGAP_MONTHLY > 0

    def test_irmaa_brackets(self):
        brackets = MEDICARE.IRMAA_BRACKETS_SINGLE
        assert len(brackets) == 6
        # First bracket: no surcharge
        assert brackets[0][1] == 0.00
        assert brackets[0][2] == 0.00
        # Ascending thresholds
        for i in range(len(brackets) - 1):
            assert brackets[i][0] < brackets[i + 1][0]

    def test_eligibility_age(self):
        assert MEDICARE.ELIGIBILITY_AGE == 65


# ── RMD constants ──────────────────────────────────────────────────────────


class TestRMDConstants:
    def test_trigger_age(self):
        assert RMD.TRIGGER_AGE == 73

    def test_penalty_rates(self):
        assert RMD.PENALTY_RATE == Decimal("0.25")
        assert RMD.PENALTY_RATE_CORRECTED == Decimal("0.10")

    def test_uniform_lifetime_table(self):
        table = RMD.UNIFORM_LIFETIME_TABLE
        assert len(table) == 48  # Ages 73-120
        assert 73 in table
        assert 120 in table
        # Factor decreases with age
        assert table[73] > table[120]


# ── FIRE constants ─────────────────────────────────────────────────────────


class TestFIREConstants:
    def test_withdrawal_rate(self):
        assert FIRE.DEFAULT_WITHDRAWAL_RATE == 0.04
        assert FIRE.FI_MULTIPLIER == 25

    def test_return_assumptions(self):
        assert FIRE.DEFAULT_EXPECTED_RETURN == 0.07
        assert FIRE.DEFAULT_INFLATION == 0.03
        assert FIRE.DEFAULT_REAL_RETURN == pytest.approx(0.04)

    def test_rate_caps(self):
        assert FIRE.MAX_CAPITAL_GAINS_RATE == 0.50
        assert FIRE.MAX_INCOME_TAX_RATE == 0.70


# ── HEALTH constants ───────────────────────────────────────────────────────


class TestHealthConstants:
    def test_grade_cutoffs(self):
        assert HEALTH.GRADE_A > HEALTH.GRADE_B > HEALTH.GRADE_C > HEALTH.GRADE_D

    def test_retirement_benchmarks(self):
        benchmarks = HEALTH.RETIREMENT_BENCHMARKS
        assert len(benchmarks) == 4
        # Ascending by age
        ages = [b[0] for b in benchmarks]
        assert ages == sorted(ages)
        # Ascending multiples
        multiples = [b[1] for b in benchmarks]
        assert multiples == sorted(multiples)


# ── PORTFOLIO constants ────────────────────────────────────────────────────


class TestPortfolioConstants:
    def test_presets_exist(self):
        assert "bogleheads_3fund" in PORTFOLIO.PRESETS
        assert "balanced_60_40" in PORTFOLIO.PRESETS
        assert "all_weather" in PORTFOLIO.PRESETS

    def test_allocations_sum_to_100(self):
        for key, preset in PORTFOLIO.PRESETS.items():
            total = sum(a["target_percent"] for a in preset["allocations"])
            assert total == 100, f"{key} allocations sum to {total}, not 100"


# ── Service re-export compatibility ────────────────────────────────────────


class TestServiceCompatibility:
    """Ensure old imports still work after centralization."""

    def test_healthcare_estimator_uses_constants(self):
        from app.services.retirement.healthcare_cost_estimator import (
            ACA_MONTHLY_SINGLE,
            MEDICARE_PART_B_MONTHLY,
        )

        assert ACA_MONTHLY_SINGLE == HEALTHCARE.ACA_MONTHLY_SINGLE
        assert MEDICARE_PART_B_MONTHLY == MEDICARE.PART_B_MONTHLY

    def test_ss_estimator_uses_constants(self):
        from app.services.retirement.social_security_estimator import (
            BEND_POINT_1,
            RATE_1,
        )

        assert BEND_POINT_1 == SS.BEND_POINT_1
        assert RATE_1 == SS.RATE_1

    def test_tax_loss_harvesting_uses_constants(self):
        from app.services.tax_loss_harvesting_service import (
            FEDERAL_TAX_RATE,
            STATE_TAX_RATE,
        )

        assert FEDERAL_TAX_RATE == TAX.FEDERAL_MARGINAL_RATE
        assert STATE_TAX_RATE == TAX.STATE_AVERAGE_RATE

    def test_rmd_calculator_uses_constants(self):
        from app.utils.rmd_calculator import UNIFORM_LIFETIME_TABLE

        assert UNIFORM_LIFETIME_TABLE == RMD.UNIFORM_LIFETIME_TABLE

    def test_education_service_uses_constants(self):
        from app.services.education_planning_service import EducationPlanningService

        assert EducationPlanningService.COLLEGE_COSTS == EDUCATION.COLLEGE_COSTS
        assert EducationPlanningService.COLLEGE_INFLATION_RATE == EDUCATION.COLLEGE_INFLATION_RATE

    def test_rebalancing_service_uses_constants(self):
        from app.services.rebalancing_service import PRESET_PORTFOLIOS

        assert PRESET_PORTFOLIOS == PORTFOLIO.PRESETS
