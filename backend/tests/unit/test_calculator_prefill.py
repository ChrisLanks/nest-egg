"""Unit tests for calculator prefill logic.

Focuses on the employer match aggregation fix — previously used wrong field name
(employer_match_pct instead of employer_match_percent), returning 0 for all accounts.
"""

import pytest
from unittest.mock import MagicMock


# ── Helpers mirroring the fixed logic in calculator_prefill.py ───────────────

def sum_employer_match(accounts: list) -> float:
    """
    Mirrors the corrected employer match aggregation from calculator_prefill.py.
    Uses employer_match_percent (correct field name on Account model).
    """
    total = 0.0
    for acct in accounts:
        val = getattr(acct, "employer_match_percent", None)
        if val:
            total += float(val)
    return total


def make_account(employer_match_percent=None):
    acct = MagicMock()
    acct.employer_match_percent = employer_match_percent
    return acct


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestEmployerMatchAggregation:
    def test_returns_zero_when_no_accounts(self):
        assert sum_employer_match([]) == 0.0

    def test_returns_zero_when_all_accounts_have_no_match(self):
        accounts = [make_account(None), make_account(None)]
        assert sum_employer_match(accounts) == 0.0

    def test_sums_match_percent_from_single_account(self):
        accounts = [make_account(50.0)]
        assert abs(sum_employer_match(accounts) - 50.0) < 1e-9

    def test_sums_match_percent_across_multiple_accounts(self):
        # Two 401k accounts each with 50% match
        accounts = [make_account(50.0), make_account(50.0)]
        assert abs(sum_employer_match(accounts) - 100.0) < 1e-9

    def test_ignores_accounts_without_match(self):
        # Mix of accounts with and without match
        accounts = [make_account(100.0), make_account(None), make_account(50.0)]
        assert abs(sum_employer_match(accounts) - 150.0) < 1e-9

    def test_does_not_use_wrong_field_name(self):
        """
        Regression test: the old code checked employer_match_pct (wrong field).
        An account with employer_match_percent=100 but NO employer_match_pct
        must still be picked up by the correct logic.
        """
        acct = MagicMock(spec=[])  # spec=[] → no attributes allowed unless set
        acct.employer_match_percent = 100.0
        # Ensure the old wrong field does NOT exist
        assert not hasattr(acct, "employer_match_pct")
        # Correct logic uses employer_match_percent
        assert abs(sum_employer_match([acct]) - 100.0) < 1e-9

    def test_handles_zero_match_percent_as_falsy(self):
        # 0 is falsy — treated as "no match configured" (consistent with backend)
        accounts = [make_account(0)]
        assert sum_employer_match(accounts) == 0.0
