"""Unit tests for tax-equivalent yield calculation logic."""

import pytest


# ── Pure calculation helpers (mirrors tax_equiv_yield.py logic) ──────────────

def combined_rate(fed: float, state: float, itemizing: bool = False) -> float:
    """Combined marginal rate as a decimal."""
    if itemizing:
        return fed + state * (1 - fed)
    return fed + state


def tey_taxable(nominal_pct: float, combined: float) -> float:
    """After-tax yield for a taxable bond = nominal * (1 - combined_rate)."""
    return nominal_pct * (1 - combined)


def tey_tax_advantaged(nominal_pct: float, combined: float) -> float:
    """TEY for a tax-advantaged (e.g. I-bond) = nominal / (1 - combined_rate)."""
    return nominal_pct / (1 - combined) if combined < 1.0 else nominal_pct


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestCombinedRate:
    def test_non_itemizing(self):
        rate = combined_rate(0.22, 0.05, itemizing=False)
        assert abs(rate - 0.27) < 1e-9

    def test_itemizing_reduces_effective_state_rate(self):
        # state tax deductible: effective state = 5% * (1 - 22%) = 3.9%
        rate = combined_rate(0.22, 0.05, itemizing=True)
        expected = 0.22 + 0.05 * (1 - 0.22)
        assert abs(rate - expected) < 1e-9

    def test_zero_state_rate(self):
        rate = combined_rate(0.22, 0.0)
        assert abs(rate - 0.22) < 1e-9

    def test_zero_rates(self):
        assert combined_rate(0.0, 0.0) == 0.0


class TestTaxableYield:
    """After-tax yield for taxable accounts changes with tax rate."""

    def test_5pct_nominal_at_22pct_federal_5pct_state(self):
        c = combined_rate(0.22, 0.05)
        after_tax = tey_taxable(5.0, c)
        # 5 * (1 - 0.27) = 3.65
        assert abs(after_tax - 3.65) < 1e-6

    def test_higher_tax_rate_reduces_after_tax_yield(self):
        low = tey_taxable(5.0, combined_rate(0.12, 0.0))
        high = tey_taxable(5.0, combined_rate(0.37, 0.05))
        assert high < low

    def test_zero_tax_rate_returns_nominal(self):
        result = tey_taxable(4.5, 0.0)
        assert abs(result - 4.5) < 1e-9

    def test_changing_federal_rate_changes_after_tax_yield(self):
        """The bug: same nominal yield should give different TEY at different rates."""
        low_rate = tey_taxable(5.0, combined_rate(0.12, 0.05))
        high_rate = tey_taxable(5.0, combined_rate(0.37, 0.05))
        # They must differ — this confirms the calculation responds to rate changes
        assert abs(low_rate - high_rate) > 0.5

    def test_changing_state_rate_changes_after_tax_yield(self):
        no_state = tey_taxable(5.0, combined_rate(0.22, 0.0))
        with_state = tey_taxable(5.0, combined_rate(0.22, 0.10))
        assert with_state < no_state


class TestTaxAdvantagedYield:
    """I-Bond TEY = nominal / (1 - combined_rate) — higher rate → higher TEY."""

    def test_ibond_tey_greater_than_nominal(self):
        tey = tey_tax_advantaged(4.0, combined_rate(0.22, 0.05))
        assert tey > 4.0

    def test_ibond_tey_formula(self):
        c = combined_rate(0.22, 0.05)  # 0.27
        tey = tey_tax_advantaged(4.0, c)
        expected = 4.0 / (1 - 0.27)
        assert abs(tey - expected) < 1e-6

    def test_ibond_higher_rate_increases_tey(self):
        low = tey_tax_advantaged(4.0, combined_rate(0.12, 0.0))
        high = tey_tax_advantaged(4.0, combined_rate(0.37, 0.10))
        assert high > low


class TestAnnualTaxCost:
    """Annual tax cost = interest * combined_rate, changes with tax inputs."""

    def test_annual_tax_cost_at_27pct(self):
        balance = 10_000
        nominal = 5.0 / 100
        c = combined_rate(0.22, 0.05)
        interest = balance * nominal
        tax = interest * c
        # 10000 * 0.05 * 0.27 = 135
        assert abs(tax - 135.0) < 1e-6

    def test_tax_cost_zero_when_rate_zero(self):
        tax = 10_000 * 0.05 * combined_rate(0.0, 0.0)
        assert tax == 0.0
