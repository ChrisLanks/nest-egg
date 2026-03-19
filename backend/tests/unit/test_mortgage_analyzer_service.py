"""Unit tests for MortgageAnalyzerService."""

from datetime import date

import pytest

from app.services.mortgage_analyzer_service import (
    MortgageAnalyzerService,
    _amortize,
    _equity_milestones,
    _iso_month,
    _monthly_payment,
)

# ── _monthly_payment ───────────────────────────────────────────────────────


class TestMonthlyPayment:
    def test_standard_30yr(self):
        pmt = _monthly_payment(300_000, 0.065, 360)
        assert 1800 < pmt < 2000  # ~$1,896

    def test_zero_rate_divides_evenly(self):
        pmt = _monthly_payment(120_000, 0.0, 120)
        assert pmt == 1000.0

    def test_zero_principal_returns_zero(self):
        assert _monthly_payment(0, 0.065, 360) == 0.0

    def test_zero_months_returns_zero(self):
        assert _monthly_payment(300_000, 0.065, 0) == 0.0

    def test_short_term_higher_payment(self):
        pmt_30yr = _monthly_payment(300_000, 0.065, 360)
        pmt_15yr = _monthly_payment(300_000, 0.065, 180)
        assert pmt_15yr > pmt_30yr


# ── _amortize ──────────────────────────────────────────────────────────────


class TestAmortize:
    def test_balance_reaches_zero(self):
        pmt = _monthly_payment(200_000, 0.06, 240)
        rows = _amortize(200_000, 0.06, pmt)
        assert rows[-1].balance == 0.0

    def test_row_count_near_term(self):
        pmt = _monthly_payment(200_000, 0.06, 240)
        rows = _amortize(200_000, 0.06, pmt)
        # Rounding can cause payoff to be off by ±1 month
        assert abs(len(rows) - 240) <= 1

    def test_month_numbers_sequential(self):
        pmt = _monthly_payment(100_000, 0.05, 60)
        rows = _amortize(100_000, 0.05, pmt)
        for i, row in enumerate(rows, 1):
            assert row.month == i

    def test_cumulative_interest_increases(self):
        pmt = _monthly_payment(200_000, 0.06, 240)
        rows = _amortize(200_000, 0.06, pmt)
        for i in range(1, len(rows)):
            assert rows[i].cumulative_interest >= rows[i - 1].cumulative_interest

    def test_extra_payment_shortens_term(self):
        pmt = _monthly_payment(300_000, 0.065, 360)
        rows_std = _amortize(300_000, 0.065, pmt, extra_monthly=0)
        rows_extra = _amortize(300_000, 0.065, pmt, extra_monthly=500)
        assert len(rows_extra) < len(rows_std)

    def test_extra_payment_reduces_total_interest(self):
        pmt = _monthly_payment(300_000, 0.065, 360)
        rows_std = _amortize(300_000, 0.065, pmt, extra_monthly=0)
        rows_extra = _amortize(300_000, 0.065, pmt, extra_monthly=500)
        assert rows_extra[-1].cumulative_interest < rows_std[-1].cumulative_interest


# ── _iso_month ─────────────────────────────────────────────────────────────


class TestIsoMonth:
    def test_no_offset(self):
        assert _iso_month(date(2025, 1, 1), 0) == "2025-01"

    def test_month_rollover(self):
        assert _iso_month(date(2025, 11, 1), 3) == "2026-02"

    def test_year_rollover(self):
        assert _iso_month(date(2025, 1, 1), 12) == "2026-01"

    def test_large_offset(self):
        result = _iso_month(date(2025, 1, 1), 360)
        assert result == "2055-01"


# ── _equity_milestones ─────────────────────────────────────────────────────


