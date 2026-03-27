"""Unit tests for the new financial planning feature constants."""

from decimal import Decimal

import pytest

from app.constants.financial import (
    CHARITABLE,
    CASH_FLOW_TIMING,
    EQUITY,
    ESTATE,
    HSA,
    JOINT_SS,
    LENDING,
    PENSION,
    STRESS_TEST,
    TAX_BUCKETS,
    TREASURY,
    VARIABLE_INCOME,
)


# ── EQUITY ─────────────────────────────────────────────────────────────────────


class TestEquity:
    def test_amt_exemption_single_range(self):
        # IRS AMT exemption for single filers (2026: $90,700; year-keyed so will grow with COLA)
        assert EQUITY.AMT_EXEMPTION_SINGLE > 80_000
        assert EQUITY.AMT_EXEMPTION_SINGLE < 500_000

    def test_amt_exemption_married_greater_than_single(self):
        # Married AMT exemption is higher than single but NOT exactly double (IRS rule)
        assert EQUITY.AMT_EXEMPTION_MARRIED > EQUITY.AMT_EXEMPTION_SINGLE
        assert EQUITY.AMT_EXEMPTION_MARRIED < EQUITY.AMT_EXEMPTION_SINGLE * 2

    def test_amt_rates_are_decimals(self):
        assert isinstance(EQUITY.AMT_RATE_26, Decimal)
        assert isinstance(EQUITY.AMT_RATE_28, Decimal)
        assert EQUITY.AMT_RATE_26 < EQUITY.AMT_RATE_28

    def test_iso_disqualifying_days(self):
        assert EQUITY.ISO_DISQUALIFYING_DISPOSITION_DAYS == 730

    def test_qsbs_exclusion_rate(self):
        assert EQUITY.QSBS_EXCLUSION_RATE == Decimal("0.50")

    def test_nso_and_rsu_tax_treatment_strings(self):
        assert EQUITY.NSO_TAX_TREATMENT == "ordinary_income"
        assert EQUITY.RSU_TAX_EVENT == "ordinary_income"


# ── HSA ────────────────────────────────────────────────────────────────────────


class TestHSA:
    def test_investment_threshold_positive(self):
        assert HSA.INVESTMENT_THRESHOLD > 0

    def test_medicare_cutoff_age(self):
        assert HSA.MEDICARE_CUTOFF_AGE == 65

    def test_non_qualified_penalty_rate(self):
        assert HSA.NON_QUALIFIED_PENALTY_RATE == Decimal("0.20")

    def test_hdhp_family_deductible_greater_than_individual(self):
        assert HSA.HDHP_MIN_DEDUCTIBLE_FAMILY > HSA.HDHP_MIN_DEDUCTIBLE_INDIVIDUAL

    def test_hdhp_max_oop_family_greater_than_individual(self):
        assert HSA.HDHP_MAX_OOP_FAMILY > HSA.HDHP_MAX_OOP_INDIVIDUAL

    def test_investment_return_default_reasonable(self):
        assert Decimal("0.01") < HSA.INVESTMENT_RETURN_DEFAULT < Decimal("0.20")


# ── TREASURY ───────────────────────────────────────────────────────────────────


class TestTreasury:
    def test_tbill_maturities_non_empty(self):
        assert len(TREASURY.TBILL_MATURITIES_WEEKS) > 0

    def test_tnote_maturities_non_empty(self):
        assert len(TREASURY.TNOTE_MATURITIES_YEARS) > 0

    def test_tbond_maturities_non_empty(self):
        assert len(TREASURY.TBOND_MATURITIES_YEARS) > 0

    def test_i_bond_annual_limit_electronic(self):
        assert TREASURY.I_BOND_ANNUAL_LIMIT_ELECTRONIC == 10_000

    def test_i_bond_min_hold_months(self):
        assert TREASURY.I_BOND_MIN_HOLD_MONTHS == 12

    def test_tips_deflation_floor(self):
        assert TREASURY.TIPS_DEFLATION_FLOOR == Decimal("1.0")

    def test_tbill_maturities_sorted(self):
        assert TREASURY.TBILL_MATURITIES_WEEKS == sorted(TREASURY.TBILL_MATURITIES_WEEKS)

    def test_tnote_maturities_sorted(self):
        assert TREASURY.TNOTE_MATURITIES_YEARS == sorted(TREASURY.TNOTE_MATURITIES_YEARS)


# ── ESTATE ─────────────────────────────────────────────────────────────────────


