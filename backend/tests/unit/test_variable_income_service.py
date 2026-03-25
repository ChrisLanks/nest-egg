"""Unit tests for VariableIncomeService."""
from decimal import Decimal
import pytest
from app.services.variable_income_service import VariableIncomeService


def test_smooth_income_average():
    """[10000, 20000] should produce average of 15000."""
    result = VariableIncomeService.calculate_smoothed_income(
        [Decimal("10000"), Decimal("20000")]
    )
    assert result["average"] == 15000.0


def test_smooth_income_volatility():
    """High variance list should have high volatility_pct."""
    result = VariableIncomeService.calculate_smoothed_income(
        [Decimal("1000"), Decimal("50000"), Decimal("1000"), Decimal("50000")]
    )
    assert result["volatility_pct"] > 50.0


def test_empty_income_returns_zeros():
    """Empty list should return all zeros."""
    result = VariableIncomeService.calculate_smoothed_income([])
    assert result["average"] == 0.0
    assert result["minimum"] == 0.0
    assert result["maximum"] == 0.0
    assert result["volatility_pct"] == 0.0
    assert result["floor"] == 0.0


def test_se_tax_calculation():
    """$100k income → SE tax = 15.3% = $15,300."""
    result = VariableIncomeService.calculate_se_tax(Decimal("100000"))
    assert abs(result["se_tax"] - 15300.0) < 1.0


def test_quarterly_safe_harbor_high_income():
    """Income > $150k should use the 110% safe harbor rule."""
    result = VariableIncomeService.estimate_quarterly_taxes(
        ytd_income=Decimal("50000"),
        prior_year_tax=Decimal("40000"),
        annual_income_estimate=Decimal("200000"),
        effective_rate=Decimal("0.22"),
        quarter=1,
    )
    # 110% of prior year tax = 44000, quarterly = 11000
    expected_safe_harbor = 40000 * 1.10 / 4
    assert abs(result["safe_harbor_payment"] - expected_safe_harbor) < 1.0


def test_quarterly_due_months():
    """Quarter 1 should have due_month = 4."""
    result = VariableIncomeService.estimate_quarterly_taxes(
        ytd_income=Decimal("10000"),
        prior_year_tax=Decimal("5000"),
        annual_income_estimate=Decimal("50000"),
        effective_rate=Decimal("0.22"),
        quarter=1,
    )
    assert result["due_month"] == 4
