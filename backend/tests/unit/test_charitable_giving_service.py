"""Unit tests for CharitableGivingService."""
from decimal import Decimal
import pytest
from app.services.charitable_giving_service import CharitableGivingService


def test_bunching_advantage_positive():
    """Bunching 2 years of large donations should yield a tax advantage."""
    result = CharitableGivingService.calculate_bunching_benefit(
        annual_donation=Decimal("15000"),
        standard_deduction=Decimal("14600"),
        marginal_rate=Decimal("0.22"),
        bunch_years=2,
    )
    assert result["bunching_advantage"] > 0
    assert result["recommended_strategy"] == "bunching"


def test_bunching_no_advantage():
    """Donations well below standard deduction have zero bunching advantage."""
    result = CharitableGivingService.calculate_bunching_benefit(
        annual_donation=Decimal("1000"),
        standard_deduction=Decimal("14600"),
        marginal_rate=Decimal("0.22"),
        bunch_years=2,
    )
    # 2 * 1000 = 2000 still below 14600 standard deduction → no deductible amount either way
    assert result["bunching_advantage"] == 0.0
    assert result["recommended_strategy"] == "annual"


def test_qcd_ineligible_age():
    """Age 65 is below QCD eligible age of 70.5."""
    result = CharitableGivingService.calculate_qcd_benefit(
        ira_rmd_amount=Decimal("10000"),
        qcd_amount=Decimal("5000"),
        marginal_rate=Decimal("0.22"),
        age=65.0,
    )
    assert result["eligible"] is False


def test_qcd_eligible():
    """Age 72 with $10k donation should return tax_avoided > 0."""
    result = CharitableGivingService.calculate_qcd_benefit(
        ira_rmd_amount=Decimal("20000"),
        qcd_amount=Decimal("10000"),
        marginal_rate=Decimal("0.22"),
        age=72.0,
    )
    assert result["eligible"] is True
    assert result["tax_avoided"] > 0


def test_qcd_capped_at_max():
    """QCD amount should be capped at QCD_MAX_ANNUAL (108,000)."""
    result = CharitableGivingService.calculate_qcd_benefit(
        ira_rmd_amount=Decimal("200000"),
        qcd_amount=Decimal("200000"),
        marginal_rate=Decimal("0.37"),
        age=75.0,
    )
    assert result["eligible"] is True
    assert result["qcd_amount"] <= 108_000


def test_appreciated_securities_avoids_gains():
    """Appreciated security donation should report positive capital gains avoided."""
    result = CharitableGivingService.calculate_appreciated_security_benefit(
        fair_market_value=Decimal("50000"),
        cost_basis=Decimal("10000"),
        marginal_rate=Decimal("0.32"),
        ltcg_rate=Decimal("0.15"),
    )
    assert result["capital_gains_tax_avoided"] > 0
    assert result["unrealized_gain"] == 40000.0
    assert result["total_tax_benefit"] > result["deduction_value"]
