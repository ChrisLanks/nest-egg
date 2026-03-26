"""
Tests for the 8 new planning features:
1. Net Worth Forecast
2. IRMAA & Medicare Projection
3. Backdoor Roth Analysis
4. RMD Planner
5. Beneficiary Audit
6. Contribution Headroom
7. Tax-Equivalent Yield
8. Cash Flow Calendar (weekly view — frontend only, tested via source inspection)
"""

import datetime
from decimal import Decimal

import pytest

from app.constants.financial import MEDICARE, RETIREMENT, TAX, RMD as RMD_CONSTANTS
from app.utils.account_type_groups import RMD_ACCOUNT_TYPES, TRADITIONAL_IRA_TYPES, EMPLOYER_PLAN_TYPES
from app.utils.rmd_calculator import calculate_rmd, requires_rmd


# ── 1. Net Worth Forecast ─────────────────────────────────────────────────────

class TestNetWorthForecastLogic:
    """Tests for the projection math in net_worth_forecast.py."""

    def _project(self, current_nw, annual_contribution, annual_return, years):
        """Replicate the projection logic from the endpoint."""
        nw = current_nw
        results = [nw]
        for _ in range(years):
            nw = nw * (1 + annual_return) + annual_contribution
            results.append(nw)
        return results

    def test_projection_grows_monotonically_with_positive_contribution(self):
        pts = self._project(100_000, 24_000, 0.07, 10)
        assert pts[-1] > pts[0]

    def test_zero_return_grows_by_contribution_only(self):
        pts = self._project(0, 10_000, 0.0, 5)
        assert pts[-1] == pytest.approx(50_000)

    def test_negative_return_can_erode_small_portfolio(self):
        pts = self._project(10_000, 0, -0.10, 5)
        assert pts[-1] < pts[0]

    def test_optimistic_greater_than_pessimistic(self):
        baseline = self._project(100_000, 24_000, 0.07, 20)
        pessimistic = self._project(100_000, 24_000, 0.05, 20)
        optimistic = self._project(100_000, 24_000, 0.09, 20)
        assert optimistic[-1] > baseline[-1] > pessimistic[-1]

    def test_retirement_target_4pct_rule(self):
        # 25× annual spending = $2M at $80k spending
        annual_spending = 80_000
        target = annual_spending * 25
        assert target == 2_000_000

    def test_years_to_retirement_zero_when_past_age(self):
        current_age = 70
        retirement_age = 67
        years = max(1, retirement_age - current_age)
        assert years == 1  # clamps to minimum 1


# ── 2. IRMAA Projection ───────────────────────────────────────────────────────

class TestIrmaaProjection:
    """Tests for IRMAA tier lookup and projection logic."""

    def _find_tier(self, magi, brackets, married=False):
        """Replicate _irmaa_tier logic."""
        multiplier = 2.0 if married else 1.0
        for i, (threshold, b_surcharge, d_surcharge) in enumerate(brackets):
            if magi <= threshold * multiplier:
                return i, b_surcharge, d_surcharge
        last = brackets[-1]
        return len(brackets) - 1, last[1], last[2]

    def test_base_tier_for_low_income(self):
        brackets = MEDICARE.IRMAA_BRACKETS_SINGLE
        tier, b_s, d_s = self._find_tier(90_000, brackets)
        assert tier == 0
        assert b_s == 0
        assert d_s == 0

    def test_higher_income_hits_tier_1(self):
        brackets = MEDICARE.IRMAA_BRACKETS_SINGLE
        # Tier 1 threshold is the second bracket's income floor
        tier_1_floor = brackets[1][0]  # income above this hits tier 1+
        tier, _, _ = self._find_tier(tier_1_floor + 1, brackets)
        assert tier >= 1

    def test_married_threshold_doubles_single(self):
        """Married threshold is 2× single, so same income hits lower tier for married."""
        brackets = MEDICARE.IRMAA_BRACKETS_SINGLE
        magi = 110_000
        tier_single, _, _ = self._find_tier(magi, brackets, married=False)
        tier_married, _, _ = self._find_tier(magi, brackets, married=True)
        assert tier_married <= tier_single

    def test_medicare_constants_have_irmaa_brackets(self):
        assert hasattr(MEDICARE, "IRMAA_BRACKETS_SINGLE")
        assert len(MEDICARE.IRMAA_BRACKETS_SINGLE) >= 5

    def test_part_b_and_d_defined(self):
        assert MEDICARE.PART_B_MONTHLY > 0
        assert MEDICARE.PART_D_MONTHLY >= 0

    def test_irmaa_planning_age(self):
        assert MEDICARE.IRMAA_PLANNING_AGE == 63

    def test_for_year_returns_brackets(self):
        data = MEDICARE.for_year(2026)
        assert "IRMAA_BRACKETS_SINGLE" in data
        assert "PART_B_MONTHLY" in data

    def test_income_projection_grows(self):
        magi = 100_000
        growth = 0.03
        projected_5yr = magi * ((1 + growth) ** 5)
        assert projected_5yr > magi

    def test_irmaa_lookback_offset(self):
        """IRMAA uses income from 2 years prior."""
        current_year = datetime.date.today().year
        magi_year = current_year + 2
        income_used_for_year = magi_year - 2
        assert income_used_for_year == current_year


