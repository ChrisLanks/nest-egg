"""Tests for PM audit round 24 fixes.

Covers:
- subscriptions.py deactivate_subscription: only checked organization_id,
  allowing any household member to deactivate another user's recurring
  subscription. Fixed to join through Account.user_id so the endpoint
  only operates on subscriptions linked to the requesting user's accounts.
"""

import inspect


def test_deactivate_subscription_joins_account():
    """deactivate_subscription must join Account to verify user_id ownership."""
    from app.api.v1.subscriptions import deactivate_subscription

    source = inspect.getsource(deactivate_subscription)
    assert "Account" in source, (
        "deactivate_subscription must join Account to verify account ownership"
    )
    assert "Account.id == RecurringTransaction.account_id" in source or \
           "account_id" in source, (
        "Must join on RecurringTransaction.account_id"
    )


def test_deactivate_subscription_checks_user_id():
    """deactivate_subscription must filter by Account.user_id == current_user.id."""
    from app.api.v1.subscriptions import deactivate_subscription

    source = inspect.getsource(deactivate_subscription)
    assert "Account.user_id == current_user.id" in source, (
        "deactivate_subscription must verify Account.user_id == current_user.id"
    )


def test_deactivate_subscription_still_checks_org():
    """deactivate_subscription must retain the organization_id filter."""
    from app.api.v1.subscriptions import deactivate_subscription

    source = inspect.getsource(deactivate_subscription)
    assert "organization_id == current_user.organization_id" in source, (
        "deactivate_subscription must retain organization_id filter as defense-in-depth"
    )


def test_deactivate_subscription_user_id_check_before_deactivate():
    """The user_id ownership check must appear before the is_active = False assignment."""
    from app.api.v1.subscriptions import deactivate_subscription

    source = inspect.getsource(deactivate_subscription)
    user_check_pos = source.find("Account.user_id")
    deactivate_pos = source.find("is_active = False")
    assert user_check_pos != -1, "user_id check must exist"
    assert deactivate_pos != -1, "deactivation must exist"
    assert user_check_pos < deactivate_pos, (
        "user_id ownership check must occur before is_active = False"
    )
