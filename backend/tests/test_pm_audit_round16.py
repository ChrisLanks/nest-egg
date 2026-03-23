"""Tests for PM audit round 16 fixes.

Covers:
- verify_household_member called with wrong argument order at line 403 of
  recurring_transactions.py — would crash at runtime when user_id is provided
  to the /price-increases endpoint.
"""

import inspect


def test_price_increases_verify_call_correct_order():
    """All verify_household_member calls in recurring_transactions must use (db, user_id, org_id)."""
    from app.api.v1 import recurring_transactions as rt_module

    source = inspect.getsource(rt_module)

    # The buggy pattern: (user_id, current_user, db) — wrong order
    assert "verify_household_member(user_id, current_user, db)" not in source, (
        "Wrong-order verify_household_member call must be removed"
    )
    # The correct pattern must be present at least 4 times (one per endpoint that uses it)
    correct_calls = source.count("verify_household_member(db, user_id, current_user.organization_id)")
    assert correct_calls >= 4, (
        f"Expected >= 4 correct verify_household_member(db, user_id, org_id) calls, found {correct_calls}"
    )


def test_verify_household_member_signature():
    """Confirm the canonical signature is (db, user_id, organization_id)."""
    from app.dependencies import verify_household_member
    import inspect as ins

    sig = ins.signature(verify_household_member)
    params = list(sig.parameters.keys())
    assert params[0] == "db", f"First param must be 'db', got '{params[0]}'"
    assert params[1] == "user_id", f"Second param must be 'user_id', got '{params[1]}'"
    assert params[2] == "organization_id", f"Third param must be 'organization_id', got '{params[2]}'"


def test_no_wrong_order_calls_anywhere():
    """Scan all api/v1 files for the wrong-order verify_household_member call pattern."""
    import os
    import glob

    api_dir = "/home/lanx/git/nest-egg/backend/app/api/v1"
    wrong_pattern = "verify_household_member(user_id, current_user, db)"

    found_in = []
    for path in glob.glob(os.path.join(api_dir, "*.py")):
        with open(path) as f:
            content = f.read()
        if wrong_pattern in content:
            found_in.append(os.path.basename(path))

    assert not found_in, (
        f"Wrong-order verify_household_member call found in: {found_in}"
    )