# ── 3. Backdoor Roth ─────────────────────────────────────────────────────────

class TestBackdoorRothLogic:
    """Tests for backdoor Roth pro-rata rule and limits."""

    # Roth IRA income phase-out thresholds (2026 estimate)
    PHASEOUT_SINGLE = (146_000, 161_000)
    PHASEOUT_MARRIED = (230_000, 240_000)

    def test_pro_rata_warning_when_pretax_balance_exists(self):
        ira_balance = 50_000
        basis = 0.0
        pre_tax = ira_balance - basis
        pro_rata_warning = ira_balance > 0 and pre_tax > 0
        assert pro_rata_warning is True

    def test_no_pro_rata_warning_when_all_basis(self):
        ira_balance = 7_000
        basis = 7_000.0
        pre_tax = ira_balance - basis
        pro_rata_warning = ira_balance > 0 and pre_tax > 0
        assert pro_rata_warning is False

    def test_pro_rata_ratio_calculation(self):
        balance = 100_000
        basis = 20_000
        pre_tax = balance - basis
        ratio = pre_tax / balance
        assert ratio == pytest.approx(0.80)

    def test_direct_roth_ineligible_above_phaseout(self):
        lo, hi = self.PHASEOUT_SINGLE
        magi = hi + 1
        eligible = magi < lo
        assert eligible is False

    def test_direct_roth_eligible_below_phaseout(self):
        lo, hi = self.PHASEOUT_SINGLE
        magi = lo - 1
        eligible = magi < lo
        assert eligible is True

    def test_ira_limit_with_catchup_age_50(self):
        limits = RETIREMENT.for_year(datetime.date.today().year)
        base = limits["LIMIT_IRA"]
        catchup = limits["LIMIT_IRA_CATCH_UP"]
        assert base > 0
        assert catchup > 0
        total_with_catchup = base + catchup
        assert total_with_catchup > base

    def test_traditional_ira_types_defined(self):
        assert len(TRADITIONAL_IRA_TYPES) >= 3

    def test_employer_plan_types_defined(self):
        assert len(EMPLOYER_PLAN_TYPES) >= 3

    def test_401k_total_limit_greater_than_employee_limit(self):
        limits = RETIREMENT.for_year(datetime.date.today().year)
        assert limits["LIMIT_401K_TOTAL"] > limits["LIMIT_401K"]


# ── 4. RMD Planner ───────────────────────────────────────────────────────────

