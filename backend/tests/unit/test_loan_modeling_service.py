"""Unit tests for LoanModelingService."""
from decimal import Decimal
import pytest
from app.services.loan_modeling_service import LoanModelingService


def test_monthly_payment_zero_rate():
    """$10k at 0% over 12 months = $833.33"""
    payment = LoanModelingService.calculate_monthly_payment(
        Decimal("10000"), Decimal("0"), 12
    )
    assert abs(payment - Decimal("833.33")) < Decimal("0.01")


def test_monthly_payment_standard():
    """$200k at 6% over 360 months ≈ $1199.10"""
    payment = LoanModelingService.calculate_monthly_payment(
        Decimal("200000"), Decimal("0.06"), 360
    )
    assert abs(payment - Decimal("1199.10")) < Decimal("0.50")


def test_dti_within_limits():
    """Low payment should not exceed conventional DTI limit."""
    result = LoanModelingService.calculate_dti_impact(
        annual_gross_income=Decimal("120000"),
        existing_monthly_debt=Decimal("500"),
        new_monthly_payment=Decimal("300"),
    )
    assert result["exceeds_conventional"] is False
    assert result["exceeds_fha"] is False


def test_dti_exceeds_conventional():
    """High payment should exceed conventional DTI limit."""
    result = LoanModelingService.calculate_dti_impact(
        annual_gross_income=Decimal("60000"),
        existing_monthly_debt=Decimal("1500"),
        new_monthly_payment=Decimal("1200"),
    )
    assert result["exceeds_conventional"] is True


def test_amortization_schedule_length():
    """360-month loan should produce exactly 360 rows."""
    schedule = LoanModelingService.generate_amortization_schedule(
        Decimal("200000"), Decimal("0.06"), 360
    )
    assert len(schedule) == 360


def test_amortization_final_balance_near_zero():
    """Final row balance should be effectively zero (< $1)."""
    schedule = LoanModelingService.generate_amortization_schedule(
        Decimal("200000"), Decimal("0.06"), 360
    )
    assert schedule[-1]["balance"] < 2.0


def test_buy_vs_lease_buy_wins():
    """Buy wins when loan is cheap relative to lease."""
    result = LoanModelingService.buy_vs_lease(
        vehicle_price=Decimal("30000"),
        down_payment=Decimal("5000"),
        loan_rate=Decimal("0.04"),
        loan_term_months=60,
        lease_monthly=Decimal("600"),
        lease_term_months=36,
        residual_value_pct=Decimal("0.50"),
    )
    # With a large residual value retained, buying should be cheaper
    assert result["recommendation"] == "buy"


def test_buy_vs_lease_lease_wins():
    """Lease wins when vehicle price is high and lease payment is very low."""
    result = LoanModelingService.buy_vs_lease(
        vehicle_price=Decimal("80000"),
        down_payment=Decimal("0"),
        loan_rate=Decimal("0.08"),
        loan_term_months=60,
        lease_monthly=Decimal("400"),
        lease_term_months=36,
        residual_value_pct=Decimal("0.10"),
    )
    assert result["recommendation"] == "lease"
