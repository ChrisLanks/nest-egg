"""Unit tests for PayoffStrategyService.

Covers:
- _DEBT_ACCOUNT_TYPES is built dynamically from AccountType.is_debt
- account_type is included in debt state dicts returned to callers
- payoff_date is set when a debt is zeroed via minimum payment (not just extra payment)
- payoff_date is set by the safety-net post-loop for any remaining paid-off debts
"""

import pytest
from decimal import Decimal
from uuid import uuid4

from app.models.account import AccountType
from app.services.payoff_strategy_service import (
    DebtAccount,
    PayoffStrategyService,
    _DEBT_ACCOUNT_TYPES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_debt(
    balance: str,
    rate: str = "18.0",
    min_payment: str = "50",
    account_type: AccountType = AccountType.CREDIT_CARD,
    name: str = "Test Debt",
) -> DebtAccount:
    return DebtAccount(
        account_id=uuid4(),
        name=name,
        balance=Decimal(balance),
        interest_rate=Decimal(rate),
        minimum_payment=Decimal(min_payment),
        account_type=account_type,
    )


# ---------------------------------------------------------------------------
# _DEBT_ACCOUNT_TYPES
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestDebtAccountTypes:
    """_DEBT_ACCOUNT_TYPES is built from AccountType.is_debt."""

    def test_includes_all_is_debt_type_names(self):
        """Should contain the NAME (uppercase) of every AccountType with is_debt=True."""
        expected = {t.name for t in AccountType if t.is_debt}
        assert set(_DEBT_ACCOUNT_TYPES) == expected

    def test_includes_core_debt_types(self):
        """Credit card, loan, student loan, and mortgage must always be present."""
        for name in ["CREDIT_CARD", "LOAN", "STUDENT_LOAN", "MORTGAGE"]:
            assert name in _DEBT_ACCOUNT_TYPES

    def test_excludes_asset_types(self):
        """Checking, savings, and other asset types must not be included."""
        for t in AccountType:
            if not t.is_debt:
                assert t.name not in _DEBT_ACCOUNT_TYPES


# ---------------------------------------------------------------------------
# account_type in debt states
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestAccountTypeInDebtStates:
    """account_type is serialised into every debt state dict."""

    def test_account_type_value_present_in_snowball_debts(self):
        """Snowball result debts should each carry account_type as a string value."""
        debt = make_debt("1000", account_type=AccountType.CREDIT_CARD)
        result = PayoffStrategyService.calculate_snowball([debt], Decimal("0"))
        assert result["debts"][0]["account_type"] == AccountType.CREDIT_CARD.value

    def test_account_type_value_present_in_avalanche_debts(self):
        """Avalanche result debts should carry account_type."""
        debt = make_debt("1000", account_type=AccountType.MORTGAGE)
        result = PayoffStrategyService.calculate_avalanche([debt], Decimal("0"))
        assert result["debts"][0]["account_type"] == AccountType.MORTGAGE.value

    def test_account_type_value_present_in_current_pace_debts(self):
        """Current-pace result debts should carry account_type."""
        debt = make_debt("500", account_type=AccountType.LOAN)
        result = PayoffStrategyService.calculate_current_pace([debt])
        assert result["debts"][0]["account_type"] == AccountType.LOAN.value

    def test_multiple_debts_each_have_correct_account_type(self):
        """Each debt in a multi-debt strategy carries its own account_type."""
        debts = [
            make_debt("500", account_type=AccountType.CREDIT_CARD, name="CC"),
            make_debt("2000", account_type=AccountType.LOAN, name="Loan"),
        ]
        result = PayoffStrategyService.calculate_snowball(debts, Decimal("0"))
        types = {d["name"]: d["account_type"] for d in result["debts"]}
        assert types["CC"] == "credit_card"
        assert types["Loan"] == "loan"


# ---------------------------------------------------------------------------
# payoff_date — set via minimum payment
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestPayoffDateViaMinimumPayment:
    """payoff_date must be populated when minimum payment zeros a debt."""

    def test_payoff_date_set_when_minimum_payment_covers_full_balance(self):
        """A debt whose balance is wiped by its minimum payment gets a payoff_date."""
        # balance=$100, min=$200, rate=0%  → paid off in month 1 by minimum payment alone
        debt = make_debt("100", rate="0", min_payment="200")
        result = PayoffStrategyService.calculate_snowball([debt], extra_payment=Decimal("0"))
        assert result["debts"][0]["payoff_date"] is not None

    def test_payoff_date_set_for_lower_priority_debt_paid_by_minimums(self):
        """Non-priority debt zeroed by minimums before extra cascade reaches it gets a date."""
        # debt_a (priority — gets extra):  large balance
        # debt_b (non-priority):           tiny balance paid off by minimum in month 1
        debt_a = make_debt("5000", rate="18", min_payment="100", name="Big Debt")
        debt_b = make_debt("50", rate="0", min_payment="200", name="Tiny Debt")

        # Snowball orders smallest first → debt_b is priority.  Use avalanche so debt_a
        # (higher rate) is priority and debt_b gets paid by its minimum.
        result = PayoffStrategyService.calculate_avalanche(
            [debt_a, debt_b], extra_payment=Decimal("0")
        )

        debt_map = {d["name"]: d for d in result["debts"]}
        assert debt_map["Tiny Debt"]["payoff_date"] is not None

    def test_payoff_date_not_none_after_extra_payment_payoff(self):
        """Extra-payment path also yields a payoff_date (regression guard)."""
        debt = make_debt("500", rate="10", min_payment="50")
        result = PayoffStrategyService.calculate_snowball([debt], extra_payment=Decimal("1000"))
        assert result["debts"][0]["payoff_date"] is not None

    def test_all_debts_have_payoff_date_when_fully_paid(self):
        """Every debt in a result where all balances reach zero has a payoff_date."""
        debts = [
            make_debt("300", rate="15", min_payment="100", name="A"),
            make_debt("700", rate="20", min_payment="80", name="B"),
        ]
        result = PayoffStrategyService.calculate_snowball(debts, extra_payment=Decimal("500"))

        for debt_state in result["debts"]:
            if debt_state["balance"] <= 0.01:
                assert debt_state["payoff_date"] is not None, (
                    f"Debt '{debt_state['name']}' has zero balance but no payoff_date"
                )

    def test_payoff_date_none_when_360_month_cap_hit(self):
        """A debt that cannot be paid off in 30 years should have payoff_date=None."""
        # $1M balance, min payment $100, rate 15% — interest alone is ~$12,500/month
        debt = make_debt("1000000", rate="15", min_payment="100")
        result = PayoffStrategyService.calculate_current_pace([debt])
        assert result["debt_free_date"] is None
        # The debt itself has no payoff date (cap hit before payoff)
        assert result["debts"][0]["payoff_date"] is None


# ---------------------------------------------------------------------------
# Empty / edge cases
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestStrategyEdgeCases:
    """Smoke tests for empty inputs and zero extra payment."""

    def test_snowball_empty_returns_zero_result(self):
        result = PayoffStrategyService.calculate_snowball([], Decimal("500"))
        assert result["total_months"] == 0
        assert result["total_interest"] == 0
        assert result["debts"] == []

    def test_avalanche_empty_returns_zero_result(self):
        result = PayoffStrategyService.calculate_avalanche([], Decimal("500"))
        assert result["total_months"] == 0

    def test_current_pace_empty_returns_zero_result(self):
        result = PayoffStrategyService.calculate_current_pace([])
        assert result["total_months"] == 0

    def test_snowball_orders_smallest_balance_first(self):
        """Snowball should place the smallest balance debt in position 0."""
        debts = [
            make_debt("5000", name="Large"),
            make_debt("500", name="Small"),
        ]
        result = PayoffStrategyService.calculate_snowball(debts, Decimal("0"))
        assert result["debts"][0]["name"] == "Small"

    def test_avalanche_orders_highest_rate_first(self):
        """Avalanche should place the highest-rate debt in position 0."""
        debts = [
            make_debt("1000", rate="5", name="LowRate"),
            make_debt("1000", rate="20", name="HighRate"),
        ]
        result = PayoffStrategyService.calculate_avalanche(debts, Decimal("0"))
        assert result["debts"][0]["name"] == "HighRate"
