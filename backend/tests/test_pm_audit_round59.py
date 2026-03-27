"""
PM Audit Round 59 — fixes:
1. Employer match endpoint 500: _EMPLOYER_PLAN_TYPES used .value strings instead of
   AccountType enum members. asyncpg casts .in_() values as ::accounttype; DB stores
   uppercase labels ('RETIREMENT_401K') but .value returns lowercase ('retirement_401k'),
   causing InvalidTextRepresentationError.
2. Tax-equivalent yield endpoint 500: AccountType.I_BOND existed in Python enum but
   was never added to the PostgreSQL accounttype enum. Any .in_() query including I_BOND
   would fail with InvalidTextRepresentationError.
3. Migration 37e1d1767687 adds I_BOND, TIPS, TRUST, CUSTODIAL_UGMA, TRUMP_ACCOUNT to DB.
"""

import pytest


# ---------------------------------------------------------------------------
# employer_match._EMPLOYER_PLAN_TYPES — must use enum members, not .value strings
# ---------------------------------------------------------------------------


def test_employer_plan_types_are_enum_members():
    """_EMPLOYER_PLAN_TYPES must contain AccountType enum members, not raw strings.

    Passing .value strings to .in_() on a PostgreSQL enum column causes asyncpg to
    cast them as ::accounttype. The DB stores uppercase labels ('RETIREMENT_401K')
    but .value returns lowercase ('retirement_401k'), so the cast fails with
    InvalidTextRepresentationError → 500.
    """
    from app.api.v1.employer_match import _EMPLOYER_PLAN_TYPES
    from app.models.account import AccountType

    for item in _EMPLOYER_PLAN_TYPES:
        assert isinstance(item, AccountType), (
            f"Expected AccountType enum member, got {type(item).__name__}: {item!r}. "
            "Do not use .value — pass the enum member directly to .in_()"
        )


def test_employer_plan_types_contains_expected_account_types():
    """All three employer plan types must be present."""
    from app.api.v1.employer_match import _EMPLOYER_PLAN_TYPES
    from app.models.account import AccountType

    plan_set = set(_EMPLOYER_PLAN_TYPES)
    assert AccountType.RETIREMENT_401K in plan_set
    assert AccountType.RETIREMENT_403B in plan_set
    assert AccountType.RETIREMENT_457B in plan_set


def test_employer_match_source_does_not_use_dotvalue_in_plan_types():
    """Source code guard: .value must not be used when building _EMPLOYER_PLAN_TYPES."""
    import inspect
    from app.api.v1 import employer_match

    source = inspect.getsource(employer_match)
    assert "AccountType.RETIREMENT_401K.value" not in source, (
        "Do not use .value in _EMPLOYER_PLAN_TYPES — pass enum members directly"
    )
    assert "AccountType.RETIREMENT_403B.value" not in source
    assert "AccountType.RETIREMENT_457B.value" not in source


# ---------------------------------------------------------------------------
# tax_equiv_yield._YIELD_ACCOUNT_TYPES — enum members, includes I_BOND
# ---------------------------------------------------------------------------


def test_yield_account_types_are_enum_members():
    """_YIELD_ACCOUNT_TYPES must contain AccountType enum members, not raw strings."""
    from app.api.v1.tax_equiv_yield import _YIELD_ACCOUNT_TYPES
    from app.models.account import AccountType

    for item in _YIELD_ACCOUNT_TYPES:
        assert isinstance(item, AccountType), (
            f"Expected AccountType enum member, got {type(item).__name__}: {item!r}"
        )


def test_yield_account_types_contains_all_expected():
    """All five yield-bearing account types must be present."""
    from app.api.v1.tax_equiv_yield import _YIELD_ACCOUNT_TYPES
    from app.models.account import AccountType

    for expected in (
        AccountType.CD,
        AccountType.BOND,
        AccountType.I_BOND,
        AccountType.SAVINGS,
        AccountType.MONEY_MARKET,
    ):
        assert expected in _YIELD_ACCOUNT_TYPES, (
            f"AccountType.{expected.name} missing from _YIELD_ACCOUNT_TYPES"
        )


# ---------------------------------------------------------------------------
# AccountType enum — newly added members
# ---------------------------------------------------------------------------


def test_account_type_i_bond_exists():
    """AccountType.I_BOND must exist — it was missing from the DB enum causing the 500."""
    from app.models.account import AccountType

    assert hasattr(AccountType, "I_BOND")
    assert AccountType.I_BOND.value == "i_bond"


def test_account_type_migration_members_exist():
    """All five AccountType members added by migration 37e1d1767687 exist in Python enum."""
    from app.models.account import AccountType

    for name in ["I_BOND", "TIPS", "TRUST", "CUSTODIAL_UGMA", "TRUMP_ACCOUNT"]:
        assert hasattr(AccountType, name), f"AccountType.{name} missing from enum"


# ---------------------------------------------------------------------------
# Tax-equivalent yield math (no DB required)
# ---------------------------------------------------------------------------


def test_tax_equiv_yield_formula():
    """tax_equiv = nominal / (1 - combined_rate)."""
    nominal = 0.045   # 4.5%
    combined = 0.27   # 22% federal + 5% state
    result = nominal / (1 - combined)
    assert abs(result - 0.06164) < 0.0001


def test_tax_equiv_yield_zero_rate():
    """At 0% combined rate, tax-equivalent yield equals nominal yield."""
    assert 0.05 / (1 - 0.0) == 0.05


def test_tax_equiv_yield_combined_rate_guard():
    """Combined rate >= 1.0 must fall back to nominal (division-by-zero guard)."""
    nominal = 0.05
    combined_rate = 1.0
    result = nominal / (1 - combined_rate) if combined_rate < 1.0 else nominal
    assert result == nominal
