"""Security tests: numeric field bounds on account and transaction schemas.

Without explicit bounds, absurdly large values pass Pydantic validation and
hit the DB's Numeric(15,2) constraint, returning a 500 instead of a 422.
These tests verify that schemas reject out-of-range values cleanly.
"""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.transaction import ManualTransactionCreate, TransactionBase
from app.schemas.account import ManualAccountCreate, AccountUpdate
from app.models.account import AccountType, AccountSource


# ---------------------------------------------------------------------------
# TransactionBase — amount bounds
# ---------------------------------------------------------------------------


class TestTransactionAmountBounds:
    def _base_kwargs(self):
        from datetime import date
        return {"date": date(2025, 1, 1)}

    def test_max_positive_amount_accepted(self):
        t = TransactionBase(**self._base_kwargs(), amount=Decimal("999999999.99"))
        assert t.amount == Decimal("999999999.99")

    def test_max_negative_amount_accepted(self):
        t = TransactionBase(**self._base_kwargs(), amount=Decimal("-999999999.99"))
        assert t.amount == Decimal("-999999999.99")

    def test_amount_above_max_rejected(self):
        with pytest.raises(ValidationError):
            TransactionBase(**self._base_kwargs(), amount=Decimal("1000000000.00"))

    def test_amount_below_min_rejected(self):
        with pytest.raises(ValidationError):
            TransactionBase(**self._base_kwargs(), amount=Decimal("-1000000000.00"))

    def test_zero_amount_accepted(self):
        t = TransactionBase(**self._base_kwargs(), amount=Decimal("0"))
        assert t.amount == Decimal("0")

    def test_very_large_amount_rejected(self):
        with pytest.raises(ValidationError):
            TransactionBase(**self._base_kwargs(), amount=Decimal("9" * 15))


# ---------------------------------------------------------------------------
# ManualAccountCreate — balance and rate bounds
# ---------------------------------------------------------------------------


def _minimal_account(**kwargs):
    defaults = {
        "name": "Test Account",
        "account_type": AccountType.CHECKING,
        "account_source": AccountSource.MANUAL,
        "balance": Decimal("1000.00"),
    }
    defaults.update(kwargs)
    return defaults


class TestAccountBalanceBounds:
    def test_normal_balance_accepted(self):
        a = ManualAccountCreate(**_minimal_account(balance=Decimal("50000.00")))
        assert a.balance == Decimal("50000.00")

    def test_negative_balance_accepted(self):
        """Debt accounts have negative balances."""
        a = ManualAccountCreate(**_minimal_account(balance=Decimal("-25000.00")))
        assert a.balance == Decimal("-25000.00")

    def test_balance_above_max_rejected(self):
        with pytest.raises(ValidationError):
            ManualAccountCreate(**_minimal_account(balance=Decimal("9999999999999.00")))

    def test_balance_below_min_rejected(self):
        with pytest.raises(ValidationError):
            ManualAccountCreate(**_minimal_account(balance=Decimal("-9999999999999.00")))


class TestAccountInterestRateBounds:
    def test_normal_rate_accepted(self):
        a = ManualAccountCreate(**_minimal_account(interest_rate=Decimal("5.25")))
        assert a.interest_rate == Decimal("5.25")

    def test_high_rate_accepted(self):
        """200% APR covers worst-case payday loans."""
        a = ManualAccountCreate(**_minimal_account(interest_rate=Decimal("199.99")))
        assert a.interest_rate == Decimal("199.99")

    def test_negative_rate_rejected(self):
        with pytest.raises(ValidationError):
            ManualAccountCreate(**_minimal_account(interest_rate=Decimal("-1.00")))

    def test_rate_above_max_rejected(self):
        with pytest.raises(ValidationError):
            ManualAccountCreate(**_minimal_account(interest_rate=Decimal("201.00")))


class TestAccountUpdateBalanceBounds:
    def test_normal_balance_update_accepted(self):
        a = AccountUpdate(current_balance=Decimal("12345.67"))
        assert a.current_balance == Decimal("12345.67")

    def test_absurd_balance_update_rejected(self):
        with pytest.raises(ValidationError):
            AccountUpdate(current_balance=Decimal("9999999999999.00"))

    def test_none_balance_update_accepted(self):
        """Omitting balance (no change) must be valid."""
        a = AccountUpdate()
        assert a.current_balance is None

    def test_employer_match_above_100_rejected(self):
        with pytest.raises(ValidationError):
            AccountUpdate(employer_match_percent=Decimal("101.00"))

    def test_employer_match_100_accepted(self):
        a = AccountUpdate(employer_match_percent=Decimal("100.00"))
        assert a.employer_match_percent == Decimal("100.00")

    def test_negative_minimum_payment_rejected(self):
        with pytest.raises(ValidationError):
            AccountUpdate(minimum_payment=Decimal("-1.00"))
