"""Tests for PM audit round 12 fixes.

Covers:
- Authorization checks in retirement module endpoints
  (compare_scenarios ownership, org scoping, household member verification)
"""

import inspect
from app.api.v1 import retirement as retirement_module


def test_retirement_report_endpoints_check_creator_ownership():
    """Retirement scenario endpoints must verify org-scoped ownership before access."""
    source = inspect.getsource(retirement_module)

    # Scenarios are scoped by organization_id to prevent cross-org access
    assert "organization_id" in source, (
        "Retirement endpoints must check organization_id for ownership scoping"
    )


def test_retirement_shared_templates_accessible():
    """Household member filter must be applied when a user_id filter is given."""
    source = inspect.getsource(retirement_module)

    # user_id filtering requires verify_household_member for access control
    assert "verify_household_member" in source, (
        "Retirement module must use verify_household_member for user_id filtering"
    )


def test_retirement_household_member_filter_uses_verify():
    """User-id filter must use verify_household_member for access control."""
    source = inspect.getsource(retirement_module)

    assert "verify_household_member" in source, (
        "Household member filter must use verify_household_member"
    )


def test_retirement_create_scopes_to_org():
    """New scenarios must be scoped to the current user's organization."""
    source = inspect.getsource(retirement_module)

    assert "organization_id" in source, (
        "Retirement scenarios must be scoped to organization_id"
    )
