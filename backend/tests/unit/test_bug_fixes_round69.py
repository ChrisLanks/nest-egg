"""
Tests for round-69 bug fixes:
1. household.py: scalar_one() → scalar_one_or_none() for invited_by user lookup
2. guest_access.py: scalar_one() → scalar_one_or_none() for org name lookups
"""
import inspect


class TestScalarOneOrNone:
    """scalar_one() raises NoResultFound; scalar_one_or_none() is safe for optional relations."""

    def test_household_invited_by_uses_scalar_one_or_none(self):
        import app.api.v1.household as hh_module
        source = inspect.getsource(hh_module)
        # The invited_by lookup must use scalar_one_or_none, not scalar_one
        # Find the section near "invited_by_user_id"
        assert "invited_by = result.scalar_one()" not in source, (
            "household.py: invited_by lookup must use scalar_one_or_none() to handle deleted users"
        )
        assert "invited_by = result.scalar_one_or_none()" in source

    def test_guest_access_org_name_uses_scalar_one_or_none(self):
        import app.api.v1.guest_access as ga_module
        source = inspect.getsource(ga_module)
        # Both org name lookups must use scalar_one_or_none
        assert "household_name = org_name_result.scalar_one()" not in source, (
            "guest_access.py: household_name lookup must use scalar_one_or_none()"
        )
        assert "org_name = org_result.scalar_one()" not in source, (
            "guest_access.py: org_name lookup must use scalar_one_or_none()"
        )
        assert "scalar_one_or_none() or" in source, (
            "guest_access.py: org name lookups must have a fallback default"
        )