class TestEquityMilestones:
    def test_milestones_returned(self):
        pmt = _monthly_payment(200_000, 0.06, 360)
        rows = _amortize(200_000, 0.06, pmt)
        milestones = _equity_milestones(200_000, rows, date(2025, 1, 1))
        assert len(milestones) == 4  # 20%, 50%, 80%, 100%

    def test_milestone_keys(self):
        pmt = _monthly_payment(200_000, 0.06, 360)
        rows = _amortize(200_000, 0.06, pmt)
        milestones = _equity_milestones(200_000, rows, date(2025, 1, 1))
        for m in milestones:
            assert "equity_pct" in m
            assert "month" in m
            assert "date" in m
            assert "balance_at_milestone" in m

    def test_milestones_ordered(self):
        pmt = _monthly_payment(200_000, 0.06, 360)
        rows = _amortize(200_000, 0.06, pmt)
        milestones = _equity_milestones(200_000, rows, date(2025, 1, 1))
        months = [m["month"] for m in milestones]
        assert months == sorted(months)

    def test_20pct_milestone_before_50pct(self):
        pmt = _monthly_payment(200_000, 0.06, 360)
        rows = _amortize(200_000, 0.06, pmt)
        milestones = _equity_milestones(200_000, rows, date(2025, 1, 1))
        m20 = next(m for m in milestones if m["equity_pct"] == 20)
        m50 = next(m for m in milestones if m["equity_pct"] == 50)
        assert m20["month"] < m50["month"]


# ── MortgageAnalyzerService.analyze ───────────────────────────────────────


class TestMortgageAnalyzerService:
    def test_basic_analysis(self):
        result = MortgageAnalyzerService.analyze(
            current_balance=350_000,
            annual_rate=0.065,
            remaining_months=300,
        )
        assert result.loan_balance == 350_000.0
        assert result.interest_rate == pytest.approx(0.065, abs=1e-6)
        assert result.monthly_payment > 0
        assert result.remaining_months == 300
        assert len(result.amortization) > 0
        assert result.summary.total_interest > 0

    def test_no_refinance_without_rate(self):
        result = MortgageAnalyzerService.analyze(
            current_balance=300_000,
            annual_rate=0.06,
            remaining_months=240,
        )
        assert result.refinance is None

    def test_refinance_lower_rate_savings(self):
        result = MortgageAnalyzerService.analyze(
            current_balance=300_000,
            annual_rate=0.065,
            remaining_months=360,
            refinance_rate=0.055,
            closing_costs=5_000,
        )
        assert result.refinance is not None
        assert result.refinance.monthly_savings > 0
        assert result.refinance.break_even_months > 0

    def test_refinance_higher_rate_negative_savings(self):
        result = MortgageAnalyzerService.analyze(
            current_balance=300_000,
            annual_rate=0.04,
            remaining_months=360,
            refinance_rate=0.07,
        )
        assert result.refinance is not None
        assert result.refinance.monthly_savings < 0

    def test_extra_payment_impact(self):
        result = MortgageAnalyzerService.analyze(
            current_balance=300_000,
            annual_rate=0.065,
            remaining_months=360,
            extra_monthly_payment=500,
        )
        assert result.extra_payment is not None
        assert result.extra_payment.months_saved > 0
        assert result.extra_payment.interest_saved > 0

    def test_no_extra_payment_impact_when_zero(self):
        result = MortgageAnalyzerService.analyze(
            current_balance=300_000,
            annual_rate=0.065,
            remaining_months=360,
            extra_monthly_payment=0,
        )
        assert result.extra_payment is None

    def test_equity_milestones_present(self):
        result = MortgageAnalyzerService.analyze(
            current_balance=200_000,
            annual_rate=0.06,
            remaining_months=360,
        )
        assert len(result.equity_milestones) == 4
        pcts = {m["equity_pct"] for m in result.equity_milestones}
        assert pcts == {20, 50, 80, 100}

    def test_summary_payoff_months_matches_amortization(self):
        result = MortgageAnalyzerService.analyze(
            current_balance=200_000,
            annual_rate=0.06,
            remaining_months=240,
        )
        assert result.summary.payoff_months == len(result.amortization)

    def test_today_override(self):
        result = MortgageAnalyzerService.analyze(
            current_balance=200_000,
            annual_rate=0.06,
            remaining_months=240,
            today=date(2025, 1, 1),
        )
        # Payoff date should be ~2025 + 20 years
        assert result.summary.payoff_date.startswith("2045")

    def test_zero_balance_guard(self):
        result = MortgageAnalyzerService.analyze(
            current_balance=0,
            annual_rate=0.065,
            remaining_months=360,
        )
        assert result.amortization == []

    def test_loan_balance_attribute(self):
        result = MortgageAnalyzerService.analyze(
            current_balance=300_000,
            annual_rate=0.065,
            remaining_months=300,
        )
        assert hasattr(result, "loan_balance")
        assert result.loan_balance == 300_000.0