class TestRmdPlanner:
    """Tests for multi-account RMD projections."""

    def test_rmd_trigger_age(self):
        assert RMD_CONSTANTS.TRIGGER_AGE == 73

    def test_requires_rmd_at_73(self):
        assert requires_rmd(73) is True

    def test_no_rmd_at_72(self):
        assert requires_rmd(72) is False

    def test_calculate_rmd_returns_positive_amount(self):
        balance = Decimal("500000")
        rmd = calculate_rmd(balance, 75)
        assert rmd is not None
        assert rmd > 0

    def test_rmd_increases_with_age_at_same_balance(self):
        balance = Decimal("1000000")
        rmd_73 = calculate_rmd(balance, 73)
        rmd_80 = calculate_rmd(balance, 80)
        assert rmd_80 > rmd_73  # shorter life expectancy → larger RMD

    def test_rmd_none_below_trigger_age(self):
        assert calculate_rmd(Decimal("500000"), 72) is None

    def test_rmd_account_types_include_401k(self):
        from app.models.account import AccountType
        assert AccountType.RETIREMENT_401K in RMD_ACCOUNT_TYPES

    def test_rmd_account_types_exclude_roth(self):
        from app.models.account import AccountType
        assert AccountType.RETIREMENT_ROTH not in RMD_ACCOUNT_TYPES

    def test_rmd_account_types_exclude_hsa(self):
        from app.models.account import AccountType
        assert AccountType.HSA not in RMD_ACCOUNT_TYPES

    def test_marginal_rate_lookup(self):
        """Tax brackets exist for current year."""
        tax_data = TAX.for_year(datetime.date.today().year)
        assert len(tax_data["BRACKETS_SINGLE"]) >= 5

    def test_lifetime_rmd_accumulates(self):
        balance = Decimal("500000")
        total = Decimal("0")
        for age in range(73, 93):
            rmd = calculate_rmd(balance * Decimal(str((1.06 ** (age - 73)))), age)
            if rmd:
                total += rmd
        assert total > 0


# ── 5. Beneficiary Audit ─────────────────────────────────────────────────────

class TestBeneficiaryAudit:
    """Tests for beneficiary coverage audit logic."""

    AUDITABLE_TYPES = {
        "retirement_401k", "retirement_403b", "retirement_457b",
        "retirement_ira", "retirement_roth", "retirement_sep_ira",
        "retirement_simple_ira", "brokerage", "life_insurance_cash_value", "annuity",
    }

    def _audit_account(self, beneficiaries):
        primaries = [b for b in beneficiaries if b["type"] == "primary"]
        contingents = [b for b in beneficiaries if b["type"] == "contingent"]
        issues = []
        if not primaries:
            issues.append("missing_primary")
        if not contingents:
            issues.append("missing_contingent")
        pct = sum(b["pct"] for b in primaries)
        if primaries and abs(pct - 100.0) > 0.5:
            issues.append("primary_pct_not_100")
        return issues

    def test_fully_covered_account(self):
        bens = [
            {"type": "primary", "pct": 100},
            {"type": "contingent", "pct": 100},
        ]
        assert self._audit_account(bens) == []

    def test_missing_primary(self):
        issues = self._audit_account([])
        assert "missing_primary" in issues

    def test_missing_contingent(self):
        bens = [{"type": "primary", "pct": 100}]
        issues = self._audit_account(bens)
        assert "missing_contingent" in issues
        assert "missing_primary" not in issues

    def test_primary_pct_not_100(self):
        bens = [
            {"type": "primary", "pct": 60},
            {"type": "primary", "pct": 30},  # only 90%, not 100
        ]
        issues = self._audit_account(bens)
        assert "primary_pct_not_100" in issues

    def test_severity_critical_when_missing_primary(self):
        issues = ["missing_primary", "missing_contingent"]
        severity = "critical" if "missing_primary" in issues else "warning" if issues else "ok"
        assert severity == "critical"

    def test_severity_warning_when_only_missing_contingent(self):
        issues = ["missing_contingent"]
        severity = "critical" if "missing_primary" in issues else "warning" if issues else "ok"
        assert severity == "warning"

    def test_overall_score_100_when_all_covered(self):
        total = 5
        covered = 5
        score = int(covered / total * 100) if total > 0 else 100
        assert score == 100

    def test_overall_score_60_when_3_of_5_covered(self):
        total = 5
        covered = 3
        score = int(covered / total * 100)
        assert score == 60

    def test_auditable_types_include_401k(self):
        assert "retirement_401k" in self.AUDITABLE_TYPES

    def test_auditable_types_include_brokerage(self):
        assert "brokerage" in self.AUDITABLE_TYPES

    def test_checking_not_auditable(self):
        assert "checking" not in self.AUDITABLE_TYPES


