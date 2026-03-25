"""Unit tests for StateTaxService."""
from decimal import Decimal
import pytest
from app.services.state_tax_service import StateTaxService


def test_no_income_state_florida():
    """Florida has no income tax — should return 0."""
    tax = StateTaxService.calculate_state_tax("FL", Decimal("100000"))
    assert tax == Decimal("0")


def test_no_income_state_texas():
    """Texas has no income tax — should return 0."""
    tax = StateTaxService.calculate_state_tax("TX", Decimal("100000"))
    assert tax == Decimal("0")


def test_california_has_tax():
    """California has income tax — result should be > 0."""
    tax = StateTaxService.calculate_state_tax("CA", Decimal("100000"))
    assert tax > 0


def test_compare_states_sorted():
    """compare_retirement_states should return results sorted by total_tax ascending."""
    results = StateTaxService.compare_retirement_states(
        states=["CA", "TX", "FL", "NY"],
        projected_income=Decimal("60000"),
        projected_ss=Decimal("20000"),
        projected_pension=Decimal("10000"),
    )
    taxes = [r["total_tax"] for r in results]
    assert taxes == sorted(taxes)


def test_unknown_state_returns_zero():
    """Unknown state code should return 0."""
    tax = StateTaxService.calculate_state_tax("ZZ", Decimal("100000"))
    assert tax == Decimal("0")
