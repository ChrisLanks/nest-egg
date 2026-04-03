"""
PM Audit Round 86 — Typed response models for previously untyped endpoints.

Changes covered:
1. accounts.py: ValuationProvidersResponse, BulkCountResponse, ValuationResultResponse
   applied to /valuation-providers, /bulk-visibility, /bulk-delete, /refresh-valuation
2. settings.py: PasswordChangeResponse, EmailNotificationsResponse, EmailConfiguredResponse
   applied to change-password, email-notifications, email-configured
3. household.py: ResendInvitationResponse, LeaveHouseholdResponse, InvitationDetailsResponse
   applied to resend, leave, and get_invitation_details
"""

import inspect


# ---------------------------------------------------------------------------
# 1. accounts.py — new response models
# ---------------------------------------------------------------------------

def test_accounts_has_valuation_providers_response():
    from app.api.v1.accounts import ValuationProvidersResponse
    assert 'property' in ValuationProvidersResponse.model_fields
    assert 'vehicle' in ValuationProvidersResponse.model_fields


def test_accounts_valuation_providers_endpoint_has_response_model():
    import app.api.v1.accounts as mod
    src = inspect.getsource(mod)
    assert 'response_model=ValuationProvidersResponse' in src


def test_accounts_has_bulk_count_response():
    from app.api.v1.accounts import BulkCountResponse
    assert 'updated_count' in BulkCountResponse.model_fields
    assert 'deleted_count' in BulkCountResponse.model_fields


def test_accounts_bulk_visibility_has_response_model():
    import app.api.v1.accounts as mod
    src = inspect.getsource(mod)
    assert 'response_model=BulkCountResponse' in src


def test_accounts_bulk_delete_has_response_model():
    import app.api.v1.accounts as mod
    src = inspect.getsource(mod.bulk_delete_accounts)
    assert 'BulkCountResponse' in src or 'response_model' in src


def test_accounts_has_valuation_result_response():
    from app.api.v1.accounts import ValuationResultResponse
    assert 'raw_value' in ValuationResultResponse.model_fields
    assert 'new_value' in ValuationResultResponse.model_fields
    assert 'provider' in ValuationResultResponse.model_fields


def test_accounts_refresh_valuation_has_response_model():
    import app.api.v1.accounts as mod
    src = inspect.getsource(mod)
    assert 'response_model=ValuationResultResponse' in src


# ---------------------------------------------------------------------------
# 2. settings.py — new response models
# ---------------------------------------------------------------------------

def test_settings_has_password_change_response():
    from app.api.v1.settings import PasswordChangeResponse
    assert 'message' in PasswordChangeResponse.model_fields


def test_settings_change_password_has_response_model():
    import app.api.v1.settings as mod
    src = inspect.getsource(mod)
    assert 'response_model=PasswordChangeResponse' in src


def test_settings_has_email_notifications_response():
    from app.api.v1.settings import EmailNotificationsResponse
    assert 'email_notifications_enabled' in EmailNotificationsResponse.model_fields


def test_settings_email_notifications_has_response_model():
    import app.api.v1.settings as mod
    src = inspect.getsource(mod)
    assert 'response_model=EmailNotificationsResponse' in src


def test_settings_has_email_configured_response():
    from app.api.v1.settings import EmailConfiguredResponse
    assert 'configured' in EmailConfiguredResponse.model_fields


def test_settings_email_configured_has_response_model():
    import app.api.v1.settings as mod
    src = inspect.getsource(mod)
    assert 'response_model=EmailConfiguredResponse' in src


# ---------------------------------------------------------------------------
# 3. household.py — new response models
# ---------------------------------------------------------------------------

def test_household_has_resend_invitation_response():
    from app.api.v1.household import ResendInvitationResponse
    assert 'id' in ResendInvitationResponse.model_fields
    assert 'email' in ResendInvitationResponse.model_fields
    assert 'join_url' in ResendInvitationResponse.model_fields


def test_household_resend_invitation_has_response_model():
    import app.api.v1.household as mod
    src = inspect.getsource(mod)
    assert 'response_model=ResendInvitationResponse' in src


def test_household_has_leave_household_response():
    from app.api.v1.household import LeaveHouseholdResponse
    assert 'message' in LeaveHouseholdResponse.model_fields


def test_household_leave_has_response_model():
    import app.api.v1.household as mod
    src = inspect.getsource(mod)
    assert 'response_model=LeaveHouseholdResponse' in src


def test_household_has_invitation_details_response():
    from app.api.v1.household import InvitationDetailsResponse
    assert 'email' in InvitationDetailsResponse.model_fields
    assert 'invited_by_name' in InvitationDetailsResponse.model_fields
    assert 'status' in InvitationDetailsResponse.model_fields
    assert 'expires_at' in InvitationDetailsResponse.model_fields


def test_household_get_invitation_details_has_response_model():
    import app.api.v1.household as mod
    src = inspect.getsource(mod)
    assert 'response_model=InvitationDetailsResponse' in src
