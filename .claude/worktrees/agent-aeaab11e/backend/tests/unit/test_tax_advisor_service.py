"""Tests for the age-based tax advisor service.

Covers:
- Long-term capital gains rate lookup
- Social Security benefit taxation percentage
- Net Investment Income Tax (NII) surtax calculation
- Contribution limit generation by age
"""

import pytest

from app.constants.financial import MEDICARE, RETIREMENT
from app.services.tax_advisor_service import (
    _add_contribution_limits,
    compute_nii_surtax,
    get_ltcg_rate,
    get_ss_taxable_pct,
)

# ── LTCG rate lookup ───────────────────────────────────────────────────────


class TestGetLTCGRate:
    def test_zero_percent_bracket_single(self):
        assert get_ltcg_rate(30_000, "single") == 0.00
        assert get_ltcg_rate(47_025, "single") == 0.00

    def test_fifteen_percent_bracket_single(self):
        assert get_ltcg_rate(50_000, "single") == 0.15
        assert get_ltcg_rate(200_000, "single") == 0.15
        assert get_ltcg_rate(518_900, "single") == 0.15

    def test_twenty_percent_bracket_single(self):
        assert get_ltcg_rate(600_000, "single") == 0.20
        assert get_ltcg_rate(1_000_000, "single") == 0.20

    def test_married_higher_thresholds(self):
        # $80k is in 0% bracket for married, 15% for single
        assert get_ltcg_rate(80_000, "married") == 0.00
        assert get_ltcg_rate(80_000, "single") == 0.15

    def test_zero_income(self):
        assert get_ltcg_rate(0, "single") == 0.00

    def test_negative_income(self):
        assert get_ltcg_rate(-10_000, "single") == 0.00


# ── SS benefit taxation ────────────────────────────────────────────────────


class TestGetSSTaxablePct:
    def test_below_threshold_single(self):
        assert get_ss_taxable_pct(20_000, "single") == 0.00
        assert get_ss_taxable_pct(25_000, "single") == 0.00

    def test_fifty_pct_bracket_single(self):
        assert get_ss_taxable_pct(30_000, "single") == 0.50

    def test_eighty_five_pct_bracket_single(self):
        assert get_ss_taxable_pct(50_000, "single") == 0.85
        assert get_ss_taxable_pct(100_000, "single") == 0.85

    def test_married_thresholds_higher(self):
        # $30k: 0% for married, 50% for single
        assert get_ss_taxable_pct(30_000, "married") == 0.00
        assert get_ss_taxable_pct(30_000, "single") == 0.50


# ── NII surtax ─────────────────────────────────────────────────────────────


class TestComputeNIISurtax:
    def test_below_threshold_no_tax(self):
        assert compute_nii_surtax(150_000, 50_000, "single") == 0.0

    def test_at_threshold_no_tax(self):
        assert compute_nii_surtax(200_000, 50_000, "single") == 0.0

    def test_above_threshold_single(self):
        # MAGI = $250k, NII = $80k
        # Excess = $50k, taxable NII = min($50k, $80k) = $50k
        # Tax = $50k * 0.038 = $1,900
        result = compute_nii_surtax(250_000, 80_000, "single")
        assert result == 1_900.0

    def test_nii_less_than_excess(self):
        # MAGI = $300k, NII = $20k
        # Excess = $100k, taxable NII = min($100k, $20k) = $20k
        # Tax = $20k * 0.038 = $760
        result = compute_nii_surtax(300_000, 20_000, "single")
        assert result == 760.0

    def test_married_threshold(self):
        # Below married threshold ($250k): no tax
        assert compute_nii_surtax(240_000, 100_000, "married") == 0.0
        # Above married threshold
        result = compute_nii_surtax(300_000, 100_000, "married")
        assert result == pytest.approx(1_900.0)


# ── Contribution limits ────────────────────────────────────────────────────


class TestContributionLimits:
    def test_under_50_no_catch_up(self):
        limits = []
        _add_contribution_limits(35, limits)
        ira = next(x for x in limits if "IRA" in x["account_type"])
        assert ira["catch_up_eligible"] is False
        assert ira["catch_up_limit"] == 0
        assert ira["total_limit"] == RETIREMENT.LIMIT_IRA

    def test_over_50_catch_up(self):
        limits = []
        _add_contribution_limits(RETIREMENT.CATCH_UP_AGE_401K + 1, limits)
        k401 = next(x for x in limits if "401k" in x["account_type"])
        assert k401["catch_up_eligible"] is True
        assert k401["total_limit"] == RETIREMENT.LIMIT_401K + RETIREMENT.LIMIT_401K_CATCH_UP

    def test_hsa_not_shown_after_65(self):
        limits = []
        _add_contribution_limits(MEDICARE.ELIGIBILITY_AGE + 1, limits)
        hsa_limits = [x for x in limits if "HSA" in x["account_type"]]
        assert len(hsa_limits) == 0

    def test_hsa_catch_up_at_55(self):
        limits = []
        _add_contribution_limits(RETIREMENT.CATCH_UP_AGE_HSA + 2, limits)
        hsa = next(x for x in limits if "HSA" in x["account_type"])
        assert hsa["catch_up_eligible"] is True
        assert hsa["catch_up_limit"] == RETIREMENT.LIMIT_HSA_CATCH_UP

    def test_529_always_included(self):
        for age in [25, 45, 70]:
            limits = []
            _add_contribution_limits(age, limits)
            plan529 = [x for x in limits if "529" in x["account_type"]]
            assert len(plan529) == 1
            assert plan529[0]["annual_gift_exclusion"] == RETIREMENT.LIMIT_529_ANNUAL_GIFT_EXCLUSION
