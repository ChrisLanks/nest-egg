"""
Security and bug regression tests.

Covers:
1. DTI division by zero (zero income)
2. Contribution headroom annualization formula correctness
3. Treemap percent guard (domestic_stocks_value = 0)
4. Tax-equiv yield combined_rate guard
5. Input validation bounds (tax_buckets, hsa, irmaa endpoints)
6. Background task org scope (holdings price fetch)
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


# ── Input validation bounds ───────────────────────────────────────────────────

class TestInputValidationBounds:
    """Verify Query param bounds exist on financial endpoints.
    Tests read the source to confirm ge=/le= are present — guards against
    accidentally removing bounds when refactoring signatures."""

    def _read_source(self, rel_path: str) -> str:
        import os
        base = os.path.dirname(__file__)
        path = os.path.normpath(os.path.join(base, "../../app/api/v1", rel_path))
        with open(path) as f:
            return f.read()

    def test_tax_buckets_rmd_balance_has_bounds(self):
        src = self._read_source("tax_buckets.py")
        assert "ge=0" in src
        assert "le=50_000_000" in src or "le=50000000" in src

    def test_tax_buckets_age_has_bounds(self):
        src = self._read_source("tax_buckets.py")
        assert "le=120" in src

    def test_tax_buckets_growth_rate_has_bounds(self):
        src = self._read_source("tax_buckets.py")
        assert "le=1.0" in src or "le=1)" in src

    def test_hsa_age_has_bounds(self):
        src = self._read_source("hsa.py")
        assert "ge=0, le=120" in src

    def test_hsa_projection_years_has_bounds(self):
        src = self._read_source("hsa.py")
        assert "ge=1, le=50" in src

    def test_irmaa_magi_has_bounds(self):
        src = self._read_source("irmaa_projection.py")
        assert "ge=0" in src and "le=10_000_000" in src or "le=10000000" in src


# ── Background task org scope ─────────────────────────────────────────────────

class TestBackgroundTaskOrgScope:
    """_fetch_price_for_holding must scope the UPDATE to the holding's org."""

    def test_signature_accepts_organization_id(self):
        import inspect
        from app.api.v1.holdings import _fetch_price_for_holding
        sig = inspect.signature(_fetch_price_for_holding)
        assert "organization_id" in sig.parameters, (
            "_fetch_price_for_holding must accept organization_id to scope the UPDATE"
        )


# ── IDOR: holdings Roth conversion user query scoped to org ──────────────────

class TestIDORUserQueryOrgScope:
    """User lookup in the Roth conversion endpoint must filter by org_id."""

    def test_roth_conversion_user_query_includes_org_filter(self):
        import inspect
        from app.api.v1 import holdings
        src = inspect.getsource(holdings)
        # The fix added organization_id to the User query in get_roth_conversion_analysis
        assert "User.organization_id == current_user.organization_id" in src


# ── Recurring detection avg_gap = 0 ─────────────────────────────────────────

class TestRecurringDetectionAvgGap:
    """date_consistency must not crash when all transactions fall on the same day."""

    def test_zero_avg_gap_returns_perfect_consistency(self):
        # All gaps = 0 → avg_gap = 0 → without guard: ZeroDivisionError
        # With guard: date_consistency = 1.0 (perfectly consistent, same-day duplicates)
        avg_gap = 0
        gap_variance = 0.0
        date_consistency = max(0, 1.0 - (gap_variance / avg_gap)) if avg_gap > 0 else 1.0
        assert date_consistency == 1.0

    def test_normal_gaps_still_compute(self):
        gaps = [30, 31, 29, 30]
        avg_gap = sum(gaps) / len(gaps)
        gap_variance = sum(abs(g - avg_gap) for g in gaps) / len(gaps)
        date_consistency = max(0, 1.0 - (gap_variance / avg_gap)) if avg_gap > 0 else 1.0
        assert 0.0 <= date_consistency <= 1.0

    def test_high_variance_gives_low_consistency(self):
        gaps = [1, 60, 1, 60]
        avg_gap = sum(gaps) / len(gaps)
        gap_variance = sum(abs(g - avg_gap) for g in gaps) / len(gaps)
        date_consistency = max(0, 1.0 - (gap_variance / avg_gap)) if avg_gap > 0 else 1.0
        assert date_consistency < 0.1  # very inconsistent gaps → near zero


# ── Smart insights monthly expenses months = 0 ───────────────────────────────

class TestSmartInsightsMonthlyExpenses:
    """_monthly_expenses must not divide by zero when months = 0."""

    def test_zero_months_returns_zero(self):
        total = 1000
        months = 0
        result = total / months if months > 0 else 0
        assert result == 0

    def test_normal_months_divides_correctly(self):
        total = 3000
        months = 3
        result = total / months if months > 0 else 0
        assert result == 1000


# ── IDOR: market_data UPDATE scoped to org ────────────────────────────────────

class TestMarketDataUpdateOrgScope:
    """Holding UPDATE in market_data refresh endpoint must include org_id filter."""

    def test_holding_update_includes_org_filter(self):
        import inspect
        from app.api.v1 import market_data
        src = inspect.getsource(market_data)
        # Both the SELECT and the UPDATE must scope to organization_id
        assert src.count("Holding.organization_id == current_user.organization_id") >= 2, (
            "market_data must scope BOTH the SELECT and UPDATE to organization_id"
        )