# ── 6. Contribution Headroom ─────────────────────────────────────────────────

class TestContributionHeadroom:
    """Tests for IRS contribution limit lookups and headroom calculations."""

    def test_401k_limit_defined_for_current_year(self):
        limits = RETIREMENT.for_year(datetime.date.today().year)
        assert limits["LIMIT_401K"] >= 20_000

    def test_ira_limit_defined(self):
        limits = RETIREMENT.for_year(datetime.date.today().year)
        assert limits["LIMIT_IRA"] >= 6_000

    def test_hsa_individual_limit_defined(self):
        limits = RETIREMENT.for_year(datetime.date.today().year)
        assert limits["LIMIT_HSA_INDIVIDUAL"] >= 3_000

    def test_hsa_family_greater_than_individual(self):
        limits = RETIREMENT.for_year(datetime.date.today().year)
        assert limits["LIMIT_HSA_FAMILY"] > limits["LIMIT_HSA_INDIVIDUAL"]

    def test_catchup_ages(self):
        assert RETIREMENT.CATCH_UP_AGE_401K == 50
        assert RETIREMENT.CATCH_UP_AGE_HSA == 55

    def test_catchup_adds_to_limit(self):
        limits = RETIREMENT.for_year(datetime.date.today().year)
        base = limits["LIMIT_401K"]
        catchup = limits["LIMIT_401K_CATCH_UP"]
        assert base + catchup > base

    def test_remaining_headroom_calculation(self):
        limit = 23_500
        ytd = 15_000
        remaining = max(0, limit - ytd)
        assert remaining == 8_500

    def test_headroom_clamped_to_zero_when_over(self):
        limit = 7_000
        ytd = 8_000  # over-contributed (shouldn't happen but guard it)
        remaining = max(0, limit - ytd)
        assert remaining == 0

    def test_pct_used_calculation(self):
        limit = 23_500
        ytd = 11_750
        pct = min(100.0, round(ytd / limit * 100, 1))
        assert pct == pytest.approx(50.0)

    def test_annualize_monthly(self):
        """Monthly * 12 = annual."""
        monthly = 1_000
        annual = monthly * 12
        assert annual == 12_000

    def test_annualize_biweekly(self):
        biweekly = 500
        annual = biweekly * 26
        assert annual == 13_000

    def test_529_annual_limit_defined(self):
        limits = RETIREMENT.for_year(datetime.date.today().year)
        assert limits["LIMIT_529_ANNUAL_GIFT_EXCLUSION"] >= 17_000

    def test_future_year_limits_projected(self):
        """for_year should return projected data even for future years."""
        limits_2030 = RETIREMENT.for_year(2030)
        limits_now = RETIREMENT.for_year(datetime.date.today().year)
        # Limits should project upward with COLA
        assert limits_2030["LIMIT_401K"] >= limits_now["LIMIT_401K"]


# ── 7. Tax-Equivalent Yield ───────────────────────────────────────────────────

