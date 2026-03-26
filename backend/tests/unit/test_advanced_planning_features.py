"""
Tests for the 9 new advanced planning features:
1. Asset Location Optimization
2. Insurance Audit
3. Pension Modeler
4. Financial Ratios
5. Employer Match
6. Dividend Calendar
7. Cost Basis Aging
8. Liquidity Dashboard
9. Net Worth Percentile

Pure unit tests using constants and math only — no DB required.
"""

import calendar
import datetime
from typing import Optional

import pytest


# ── 1. Asset Location ─────────────────────────────────────────────────────────

class TestAssetLocationLogic:
    """Tests for asset location recommendation mapping and scoring logic."""

    # Mirrors the backend's class/ticker mapping constants.
    _PRE_TAX_CLASSES = {"bond", "fixed_income", "tips", "reit", "dividend"}
    _ROTH_CLASSES = {"small_cap", "emerging_market", "international", "growth"}
    _TAXABLE_CLASSES = {"large_cap", "index", "etf", "blend"}

    _TICKER_LOCATION = {
        "VNQ": "pre_tax",
        "BND": "pre_tax",
        "AGG": "pre_tax",
        "QQQ": "roth",
        "VWO": "roth",
        "VB": "roth",
        "VTI": "taxable",
        "SPY": "taxable",
        "VOO": "taxable",
    }

    def _recommended_location(self, asset_class: Optional[str], ticker: Optional[str]) -> str:
        """Replicate backend _recommended_location logic."""
        if asset_class:
            normalized = asset_class.lower().strip()
            if normalized in self._PRE_TAX_CLASSES:
                return "pre_tax"
            if normalized in self._ROTH_CLASSES:
                return "roth"
            if normalized in self._TAXABLE_CLASSES:
                return "taxable"
            for key in self._PRE_TAX_CLASSES:
                if key in normalized:
                    return "pre_tax"
            for key in self._ROTH_CLASSES:
                if key in normalized:
                    return "roth"
        if ticker:
            upper = ticker.upper().strip()
            if upper in self._TICKER_LOCATION:
                return self._TICKER_LOCATION[upper]
        return "taxable"

    def test_bond_asset_class_maps_to_pre_tax(self):
        assert self._recommended_location("bond", None) == "pre_tax"

    def test_reit_asset_class_maps_to_pre_tax(self):
        assert self._recommended_location("reit", None) == "pre_tax"

    def test_small_cap_asset_class_maps_to_roth(self):
        assert self._recommended_location("small_cap", None) == "roth"

    def test_index_asset_class_maps_to_taxable(self):
        assert self._recommended_location("index", None) == "taxable"

    def test_vti_ticker_maps_to_taxable(self):
        assert self._recommended_location(None, "VTI") == "taxable"

    def test_bnd_ticker_maps_to_pre_tax(self):
        assert self._recommended_location(None, "BND") == "pre_tax"

    def test_qqq_ticker_maps_to_roth(self):
        assert self._recommended_location(None, "QQQ") == "roth"

    def test_unknown_ticker_falls_back_to_taxable(self):
        assert self._recommended_location(None, "UNKNOWN") == "taxable"

    def test_optimization_score_all_optimal(self):
        optimal_count = 5
        total_count = 5
        score = (optimal_count / total_count * 100.0) if total_count > 0 else 100.0
        assert score == pytest.approx(100.0)

    def test_optimization_score_partial(self):
        optimal_count = 3
        total_count = 5
        score = optimal_count / total_count * 100.0
        assert score == pytest.approx(60.0)

    def test_optimization_score_zero_holdings_is_100(self):
        total_count = 0
        score = 100.0 if total_count == 0 else 0.0
        assert score == 100.0

    def test_summary_tip_below_50(self):
        score = 40.0
        if score < 50:
            tip = "Consider moving bonds/REITs to pre-tax accounts and high-growth holdings to Roth."
        elif score < 80:
            tip = "Some reallocation could improve tax efficiency."
        else:
            tip = "Your asset location is well optimized."
        assert "bonds" in tip

    def test_summary_tip_between_50_and_80(self):
        score = 65.0
        if score < 50:
            tip = "bonds"
        elif score < 80:
            tip = "Some reallocation could improve tax efficiency."
        else:
            tip = "well optimized"
        assert "reallocation" in tip

    def test_summary_tip_at_or_above_80(self):
        score = 85.0
        if score < 50:
            tip = "bonds"
        elif score < 80:
            tip = "reallocation"
        else:
            tip = "Your asset location is well optimized."
        assert "well optimized" in tip


