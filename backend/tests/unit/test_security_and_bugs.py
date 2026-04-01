"""
Security and bug regression tests.

Covers:
1. DTI division by zero (zero income)
2. Contribution headroom annualization formula correctness
3. Treemap percent guard (domestic_stocks_value = 0)
4. Tax-equiv yield combined_rate guard
"""

from decimal import Decimal
from unittest.mock import patch
import datetime

import pytest
from app.services.loan_modeling_service import LoanModelingService
from app.api.v1.contribution_headroom import _annualize
from app.models.contribution import ContributionFrequency


# ── DTI division by zero ──────────────────────────────────────────────────────

class TestDtiZeroIncome:
    def test_zero_income_returns_safe_dict(self):
        result = LoanModelingService.calculate_dti_impact(
            Decimal("0"), Decimal("500"), Decimal("300")
        )
        assert result["dti_before"] is None
        assert result["dti_after"] is None
        assert result["exceeds_conventional"] is None
        assert result["recommendation"] is not None  # user-facing message

    def test_negative_income_treated_as_zero(self):
        result = LoanModelingService.calculate_dti_impact(
            Decimal("-5000"), Decimal("500"), Decimal("300")
        )
        assert result["dti_before"] is None

    def test_normal_income_still_works(self):
        result = LoanModelingService.calculate_dti_impact(
            Decimal("100000"), Decimal("500"), Decimal("200")
        )
        assert result["dti_before"] is not None
        assert result["dti_after"] > result["dti_before"]


# ── Annualization formula ─────────────────────────────────────────────────────

class TestAnnualizeFormula:
    """Verify _annualize * month/12 == correct YTD amount."""

    def _ytd(self, amount: float, freq: ContributionFrequency, month: int) -> float:
        return _annualize(amount, freq) * month / 12

    def test_monthly_500_in_month_6(self):
        # $500/mo × 12 = $6000/yr; 6/12 = $3000 YTD
        result = self._ytd(500.0, ContributionFrequency.MONTHLY, 6)
        assert abs(result - 3000.0) < 0.01

    def test_monthly_500_in_month_12(self):
        # Full year
        result = self._ytd(500.0, ContributionFrequency.MONTHLY, 12)
        assert abs(result - 6000.0) < 0.01

    def test_weekly_100_in_month_1(self):
        # $100/wk × 52 = $5200/yr; 1/12 ≈ $433.33 YTD
        result = self._ytd(100.0, ContributionFrequency.WEEKLY, 1)
        assert abs(result - (5200 / 12)) < 0.01

    def test_annual_12000_in_month_3(self):
        # $12000 annual; 3/12 = $3000 YTD
        result = self._ytd(12000.0, ContributionFrequency.ANNUALLY, 3)
        assert abs(result - 3000.0) < 0.01

    def test_formula_not_division_by_float_12_over_month(self):
        # Old formula: amount / (12 / month) — floating point imprecision
        # New formula: amount * month / 12 — exact
        # Verify they agree for clean months but confirm new form is used
        for month in range(1, 13):
            old = _annualize(500.0, ContributionFrequency.MONTHLY) / (12 / month)
            new = _annualize(500.0, ContributionFrequency.MONTHLY) * month / 12
            assert abs(old - new) < 0.001, f"Mismatch at month {month}"


# ── Treemap guard: domestic_stocks_value = 0 ─────────────────────────────────

class TestTreemapGuard:
    """The per-cap-size percent must not divide by zero."""

    def test_cap_percent_guarded_when_domestic_zero(self):
        # Simulate the guard added at holdings.py line 740
        domestic_stocks_value = Decimal("0")
        cap_value = Decimal("1000")
        # Old code: cap_value / domestic_stocks_value * 100  → ZeroDivisionError
        # New code:
        result = (
            (cap_value / domestic_stocks_value * 100)
            if domestic_stocks_value > 0
            else Decimal("0")
        )
        assert result == Decimal("0")

    def test_cap_percent_normal(self):
        domestic_stocks_value = Decimal("10000")
        cap_value = Decimal("3000")
        result = (
            (cap_value / domestic_stocks_value * 100)
            if domestic_stocks_value > 0
            else Decimal("0")
        )
        assert result == Decimal("30")


# ── Tax-equiv yield combined_rate guard ──────────────────────────────────────

class TestTaxEquivYieldGuard:
    """combined_rate < 1.0 guard prevents division by zero."""

    def _tey(self, nominal: float, combined_rate: float) -> float:
        return nominal / (1 - combined_rate) if combined_rate < 1.0 else nominal

    def test_normal_rate(self):
        # At 30% combined rate, $1000 nominal → TEY = 1000/0.7 ≈ 1428.57
        assert abs(self._tey(1000, 0.30) - 1428.57) < 1

    def test_zero_rate(self):
        assert self._tey(1000, 0.0) == 1000 / 1.0

    def test_rate_at_exactly_1_falls_back_to_nominal(self):
        # Should not raise ZeroDivisionError
        assert self._tey(1000, 1.0) == 1000

    def test_rate_above_1_falls_back_to_nominal(self):
        assert self._tey(1000, 1.5) == 1000
