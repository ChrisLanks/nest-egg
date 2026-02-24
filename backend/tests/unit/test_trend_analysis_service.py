"""Unit tests for TrendAnalysisService — CAGR, growth rate calculations."""

import pytest

from app.services.trend_analysis_service import TrendAnalysisService


svc = TrendAnalysisService


class TestCalculateGrowthRate:
    def test_positive_growth(self):
        result = svc.calculate_growth_rate(100.0, 115.0)
        assert result == pytest.approx(15.0)

    def test_negative_growth(self):
        result = svc.calculate_growth_rate(100.0, 80.0)
        assert result == pytest.approx(-20.0)

    def test_zero_base_returns_none(self):
        assert svc.calculate_growth_rate(0.0, 100.0) is None

    def test_no_change(self):
        result = svc.calculate_growth_rate(100.0, 100.0)
        assert result == pytest.approx(0.0)


class TestCalculateCAGR:
    def test_known_cagr(self):
        """$100 → $200 over 5 years ≈ 14.87% CAGR."""
        result = svc.calculate_cagr(100.0, 200.0, 5)
        assert result == pytest.approx(14.87, abs=0.1)

    def test_zero_starting_value(self):
        assert svc.calculate_cagr(0.0, 200.0, 5) is None

    def test_zero_years(self):
        assert svc.calculate_cagr(100.0, 200.0, 0) is None

    def test_negative_years(self):
        assert svc.calculate_cagr(100.0, 200.0, -1) is None

    def test_negative_ratio(self):
        """Ending value negative → ratio < 0 → CAGR undefined."""
        assert svc.calculate_cagr(100.0, -50.0, 3) is None

    def test_no_growth(self):
        result = svc.calculate_cagr(100.0, 100.0, 5)
        assert result == pytest.approx(0.0)

    def test_decline(self):
        """$200 → $100 over 3 years → negative CAGR."""
        result = svc.calculate_cagr(200.0, 100.0, 3)
        assert result is not None
        assert result < 0

    def test_one_year_equals_simple_growth(self):
        """Over 1 year, CAGR = simple growth rate."""
        result = svc.calculate_cagr(100.0, 120.0, 1)
        assert result == pytest.approx(20.0)