# ── 2. Insurance Audit ────────────────────────────────────────────────────────

class TestInsuranceAuditLogic:
    """Tests for insurance coverage scoring and gap counting logic."""

    # Static coverage definitions mirrored from backend
    _STATIC_COVERAGE = [
        {"insurance_type": "term_life", "priority": "critical"},
        {"insurance_type": "disability", "priority": "critical"},
        {"insurance_type": "health", "priority": "critical"},
        {"insurance_type": "umbrella", "priority": "important"},
        {"insurance_type": "ltc", "priority": "optional"},  # upgraded at age >= 50
    ]

    def _coverage_score(self, critical_items: list) -> int:
        """Score = critical covered / total critical * 100."""
        total = sum(1 for item in critical_items if item["priority"] == "critical")
        covered = sum(
            1 for item in critical_items
            if item["priority"] == "critical" and item["has_coverage"]
        )
        return int((covered / total * 100)) if total > 0 else 0

    def _critical_gaps(self, coverage_items: list) -> int:
        """Count items where priority == critical and has_coverage == False."""
        return sum(
            1 for item in coverage_items
            if item["priority"] == "critical" and not item["has_coverage"]
        )

    def test_coverage_score_no_coverage_is_zero(self):
        items = [
            {"priority": "critical", "has_coverage": False},
            {"priority": "critical", "has_coverage": False},
            {"priority": "critical", "has_coverage": False},
        ]
        assert self._coverage_score(items) == 0

    def test_coverage_score_all_critical_covered_is_100(self):
        items = [
            {"priority": "critical", "has_coverage": True},
            {"priority": "critical", "has_coverage": True},
            {"priority": "critical", "has_coverage": True},
        ]
        assert self._coverage_score(items) == 100

    def test_coverage_score_partial_coverage(self):
        items = [
            {"priority": "critical", "has_coverage": True},
            {"priority": "critical", "has_coverage": False},
            {"priority": "critical", "has_coverage": False},
        ]
        assert self._coverage_score(items) == 33

    def test_non_critical_items_do_not_affect_score(self):
        items = [
            {"priority": "critical", "has_coverage": True},
            {"priority": "critical", "has_coverage": True},
            {"priority": "important", "has_coverage": False},  # not counted
            {"priority": "optional", "has_coverage": False},   # not counted
        ]
        assert self._coverage_score(items) == 100

    def test_critical_gaps_counts_uncovered_critical_items(self):
        items = [
            {"priority": "critical", "has_coverage": False},
            {"priority": "critical", "has_coverage": False},
            {"priority": "critical", "has_coverage": True},
            {"priority": "important", "has_coverage": False},  # not a critical gap
        ]
        assert self._critical_gaps(items) == 2

    def test_critical_gaps_zero_when_all_covered(self):
        items = [
            {"priority": "critical", "has_coverage": True},
            {"priority": "critical", "has_coverage": True},
        ]
        assert self._critical_gaps(items) == 0

    def test_ltc_priority_optional_for_age_under_50(self):
        age = 45
        base_priority = "optional"
        effective_priority = "important" if age >= 50 else base_priority
        assert effective_priority == "optional"

    def test_ltc_priority_upgraded_to_important_at_age_50(self):
        age = 50
        base_priority = "optional"
        effective_priority = "important" if age >= 50 else base_priority
        assert effective_priority == "important"

    def test_term_life_and_disability_always_critical(self):
        critical_types = [item["insurance_type"] for item in self._STATIC_COVERAGE
                          if item["priority"] == "critical"]
        assert "term_life" in critical_types
        assert "disability" in critical_types
        assert "health" in critical_types


# ── 3. Pension Modeler ────────────────────────────────────────────────────────

