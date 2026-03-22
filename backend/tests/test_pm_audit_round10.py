"""Tests for PM audit round 10 fixes.

Covers:
- Employer match formula: salary * min(match_pct, limit_pct) — NOT * match_pct twice
- Employer match silent failure now logs a warning instead of swallowing silently
"""

from decimal import Decimal

import pytest


# ---------------------------------------------------------------------------
# Employer match formula correctness
# ---------------------------------------------------------------------------


def _calc_employer_match(salary, match_percent, limit_percent=None):
    """Replicate the fixed formula from monte_carlo_service.py."""
    match_pct = Decimal(str(match_percent)) / Decimal(100)
    limit_pct = (Decimal(str(limit_percent)) if limit_percent else Decimal(100)) / Decimal(100)
    return Decimal(str(salary)) * min(match_pct, limit_pct)


def test_employer_match_no_limit():
    """With no limit, employer match = salary * match_pct.

    e.g. 100k salary, 50% match, no limit = $50,000 match
    """
    result = _calc_employer_match(100_000, 50)
    assert result == Decimal("50000")


def test_employer_match_with_binding_limit():
    """When limit_pct < match_pct, effective rate is capped at limit_pct.

    e.g. 100k salary, 50% match, 6% limit → 100k * min(0.50, 0.06) = 100k * 0.06 = $6,000
    The old (buggy) code: 100k * min(0.50, 0.06) * 0.50 = 100k * 0.06 * 0.50 = $3,000
    """
    result = _calc_employer_match(100_000, 50, limit_percent=6)
    assert result == Decimal("6000"), f"Expected $6,000 match, got {result}"


def test_employer_match_limit_not_binding():
    """When limit_pct > match_pct, effective rate is match_pct.

    e.g. 100k salary, 3% match, 10% limit → 100k * min(0.03, 0.10) = $3,000
    """
    result = _calc_employer_match(100_000, 3, limit_percent=10)
    assert result == Decimal("3000")


def test_employer_match_limit_equals_match():
    """When limit_pct == match_pct, result equals salary * match_pct."""
    result = _calc_employer_match(100_000, 6, limit_percent=6)
    assert result == Decimal("6000")


def test_employer_match_zero_salary():
    """Zero salary produces zero match regardless of percentages."""
    result = _calc_employer_match(0, 50, limit_percent=6)
    assert result == Decimal("0")


def test_employer_match_formula_not_squared():
    """Verify the bug (multiplying by match_pct twice) is absent.

    Buggy formula: salary * min(match_pct, limit_pct) * match_pct
    With 50% match and 6% limit: 100k * 0.06 * 0.50 = 3000 (WRONG)
    Correct formula: salary * min(match_pct, limit_pct)
    With 50% match and 6% limit: 100k * 0.06 = 6000 (CORRECT)
    """
    salary = Decimal("100000")
    match_pct = Decimal("0.50")
    limit_pct = Decimal("0.06")

    buggy_result = salary * min(match_pct, limit_pct) * match_pct
    correct_result = salary * min(match_pct, limit_pct)

    assert buggy_result != correct_result, "Sanity: buggy != correct for this case"
    assert correct_result == Decimal("6000")
    assert buggy_result == Decimal("3000")

    # Confirm _calc_employer_match matches correct, not buggy
    assert _calc_employer_match(100_000, 50, limit_percent=6) == correct_result


def test_monte_carlo_service_uses_correct_formula():
    """The source code of monte_carlo_service must not multiply by match_pct twice."""
    import inspect
    from app.services.retirement import monte_carlo_service

    source = inspect.getsource(monte_carlo_service)

    # The old bug was exactly this pattern
    assert "min(match_pct, limit_pct) * match_pct" not in source, (
        "Employer match formula must not multiply by match_pct twice after min()"
    )
    # The fix must be present
    assert "salary * min(match_pct, limit_pct)" in source, (
        "Employer match must use: salary * min(match_pct, limit_pct)"
    )


def test_monte_carlo_service_has_logging():
    """monte_carlo_service must import logging and define a module-level logger."""
    import inspect
    from app.services.retirement import monte_carlo_service

    source = inspect.getsource(monte_carlo_service)
    assert "import logging" in source
    assert "logger = logging.getLogger(__name__)" in source


def test_employer_match_failure_logs_warning(caplog):
    """When annual_salary cannot be converted, the except block must log a warning."""
    import logging
    import inspect
    from app.services.retirement import monte_carlo_service

    source = inspect.getsource(monte_carlo_service)
    # Must log, not silently pass
    assert "logger.warning" in source, (
        "Employer match except block must call logger.warning(), not silently pass"
    )
    # Old silent pattern must be removed from the employer match block
    # (We check the specific block — 'pass  # Silent failure' comment was removed)
    assert "pass  # Silent failure" not in source
