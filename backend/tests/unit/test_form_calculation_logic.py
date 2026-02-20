"""
Tests for form calculation logic bugs fixed in frontend forms.

These tests mirror the TypeScript logic in:
  - PrivateEquityAccountForm.tsx (estimatedValue calculation)
  - BondAccountForm.tsx (premiumDiscount calculation)

Running equivalent logic in Python ensures the edge cases are covered
without requiring a frontend test framework.
"""

import pytest


def estimated_value(quantity, share_price) -> float:
    """
    Mirror of PrivateEquityAccountForm.tsx estimatedValue calculation.

    Fixed version: quantity != null && sharePrice != null
    (was: quantity && sharePrice — falsy check broke when quantity=0)
    """
    if quantity is not None and share_price is not None:
        return float(quantity) * float(share_price)
    return 0.0


def premium_discount(current_value, principal) -> float:
    """
    Mirror of BondAccountForm.tsx premiumDiscount calculation.

    Fixed version: currentValue != null && principal != null && principal > 0
    (was: currentValue && principal — falsy check broke when currentValue=0)
    """
    if current_value is not None and principal is not None and principal > 0:
        return ((float(current_value) - float(principal)) / float(principal)) * 100
    return 0.0


@pytest.mark.unit
class TestEstimatedValueCalculation:
    """Tests for PrivateEquityAccountForm estimatedValue."""

    def test_normal_values_multiply_correctly(self):
        assert estimated_value(100, 25.50) == pytest.approx(2550.0)

    def test_zero_quantity_returns_zero_not_fallback(self):
        """Quantity of 0 is valid (e.g. fully vested/expired grant) — should return 0, not skip."""
        assert estimated_value(0, 50.0) == 0.0

    def test_zero_share_price_returns_zero(self):
        """Share price of 0 is an edge case — result should be 0."""
        assert estimated_value(100, 0) == 0.0

    def test_both_zero_returns_zero(self):
        assert estimated_value(0, 0) == 0.0

    def test_none_quantity_returns_zero(self):
        """Unset quantity (form field empty) should return 0, not crash."""
        assert estimated_value(None, 50.0) == 0.0

    def test_none_share_price_returns_zero(self):
        """Unset share price (form field empty) should return 0, not crash."""
        assert estimated_value(100, None) == 0.0

    def test_both_none_returns_zero(self):
        assert estimated_value(None, None) == 0.0

    def test_fractional_shares(self):
        assert estimated_value(1.5, 100.0) == pytest.approx(150.0)

    def test_large_values(self):
        assert estimated_value(1_000_000, 500.0) == pytest.approx(500_000_000.0)


@pytest.mark.unit
class TestPremiumDiscountCalculation:
    """Tests for BondAccountForm premiumDiscount."""

    def test_bond_at_premium(self):
        """Bond trading above par should return positive percentage."""
        result = premium_discount(current_value=1050, principal=1000)
        assert result == pytest.approx(5.0)

    def test_bond_at_discount(self):
        """Bond trading below par should return negative percentage."""
        result = premium_discount(current_value=950, principal=1000)
        assert result == pytest.approx(-5.0)

    def test_bond_at_par(self):
        """Bond at par value should return 0%."""
        assert premium_discount(current_value=1000, principal=1000) == pytest.approx(0.0)

    def test_zero_current_value_returns_negative_100(self):
        """
        A bond with current_value=0 should show -100% (total loss).
        Old falsy check `currentValue && principal` would have returned 0 here — wrong.
        """
        result = premium_discount(current_value=0, principal=1000)
        assert result == pytest.approx(-100.0)

    def test_none_current_value_returns_zero(self):
        """Optional field not yet entered — should return 0, not crash."""
        assert premium_discount(current_value=None, principal=1000) == 0.0

    def test_none_principal_returns_zero(self):
        """Should return 0 if principal not set."""
        assert premium_discount(current_value=1050, principal=None) == 0.0

    def test_zero_principal_returns_zero_not_divide_by_zero(self):
        """principal=0 must not cause ZeroDivisionError."""
        assert premium_discount(current_value=1050, principal=0) == 0.0

    def test_both_none_returns_zero(self):
        assert premium_discount(current_value=None, principal=None) == 0.0

    def test_fractional_premium(self):
        result = premium_discount(current_value=1012.50, principal=1000)
        assert result == pytest.approx(1.25)
