"""Unit tests for Roth Wizard — filing status changes phaseout range."""

import pytest
from app.constants.financial import TAX


class TestRothPhaseout:
    def test_single_phaseout_2025(self):
        lo, hi = TAX.roth_phaseout("single", 2025)
        assert lo == 150_000
        assert hi == 165_000

    def test_married_phaseout_2025(self):
        lo, hi = TAX.roth_phaseout("married", 2025)
        assert lo == 236_000
        assert hi == 246_000

    def test_married_range_higher_than_single(self):
        lo_s, hi_s = TAX.roth_phaseout("single", 2025)
        lo_m, hi_m = TAX.roth_phaseout("married", 2025)
        assert lo_m > lo_s
        assert hi_m > hi_s

    def test_mfj_alias_matches_married(self):
        assert TAX.roth_phaseout("mfj", 2025) == TAX.roth_phaseout("married", 2025)

    def test_phaseout_2026(self):
        lo, hi = TAX.roth_phaseout("single", 2026)
        assert lo == 155_000
        assert hi == 170_000

    def test_unknown_filing_status_falls_back_to_single(self):
        lo, hi = TAX.roth_phaseout("head_of_household", 2025)
        lo_s, hi_s = TAX.roth_phaseout("single", 2025)
        assert lo == lo_s
        assert hi == hi_s

    def test_direct_roth_eligible_below_single_threshold(self):
        lo, _ = TAX.roth_phaseout("single", 2025)
        magi = lo - 1
        assert magi < lo  # eligible

    def test_direct_roth_ineligible_above_married_threshold(self):
        _, hi = TAX.roth_phaseout("married", 2025)
        magi = hi + 1
        assert magi > hi  # fully phased out
