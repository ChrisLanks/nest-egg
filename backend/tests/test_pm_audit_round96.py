"""
PM Audit Round 96 — Typed response models for csv_import/teller/reports/household/guest_access.

Changes covered:
1. csv_import.py: CsvValidateResponse on POST /validate
2. teller.py: WebhookAckResponse on POST /webhook
3. reports.py: response_model=Dict[str, Any] on POST /execute
4. household.py: AcceptInvitationResponse on POST /accept/{invitation_code}
5. guest_access.py: GuestActionResponse on POST /accept/{code} and /decline/{code}
"""

import inspect


# ---------------------------------------------------------------------------
# 1. csv_import.py
# ---------------------------------------------------------------------------

def test_csv_import_has_validate_response():
    import app.api.v1.csv_import as mod
    assert hasattr(mod, "CsvValidateResponse")
    fields = mod.CsvValidateResponse.model_fields
    assert "message" in fields


def test_csv_import_validate_has_response_model():
    import app.api.v1.csv_import as mod
    src = inspect.getsource(mod)
    assert "response_model=CsvValidateResponse" in src


def test_csv_import_validate_returns_model():
    import app.api.v1.csv_import as mod
    src = inspect.getsource(mod.validate_csv)
    assert "CsvValidateResponse(" in src


# ---------------------------------------------------------------------------
# 2. teller.py
# ---------------------------------------------------------------------------

def test_teller_has_webhook_ack_response():
    import app.api.v1.teller as mod
    assert hasattr(mod, "WebhookAckResponse")
    fields = mod.WebhookAckResponse.model_fields
    assert "status" in fields


def test_teller_webhook_has_response_model():
    import app.api.v1.teller as mod
    src = inspect.getsource(mod)
    assert "response_model=WebhookAckResponse" in src


def test_teller_webhook_returns_model():
    import app.api.v1.teller as mod
    src = inspect.getsource(mod.handle_teller_webhook)
    assert "WebhookAckResponse(" in src


# ---------------------------------------------------------------------------
# 3. reports.py
# ---------------------------------------------------------------------------

def test_reports_execute_has_response_model():
    import app.api.v1.reports as mod
    src = inspect.getsource(mod)
    assert "response_model=Dict[str, Any]" in src


def test_reports_imports_dict_and_any():
    import app.api.v1.reports as mod
    src = inspect.getsource(mod)
    assert "Dict" in src
    assert "Any" in src


# ---------------------------------------------------------------------------
# 4. household.py
# ---------------------------------------------------------------------------

def test_household_has_accept_invitation_response():
    import app.api.v1.household as mod
    assert hasattr(mod, "AcceptInvitationResponse")
    fields = mod.AcceptInvitationResponse.model_fields
    assert "message" in fields
    assert "organization_id" in fields
    assert "accounts_migrated" in fields


def test_household_accept_has_response_model():
    import app.api.v1.household as mod
    src = inspect.getsource(mod)
    assert "response_model=AcceptInvitationResponse" in src


def test_household_accept_returns_model():
    import app.api.v1.household as mod
    src = inspect.getsource(mod.accept_invitation)
    assert "AcceptInvitationResponse(" in src


# ---------------------------------------------------------------------------
# 5. guest_access.py
# ---------------------------------------------------------------------------

def test_guest_access_has_action_response():
    import app.api.v1.guest_access as mod
    assert hasattr(mod, "GuestActionResponse")
    fields = mod.GuestActionResponse.model_fields
    assert "detail" in fields


def test_guest_access_accept_has_response_model():
    import app.api.v1.guest_access as mod
    src = inspect.getsource(mod)
    assert "response_model=GuestActionResponse" in src


def test_guest_access_accept_returns_model():
    import app.api.v1.guest_access as mod
    src = inspect.getsource(mod.accept_guest_invitation)
    assert "GuestActionResponse(" in src


def test_guest_access_decline_returns_model():
    import app.api.v1.guest_access as mod
    src = inspect.getsource(mod.decline_guest_invitation)
    assert "GuestActionResponse(" in src