class TestEstate:
    def test_federal_exemption_above_ten_million(self):
        assert ESTATE.FEDERAL_EXEMPTION > 10_000_000

    def test_federal_tax_rate(self):
        assert ESTATE.FEDERAL_TAX_RATE == Decimal("0.40")

    def test_annual_gift_exclusion_married_is_double(self):
        assert ESTATE.ANNUAL_GIFT_EXCLUSION_MARRIED == ESTATE.ANNUAL_GIFT_EXCLUSION * 2

    def test_portability_deadline_months(self):
        assert ESTATE.PORTABILITY_ELECTION_DEADLINE_MONTHS == 9

    def test_tcja_sunset_risk_is_bool(self):
        assert isinstance(ESTATE.TCJA_SUNSET_RISK, bool)


# ── STRESS_TEST ────────────────────────────────────────────────────────────────


class TestStressTest:
    def test_scenarios_has_six_keys(self):
        assert len(STRESS_TEST.SCENARIOS) == 6

    def test_expected_scenario_keys_present(self):
        expected = {
            "market_crash_30",
            "dot_com_2000",
            "gfc_2008",
            "covid_2020",
            "stagflation_1970s",
            "rate_shock_200bps",
        }
        assert set(STRESS_TEST.SCENARIOS.keys()) == expected

    def test_each_scenario_has_label(self):
        for key, scenario in STRESS_TEST.SCENARIOS.items():
            assert "label" in scenario, f"Scenario '{key}' missing 'label'"

    def test_each_scenario_has_duration_years(self):
        for key, scenario in STRESS_TEST.SCENARIOS.items():
            assert "duration_years" in scenario, f"Scenario '{key}' missing 'duration_years'"

    def test_equity_drops_are_negative(self):
        for key, scenario in STRESS_TEST.SCENARIOS.items():
            drop = scenario.get("equity_drop")
            if drop is not None:
                assert drop < 0, f"Scenario '{key}' equity_drop should be negative"

    def test_bond_price_sensitivity_negative(self):
        assert STRESS_TEST.BOND_PRICE_SENSITIVITY_PER_YEAR_PER_100BPS < 0


# ── CASH_FLOW_TIMING ───────────────────────────────────────────────────────────


class TestCashFlowTiming:
    def test_paycheck_frequencies_non_empty(self):
        assert len(CASH_FLOW_TIMING.PAYCHECK_FREQUENCIES) > 0

    def test_biweekly_frequency(self):
        assert CASH_FLOW_TIMING.PAYCHECK_FREQUENCIES["biweekly"] == 26

    def test_default_frequency_in_map(self):
        assert CASH_FLOW_TIMING.DEFAULT_FREQUENCY in CASH_FLOW_TIMING.PAYCHECK_FREQUENCIES

    def test_low_balance_warning_positive(self):
        assert CASH_FLOW_TIMING.LOW_BALANCE_WARNING_USD > 0

    def test_bill_warning_days_positive(self):
        assert CASH_FLOW_TIMING.BILL_WARNING_DAYS_BEFORE_SHORTFALL > 0


# ── PENSION ────────────────────────────────────────────────────────────────────


class TestPension:
    def test_cola_default_rate_reasonable(self):
        assert Decimal("0.00") < PENSION.COLA_DEFAULT_RATE < Decimal("0.10")

    def test_survivor_100_cost_greater_than_50(self):
        assert PENSION.SURVIVOR_100_COST_PCT > PENSION.SURVIVOR_50_COST_PCT

    def test_wep_max_monthly_reduction_positive(self):
        assert PENSION.WEP_MAX_MONTHLY_REDUCTION > 0

    def test_gpo_reduction_rate(self):
        assert PENSION.GPO_REDUCTION_RATE == Decimal("0.667")

    def test_lump_sum_hurdle_rate_positive(self):
        assert PENSION.LUMP_SUM_HURDLE_RATE > 0


# ── VARIABLE_INCOME ────────────────────────────────────────────────────────────


class TestVariableIncome:
    def test_smoothing_months(self):
        assert VARIABLE_INCOME.SMOOTHING_MONTHS == 12

    def test_emergency_fund_months_minimum(self):
        assert VARIABLE_INCOME.EMERGENCY_FUND_MONTHS_MINIMUM >= 6

    def test_quarterly_tax_due_months_has_four_entries(self):
        assert len(VARIABLE_INCOME.QUARTERLY_TAX_DUE_MONTHS) == 4

    def test_se_tax_rate(self):
        assert VARIABLE_INCOME.SE_TAX_RATE == Decimal("0.153")

    def test_qbi_threshold_married_double_single(self):
        assert VARIABLE_INCOME.QBI_THRESHOLD_MARRIED == VARIABLE_INCOME.QBI_THRESHOLD_SINGLE * 2

    def test_safe_harbor_high_income_rate_greater(self):
        assert (
            VARIABLE_INCOME.SAFE_HARBOR_RATE_HIGH_INCOME
            > VARIABLE_INCOME.SAFE_HARBOR_RATE_NORMAL
        )


