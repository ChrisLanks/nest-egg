"""Unit test: liquidity dashboard returns bare account type values."""
import pytest
from app.models.account import AccountType


def test_account_type_value_is_bare_string():
    """AccountType enum .value must be a bare lowercase string, not 'AccountType.CHECKING'."""
    assert AccountType.CHECKING.value == "checking"
    assert AccountType.SAVINGS.value == "savings"
    assert AccountType.MONEY_MARKET.value == "money_market"
    assert AccountType.CD.value == "cd"
    # str() of an enum gives the qualified name — .value gives the raw string
    assert str(AccountType.CHECKING) != AccountType.CHECKING.value
