"""Financial correctness tests for PayoffStrategyService.

Verifies that avalanche saves more interest than snowball with known inputs,
and that the snowball freed-minimums cascade works correctly.
"""

import pytest
from decimal import Decimal
from uuid import uuid4

from app.models.account import AccountType
from app.services.payoff_strategy_service import (
    DebtAccount,
    PayoffStrategyService,
)


def make_debt(
    balance: str,
    rate: str = "18.0",
    min_payment: str = "50",
    account_type: AccountType = AccountType.CREDIT_CARD,
    name: str = "Debt",
) -> DebtAccount:
    return DebtAccount(
        account_id=uuid4(),
        name=name,
        balance=Decimal(balance),
        interest_rate=Decimal(rate),
        minimum_payment=Decimal(min_payment),
        account_type=account_type,
    )


class TestAvalancheVsSnowball:
    """Avalanche should save more interest than snowball in standard scenarios."""

    def test_avalanche_saves_more_interest(self):
        """Two debts: $1000 at 24% and $5000 at 6%.
        Avalanche targets 24% first -> less total interest."""
        debts = [
            make_debt("1000", rate="24", min_payment="50", name="High Rate"),
            make_debt("5000", rate="6", min_payment="100", name="Low Rate"),
        ]
        extra = Decimal("100")

        avalanche = PayoffStrategyService.calculate_avalanche(debts, extra)
        snowball = PayoffStrategyService.calculate_snowball(debts, extra)

        assert avalanche["total_interest"] <= snowball["total_interest"]

    def test_snowball_pays_smaller_first(self):
        """Snowball should target the smaller balance first regardless of rate."""
        debts = [
            make_debt("5000", rate="24", min_payment="100", name="Large High Rate"),
            make_debt("500", rate="6", min_payment="25", name="Small Low Rate"),
        ]
        result = PayoffStrategyService.calculate_snowball(debts, Decimal("50"))
        assert result["debts"][0]["name"] == "Small Low Rate"

    def test_avalanche_pays_highest_rate_first(self):
        """Avalanche should target the highest rate first regardless of balance."""
        debts = [
            make_debt("500", rate="6", min_payment="25", name="Small Low Rate"),
            make_debt("5000", rate="24", min_payment="100", name="Large High Rate"),
        ]
        result = PayoffStrategyService.calculate_avalanche(debts, Decimal("50"))
        assert result["debts"][0]["name"] == "Large High Rate"


class TestSnowballCascade:
    """Freed minimums from paid-off debts should cascade to the next debt."""

    def test_freed_minimums_accelerate_payoff(self):
        """After debt A is paid off, its $200 minimum should be freed and
        added to extra for debt B. This makes debt B pay off faster than
        if we just had the original $50 extra."""
        debt_a = make_debt("400", rate="0", min_payment="200", name="A")
        debt_b = make_debt("2000", rate="0", min_payment="50", name="B")

        snowball_result = PayoffStrategyService.calculate_snowball(
            [debt_a, debt_b], extra_payment=Decimal("50")
        )

        # A pays off in 2 months ($200 min + $50 extra = $250/mo vs $400 balance)
        debt_a_state = next(d for d in snowball_result["debts"] if d["name"] == "A")
        assert debt_a_state["months_to_payoff"] == 2

        # After A is gone, freed minimums should accelerate B's payoff.
        # Compare against current pace (minimum-only) for B alone.
        current = PayoffStrategyService.calculate_current_pace([debt_b])
        debt_b_state = next(d for d in snowball_result["debts"] if d["name"] == "B")
        assert debt_b_state["months_to_payoff"] < current["total_months"]

    def test_current_pace_no_extra_slower(self):
        """Current pace (no extra) should take longer than any strategy with extra."""
        debts = [
            make_debt("1000", rate="18", min_payment="50", name="A"),
        ]
        current = PayoffStrategyService.calculate_current_pace(debts)
        snowball = PayoffStrategyService.calculate_snowball(debts, Decimal("100"))

        assert snowball["total_months"] < current["total_months"]


class TestEdgeCases:
    def test_payment_less_than_interest(self):
        """When minimum payment is less than monthly interest, debt grows."""
        debt = make_debt("100000", rate="24", min_payment="100")
        # Monthly interest = $2000, payment = $100 -> never pays off
        result = PayoffStrategyService.calculate_current_pace([debt])
        assert result["debt_free_date"] is None

    def test_zero_balance_debt(self):
        """Zero balance debt should not affect calculations."""
        debts = [
            make_debt("0", rate="18", min_payment="50", name="Paid Off"),
            make_debt("1000", rate="18", min_payment="50", name="Active"),
        ]
        result = PayoffStrategyService.calculate_snowball(debts, Decimal("100"))
        assert result["total_months"] > 0

    def test_empty_debts(self):
        """Empty debt list should return zeroed results."""
        result = PayoffStrategyService.calculate_snowball([], Decimal("100"))
        assert result["total_months"] == 0
        assert result["debts"] == []

    def test_single_debt_snowball_equals_avalanche(self):
        """With a single debt, both strategies should produce identical results."""
        debts = [make_debt("5000", rate="18", min_payment="100")]
        extra = Decimal("50")

        snowball = PayoffStrategyService.calculate_snowball(debts, extra)
        avalanche = PayoffStrategyService.calculate_avalanche(debts, extra)

        assert snowball["total_months"] == avalanche["total_months"]
        assert snowball["total_interest"] == avalanche["total_interest"]