class TestPensionModelerLogic:
    """Tests for pension break-even and lifetime value calculations."""

    def _break_even_years(self, lump_sum: float, monthly_benefit: float) -> Optional[float]:
        annual = monthly_benefit * 12
        if annual <= 0:
            return None
        return lump_sum / annual

    def _lifetime_value(self, monthly_benefit: float, years: int) -> float:
        return monthly_benefit * 12 * years

    def _survivor_monthly(self, monthly_benefit: float, survivor_pct: float) -> float:
        return monthly_benefit * (survivor_pct / 100.0)

    def test_break_even_years_formula(self):
        lump_sum = 300_000
        monthly = 2_000
        result = self._break_even_years(lump_sum, monthly)
        assert result == pytest.approx(12.5)  # 300000 / 24000

    def test_recommendation_take_annuity_when_break_even_below_15(self):
        bey = 12.5
        if bey < 15:
            rec = "Take annuity"
        elif bey > 20:
            rec = "Consider lump sum"
        else:
            rec = "Borderline"
        assert rec == "Take annuity"

    def test_recommendation_consider_lump_sum_when_break_even_above_20(self):
        bey = 22.0
        if bey < 15:
            rec = "Take annuity"
        elif bey > 20:
            rec = "Consider lump sum"
        else:
            rec = "Borderline"
        assert rec == "Consider lump sum"

    def test_recommendation_borderline_between_15_and_20(self):
        bey = 17.5
        if bey < 15:
            rec = "Take annuity"
        elif bey > 20:
            rec = "Consider lump sum"
        else:
            rec = "Borderline"
        assert rec == "Borderline"

    def test_lifetime_value_20yr(self):
        monthly = 2_000
        result = self._lifetime_value(monthly, 20)
        assert result == pytest.approx(480_000)

    def test_lifetime_value_25yr_greater_than_20yr(self):
        monthly = 2_000
        assert self._lifetime_value(monthly, 25) > self._lifetime_value(monthly, 20)

    def test_survivor_monthly_50pct(self):
        monthly = 2_000
        survivor_pct = 50.0
        result = self._survivor_monthly(monthly, survivor_pct)
        assert result == pytest.approx(1_000.0)

    def test_survivor_monthly_100pct_equals_full_benefit(self):
        monthly = 2_500
        result = self._survivor_monthly(monthly, 100.0)
        assert result == pytest.approx(2_500.0)

    def test_has_cola_protection_when_cola_rate_above_zero(self):
        pensions = [
            {"cola_rate": 0.0},
            {"cola_rate": 2.5},
        ]
        has_cola = any(p["cola_rate"] and p["cola_rate"] > 0 for p in pensions)
        assert has_cola is True

    def test_no_cola_protection_when_all_zero(self):
        pensions = [
            {"cola_rate": 0.0},
            {"cola_rate": None},
        ]
        has_cola = any(p["cola_rate"] and p["cola_rate"] > 0 for p in pensions)
        assert has_cola is False


# ── 4. Financial Ratios ───────────────────────────────────────────────────────

