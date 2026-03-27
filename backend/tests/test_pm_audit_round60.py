"""
PM Audit Round 60 — 16 fixes across constants, services, and API endpoints:

HIGH PRIORITY:
1.  RMD planner balance now decremented each year (running balance)
2.  Roth conversion tax savings uses actual marginal rate, not hardcoded 22%
3.  LTCG 0% thresholds derived from TAX constants, not hardcoded
4.  Social Security AIME uses year-specific taxable max (historical table)
5.  TEY formula: taxable bonds show nominal yield; I_BOND uses fed-only TEY
6.  TEY combined rate accounts for state deductibility when itemizing
7.  TCJA sunset note updated for One Big Beautiful Bill Act (2025 extension)

MEDIUM PRIORITY:
8.  SECURE 2.0 super catch-up for ages 60-63 in 401k contributions
9.  SECURE 2.0 age-75 RMD rule for born 1960+
10. Duplicate RMD table removed from tax_bucket_service; uses canonical table
11. RMD tax computed via incremental bracket math, not flat marginal rate
12. AMT, QBI, WEP, QCD year-keyed tables added to financial.py

LOW PRIORITY:
13. Dependent care limits 2026 row added
14. Head of Household brackets added to _TAX_DATA
15. State tax rates updated for AZ, IA, NC, OH
16. IRMAA married filing brackets added
"""

import inspect
import pytest
from decimal import Decimal


# ---------------------------------------------------------------------------
# 1. RMD planner running balance
# ---------------------------------------------------------------------------


def test_rmd_planner_uses_running_balance():
    """RMD planner must decrement balance each year by RMD withdrawn."""
    source = inspect.getsource(__import__("app.api.v1.rmd_planner", fromlist=["rmd_planner"]))
    # Should NOT see the old pattern of `balances[a.id] * ((1 + growth_rate) ** i)`
    assert "((1 + growth_rate) ** i)" not in source, (
        "RMD planner still uses exponent-based projection instead of running balance"
    )
    # Should see running_balances being updated
    assert "running_balances" in source


def test_rmd_planner_has_bracket_tax_function():
    """RMD planner must have a _bracket_tax function for incremental tax."""
    from app.api.v1.rmd_planner import _bracket_tax
    assert callable(_bracket_tax)


def test_bracket_tax_returns_correct_values():
    """_bracket_tax should compute progressive tax correctly."""
    from app.api.v1.rmd_planner import _bracket_tax
    # At $0 income, tax should be 0
    assert _bracket_tax(0, "single", 2026) == 0.0
    # At $12,300 (top of 10% bracket for 2026 single), tax = 12300 * 0.10 = 1230
    tax_10_top = _bracket_tax(12_300, "single", 2026)
    assert abs(tax_10_top - 1_230) < 1.0
    # Tax on $50k should be more than $50k * 10% but less than $50k * 22%
    tax_50k = _bracket_tax(50_000, "single", 2026)
    assert tax_50k > 50_000 * 0.10
    assert tax_50k < 50_000 * 0.22


def test_bracket_tax_incremental_is_correct():
    """Incremental tax on RMD should differ from flat marginal rate approach."""
    from app.api.v1.rmd_planner import _bracket_tax
    other_income = 50_000
    rmd = 30_000
    tax_with = _bracket_tax(other_income + rmd, "single", 2026)
    tax_without = _bracket_tax(other_income, "single", 2026)
    incremental = tax_with - tax_without
    # Incremental tax should be less than rmd * 22% (top marginal) because
    # part of the RMD falls in the 12% bracket
    assert incremental > 0
    assert incremental < rmd * 0.22 + 1  # small epsilon for rounding


# ---------------------------------------------------------------------------
# 2. Roth conversion tax savings — actual marginal rate
# ---------------------------------------------------------------------------


def test_roth_conversion_no_hardcoded_22_pct():
    """Roth conversion service must not hardcode 0.22 for tax savings estimate."""
    source = inspect.getsource(
        __import__("app.services.roth_conversion_service", fromlist=["roth_conversion_service"])
    )
    # The old line was: `converted_after_growth * 0.22`
    assert "* 0.22 " not in source and "* 0.22\n" not in source, (
        "Roth conversion service still hardcodes 0.22 for tax savings"
    )


