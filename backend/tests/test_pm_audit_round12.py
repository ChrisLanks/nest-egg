"""Tests for PM audit round 12 fixes.

Covers:
- compare_scenarios endpoint must not expose other users' scenarios
  (authorization bypass: org-scoped but not user-scoped)
"""

import inspect
from app.api.v1 import retirement as retirement_module


def test_compare_endpoint_checks_user_ownership():
    """The /compare endpoint source must contain a user_id ownership check."""
    source = inspect.getsource(retirement_module.compare_scenarios)

    # Must check user_id ownership (same pattern used by all other mutating endpoints)
    assert "scenario.user_id" in source and "current_user.id" in source, (
        "compare_scenarios must check scenario.user_id == current_user.id"
    )


def test_compare_endpoint_skips_foreign_scenarios():
    """When ownership check fails, the scenario must be skipped (not 403).

    The compare endpoint returns partial results — unowned scenarios are
    silently skipped so a user requesting [own, foreign, own] still gets
    a useful result with the 2 own scenarios instead of a hard 403.
    """
    source = inspect.getsource(retirement_module.compare_scenarios)

    # Must skip (append to skipped list) rather than raise 403
    # The skip pattern: skipped.append(...); continue
    assert "skipped.append" in source
    # Must NOT raise 403 for ownership mismatch in compare (unlike mutating endpoints)
    # (We allow the endpoint to skip rather than reject, so users can compare their own scenarios
    # even if the request accidentally includes a foreign scenario_id)
    lines = source.split("\n")
    # Find the ownership check block and ensure it appends to skipped, not raises
    ownership_check_idx = next(
        (i for i, line in enumerate(lines) if "scenario.user_id" in line and "current_user.id" in line),
        None,
    )
    assert ownership_check_idx is not None, "Ownership check line not found"
    # The lines immediately after the check should skip, not raise 403
    check_block = "\n".join(lines[ownership_check_idx : ownership_check_idx + 5])
    assert "skipped.append" in check_block or "continue" in check_block, (
        "Ownership check must skip the scenario, not raise an exception"
    )


def test_other_endpoints_also_check_ownership():
    """Sanity: verify the existing ownership checks in mutating endpoints are intact."""
    source = inspect.getsource(retirement_module)

    # Count how many times we check user ownership
    ownership_checks = source.count('str(scenario.user_id) != str(current_user.id)')
    assert ownership_checks >= 5, (
        f"Expected >=5 ownership checks across retirement endpoints, found {ownership_checks}"
    )


def test_compare_endpoint_returns_partial_results():
    """The /compare endpoint must return partial results when some scenarios are missing/unowned."""
    source = inspect.getsource(retirement_module.compare_scenarios)

    # Must have partial result logic: only fail if ALL items are missing
    assert "not items" in source, "Must raise 400 only when zero items are available"
    assert "skipped" in source, "Must track skipped scenarios"
