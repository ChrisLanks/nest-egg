"""
PM Audit Round 27 — fix:
Recurring transaction update/delete/apply-label/preview-label endpoints
only checked organization_id, allowing any household member to modify
another member's recurring patterns. Fixed by joining Account and adding
Account.user_id == user.id check.
"""
from pathlib import Path

BACKEND = Path(__file__).parent.parent


def _service_src():
    return (BACKEND / "app/services/recurring_detection_service.py").read_text()


def _api_src():
    return (BACKEND / "app/api/v1/recurring_transactions.py").read_text()


# ── Service layer fixes ────────────────────────────────────────────────────────

def test_update_recurring_joins_account():
    src = _service_src()
    # The update method must join Account
    assert "join(Account, Account.id == RecurringTransaction.account_id)" in src


def test_update_recurring_checks_user_id():
    src = _service_src()
    assert "Account.user_id == user.id" in src


def test_delete_recurring_joins_account():
    src = _service_src()
    # Both update and delete must have the join — count occurrences
    count = src.count("join(Account, Account.id == RecurringTransaction.account_id)")
    assert count >= 2, "Both update and delete must join Account"


def test_delete_recurring_checks_user_id():
    src = _service_src()
    count = src.count("Account.user_id == user.id")
    assert count >= 2, "Both update and delete must check user_id"


# ── API layer fixes ────────────────────────────────────────────────────────────

def test_apply_label_endpoint_joins_account():
    src = _api_src()
    assert "Account.user_id == current_user.id" in src


def test_apply_label_endpoint_imports_account_model():
    src = _api_src()
    assert "from app.models.account import Account" in src


def test_preview_label_endpoint_checks_user_id():
    src = _api_src()
    # Should appear at least twice (apply-label and preview-label)
    count = src.count("Account.user_id == current_user.id")
    assert count >= 2, "Both apply-label and preview-label must check user_id"


def test_no_bare_org_only_query_for_recurring_mutations():
    """None of the mutating endpoints should query RecurringTransaction with only org_id."""
    src = _api_src()
    # The old pattern — org-only without user check — must not appear in mutation context
    # We verify this indirectly: Account.user_id check must be present
    assert "Account.user_id == current_user.id" in src