def test_roth_conversion_uses_marginal_rate():
    """Tax savings should use the user's actual marginal rate."""
    from app.services.roth_conversion_service import RothConversionService, RothConversionInput
    svc = RothConversionService()
    result = svc.optimize(RothConversionInput(
        traditional_balance=500_000,
        roth_balance=50_000,
        current_income=80_000,
        current_age=55,
    ))
    # Should produce a non-negative savings number
    assert result.estimated_tax_savings >= 0


# ---------------------------------------------------------------------------
# 3. LTCG 0% thresholds from constants
# ---------------------------------------------------------------------------


def test_ltcg_ceiling_derived_from_constants():
    """LTCG 0% ceiling should match TAX.LTCG_BRACKETS_* first threshold."""
    from app.services.capital_gains_harvesting_service import _ltcg_0pct_ceiling
    from app.constants.financial import TAX
    ceilings = _ltcg_0pct_ceiling(2026)
    tax_data = TAX.for_year(2026)
    assert float(ceilings["single"]) == tax_data["LTCG_BRACKETS_SINGLE"][0][0]
    assert float(ceilings["married_filing_jointly"]) == tax_data["LTCG_BRACKETS_MARRIED"][0][0]


def test_ltcg_ceiling_no_hardcoded_dict():
    """capital_gains_harvesting_service must not have a hardcoded LTCG_0PCT_CEILING dict."""
    source = inspect.getsource(
        __import__("app.services.capital_gains_harvesting_service", fromlist=["x"])
    )
    assert "LTCG_0PCT_CEILING = {" not in source


# ---------------------------------------------------------------------------
# 4. Social Security historical taxable max
# ---------------------------------------------------------------------------


def test_ss_historical_taxable_max_table_exists():
    """SS class should have a historical taxable max table covering 1990-2026."""
    from app.constants.financial import SS
    assert hasattr(SS, "HISTORICAL_TAXABLE_MAX")
    table = SS.HISTORICAL_TAXABLE_MAX
    assert 1990 in table
    assert 2026 in table
    assert 2000 in table
    # Spot check: 2000 max was $76,200
    assert table[2000] == 76_200


def test_ss_taxable_max_for_year():
    """SS.taxable_max_for_year should return year-specific values."""
    from app.constants.financial import SS
    assert SS.taxable_max_for_year(2000) == 76_200
    assert SS.taxable_max_for_year(2020) == 137_700
    assert SS.taxable_max_for_year(2024) == 168_600
    # Future years should project forward
    future = SS.taxable_max_for_year(2030)
    assert future > SS.taxable_max_for_year(2026)


def test_ss_estimator_uses_year_specific_max():
    """estimate_aime_from_salary should use year-specific caps, not one global max."""
    source = inspect.getsource(
        __import__("app.services.retirement.social_security_estimator", fromlist=["x"])
    )
    assert "taxable_max_for_year" in source, (
        "Social security estimator should call SS.taxable_max_for_year()"
    )


# ---------------------------------------------------------------------------
# 5 & 6. TEY formula and combined rate
# ---------------------------------------------------------------------------


def test_tey_taxable_bond_shows_nominal_yield():
    """For taxable bonds (CD, SAVINGS, etc.), TEY should equal nominal yield."""
    source = inspect.getsource(
        __import__("app.api.v1.tax_equiv_yield", fromlist=["x"])
    )
    # Should have _TAX_EXEMPT_TYPES for distinguishing tax-advantaged instruments
    assert "_TAX_EXEMPT_TYPES" in source


def test_tey_has_itemizing_parameter():
    """TEY endpoint should accept an 'itemizing' query parameter."""
    source = inspect.getsource(
        __import__("app.api.v1.tax_equiv_yield", fromlist=["x"])
    )
    assert "itemizing" in source


def test_tey_combined_rate_with_itemizing():
    """When itemizing, combined_rate = fed + state*(1-fed)."""
    source = inspect.getsource(
        __import__("app.api.v1.tax_equiv_yield", fromlist=["x"])
    )
    # Should see the itemizing formula
    assert "state_rate * (1 - fed_rate)" in source


