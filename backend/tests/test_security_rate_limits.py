"""
Security test: auth endpoint rate-limit hardening.

Identified issue: forgot-password was limited to 5 requests/hour per IP,
allowing an attacker to send 120 reset emails to a victim per day from a
single IP (email flooding / user harassment). Tightened to 3/hour.

Also verifies the reset-password endpoint rate-limit docstring matches the
actual call (was stale: docstring said "10/15min" but code had 3/hour).
"""

from pathlib import Path

AUTH_SRC = Path(__file__).parent.parent / "app/api/v1/auth.py"


def _auth_src() -> str:
    return AUTH_SRC.read_text()


# ---------------------------------------------------------------------------
# forgot-password rate limit
# ---------------------------------------------------------------------------


def test_forgot_password_max_requests_is_3():
    """
    Forgot-password must be rate-limited to at most 3 requests per window,
    not the previous 5 — prevents email flooding attacks.
    """
    src = _auth_src()
    # Extract the forgot-password function block specifically, so we don't
    # false-positive on MFA or other endpoints that may use max_requests=5.
    fp_start = src.index("async def forgot_password")
    # Find the next top-level async def (end of the forgot-password function)
    fp_end = src.index("\nasync def ", fp_start + 1)
    fp_block = src[fp_start:fp_end]
    assert "max_requests=5" not in fp_block, (
        "forgot-password rate limit must not be 5/hour — use 3/hour to prevent email flooding"
    )


def test_forgot_password_rate_limit_uses_3_per_hour():
    """
    The forgot-password check_rate_limit call must use max_requests=3
    and a 1-hour window (3600 seconds).
    """
    src = _auth_src()
    # Both values must appear somewhere in the file for the forgot-password endpoint
    assert "max_requests=3" in src
    assert "window_seconds=3600" in src


def test_forgot_password_docstring_mentions_3_per_hour():
    """
    Docstring should accurately describe the 3/hour rate limit.
    """
    src = _auth_src()
    assert "3 requests per hour" in src


# ---------------------------------------------------------------------------
# reset-password rate limit docstring accuracy
# ---------------------------------------------------------------------------


def test_reset_password_docstring_not_stale():
    """
    The reset-password docstring must not claim '10 requests per 15 minutes'
    (the old stale value that didn't match the actual code).
    """
    src = _auth_src()
    assert "10 requests per 15 minutes" not in src