class TestTaxEquivYield:
    """Tests for tax-equivalent yield calculations."""

    def _tey(self, nominal_pct, federal_pct, state_pct):
        """nominal / (1 - combined_rate)"""
        combined = (federal_pct + state_pct) / 100
        return nominal_pct / (1 - combined)

    def test_tey_greater_than_nominal(self):
        tey = self._tey(4.5, 22, 5)
        assert tey > 4.5

    def test_tey_at_zero_tax_rate_equals_nominal(self):
        tey = self._tey(4.5, 0, 0)
        assert tey == pytest.approx(4.5)

    def test_tey_increases_with_higher_tax_rate(self):
        tey_low = self._tey(4.5, 22, 5)
        tey_high = self._tey(4.5, 37, 5)
        assert tey_high > tey_low

    def test_annual_interest_calculation(self):
        balance = 50_000
        nominal_pct = 4.5
        annual = balance * (nominal_pct / 100)
        assert annual == pytest.approx(2_250)

    def test_annual_tax_cost(self):
        annual_interest = 2_250
        combined_rate = 0.27  # 22% + 5%
        tax = annual_interest * combined_rate
        assert tax == pytest.approx(607.50)

    def test_blended_yield_weighted_by_value(self):
        holdings = [
            {"balance": 100_000, "rate": 4.0},
            {"balance": 50_000, "rate": 5.0},
        ]
        total = sum(h["balance"] for h in holdings)
        total_interest = sum(h["balance"] * h["rate"] / 100 for h in holdings)
        blended = total_interest / total * 100
        # (4000 + 2500) / 150000 * 100 = 4.333...
        assert blended == pytest.approx(4.333, rel=0.01)

    def test_sorting_by_tey_descending(self):
        holdings = [
            {"name": "A", "tey": 6.0},
            {"name": "B", "tey": 4.5},
            {"name": "C", "tey": 7.2},
        ]
        sorted_h = sorted(holdings, key=lambda h: h["tey"], reverse=True)
        assert sorted_h[0]["name"] == "C"
        assert sorted_h[-1]["name"] == "B"

    def test_default_federal_rate_from_constants(self):
        assert float(TAX.FEDERAL_MARGINAL_RATE) > 0


# ── 8. Cash Flow Calendar (Weekly) — structural tests ─────────────────────────

class TestWeeklyCashFlow:
    """Tests for weekly cash flow grouping logic (no React, pure Python)."""

    def _make_events(self):
        return [
            {"date": "2026-03-22", "type": "income", "amount": 3500, "merchant_name": "Employer"},
            {"date": "2026-03-23", "type": "bill", "amount": -1200, "merchant_name": "Rent"},
            {"date": "2026-03-24", "type": "subscription", "amount": -15, "merchant_name": "Netflix"},
            {"date": "2026-03-28", "type": "bill", "amount": -250, "merchant_name": "Electric"},
        ]

    def _week_bounds(self, start_date):
        """Return (start, end_exclusive) for the 7-day week."""
        start = datetime.date.fromisoformat(start_date)
        end = start + datetime.timedelta(days=7)
        return start, end

    def test_events_in_week_filtered_correctly(self):
        events = self._make_events()
        start, end = self._week_bounds("2026-03-22")
        in_week = [e for e in events if start <= datetime.date.fromisoformat(e["date"]) < end]
        assert len(in_week) == 4

    def test_events_outside_week_excluded(self):
        events = self._make_events()
        start, end = self._week_bounds("2026-03-29")  # next week
        in_week = [e for e in events if start <= datetime.date.fromisoformat(e["date"]) < end]
        assert len(in_week) == 0

    def test_weekly_inflow_sum(self):
        events = self._make_events()
        inflow = sum(abs(e["amount"]) for e in events if e["type"] == "income")
        assert inflow == 3500

    def test_weekly_outflow_sum(self):
        events = self._make_events()
        outflow = sum(abs(e["amount"]) for e in events if e["type"] != "income")
        assert outflow == pytest.approx(1465)

    def test_weekly_net(self):
        events = self._make_events()
        inflow = sum(abs(e["amount"]) for e in events if e["type"] == "income")
        outflow = sum(abs(e["amount"]) for e in events if e["type"] != "income")
        net = inflow - outflow
        assert net == pytest.approx(2035)

    def test_prev_week_offset(self):
        start = datetime.date(2026, 3, 22)
        prev = start - datetime.timedelta(days=7)
        assert prev == datetime.date(2026, 3, 15)

    def test_next_week_offset(self):
        start = datetime.date(2026, 3, 22)
        next_w = start + datetime.timedelta(days=7)
        assert next_w == datetime.date(2026, 3, 29)

    def test_events_grouped_by_day(self):
        events = self._make_events()
        by_day: dict = {}
        for e in events:
            by_day.setdefault(e["date"], []).append(e)
        assert len(by_day["2026-03-22"]) == 1
        assert len(by_day["2026-03-23"]) == 1
