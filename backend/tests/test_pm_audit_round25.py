"""Tests for PM audit round 25 fixes.

Covers:
- PropertyAccountForm helper text explains auto-create mortgage behavior
- AddAccountModal creates a linked mortgage account when mortgage_balance > 0
- Mortgage balance passed as positive value (backend negates debt balances)
"""

import inspect


def test_property_form_helper_text_mentions_auto_create():
    """PropertyAccountForm helper text must mention automatic mortgage account creation."""
    from pathlib import Path

    form_path = (
        Path(__file__).parent.parent.parent
        / "frontend/src/features/accounts/components/forms/PropertyAccountForm.tsx"
    )
    source = form_path.read_text()
    assert "linked mortgage account" in source or "mortgage account will be created" in source, (
        "PropertyAccountForm must explain that a linked mortgage account is auto-created"
    )


def test_add_account_modal_has_property_mutation():
    """AddAccountModal must have a dedicated property mutation (createPropertyAccountMutation)."""
    from pathlib import Path

    modal_path = (
        Path(__file__).parent.parent.parent
        / "frontend/src/features/accounts/components/AddAccountModal.tsx"
    )
    source = modal_path.read_text()
    assert "createPropertyAccountMutation" in source, (
        "AddAccountModal must have createPropertyAccountMutation for property + mortgage creation"
    )


def test_property_mutation_creates_mortgage_when_balance_provided():
    """AddAccountModal property mutation must post a mortgage account when mortgage_balance > 0."""
    from pathlib import Path

    modal_path = (
        Path(__file__).parent.parent.parent
        / "frontend/src/features/accounts/components/AddAccountModal.tsx"
    )
    source = modal_path.read_text()
    assert 'account_type: "mortgage"' in source, (
        "Property mutation must create a mortgage account type when balance is provided"
    )
    assert "mortgage_balance > 0" in source, (
        "Mortgage account creation must be conditional on mortgage_balance > 0"
    )


def test_mortgage_balance_passed_as_positive():
    """Mortgage balance must be passed as positive (backend negates debt balances automatically)."""
    from pathlib import Path

    modal_path = (
        Path(__file__).parent.parent.parent
        / "frontend/src/features/accounts/components/AddAccountModal.tsx"
    )
    source = modal_path.read_text()
    assert "Math.abs(data.mortgage_balance)" in source, (
        "Mortgage balance must use Math.abs() to pass positive value; backend negates debt balances"
    )
    # Must NOT pass negative value directly
    assert "balance: -Math.abs" not in source, (
        "Must not negate in frontend — backend handles that for debt account types"
    )


def test_property_mutation_is_loading_wired_to_property_form():
    """PropertyAccountForm isLoading must use createPropertyAccountMutation, not createManualAccountMutation."""
    from pathlib import Path

    modal_path = (
        Path(__file__).parent.parent.parent
        / "frontend/src/features/accounts/components/AddAccountModal.tsx"
    )
    source = modal_path.read_text()
    # Find the PropertyAccountForm JSX block
    prop_form_idx = source.find("<PropertyAccountForm")
    assert prop_form_idx != -1, "PropertyAccountForm usage must exist"
    # The next 300 chars should reference createPropertyAccountMutation, not createManualAccountMutation
    prop_form_snippet = source[prop_form_idx : prop_form_idx + 300]
    assert "createPropertyAccountMutation.isPending" in prop_form_snippet, (
        "PropertyAccountForm isLoading must be wired to createPropertyAccountMutation.isPending"
    )
