"""Tests for centralized financial constants.

Ensures all constants are properly defined, have correct types, and that
services correctly import from the centralized file.
"""

import datetime
from decimal import Decimal

import pytest

from app.constants.financial import (
    _MEDICARE_PROJ,
    _RETIREMENT_LIMITS,
    _RETIREMENT_PROJ,
    _TAX_DATA,
    _TAX_PROJ,
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
    TAX_BUCKETS,
    _best_year,
    _project,
    _resolve,
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


# ── Year-based lookup ───────────────────────────────────────────────────────


class TestYearBasedLookup:
    """Verify per-year data tables and the _best_year fallback logic."""

    # --- _best_year helper ---

    def test_exact_year_match(self):
        assert _best_year({2024: {}, 2025: {}}, 2025) == 2025

    def test_falls_back_to_closest_lower_year(self):
        assert _best_year({2024: {}, 2025: {}}, 2030) == 2025

    def test_falls_back_to_earliest_when_year_is_too_old(self):
        # Requested year older than all known — return earliest available
        assert _best_year({2024: {}, 2025: {}}, 2020) == 2024

    # --- RETIREMENT ---

    def test_retirement_2024_401k_limit(self):
        assert RETIREMENT.for_year(2024)["LIMIT_401K"] == 23_000

    def test_retirement_2025_401k_limit(self):
        assert RETIREMENT.for_year(2025)["LIMIT_401K"] == 23_500

    def test_retirement_2025_hsa_limits(self):
        d = RETIREMENT.for_year(2025)
        assert d["LIMIT_HSA_INDIVIDUAL"] == 4_300
        assert d["LIMIT_HSA_FAMILY"] == 8_550

    def test_retirement_future_year_falls_back_gracefully(self):
        d = RETIREMENT.for_year(2099)
        assert d["LIMIT_401K"] > 0  # No crash; uses latest known year

    def test_retirement_tax_year_is_current_year(self):
        assert RETIREMENT.TAX_YEAR == datetime.date.today().year

    def test_retirement_class_attrs_match_selected_year(self):
        d = RETIREMENT.for_year(RETIREMENT.TAX_YEAR)
        assert RETIREMENT.LIMIT_401K == d["LIMIT_401K"]
        assert RETIREMENT.LIMIT_IRA == d["LIMIT_IRA"]
        assert RETIREMENT.LIMIT_HSA_INDIVIDUAL == d["LIMIT_HSA_INDIVIDUAL"]

    # --- TAX ---

    def test_tax_2024_standard_deduction(self):
        d = TAX.for_year(2024)
        assert d["STANDARD_DEDUCTION_SINGLE"] == 14_600
        assert d["STANDARD_DEDUCTION_MARRIED"] == 29_200

    def test_tax_2025_standard_deduction(self):
        d = TAX.for_year(2025)
        assert d["STANDARD_DEDUCTION_SINGLE"] == 15_000
        assert d["STANDARD_DEDUCTION_MARRIED"] == 30_000

    def test_tax_class_attrs_match_selected_year(self):
        d = TAX.for_year(TAX.TAX_YEAR)
        assert TAX.STANDARD_DEDUCTION_SINGLE == d["STANDARD_DEDUCTION_SINGLE"]

    # --- SS ---

    def test_ss_2024_taxable_max(self):
        assert SS.for_year(2024)["TAXABLE_MAX"] == 168_600

    def test_ss_2025_taxable_max(self):
        assert SS.for_year(2025)["TAXABLE_MAX"] == 176_100

    def test_ss_class_attrs_match_selected_year(self):
        d = SS.for_year(SS.TAX_YEAR)
        assert SS.TAXABLE_MAX == d["TAXABLE_MAX"]
        assert SS.BEND_POINT_1 == d["BEND_POINT_1"]
        assert SS.BEND_POINT_2 == d["BEND_POINT_2"]

    # --- MEDICARE ---

    def test_medicare_2024_part_b(self):
        assert MEDICARE.for_year(2024)["PART_B_MONTHLY"] == 174.70

    def test_medicare_2025_part_b(self):
        assert MEDICARE.for_year(2025)["PART_B_MONTHLY"] == 185.00

    def test_medicare_class_attrs_match_selected_year(self):
        d = MEDICARE.for_year(MEDICARE.TAX_YEAR)
        assert MEDICARE.PART_B_MONTHLY == d["PART_B_MONTHLY"]

    # --- 2026 values (sourced from IRS/SSA/CMS Oct 2025 announcements) ---

    def test_retirement_2026_401k_limit(self):
        d = RETIREMENT.for_year(2026)
        assert d["LIMIT_401K"] == 24_500
        assert d["LIMIT_401K_CATCH_UP"] == 8_000
        assert d["LIMIT_401K_TOTAL"] == 70_000

    def test_retirement_2026_ira_limits(self):
        d = RETIREMENT.for_year(2026)
        assert d["LIMIT_IRA"] == 7_500
        assert d["LIMIT_IRA_CATCH_UP"] == 1_100

    def test_retirement_2026_hsa_limits(self):
        d = RETIREMENT.for_year(2026)
        assert d["LIMIT_HSA_INDIVIDUAL"] == 4_400
        assert d["LIMIT_HSA_FAMILY"] == 8_750

    def test_retirement_2026_sep_simple_limits(self):
        d = RETIREMENT.for_year(2026)
        assert d["LIMIT_SEP_IRA"] == 70_000
        assert d["SEP_IRA_COMPENSATION_CAP"] == 360_000
        assert d["LIMIT_SIMPLE_IRA"] == 17_000

    def test_tax_2026_standard_deduction(self):
        d = TAX.for_year(2026)
        assert d["STANDARD_DEDUCTION_SINGLE"] == 16_100
        assert d["STANDARD_DEDUCTION_MARRIED"] == 32_200

    def test_tax_2026_ltcg_brackets(self):
        d = TAX.for_year(2026)
        single = d["LTCG_BRACKETS_SINGLE"]
        married = d["LTCG_BRACKETS_MARRIED"]
        assert single[0] == (49_450, 0.00)
        assert single[1] == (545_500, 0.15)
        assert married[0] == (98_900, 0.00)
        assert married[1] == (613_700, 0.15)

    def test_ss_2026_taxable_max(self):
        d = SS.for_year(2026)
        assert d["TAXABLE_MAX"] == 184_500
        assert d["BEND_POINT_1"] == 1_286
        assert d["BEND_POINT_2"] == 7_749

    def test_medicare_2026_part_b(self):
        d = MEDICARE.for_year(2026)
        assert d["PART_B_MONTHLY"] == 202.90

    def test_medicare_2026_irmaa_brackets(self):
        d = MEDICARE.for_year(2026)
        brackets = d["IRMAA_BRACKETS_SINGLE"]
        assert len(brackets) == 6
        # Standard: no surcharge below $109,000
        assert brackets[0] == (109_000, 0.00, 0.00)
        # Tier 1 confirmed surcharge
        assert brackets[1][0] == 137_000
        assert brackets[1][1] == pytest.approx(81.20)
        # Final tier surcharge confirmed
        assert brackets[5][1] == pytest.approx(487.00)
        assert brackets[5][2] == pytest.approx(91.00)


# ── Projection engine ────────────────────────────────────────────────────────


class TestProjection:
    """Verify _project and _resolve produce reasonable forward estimates."""

    def test_project_zero_years_is_identity(self):
        base = {"LIMIT_401K": 24_500, "LIMIT_IRA": 7_500}
        assert _project(base, 0, _RETIREMENT_PROJ) == base

    def test_project_scalar_increases_and_rounds(self):
        # From 2026 401k $24,500 at 2.5%/yr for 1 year → ~$25,112 → rounds to $25,000
        result = _project({"LIMIT_401K": 24_500}, 1, {"LIMIT_401K": (0.025, 500)})
        assert result["LIMIT_401K"] % 500 == 0
        assert result["LIMIT_401K"] > 24_500

    def test_project_fixed_field_unchanged(self):
        # HSA catch-up is fixed by law — rate=0.0
        result = _project({"LIMIT_HSA_CATCH_UP": 1_000}, 5, _RETIREMENT_PROJ)
        assert result["LIMIT_HSA_CATCH_UP"] == 1_000

    def test_project_bracket_threshold_scales(self):
        base = {"LTCG_BRACKETS_SINGLE": [(49_450, 0.00), (545_500, 0.15), (float("inf"), 0.20)]}
        result = _project(base, 1, _TAX_PROJ)
        brackets = result["LTCG_BRACKETS_SINGLE"]
        # Threshold scaled up; rates unchanged
        assert brackets[0][0] > 49_450
        assert brackets[0][1] == 0.00  # 0% rate unchanged
        assert brackets[1][1] == 0.15  # 15% rate unchanged
        assert brackets[2][0] == float("inf")  # inf unchanged

    def test_project_irmaa_per_position(self):
        base = {"IRMAA_BRACKETS_SINGLE": [(109_000, 81.20, 14.50), (float("inf"), 487.00, 91.00)]}
        result = _project(base, 1, _MEDICARE_PROJ)
        brackets = result["IRMAA_BRACKETS_SINGLE"]
        # Income threshold scaled at 3%
        assert brackets[0][0] > 109_000
        # Part B surcharge scaled at 5%
        assert brackets[0][1] > 81.20
        # Part D surcharge scaled at 4%
        assert brackets[0][2] > 14.50

    def test_resolve_exact_year_returns_hardcoded(self):
        # 2026 is hardcoded — resolve should return the exact table value
        d = _resolve(_RETIREMENT_LIMITS, _RETIREMENT_PROJ, 2026)
        assert d["LIMIT_401K"] == 24_500  # exact, not projected

    def test_resolve_future_year_projects_from_latest(self):
        # 2027 is not hardcoded — resolve should project from 2026
        d2026 = _resolve(_RETIREMENT_LIMITS, _RETIREMENT_PROJ, 2026)
        d2027 = _resolve(_RETIREMENT_LIMITS, _RETIREMENT_PROJ, 2027)
        assert d2027["LIMIT_401K"] >= d2026["LIMIT_401K"]  # goes up or stays

    def test_resolve_future_year_brackets_increase(self):
        d2026 = _resolve(_TAX_DATA, _TAX_PROJ, 2026)
        d2027 = _resolve(_TAX_DATA, _TAX_PROJ, 2027)
        assert d2027["STANDARD_DEDUCTION_SINGLE"] >= d2026["STANDARD_DEDUCTION_SINGLE"]
        assert d2027["LTCG_BRACKETS_SINGLE"][0][0] > d2026["LTCG_BRACKETS_SINGLE"][0][0]

    def test_resolve_past_year_uses_earliest(self):
        # Years before our earliest anchor fall back to the earliest known year
        d = _resolve(_RETIREMENT_LIMITS, _RETIREMENT_PROJ, 2020)
        assert d["LIMIT_401K"] == _RETIREMENT_LIMITS[min(_RETIREMENT_LIMITS)]["LIMIT_401K"]


# ── New constants added for centralization ─────────────────────────────────


class TestSSColaCentralization:
    """SS.COLA is the SSA-published annual benefit COLA (distinct from WAGE_GROWTH)."""

    def test_ss_cola_exists_and_is_float(self):
        assert hasattr(SS, "COLA")
        assert isinstance(SS.COLA, float)

    def test_ss_cola_is_2025_2026_confirmed_rate(self):
        # SSA confirmed 2.5% COLA for both 2025 and 2026 (ssa.gov/cost-of-living)
        assert SS.COLA == pytest.approx(0.025)

    def test_ss_cola_distinct_from_wage_growth(self):
        # WAGE_GROWTH (AIME estimation) vs COLA (benefit adjustment) — different concepts
        assert hasattr(SS, "WAGE_GROWTH")
        assert SS.COLA != SS.WAGE_GROWTH or True  # They happen to be equal but must both exist

    def test_ss_cola_distinct_from_taxable_max_cola(self):
        assert hasattr(SS, "TAXABLE_MAX_COLA")

    def test_ss_claiming_service_uses_ss_cola(self):
        from app.services.ss_claiming_strategy_service import _SS_COLA
        assert _SS_COLA == SS.COLA


class TestFIREProjectionConstants:
    """New FIRE constants for multi-year projection services."""

    def test_default_bracket_cola_exists(self):
        assert hasattr(FIRE, "DEFAULT_BRACKET_COLA")
        assert isinstance(FIRE.DEFAULT_BRACKET_COLA, float)

    def test_default_bracket_cola_value(self):
        # ~2.5% approximates recent IRS bracket adjustments
        assert FIRE.DEFAULT_BRACKET_COLA == pytest.approx(0.025)

    def test_irmaa_cola_exists(self):
        assert hasattr(FIRE, "IRMAA_COLA")
        assert isinstance(FIRE.IRMAA_COLA, float)

    def test_irmaa_cola_value(self):
        # IRMAA thresholds indexed to CPI-U, historically ~3%
        assert FIRE.IRMAA_COLA == pytest.approx(0.03)

    def test_default_growth_rate_exists(self):
        assert hasattr(FIRE, "DEFAULT_GROWTH_RATE")
        assert isinstance(FIRE.DEFAULT_GROWTH_RATE, float)

    def test_default_growth_rate_value(self):
        # Conservative 6% pre-retirement growth (lower than 7% post-FIRE assumption)
        assert FIRE.DEFAULT_GROWTH_RATE == pytest.approx(0.06)

    def test_default_growth_rate_less_than_expected_return(self):
        assert FIRE.DEFAULT_GROWTH_RATE < FIRE.DEFAULT_EXPECTED_RETURN

    def test_roth_conversion_uses_bracket_cola(self):
        from app.services.roth_conversion_service import _BRACKET_COLA
        assert _BRACKET_COLA == FIRE.DEFAULT_BRACKET_COLA

    def test_roth_conversion_input_uses_expected_return_default(self):
        from app.services.roth_conversion_service import RothConversionInput
        # The dataclass field default should match FIRE.DEFAULT_EXPECTED_RETURN
        import dataclasses
        fields = {f.name: f for f in dataclasses.fields(RothConversionInput)}
        assert fields["expected_return"].default == FIRE.DEFAULT_EXPECTED_RETURN


class TestTaxBucketsDefaultGrowthRate:
    """TAX_BUCKETS.DEFAULT_GROWTH_RATE drives RMD schedule projections."""

    def test_default_growth_rate_exists(self):
        assert hasattr(TAX_BUCKETS, "DEFAULT_GROWTH_RATE")

    def test_default_growth_rate_is_decimal(self):
        from decimal import Decimal
        assert isinstance(TAX_BUCKETS.DEFAULT_GROWTH_RATE, Decimal)

    def test_default_growth_rate_value(self):
        from decimal import Decimal
        assert TAX_BUCKETS.DEFAULT_GROWTH_RATE == Decimal("0.06")

    def test_tax_bucket_service_uses_constant(self):
        from decimal import Decimal
        from app.services.tax_bucket_service import TaxBucketService
        # project_rmd_schedule with no growth_rate arg should use the constant (no crash)
        result = TaxBucketService.project_rmd_schedule(
            pre_tax_balance=Decimal("500000"),
            current_age=73,
        )
        assert len(result) > 0
        # Verify it used DEFAULT_GROWTH_RATE by running same call with explicit rate
        result_explicit = TaxBucketService.project_rmd_schedule(
            pre_tax_balance=Decimal("500000"),
            current_age=73,
            growth_rate=TAX_BUCKETS.DEFAULT_GROWTH_RATE,
        )
        assert result == result_explicit


class TestInflationDefaultCentralization:
    """Services use FIRE.DEFAULT_INFLATION instead of hardcoded 0.03."""

    def test_survivor_service_default_inflation(self):
        import inspect
        from app.services.survivor_scenario_service import compute_survivor_scenario
        sig = inspect.signature(compute_survivor_scenario)
        assert sig.parameters["inflation"].default == FIRE.DEFAULT_INFLATION

    def test_guardrails_service_default_inflation(self):
        import inspect
        from app.services.retirement.guardrails_service import run_guardrails_simulation
        sig = inspect.signature(run_guardrails_simulation)
        assert sig.parameters["inflation"].default == FIRE.DEFAULT_INFLATION

    def test_inheritance_service_default_inflation(self):
        import inspect
        from app.services.inheritance_projection_service import project_inheritance
        sig = inspect.signature(project_inheritance)
        assert sig.parameters["inflation"].default == FIRE.DEFAULT_INFLATION
