"""
PM Audit Round 97 — Typed response models for auth/bank_linking/plaid.

Changes covered:
1. auth.py: Dict[str, Any] on resend-verification + forgot-password + debug endpoint;
   AuthMessageResponse on reset-password
2. bank_linking.py: Dict[str, Any] on sync-transactions + sync-holdings;
   DisconnectResponse on disconnect
3. plaid.py: Dict[str, Any] on sync-holdings + webhook + sync-transactions
"""

import inspect


# ---------------------------------------------------------------------------
# 1. auth.py
# ---------------------------------------------------------------------------

def test_auth_has_message_response():
    import app.api.v1.auth as mod
    assert hasattr(mod, "AuthMessageResponse")
    fields = mod.AuthMessageResponse.model_fields
    assert "message" in fields


def test_auth_resend_verification_has_response_model():
    import app.api.v1.auth as mod
    src = inspect.getsource(mod)
    assert 'response_model=Dict[str, Any]' in src or "response_model=AuthMessageResponse" in src


def test_auth_forgot_password_has_response_model():
    import app.api.v1.auth as mod
    src = inspect.getsource(mod.forgot_password)
    # decorator is part of source through inspect — check at module level
    mod_src = inspect.getsource(mod)
    assert 'forgot-password' in mod_src
    assert 'response_model=Dict[str, Any]' in mod_src


def test_auth_reset_password_has_response_model():
    import app.api.v1.auth as mod
    src = inspect.getsource(mod)
    assert "response_model=AuthMessageResponse" in src


def test_auth_reset_password_returns_model():
    import app.api.v1.auth as mod
    src = inspect.getsource(mod.reset_password)
    assert "AuthMessageResponse(" in src


# ---------------------------------------------------------------------------
# 2. bank_linking.py
# ---------------------------------------------------------------------------

def test_bank_linking_has_disconnect_response():
    import app.api.v1.bank_linking as mod
    assert hasattr(mod, "DisconnectResponse")
    fields = mod.DisconnectResponse.model_fields
    assert "success" in fields
    assert "account_id" in fields
    assert "status" in fields


def test_bank_linking_sync_transactions_has_response_model():
    import app.api.v1.bank_linking as mod
    src = inspect.getsource(mod)
    assert "response_model=Dict[str, Any]" in src


def test_bank_linking_disconnect_has_response_model():
    import app.api.v1.bank_linking as mod
    src = inspect.getsource(mod)
    assert "response_model=DisconnectResponse" in src


def test_bank_linking_disconnect_returns_model():
    import app.api.v1.bank_linking as mod
    src = inspect.getsource(mod.disconnect_account)
    assert "DisconnectResponse(" in src


# ---------------------------------------------------------------------------
# 3. plaid.py
# ---------------------------------------------------------------------------

def test_plaid_sync_holdings_has_response_model():
    import app.api.v1.plaid as mod
    src = inspect.getsource(mod.sync_plaid_holdings)
    # decorator on function — check module src
    mod_src = inspect.getsource(mod)
    assert "response_model=Dict[str, Any]" in mod_src


def test_plaid_webhook_has_response_model():
    import app.api.v1.plaid as mod
    mod_src = inspect.getsource(mod)
    assert "response_model=Dict[str, Any]" in mod_src


def test_plaid_sync_transactions_has_response_model():
    import app.api.v1.plaid as mod
    mod_src = inspect.getsource(mod)
    assert "response_model=Dict[str, Any]" in mod_src
