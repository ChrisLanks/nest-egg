"""Round 72 bug fix tests: scalar_one() → scalar_one_or_none() in holdings and guest_access."""

import inspect


class TestHoldingsScalarOneOrNone:
    """holdings.py: scalar_one() replaced with scalar_one_or_none() + 404 guard."""

    def test_no_bare_scalar_one_for_user_lookup(self):
        import app.api.v1.holdings as mod

        src = inspect.getsource(mod)
        # The user lookup in the RMD section should use scalar_one_or_none
        # We can verify by checking the pattern is not bare scalar_one() on target_user
        lines = src.splitlines()
        for i, line in enumerate(lines):
            if "target_user = result.scalar_one()" in line:
                raise AssertionError(
                    f"Found bare scalar_one() for target_user at line {i + 1}"
                )

    def test_has_404_guard_after_user_lookup(self):
        import app.api.v1.holdings as mod

        src = inspect.getsource(mod)
        assert "target_user = result.scalar_one_or_none()" in src
        # Should raise 404 if not found
        assert 'raise HTTPException(status_code=404, detail="User not found")' in src


class TestGuestAccessScalarOneOrNone:
    """guest_access.py: scalar_one() replaced with scalar_one_or_none() for email lookup."""

    def test_user_email_uses_scalar_one_or_none(self):
        import app.api.v1.guest_access as mod

        src = inspect.getsource(mod)
        assert "user_email = user_result.scalar_one_or_none()" in src

    def test_no_bare_scalar_one_for_user_email(self):
        import app.api.v1.guest_access as mod

        src = inspect.getsource(mod)
        assert "user_email = user_result.scalar_one()" not in src