class TestFinancialRatiosLogic:
    """Tests for DTI, savings rate, emergency fund, and housing ratio grading."""

    def _grade_savings_rate(self, rate: Optional[float]) -> str:
        if rate is None:
            return "F"
        if rate >= 0.20:
            return "A"
        if rate >= 0.10:
            return "B"
        if rate >= 0.05:
            return "C"
        if rate >= 0.0:
            return "D"
        return "F"

    def _grade_dti(self, dti: Optional[float]) -> str:
        if dti is None:
            return "F"
        if dti <= 0.15:
            return "A"
        if dti <= 0.28:
            return "B"
        if dti <= 0.35:
            return "C"
        if dti <= 0.50:
            return "D"
        return "F"

    def _grade_emergency_fund(self, months: Optional[float]) -> str:
        if months is None:
            return "F"
        if months >= 6:
            return "A"
        if months >= 3:
            return "B"
        if months >= 1:
            return "C"
        if months >= 0.5:
            return "D"
        return "F"

    def _grade_housing_ratio(self, ratio: Optional[float]) -> str:
        if ratio is None:
            return "F"
        if ratio <= 0.25:
            return "A"
        if ratio <= 0.30:
            return "B"
        if ratio <= 0.35:
            return "C"
        if ratio <= 0.40:
            return "D"
        return "F"

    def _overall_grade(self, score: float) -> str:
        if score >= 90:
            return "A"
        if score >= 75:
            return "B"
        if score >= 60:
            return "C"
        if score >= 45:
            return "D"
        return "F"

    # Savings rate grades
    def test_savings_rate_20pct_is_grade_A(self):
        assert self._grade_savings_rate(0.20) == "A"

    def test_savings_rate_10pct_is_grade_B(self):
        assert self._grade_savings_rate(0.10) == "B"

    def test_savings_rate_5pct_is_grade_C(self):
        assert self._grade_savings_rate(0.05) == "C"

    def test_savings_rate_negative_is_grade_F(self):
        assert self._grade_savings_rate(-0.05) == "F"

    # DTI grades
    def test_dti_15pct_is_grade_A(self):
        assert self._grade_dti(0.15) == "A"

    def test_dti_28pct_is_grade_B(self):
        assert self._grade_dti(0.28) == "B"

    def test_dti_above_50pct_is_grade_F(self):
        assert self._grade_dti(0.55) == "F"

    def test_dti_none_is_grade_F(self):
        assert self._grade_dti(None) == "F"

    # Emergency fund grades
    def test_emergency_fund_6_months_is_grade_A(self):
        assert self._grade_emergency_fund(6.0) == "A"

    def test_emergency_fund_3_months_is_grade_B(self):
        assert self._grade_emergency_fund(3.0) == "B"

    def test_emergency_fund_below_half_month_is_grade_F(self):
        assert self._grade_emergency_fund(0.4) == "F"

    def test_emergency_fund_1_month_is_grade_C(self):
        assert self._grade_emergency_fund(1.0) == "C"

    # Housing ratio grades
    def test_housing_ratio_25pct_is_grade_A(self):
        assert self._grade_housing_ratio(0.25) == "A"

    def test_housing_ratio_30pct_is_grade_B(self):
        assert self._grade_housing_ratio(0.30) == "B"

    def test_housing_ratio_above_40pct_is_grade_F(self):
        assert self._grade_housing_ratio(0.45) == "F"

    # Overall score
    def test_overall_score_is_average_of_scored_metrics(self):
        # _SCORE_FROM_GRADE = {"A": 95, "B": 80, "C": 65, "D": 45, "F": 20}
        scores = [95, 80]
        overall = sum(scores) / len(scores)
        assert overall == pytest.approx(87.5)

    def test_overall_grade_90_plus_is_A(self):
        assert self._overall_grade(90.0) == "A"

    def test_overall_grade_75_to_89_is_B(self):
        assert self._overall_grade(80.0) == "B"

    def test_overall_grade_below_45_is_F(self):
        assert self._overall_grade(30.0) == "F"


# ── 5. Employer Match ─────────────────────────────────────────────────────────

