"""Unit tests for contribution headroom — account_type uses .value not str(enum)."""

import pytest
from app.models.account import AccountType


class TestAccountTypeValueFormat:
    """The API must send account_type as the enum .value so the frontend
    ACCOUNT_TYPE_LABELS lookup works (keys are e.g. 'retirement_401k',
    not 'AccountType.RETIREMENT_401K')."""

    def test_account_type_value_is_snake_case(self):
        assert AccountType.RETIREMENT_401K.value == "retirement_401k"

    def test_str_enum_is_not_value(self):
        # str(enum) returns 'AccountType.RETIREMENT_401K' — NOT what we want
        assert str(AccountType.RETIREMENT_401K) != AccountType.RETIREMENT_401K.value

    def test_all_limit_types_have_lowercase_values(self):
        limit_types = [
            AccountType.RETIREMENT_401K,
            AccountType.RETIREMENT_403B,
            AccountType.RETIREMENT_457B,
            AccountType.RETIREMENT_IRA,
            AccountType.RETIREMENT_ROTH,
            AccountType.RETIREMENT_SEP_IRA,
            AccountType.RETIREMENT_SIMPLE_IRA,
            AccountType.HSA,
            AccountType.RETIREMENT_529,
        ]
        for at in limit_types:
            assert at.value == at.value.lower(), f"{at} .value should be lowercase"
            assert "AccountType" not in at.value, f"{at} .value must not contain 'AccountType'"

    def test_hsa_value(self):
        assert AccountType.HSA.value == "hsa"

    def test_roth_ira_value(self):
        assert AccountType.RETIREMENT_ROTH.value == "retirement_roth"

    def test_traditional_ira_value(self):
        assert AccountType.RETIREMENT_IRA.value == "retirement_ira"
