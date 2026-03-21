"""Tests for the Savings Rate Service pure logic."""

import pytest

from app.services.savings_rate_service import MonthlySavingsRate, SavingsRateSummary

# ---------------------------------------------------------------------------
# _avg_rate logic (extracted inline from service for testing)
# ---------------------------------------------------------------------------


def _avg_rate(window: list[MonthlySavingsRate]) -> float | None:
    total_income = sum(m.income for m in window)
    total_savings = sum(m.savings for m in window)
    if total_income <= 0:
        return None
    return round(total_savings / total_income, 4)


def _make_month(month: str, income: float, expenses: float) -> MonthlySavingsRate:
    savings = income - expenses
    rate = (savings / income) if income > 0 else 0.0
    return MonthlySavingsRate(
        month=month,
        income=income,
        expenses=expenses,
        savings=savings,
        savings_rate=round(rate, 4),
    )


class TestAvgRate:
    def test_simple_50_pct(self):
        months = [_make_month("2024-01", 1000.0, 500.0)]
        assert _avg_rate(months) == 0.5

    def test_zero_income_returns_none(self):
        months = [_make_month("2024-01", 0.0, 0.0)]
        assert _avg_rate(months) is None

    def test_negative_savings(self):
        months = [_make_month("2024-01", 1000.0, 1200.0)]
        result = _avg_rate(months)
        assert result is not None
        assert result < 0

    def test_multi_month_weighted(self):
        # Month 1: income=1000 savings=200 (20%)
        # Month 2: income=2000 savings=1600 (80%)
        # Weighted: (200+1600)/(1000+2000) = 1800/3000 = 0.60
        months = [
            _make_month("2024-01", 1000.0, 800.0),
            _make_month("2024-02", 2000.0, 400.0),
        ]
        assert _avg_rate(months) == pytest.approx(0.6, abs=1e-4)

    def test_trailing_window_uses_last_3(self):
        all_months = [
            _make_month("2024-01", 1000.0, 1000.0),  # 0% savings
            _make_month("2024-02", 1000.0, 1000.0),
            _make_month("2024-03", 1000.0, 800.0),  # 20%
            _make_month("2024-04", 1000.0, 800.0),
            _make_month("2024-05", 1000.0, 800.0),
        ]
        trailing_3 = all_months[-3:]
        result = _avg_rate(trailing_3)
        assert result == pytest.approx(0.2, abs=1e-4)


class TestMonthFormatting:
    def test_month_zero_padded(self):
        m = _make_month("2024-03", 500.0, 250.0)
        assert m.month == "2024-03"

    def test_savings_rate_capped_at_1_when_no_expenses(self):
        m = _make_month("2024-01", 1000.0, 0.0)
        assert m.savings_rate == 1.0

    def test_savings_negative_when_overspending(self):
        m = _make_month("2024-01", 500.0, 700.0)
        assert m.savings < 0
        assert m.savings_rate < 0


class TestSavingsRateSummaryEmpty:
    def test_empty_returns_none_rates(self):
        summary = SavingsRateSummary(
            current_month_rate=None,
            trailing_3m_rate=None,
            trailing_12m_rate=None,
            monthly_trend=[],
            avg_monthly_savings=0.0,
            best_month=None,
            worst_month=None,
        )
        assert summary.current_month_rate is None
        assert summary.monthly_trend == []
