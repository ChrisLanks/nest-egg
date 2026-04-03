"""
PM Audit Round 85 — Rate limits on budgets/notifications/household admin endpoints
+ HOUSEHOLD constants extracted to financial.py.

Changes covered:
1. budgets.py: router-level Depends(_rate_limit) — covers all CRUD endpoints
2. notifications.py: router-level Depends(_rate_limit) — covers read/dismiss/create/test
3. household.py: per-endpoint rate limits on remove_member, update_member_role,
   update_member_status, cancel_invitation
4. financial.py: HOUSEHOLD.MAX_MEMBERS and HOUSEHOLD.INVITATION_EXPIRY_DAYS constants
5. household.py: MAX_HOUSEHOLD_MEMBERS bare literal + timedelta(days=7) replaced
   with HOUSEHOLD constants
"""

import inspect


# ---------------------------------------------------------------------------
# 1. budgets.py — router-level rate limit
# ---------------------------------------------------------------------------

def test_budgets_has_rate_limit():
    import app.api.v1.budgets as mod
    src = inspect.getsource(mod)
    assert "rate_limit_service" in src
    assert "_rate_limit" in src


def test_budgets_router_uses_rate_limit_dependency():
    import app.api.v1.budgets as mod
    src = inspect.getsource(mod)
    assert 'dependencies=[Depends(_rate_limit)]' in src


def test_budgets_rate_limit_uses_user_id():
    import app.api.v1.budgets as mod
    src = inspect.getsource(mod._rate_limit)
    assert "current_user.id" in src


# ---------------------------------------------------------------------------
# 2. notifications.py — router-level rate limit
# ---------------------------------------------------------------------------

def test_notifications_router_uses_rate_limit_dependency():
    import app.api.v1.notifications as mod
    src = inspect.getsource(mod)
    assert 'dependencies=[Depends(_rate_limit)]' in src


def test_notifications_has_rate_limit_function():
    import app.api.v1.notifications as mod
    assert callable(mod._rate_limit)


# ---------------------------------------------------------------------------
# 3. household.py — per-endpoint rate limits on admin destructive ops
# ---------------------------------------------------------------------------

def test_household_remove_member_has_rate_limit():
    import app.api.v1.household as mod
    src = inspect.getsource(mod.remove_member)
    assert "rate_limit_service" in src or "check_rate_limit" in src


def test_household_update_member_role_has_rate_limit():
    import app.api.v1.household as mod
    src = inspect.getsource(mod.update_member_role)
    assert "check_rate_limit" in src


def test_household_update_member_status_has_rate_limit():
    import app.api.v1.household as mod
    src = inspect.getsource(mod.update_member_status)
    assert "check_rate_limit" in src


def test_household_cancel_invitation_has_rate_limit():
    import app.api.v1.household as mod
    src = inspect.getsource(mod.cancel_invitation)
    assert "check_rate_limit" in src


# ---------------------------------------------------------------------------
# 4. financial.py — HOUSEHOLD constants
# ---------------------------------------------------------------------------

def test_household_max_members_constant():
    from app.constants.financial import HOUSEHOLD
    assert hasattr(HOUSEHOLD, "MAX_MEMBERS")
    assert HOUSEHOLD.MAX_MEMBERS == 5


def test_household_invitation_expiry_days_constant():
    from app.constants.financial import HOUSEHOLD
    assert hasattr(HOUSEHOLD, "INVITATION_EXPIRY_DAYS")
    assert HOUSEHOLD.INVITATION_EXPIRY_DAYS == 7


# ---------------------------------------------------------------------------
# 5. household.py — no bare literals for max members or invitation expiry
# ---------------------------------------------------------------------------

def test_household_no_bare_max_members_literal():
    import app.api.v1.household as mod
    src = inspect.getsource(mod)
    # The old module-level MAX_HOUSEHOLD_MEMBERS = 5 should be gone
    assert "MAX_HOUSEHOLD_MEMBERS" not in src


def test_household_no_bare_invitation_expiry_days():
    import app.api.v1.household as mod
    src = inspect.getsource(mod)
    # timedelta(days=7) invite expiry replaced with HOUSEHOLD.INVITATION_EXPIRY_DAYS
    assert "timedelta(days=7)" not in src


def test_household_uses_household_constant():
    import app.api.v1.household as mod
    src = inspect.getsource(mod)
    assert "HOUSEHOLD" in src
    assert "HOUSEHOLD.MAX_MEMBERS" in src
    assert "HOUSEHOLD.INVITATION_EXPIRY_DAYS" in src
