"""
PM Audit Round 26 — fixes:
1. Sync status fields (last_synced_at, last_error_code, last_error_message, needs_reauth)
   now included in Account schema and populated in GET /accounts/{id}
2. Recurring tasks org loop isolated so one failing org doesn't block others
3. Advanced nav items gated by showAdvancedNav preference in Layout.tsx
4. SS Optimizer hidden for new users with no birthdate (was shown to everyone)
"""
from pathlib import Path

BACKEND = Path(__file__).parent.parent
FRONTEND = BACKEND.parent / "frontend/src"


# ── 1. Account schema includes sync status fields ──────────────────────────────

def test_account_schema_has_sync_fields():
    src = (BACKEND / "app/schemas/account.py").read_text()
    for field in ("last_synced_at", "last_error_code", "last_error_message", "needs_reauth"):
        assert field in src, f"Account schema missing sync field: {field}"


def test_account_schema_sync_fields_in_account_class_not_only_summary():
    """Fields must be in the Account class (used by GET /accounts/{id}), not just AccountSummary."""
    src = (BACKEND / "app/schemas/account.py").read_text()
    # Find Account class (before AccountSummary)
    account_class_end = src.index("class AccountSummary")
    account_class_src = src[:account_class_end]
    assert "last_synced_at" in account_class_src
    assert "needs_reauth" in account_class_src


def test_get_account_endpoint_populates_plaid_sync_fields():
    src = (BACKEND / "app/api/v1/accounts.py").read_text()
    assert "account.last_synced_at = account.plaid_item.last_synced_at" in src
    assert "account.last_error_code = account.plaid_item.last_error_code" in src
    assert "account.needs_reauth = account.plaid_item.needs_reauth" in src


def test_get_account_populates_teller_sync_fields():
    src = (BACKEND / "app/api/v1/accounts.py").read_text()
    assert "account.teller_enrollment.last_synced_at" in src
    assert "account.teller_enrollment.last_error_code" in src


# ── 2. Recurring tasks org loop is isolated ────────────────────────────────────

def test_recurring_tasks_org_loop_has_per_org_try_except():
    src = (BACKEND / "app/workers/tasks/recurring_tasks.py").read_text()
    assert "except Exception as org_exc:" in src


def test_recurring_tasks_org_loop_continues_on_error():
    src = (BACKEND / "app/workers/tasks/recurring_tasks.py").read_text()
    assert "continue" in src


def test_recurring_tasks_logs_org_error():
    src = (BACKEND / "app/workers/tasks/recurring_tasks.py").read_text()
    assert "org_exc" in src


def test_recurring_tasks_outer_exception_still_raised():
    src = (BACKEND / "app/workers/tasks/recurring_tasks.py").read_text()
    assert "raise" in src


# ── 3. Advanced nav gated by preference ────────────────────────────────────────

def test_layout_reads_advanced_nav_preference():
    src = (FRONTEND / "components/Layout.tsx").read_text()
    assert "nest-egg-show-advanced-nav" in src


def test_layout_filter_visible_gates_advanced_items():
    src = (FRONTEND / "components/Layout.tsx").read_text()
    # Advanced items are gated: hidden when !showAdvancedNav unless per-item override
    assert "item.advanced && !showAdvancedNav" in src


# ── 4. SS Optimizer hidden for new users ───────────────────────────────────────

def test_ss_optimizer_not_shown_when_age_unknown():
    src = (FRONTEND / "hooks/useNavDefaults.ts").read_text()
    # Must NOT use the old pattern that showed SS to everyone with no birthdate
    assert "userAge === null || userAge >= 50" not in src


def test_ss_optimizer_requires_age_gte_50():
    src = (FRONTEND / "hooks/useNavDefaults.ts").read_text()
    assert "userAge !== null && userAge >= 50" in src
