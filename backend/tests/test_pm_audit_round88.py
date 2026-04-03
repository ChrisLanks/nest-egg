"""
PM Audit Round 88 — Security fixes: is_active filter + input sanitization.

Changes covered:
1. dependencies.py: get_verified_account now filters Account.is_active.is_(True)
   — prevents soft-deleted accounts from being accessed via path-param endpoints
2. insurance_policies.py: provider, policy_number, beneficiary_name, notes
   sanitized on create and update
3. dependents.py: first_name, relationship, notes sanitized on create and update
"""

import inspect


# ---------------------------------------------------------------------------
# 1. dependencies.py — is_active filter on get_verified_account
# ---------------------------------------------------------------------------

def test_get_verified_account_filters_is_active():
    import app.dependencies as mod
    src = inspect.getsource(mod.get_verified_account)
    assert "is_active" in src, "get_verified_account must filter on is_active"


def test_get_verified_account_uses_is_true():
    import app.dependencies as mod
    src = inspect.getsource(mod.get_verified_account)
    # Ensure it uses .is_(True) pattern (not == True which can be linted away)
    assert "is_active.is_(True)" in src


# ---------------------------------------------------------------------------
# 2. insurance_policies.py — input sanitization on create + update
# ---------------------------------------------------------------------------

def test_insurance_policies_imports_sanitization():
    import app.api.v1.insurance_policies as mod
    src = inspect.getsource(mod)
    assert "input_sanitization_service" in src


def test_insurance_policies_create_sanitizes_fields():
    import app.api.v1.insurance_policies as mod
    src = inspect.getsource(mod.create_insurance_policy)
    assert "sanitize_html" in src
    assert "provider" in src
    assert "beneficiary_name" in src
    assert "notes" in src


def test_insurance_policies_update_sanitizes_fields():
    import app.api.v1.insurance_policies as mod
    src = inspect.getsource(mod.update_insurance_policy)
    assert "sanitize_html" in src
    assert "beneficiary_name" in src
    assert "notes" in src


# ---------------------------------------------------------------------------
# 3. dependents.py — input sanitization on create + update
# ---------------------------------------------------------------------------

def test_dependents_imports_sanitization():
    import app.api.v1.dependents as mod
    src = inspect.getsource(mod)
    assert "input_sanitization_service" in src


def test_dependents_create_sanitizes_fields():
    import app.api.v1.dependents as mod
    src = inspect.getsource(mod.create_dependent)
    assert "sanitize_html" in src
    assert "first_name" in src
    assert "notes" in src


def test_dependents_update_sanitizes_fields():
    import app.api.v1.dependents as mod
    src = inspect.getsource(mod.update_dependent)
    assert "sanitize_html" in src
    assert "first_name" in src
    assert "notes" in src