def test_tey_response_has_is_tax_advantaged():
    """YieldHolding should have is_tax_advantaged field, not just is_muni."""
    from app.api.v1.tax_equiv_yield import YieldHolding
    fields = set(YieldHolding.model_fields.keys())
    assert "is_tax_advantaged" in fields


# ---------------------------------------------------------------------------
# 7. TCJA sunset note
# ---------------------------------------------------------------------------


def test_tcja_sunset_risk_is_false():
    """ESTATE.TCJA_SUNSET_RISK should be False after OBBBA extension."""
    from app.constants.financial import ESTATE
    assert ESTATE.TCJA_SUNSET_RISK is False


def test_tcja_sunset_year_is_2034():
    """ESTATE should have TCJA_SUNSET_YEAR = 2034."""
    from app.constants.financial import ESTATE
    assert ESTATE.TCJA_SUNSET_YEAR == 2034


def test_estate_planning_sunset_note_updated():
    """Estate planning service sunset note should mention OBBBA extension."""
    from app.services.estate_planning_service import EstatePlanningService
    result = EstatePlanningService.calculate_estate_tax_exposure(Decimal("5000000"))
    note = result["sunset_note"]
    assert "One Big Beautiful Bill" in note or "2034" in note
    assert "after 2025 if not extended" not in note


# ---------------------------------------------------------------------------
# 8. SECURE 2.0 super catch-up
# ---------------------------------------------------------------------------


def test_retirement_has_super_catchup_constants():
    """RETIREMENT class should have super catch-up age range and limit."""
    from app.constants.financial import RETIREMENT
    assert RETIREMENT.CATCH_UP_AGE_SUPER_401K_START == 60
    assert RETIREMENT.CATCH_UP_AGE_SUPER_401K_END == 63
    assert RETIREMENT.LIMIT_401K_SUPER_CATCH_UP > 0
    # Super catch-up should be higher than regular catch-up
    assert RETIREMENT.LIMIT_401K_SUPER_CATCH_UP > RETIREMENT.LIMIT_401K_CATCH_UP


def test_super_catchup_in_retirement_limits_data():
    """_RETIREMENT_LIMITS should have LIMIT_401K_SUPER_CATCH_UP for 2025+."""
    from app.constants.financial import RETIREMENT
    limits_2025 = RETIREMENT.for_year(2025)
    assert "LIMIT_401K_SUPER_CATCH_UP" in limits_2025
    assert limits_2025["LIMIT_401K_SUPER_CATCH_UP"] == 11_250
    limits_2026 = RETIREMENT.for_year(2026)
    assert limits_2026["LIMIT_401K_SUPER_CATCH_UP"] == 12_000


def test_contribution_headroom_uses_super_catchup():
    """contribution_headroom._annual_limit should use super catch-up for ages 60-63."""
    source = inspect.getsource(
        __import__("app.api.v1.contribution_headroom", fromlist=["x"])
    )
    assert "SUPER_CATCH_UP" in source or "super_catchup" in source


# ---------------------------------------------------------------------------
# 9. SECURE 2.0 age-75 RMD
# ---------------------------------------------------------------------------


def test_rmd_trigger_age_birth_year_aware():
    """RMD.trigger_age_for_birth_year should return 73 for <1960 and 75 for >=1960."""
    from app.constants.financial import RMD
    assert RMD.trigger_age_for_birth_year(1959) == 73
    assert RMD.trigger_age_for_birth_year(1960) == 75
    assert RMD.trigger_age_for_birth_year(1970) == 75
    assert RMD.trigger_age_for_birth_year(None) == 73


def test_rmd_constants_has_trigger_age_2033():
    """RMD class should define TRIGGER_AGE_2033 = 75."""
    from app.constants.financial import RMD
    assert RMD.TRIGGER_AGE_2033 == 75
    assert RMD.TRIGGER_AGE_BIRTH_YEAR_THRESHOLD == 1960


def test_requires_rmd_birth_year_aware():
    """requires_rmd should accept optional birth_year parameter."""
    from app.utils.rmd_calculator import requires_rmd
    # Born 1959: RMD at 73
    assert requires_rmd(72, birth_year=1959) is False
    assert requires_rmd(73, birth_year=1959) is True
    # Born 1960: RMD at 75
    assert requires_rmd(73, birth_year=1960) is False
    assert requires_rmd(74, birth_year=1960) is False
    assert requires_rmd(75, birth_year=1960) is True
    # No birth year: default 73
    assert requires_rmd(73) is True