# ── LENDING ────────────────────────────────────────────────────────────────────


class TestLending:
    def test_max_dti_conventional_at_or_below_50_pct(self):
        assert LENDING.MAX_DTI_CONVENTIONAL <= Decimal("0.50")

    def test_max_dti_fha_at_or_below_60_pct(self):
        assert LENDING.MAX_DTI_FHA <= Decimal("0.60")

    def test_front_end_less_than_back_end(self):
        assert LENDING.FRONT_END_DTI_LIMIT < LENDING.MAX_DTI_CONVENTIONAL

    def test_prime_credit_score_threshold_reasonable(self):
        assert 600 < LENDING.PRIME_CREDIT_SCORE_THRESHOLD <= 850

    def test_auto_depreciation_new_greater_than_used(self):
        # New cars depreciate faster (higher rate)
        assert LENDING.AUTO_DEPRECIATION_NEW_ANNUAL >= LENDING.AUTO_DEPRECIATION_USED_ANNUAL

    def test_lease_money_factor_positive(self):
        assert LENDING.LEASE_MONEY_FACTOR_TO_APR > 0


# ── CHARITABLE ─────────────────────────────────────────────────────────────────


class TestCharitable:
    def test_qcd_max_annual_positive(self):
        assert CHARITABLE.QCD_MAX_ANNUAL > 0

    def test_qcd_eligible_age(self):
        assert CHARITABLE.QCD_ELIGIBLE_AGE == Decimal("70.5")

    def test_carryforward_years(self):
        assert CHARITABLE.CARRYFORWARD_YEARS == 5

    def test_deduction_limits_under_one(self):
        assert CHARITABLE.DEDUCTION_LIMIT_CASH_PCT_AGI < Decimal("1.0")
        assert CHARITABLE.DEDUCTION_LIMIT_PROPERTY_PCT_AGI < Decimal("1.0")
        assert CHARITABLE.DEDUCTION_LIMIT_APPRECIATED_PCT_AGI < Decimal("1.0")

    def test_appreciated_security_bool(self):
        assert isinstance(CHARITABLE.APPRECIATED_SECURITY_AVOIDS_LTCG, bool)


# ── JOINT_SS ───────────────────────────────────────────────────────────────────


class TestJointSS:
    def test_spousal_benefit_pct(self):
        assert JOINT_SS.SPOUSAL_BENEFIT_PCT == Decimal("0.50")

    def test_survivor_benefit_pct(self):
        assert JOINT_SS.SURVIVOR_BENEFIT_PCT == Decimal("1.00")

    def test_divorced_spouse_min_marriage_years(self):
        assert JOINT_SS.DIVORCED_SPOUSE_MIN_MARRIAGE_YEARS == 10

    def test_dual_entitlement_rule_bool(self):
        assert isinstance(JOINT_SS.DUAL_ENTITLEMENT_RULE, bool)

    def test_restricted_application_birth_year(self):
        assert JOINT_SS.RESTRICTED_APPLICATION_BIRTH_YEAR_CUTOFF == 1954


# ── TAX_BUCKETS ────────────────────────────────────────────────────────────────


class TestTaxBuckets:
    def test_pre_tax_warning_threshold_reasonable(self):
        assert Decimal("0.50") < TAX_BUCKETS.PRE_TAX_WARNING_THRESHOLD_PCT < Decimal("1.00")

    def test_rmd_bomb_multiple_positive(self):
        assert TAX_BUCKETS.RMD_BOMB_MULTIPLE_OF_SPENDING > 0

    def test_optimal_conversion_bracket_reasonable(self):
        assert Decimal("0.10") <= TAX_BUCKETS.OPTIMAL_CONVERSION_BRACKET <= Decimal("0.37")

    def test_projection_default_years_positive(self):
        assert TAX_BUCKETS.PROJECTION_DEFAULT_YEARS > 0

    def test_roth_ladder_seasoning_years(self):
        assert TAX_BUCKETS.ROTH_LADDER_SEASONING_YEARS == 5
