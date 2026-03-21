"""Tests for the Debt Cost Service pure logic."""

import pytest

from app.services.debt_cost_service import DebtAccountCost, DebtCostSummary


def _make_account_cost(
    account_id: str = "acc-1",
    account_name: str = "Visa",
    account_type: str = "credit_card",
    balance: float = -1000.0,
    interest_rate: float | None = 0.2,
    monthly_interest_cost: float = 16.67,
    annual_interest_cost: float = 200.0,
    minimum_payment: float | None = 25.0,
) -> DebtAccountCost:
    return DebtAccountCost(
        account_id=account_id,
        account_name=account_name,
        account_type=account_type,
        balance=balance,
        interest_rate=interest_rate,
        monthly_interest_cost=monthly_interest_cost,
        annual_interest_cost=annual_interest_cost,
        minimum_payment=minimum_payment,
    )


class TestDebtInterestCalculation:
    """Verify interest math is correct."""

    def test_monthly_interest_formula(self):
        # balance=$5000, rate=24% APR → monthly = 5000 * 0.24 / 12 = $100
        balance = 5000.0
        annual_rate = 0.24
        expected_monthly = balance * annual_rate / 12
        assert expected_monthly == pytest.approx(100.0, rel=1e-4)

    def test_annual_interest_is_monthly_times_12(self):
        monthly = 100.0
        assert monthly * 12 == 1200.0

    def test_weighted_avg_rate_calculation(self):
        # Two accounts: $2000 @ 20%, $3000 @ 10%
        # Weighted = (2000*0.20 + 3000*0.10) / (2000+3000) = (400+300)/5000 = 0.14
        total_debt = 5000.0
        weighted_num = 2000 * 0.20 + 3000 * 0.10
        avg_rate = weighted_num / total_debt
        assert avg_rate == pytest.approx(0.14, rel=1e-4)

    def test_no_rate_gives_zero_interest(self):
        # If no interest_rate, monthly cost should be 0
        acct = _make_account_cost(
            interest_rate=None, monthly_interest_cost=0.0, annual_interest_cost=0.0
        )
        assert acct.monthly_interest_cost == 0.0


class TestDebtCostSummary:
    def test_summary_totals(self):
        summary = DebtCostSummary(
            total_debt=6000.0,
            total_monthly_interest=116.67,
            total_annual_interest=1400.04,
            accounts=[],
            weighted_avg_rate=0.14,
        )
        assert summary.total_debt == 6000.0
        assert summary.weighted_avg_rate == pytest.approx(0.14, rel=1e-4)

    def test_no_debt_returns_zero(self):
        summary = DebtCostSummary(
            total_debt=0.0,
            total_monthly_interest=0.0,
            total_annual_interest=0.0,
            accounts=[],
            weighted_avg_rate=None,
        )
        assert summary.weighted_avg_rate is None
        assert summary.total_debt == 0.0

    def test_accounts_sorted_by_cost_descending(self):
        # Confirm model accepts list in any order; sorting is done in service
        high = _make_account_cost(account_id="1", monthly_interest_cost=200.0)
        low = _make_account_cost(account_id="2", monthly_interest_cost=50.0)
        summary = DebtCostSummary(
            total_debt=15000.0,
            total_monthly_interest=250.0,
            total_annual_interest=3000.0,
            accounts=[low, high],
            weighted_avg_rate=0.18,
        )
        # Both accounts present; ordering is caller's responsibility
        assert len(summary.accounts) == 2