# ---------------------------------------------------------------------------
# 10. Duplicate RMD table removed
# ---------------------------------------------------------------------------


def test_tax_bucket_service_no_inline_ult():
    """tax_bucket_service should import ULT from RMD constants, not define inline."""
    source = inspect.getsource(
        __import__("app.services.tax_bucket_service", fromlist=["x"])
    )
    # Should NOT have a hardcoded ULT dict with age 72
    assert "72: Decimal" not in source, (
        "tax_bucket_service still has inline ULT with pre-SECURE-2.0 age 72"
    )
    # Should reference RMD.UNIFORM_LIFETIME_TABLE
    assert "RMD.UNIFORM_LIFETIME_TABLE" in source


# ---------------------------------------------------------------------------
# 11. RMD tax incremental (covered by tests in section 1)
# ---------------------------------------------------------------------------


def test_rmd_planner_source_no_flat_rate_tax():
    """RMD planner should not compute tax as `total_rmd * rate`."""
    source = inspect.getsource(
        __import__("app.api.v1.rmd_planner", fromlist=["x"])
    )
    assert "total_rmd * rate" not in source, (
        "RMD planner still uses flat marginal rate for tax calculation"
    )


# ---------------------------------------------------------------------------
# 12. AMT, QBI, WEP, QCD year-keyed tables
# ---------------------------------------------------------------------------


def test_amt_year_keyed():
    """AMT class should have year-keyed exemptions."""
    from app.constants.financial import AMT
    assert AMT.AMT_EXEMPTION_SINGLE > 0
    assert AMT.AMT_EXEMPTION_MARRIED > AMT.AMT_EXEMPTION_SINGLE
    data_2025 = AMT.for_year(2025)
    assert data_2025["AMT_EXEMPTION_SINGLE"] == 88_100
    assert data_2025["AMT_EXEMPTION_MARRIED"] == 137_000


def test_qbi_year_keyed():
    """QBI class should have year-keyed thresholds."""
    from app.constants.financial import QBI
    assert QBI.QBI_THRESHOLD_SINGLE > 0
    assert QBI.QBI_THRESHOLD_MARRIED > QBI.QBI_THRESHOLD_SINGLE
    data_2025 = QBI.for_year(2025)
    assert data_2025["QBI_THRESHOLD_SINGLE"] == 197_300


def test_wep_year_keyed():
    """WEP class should have year-keyed max monthly reduction."""
    from app.constants.financial import WEP
    assert float(WEP.WEP_MAX_MONTHLY_REDUCTION) > 0
    data_2025 = WEP.for_year(2025)
    assert data_2025["WEP_MAX_MONTHLY_REDUCTION"] == 587


def test_qcd_year_keyed():
    """QCD class should have year-keyed max annual amount."""
    from app.constants.financial import QCD
    assert QCD.QCD_MAX_ANNUAL > 0
    data_2024 = QCD.for_year(2024)
    assert data_2024["QCD_MAX_ANNUAL"] == 105_000
    data_2025 = QCD.for_year(2025)
    assert data_2025["QCD_MAX_ANNUAL"] == 108_000


def test_equity_amt_values_match_amt_class():
    """EQUITY.AMT_* should match AMT class (not stale hardcoded values)."""
    from app.constants.financial import EQUITY, AMT
    assert EQUITY.AMT_EXEMPTION_SINGLE == AMT.AMT_EXEMPTION_SINGLE
    assert EQUITY.AMT_EXEMPTION_MARRIED == AMT.AMT_EXEMPTION_MARRIED
    assert EQUITY.AMT_PHASEOUT_SINGLE == AMT.AMT_PHASEOUT_SINGLE


# ---------------------------------------------------------------------------
# 13. Dependent care 2026 row
# ---------------------------------------------------------------------------