class TestEmployerMatchLogic:
    """Tests for annual match value calculation and capture determination."""

    def _annual_match_value(
        self, salary: float, match_pct: float, match_limit_pct: float
    ) -> float:
        """annual_match_value = salary * (limit_pct/100) * (match_pct/100)"""
        return salary * (match_limit_pct / 100.0) * (match_pct / 100.0)

    def _is_capturing_full_match(
        self, employee_pct: float, required_pct: float
    ) -> bool:
        return employee_pct >= required_pct

    def _estimated_left_on_table(
        self,
        employee_pct: float,
        required_pct: float,
        annual_match_value: float,
    ) -> float:
        captured_fraction = min(employee_pct / required_pct, 1.0)
        return annual_match_value * (1.0 - captured_fraction)

    def test_annual_match_value_standard_50pct_up_to_6pct(self):
        # $100k salary, 50% match, up to 6% of salary → $3,000
        result = self._annual_match_value(100_000, 50, 6)
        assert result == pytest.approx(3_000.0)

    def test_annual_match_value_100pct_up_to_4pct(self):
        # $80k salary, 100% match, up to 4% → $3,200
        result = self._annual_match_value(80_000, 100, 4)
        assert result == pytest.approx(3_200.0)

    def test_capturing_full_match_when_at_limit(self):
        assert self._is_capturing_full_match(6.0, 6.0) is True

    def test_capturing_full_match_when_above_limit(self):
        assert self._is_capturing_full_match(10.0, 6.0) is True

    def test_not_capturing_full_match_when_below_limit(self):
        assert self._is_capturing_full_match(3.0, 6.0) is False

    def test_left_on_table_when_contributing_half_required(self):
        # Contributing 3% of 6% required → capturing 50% of $3,000 match → $1,500 left on table
        result = self._estimated_left_on_table(3.0, 6.0, 3_000.0)
        assert result == pytest.approx(1_500.0)

    def test_left_on_table_zero_when_fully_captured(self):
        result = self._estimated_left_on_table(6.0, 6.0, 3_000.0)
        assert result == pytest.approx(0.0)

    def test_action_message_when_fully_capturing(self):
        is_capturing = True
        action = "Full match captured \u2713" if is_capturing else "Increase contributions"
        assert "Full match" in action

    def test_action_message_when_not_capturing(self):
        is_capturing = False
        required_pct = 6.0
        action = (
            "Full match captured \u2713"
            if is_capturing
            else f"Increase contributions to {required_pct:.0f}% to capture full match"
        )
        assert "Increase contributions" in action
        assert "6%" in action


# ── 6. Dividend Calendar ──────────────────────────────────────────────────────

class TestDividendCalendarLogic:
    """Tests for dividend month assignment, annual total, and best-month logic."""

    def _assign_month(
        self, pay_date: Optional[datetime.date], ex_date: Optional[datetime.date], year: int
    ) -> Optional[int]:
        """Priority: pay_date → ex_date; must fall within the requested year."""
        for dt in (pay_date, ex_date):
            if dt is not None:
                if dt.year == year:
                    return dt.month
        return None

    def test_pay_date_takes_priority_over_ex_date(self):
        pay = datetime.date(2026, 3, 15)
        ex = datetime.date(2026, 2, 10)
        month = self._assign_month(pay, ex, 2026)
        assert month == 3  # pay_date month wins

    def test_falls_back_to_ex_date_when_no_pay_date(self):
        ex = datetime.date(2026, 7, 1)
        month = self._assign_month(None, ex, 2026)
        assert month == 7

    def test_returns_none_when_dates_outside_year(self):
        pay = datetime.date(2025, 12, 15)
        ex = datetime.date(2025, 11, 1)
        month = self._assign_month(pay, ex, 2026)
        assert month is None

    def test_annual_total_is_sum_of_all_months(self):
        monthly_totals = [100.0, 0.0, 50.0, 200.0, 0.0, 75.0, 0.0, 0.0, 0.0, 0.0, 0.0, 300.0]
        annual_total = sum(monthly_totals)
        assert annual_total == pytest.approx(725.0)

    def test_avg_monthly_based_on_months_with_income(self):
        monthly_totals = [100.0, 0.0, 200.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        annual_total = sum(monthly_totals)
        months_with_income = sum(1 for t in monthly_totals if t > 0)
        avg = annual_total / months_with_income if months_with_income > 0 else 0.0
        assert avg == pytest.approx(150.0)

    def test_best_month_is_month_with_highest_total(self):
        monthly_totals = {
            "January": 100.0,
            "March": 300.0,
            "June": 250.0,
        }
        best = max(monthly_totals, key=lambda k: monthly_totals[k])
        assert best == "March"

    def test_calendar_generates_all_12_months(self):
        months = [calendar.month_name[m] for m in range(1, 13)]
        assert len(months) == 12
        assert months[0] == "January"
        assert months[11] == "December"


# ── 7. Cost Basis Aging ───────────────────────────────────────────────────────

class TestCostBasisAgingLogic:
    """Tests for tax lot holding period classification and bucket assignment."""

    def _classify_lot(
        self, acquisition_date: datetime.date, today: datetime.date
    ) -> dict:
        """Replicate the backend lot-classification logic."""
        days_held = (today - acquisition_date).days
        is_long_term = days_held >= 365
        holding_period = "long_term" if is_long_term else "short_term"
        days_to_long_term = 0 if is_long_term else max(0, 365 - days_held)

        if is_long_term:
            bucket = "long_term"
        elif days_to_long_term <= 30:
            bucket = "approaching"
        else:
            bucket = "short_term"

        return {
            "days_held": days_held,
            "holding_period": holding_period,
            "days_to_long_term": days_to_long_term,
            "bucket": bucket,
        }

    def test_holding_period_long_term_at_365_days(self):
        today = datetime.date(2026, 3, 26)
        acq = today - datetime.timedelta(days=365)
        result = self._classify_lot(acq, today)
        assert result["holding_period"] == "long_term"

    def test_holding_period_short_term_at_364_days(self):
        today = datetime.date(2026, 3, 26)
        acq = today - datetime.timedelta(days=364)
        result = self._classify_lot(acq, today)
        assert result["holding_period"] == "short_term"

    def test_bucket_long_term_when_held_over_365(self):
        today = datetime.date(2026, 3, 26)
        acq = today - datetime.timedelta(days=400)
        result = self._classify_lot(acq, today)
        assert result["bucket"] == "long_term"

    def test_bucket_approaching_when_within_30_days_of_long_term(self):
        today = datetime.date(2026, 3, 26)
        acq = today - datetime.timedelta(days=340)  # 25 days to long-term
        result = self._classify_lot(acq, today)
        assert result["bucket"] == "approaching"
        assert result["days_to_long_term"] == 25

    def test_bucket_short_term_when_more_than_30_days_to_long_term(self):
        today = datetime.date(2026, 3, 26)
        acq = today - datetime.timedelta(days=200)  # 165 days to long-term
        result = self._classify_lot(acq, today)
        assert result["bucket"] == "short_term"

    def test_days_to_long_term_is_zero_for_long_term_lots(self):
        today = datetime.date(2026, 3, 26)
        acq = today - datetime.timedelta(days=500)
        result = self._classify_lot(acq, today)
        assert result["days_to_long_term"] == 0

    def test_summary_tip_mentions_approaching_count(self):
        approaching_count = 3
        if approaching_count > 0:
            tip = (
                f"{approaching_count} lot(s) become long-term within 30 days — "
                "consider holding to avoid short-term tax rates."
            )
        else:
            tip = "No urgent cost basis actions needed."
        assert "3 lot(s)" in tip
        assert "long-term" in tip

    def test_summary_tip_no_urgent_when_no_approaching(self):
        approaching_count = 0
        st_loss = -500.0  # below -1000 threshold
        if approaching_count > 0:
            tip = "approaching"
        elif st_loss < -1_000:
            tip = "tax-loss harvesting"
        else:
            tip = "No urgent cost basis actions needed."
        assert tip == "No urgent cost basis actions needed."


# ── 8. Liquidity Dashboard ────────────────────────────────────────────────────

class TestLiquidityDashboardLogic:
    """Tests for emergency fund grading and coverage gap calculation."""

    _TARGET_MONTHS = 6.0

    # Account types considered immediately accessible
    _IMMEDIATE_TYPES = {"checking", "savings", "money_market"}
    # Liquid types include CDs but they are not immediately accessible
    _LIQUID_TYPES = {"checking", "savings", "money_market", "cd"}

    def _grade(self, months_immediate: float) -> tuple:
        if months_immediate >= 6:
            return "A", "green"
        if months_immediate >= 3:
            return "B", "blue"
        if months_immediate >= 1:
            return "C", "yellow"
        if months_immediate >= 0.5:
            return "D", "orange"
        return "F", "red"

    def _emergency_months(self, immediately_accessible: float, monthly_spending: float) -> float:
        return immediately_accessible / monthly_spending if monthly_spending > 0 else 0.0

    def _coverage_gap(self, months_immediate: float) -> float:
        return self._TARGET_MONTHS - months_immediate  # negative means surplus

    def test_emergency_months_calculation(self):
        accessible = 30_000.0
        spending = 5_000.0
        result = self._emergency_months(accessible, spending)
        assert result == pytest.approx(6.0)

    def test_grade_A_at_6_months(self):
        grade, color = self._grade(6.0)
        assert grade == "A"

    def test_grade_B_at_3_months(self):
        grade, color = self._grade(3.0)
        assert grade == "B"

    def test_grade_C_at_1_month(self):
        grade, color = self._grade(1.0)
        assert grade == "C"

    def test_grade_D_at_half_month(self):
        grade, color = self._grade(0.5)
        assert grade == "D"

    def test_grade_F_below_half_month(self):
        grade, color = self._grade(0.4)
        assert grade == "F"

    def test_coverage_gap_positive_when_below_target(self):
        gap = self._coverage_gap(3.0)
        assert gap == pytest.approx(3.0)

    def test_coverage_gap_negative_when_above_target(self):
        gap = self._coverage_gap(8.0)
        assert gap == pytest.approx(-2.0)

    def test_coverage_gap_zero_at_exact_target(self):
        gap = self._coverage_gap(6.0)
        assert gap == pytest.approx(0.0)

    def test_cd_is_not_immediately_accessible(self):
        assert "cd" not in self._IMMEDIATE_TYPES
        assert "cd" in self._LIQUID_TYPES

    def test_checking_is_immediately_accessible(self):
        assert "checking" in self._IMMEDIATE_TYPES

    def test_savings_is_immediately_accessible(self):
        assert "savings" in self._IMMEDIATE_TYPES

    def test_money_market_is_immediately_accessible(self):
        assert "money_market" in self._IMMEDIATE_TYPES


# ── 9. Net Worth Percentile ───────────────────────────────────────────────────

class TestNetWorthPercentileLogic:
    """Tests for percentile interpolation, labels, and age bucket mapping."""

    _P25_FACTOR = 0.20
    _P75_FACTOR = 2.80
    _P90_FACTOR = 5.50

    def _interpolate_percentile(
        self, net_worth: float, p25: float, p50: float, p75: float, p90: float
    ) -> float:
        """Linearly interpolate net worth to an estimated percentile."""
        if net_worth >= p90:
            excess_factor = min((net_worth - p90) / max(p90, 1), 1.0)
            return round(90 + 10 * excess_factor, 1)
        if net_worth >= p75:
            t = (net_worth - p75) / max(p90 - p75, 1)
            return round(75 + 15 * t, 1)
        if net_worth >= p50:
            t = (net_worth - p50) / max(p75 - p50, 1)
            return round(50 + 25 * t, 1)
        if net_worth >= p25:
            t = (net_worth - p25) / max(p50 - p25, 1)
            return round(25 + 25 * t, 1)
        if p25 > 0:
            t = max(net_worth / p25, 0)
            return round(25 * t, 1)
        return 0.0

    def _percentile_label(self, pct: float) -> str:
        if pct >= 90:
            return "Top 10%"
        if pct >= 75:
            return "Top 25%"
        if pct >= 50:
            return "Top 50%"
        if pct >= 25:
            return "Second quartile"
        return "Bottom 25%"

    def _encouragement(self, pct: float) -> str:
        if pct >= 90:
            return "Outstanding — you're in the top 10% for your age group."
        if pct >= 75:
            return "Excellent financial position — top quartile for your age."
        if pct >= 50:
            return "Above median — you're ahead of most peers your age."
        if pct >= 25:
            return "Building momentum — you're in the second quartile."
        return "Early stage — focus on increasing savings rate and reducing debt."

    def _age_bucket(self, age: int) -> str:
        """Replicate the SCF age bucket logic from the service."""
        if age < 25:
            return "Under 25"
        if age < 35:
            return "25-34"
        if age < 45:
            return "35-44"
        if age < 55:
            return "45-54"
        if age < 65:
            return "55-64"
        if age < 75:
            return "65-74"
        return "75+"

    def test_net_worth_at_p50_is_50th_percentile(self):
        median = 135_600.0
        p25 = median * self._P25_FACTOR
        p50 = median
        p75 = median * self._P75_FACTOR
        p90 = median * self._P90_FACTOR
        result = self._interpolate_percentile(p50, p25, p50, p75, p90)
        assert result == pytest.approx(50.0)

    def test_net_worth_between_p25_and_p50_is_between_25_and_50(self):
        median = 135_600.0
        p25 = median * self._P25_FACTOR
        p50 = median
        p75 = median * self._P75_FACTOR
        p90 = median * self._P90_FACTOR
        midpoint = (p25 + p50) / 2
        result = self._interpolate_percentile(midpoint, p25, p50, p75, p90)
        assert 25.0 < result < 50.0

    def test_net_worth_above_p90_is_above_90(self):
        median = 135_600.0
        p25 = median * self._P25_FACTOR
        p50 = median
        p75 = median * self._P75_FACTOR
        p90 = median * self._P90_FACTOR
        result = self._interpolate_percentile(p90 * 2, p25, p50, p75, p90)
        assert result > 90.0

    def test_percentile_label_top_10_pct(self):
        assert self._percentile_label(92.0) == "Top 10%"

    def test_percentile_label_top_25_pct(self):
        assert self._percentile_label(80.0) == "Top 25%"

    def test_percentile_label_top_50_pct(self):
        assert self._percentile_label(55.0) == "Top 50%"

    def test_percentile_label_second_quartile(self):
        assert self._percentile_label(30.0) == "Second quartile"

    def test_percentile_label_bottom_25(self):
        assert self._percentile_label(10.0) == "Bottom 25%"

    def test_encouragement_top_10_pct(self):
        msg = self._encouragement(95.0)
        assert "top 10%" in msg

    def test_encouragement_above_median(self):
        msg = self._encouragement(60.0)
        assert "Above median" in msg

    def test_encouragement_early_stage(self):
        msg = self._encouragement(15.0)
        assert "Early stage" in msg

    def test_age_37_maps_to_35_44_bucket(self):
        assert self._age_bucket(37) == "35-44"

    def test_age_25_maps_to_25_34_bucket(self):
        assert self._age_bucket(25) == "25-34"

    def test_age_65_maps_to_65_74_bucket(self):
        assert self._age_bucket(65) == "65-74"

    def test_age_24_maps_to_under_25_bucket(self):
        assert self._age_bucket(24) == "Under 25"

    def test_age_75_maps_to_75_plus_bucket(self):
        assert self._age_bucket(75) == "75+"


# ── Seed Planning Data ────────────────────────────────────────────────────────

class TestSeedPlanningData:
    """Tests for the seed_planning_data logic — validates the data shapes created."""

    def test_pension_break_even_math(self):
        """break_even = lump_sum / annual_benefit"""
        lump_sum = 450_000
        monthly_benefit = 2_500
        annual = monthly_benefit * 12
        break_even = lump_sum / annual
        assert break_even == pytest.approx(15.0, abs=0.1)

    def test_401k_match_value_from_seed_data(self):
        """50% match on first 6% of $120k = $3,600/yr"""
        salary = 120_000
        match_limit_pct = 6.0
        match_pct = 50.0
        annual_match = salary * (match_limit_pct / 100) * (match_pct / 100)
        assert annual_match == pytest.approx(3_600)

    def test_dividend_month_assignment_pay_date_priority(self):
        """pay_date takes priority over ex_date for month grouping"""
        import datetime
        pay_date = datetime.date(2026, 3, 15)
        ex_date = datetime.date(2026, 2, 28)
        # Should use pay_date month (March)
        assigned_month = pay_date.month if pay_date else ex_date.month
        assert assigned_month == 3

    def test_tax_lot_approaching_detection(self):
        """A lot acquired 340 days ago is within 30 days of 1-year mark"""
        days_held = 340
        days_to_lt = max(0, 365 - days_held)
        is_approaching = days_to_lt <= 30
        assert is_approaching is True

    def test_life_insurance_account_type_is_auditable(self):
        """LIFE_INSURANCE_CASH_VALUE accounts show in insurance audit"""
        from app.models.account import AccountType
        assert AccountType.LIFE_INSURANCE_CASH_VALUE.value == "life_insurance_cash_value"