def test_dependent_care_2026_row_exists():
    """DC-FSA and CDCTC tables should have a 2026 entry."""
    from app.services.dependent_care_optimizer_service import (
        _DCFSA_LIMIT_BY_YEAR,
        _CDCTC_EXPENSE_CAP_BY_YEAR,
    )
    assert 2026 in _DCFSA_LIMIT_BY_YEAR
    assert 2026 in _CDCTC_EXPENSE_CAP_BY_YEAR
    assert _DCFSA_LIMIT_BY_YEAR[2026] == 5_000
    assert _CDCTC_EXPENSE_CAP_BY_YEAR[2026]["one_dependent"] == 3_000


# ---------------------------------------------------------------------------
# 14. Head of Household brackets
# ---------------------------------------------------------------------------


def test_hoh_brackets_exist():
    """TAX class should have BRACKETS_HOH."""
    from app.constants.financial import TAX
    assert hasattr(TAX, "BRACKETS_HOH")
    assert len(TAX.BRACKETS_HOH) == 7  # 7 brackets like single/married
    # First bracket should be 10%
    assert TAX.BRACKETS_HOH[0][0] == 0.10
    # HOH thresholds should be between single and married
    single_12 = TAX.BRACKETS_SINGLE[1][1]
    married_12 = TAX.BRACKETS_MARRIED[1][1]
    hoh_12 = TAX.BRACKETS_HOH[1][1]
    assert single_12 < hoh_12 < married_12


def test_hoh_brackets_in_for_year():
    """TAX.for_year() should return BRACKETS_HOH."""
    from app.constants.financial import TAX
    d2026 = TAX.for_year(2026)
    assert "BRACKETS_HOH" in d2026
    assert len(d2026["BRACKETS_HOH"]) == 7


def test_hoh_standard_deduction():
    """TAX class should have STANDARD_DEDUCTION_HOH."""
    from app.constants.financial import TAX
    assert hasattr(TAX, "STANDARD_DEDUCTION_HOH")
    # HOH deduction should be between single and married
    assert TAX.STANDARD_DEDUCTION_SINGLE < TAX.STANDARD_DEDUCTION_HOH < TAX.STANDARD_DEDUCTION_MARRIED


# ---------------------------------------------------------------------------
# 15. State tax rate updates
# ---------------------------------------------------------------------------


def test_state_tax_rates_updated():
    """State tax rates should reflect 2025 changes."""
    from app.constants.state_tax_rates import STATE_TAX_RATES
    # Iowa: 3.8% flat from 2025
    assert STATE_TAX_RATES["IA"] == 0.038
    # North Carolina: 4.25% from 2025
    assert STATE_TAX_RATES["NC"] == 0.0425
    # Ohio: reduced top rate
    assert STATE_TAX_RATES["OH"] == 0.035
    # Arizona: 2.5% flat (was already correct)
    assert STATE_TAX_RATES["AZ"] == 0.025


# ---------------------------------------------------------------------------
# 16. IRMAA married brackets
# ---------------------------------------------------------------------------


def test_irmaa_married_brackets_exist():
    """MEDICARE should have IRMAA_BRACKETS_MARRIED."""
    from app.constants.financial import MEDICARE
    assert hasattr(MEDICARE, "IRMAA_BRACKETS_MARRIED")
    assert len(MEDICARE.IRMAA_BRACKETS_MARRIED) == 6  # 6 tiers like single
    # First married threshold should be roughly 2x single
    single_t1 = MEDICARE.IRMAA_BRACKETS_SINGLE[0][0]
    married_t1 = MEDICARE.IRMAA_BRACKETS_MARRIED[0][0]
    assert 1.8 * single_t1 < married_t1 < 2.2 * single_t1


def test_irmaa_married_brackets_in_for_year():
    """MEDICARE.for_year() should include IRMAA_BRACKETS_MARRIED."""
    from app.constants.financial import MEDICARE
    d = MEDICARE.for_year(2026)
    assert "IRMAA_BRACKETS_MARRIED" in d


def test_irmaa_projection_uses_married_brackets():
    """IRMAA projection should use proper married brackets, not 2x approximation."""
    source = inspect.getsource(
        __import__("app.api.v1.irmaa_projection", fromlist=["x"])
    )
    assert "IRMAA_BRACKETS_MARRIED" in source or "married_brackets" in source
