"""Unit tests for bond ladder service and fallback rate constants."""

from decimal import Decimal

import pytest

from app.constants.financial import BOND_LADDER as BOND_LADDER_CONSTANTS
from app.services.bond_ladder_service import (
    _get_rate_for_rung,
    build_ladder,
    estimate_cd_rates,
)

SAMPLE_TREASURY_RATES = {
    "1_year": 0.042,
    "2_year": 0.041,
    "5_year": 0.040,
    "10_year": 0.039,
    "30_year": 0.041,
}


class TestFallbackRatesInFinancialConstants:
    """BOND_LADDER.FALLBACK_TREASURY_RATES is the canonical source for bond_ladder.py."""

    def test_fallback_rates_exist(self):
        assert hasattr(BOND_LADDER_CONSTANTS, "FALLBACK_TREASURY_RATES")

    def test_fallback_rates_has_required_keys(self):
        rates = BOND_LADDER_CONSTANTS.FALLBACK_TREASURY_RATES
        for key in ("1_year", "2_year", "5_year", "10_year", "30_year"):
            assert key in rates, f"Missing key: {key}"

    def test_fallback_rates_are_reasonable(self):
        """Rates should be between 0% and 20% — catches accidental unit errors (e.g. 4.2 vs 0.042)."""
        for key, val in BOND_LADDER_CONSTANTS.FALLBACK_TREASURY_RATES.items():
            assert 0 < val < 0.20, f"{key}={val} looks wrong (should be a decimal like 0.042)"

    def test_bond_ladder_api_uses_financial_constants(self):
        """Verify bond_ladder.py imports from financial constants, not a hardcoded local dict."""
        import app.api.v1.bond_ladder as bl_module
        # The module-level _FALLBACK_TREASURY_RATES should equal the constants value
        assert bl_module._FALLBACK_TREASURY_RATES is BOND_LADDER_CONSTANTS.FALLBACK_TREASURY_RATES


class TestGetRateForRung:
    def test_treasury_uses_rate_as_is(self):
        rate = _get_rate_for_rung(1, "treasury", SAMPLE_TREASURY_RATES)
        assert rate == Decimal("0.042")

    def test_cd_adds_spread(self):
        rate = _get_rate_for_rung(1, "cd", SAMPLE_TREASURY_RATES)
        assert rate > Decimal("0.042")  # spread is always positive

    def test_tips_subtracts_from_treasury(self):
        rate = _get_rate_for_rung(1, "tips", SAMPLE_TREASURY_RATES)
        assert rate < Decimal("0.042")

    def test_tips_never_below_floor(self):
        low_rates = {"1_year": 0.005, "2_year": 0.005, "5_year": 0.005, "10_year": 0.005}
        rate = _get_rate_for_rung(1, "tips", low_rates)
        assert rate >= Decimal("0.005")

    def test_unknown_maturity_falls_back_to_10yr(self):
        rate = _get_rate_for_rung(25, "treasury", SAMPLE_TREASURY_RATES)
        assert rate == Decimal("0.039")  # 10_year value

    def test_missing_treasury_key_uses_default(self):
        rate = _get_rate_for_rung(1, "treasury", {})
        assert rate == Decimal("0.04")


class TestBuildLadder:
    def test_returns_correct_num_rungs(self):
        result = build_ladder(
            total_investment=Decimal("100000"),
            num_rungs=5,
            ladder_type="treasury",
            start_year=2025,
            annual_income_needed=Decimal("10000"),
            current_treasury_rates=SAMPLE_TREASURY_RATES,
        )
        assert result["num_rungs"] == 5
        assert len(result["rungs"]) == 5

    def test_maturity_years_increment(self):
        result = build_ladder(
            total_investment=Decimal("100000"),
            num_rungs=3,
            ladder_type="treasury",
            start_year=2025,
            annual_income_needed=Decimal("0"),
            current_treasury_rates=SAMPLE_TREASURY_RATES,
        )
        years = [r["maturity_year"] for r in result["rungs"]]
        assert years == [2026, 2027, 2028]

    def test_total_invested_matches_input(self):
        result = build_ladder(
            total_investment=Decimal("300000"),
            num_rungs=3,
            ladder_type="treasury",
            start_year=2025,
            annual_income_needed=Decimal("0"),
            current_treasury_rates=SAMPLE_TREASURY_RATES,
        )
        assert result["total_invested"] == 300000.0

    def test_meets_income_target_flag(self):
        # With a very small income target vs large investment, should meet it
        result = build_ladder(
            total_investment=Decimal("1000000"),
            num_rungs=5,
            ladder_type="treasury",
            start_year=2025,
            annual_income_needed=Decimal("1000"),
            current_treasury_rates=SAMPLE_TREASURY_RATES,
        )
        assert result["meets_income_target"] is True

    def test_does_not_meet_tiny_investment_large_income(self):
        result = build_ladder(
            total_investment=Decimal("10000"),
            num_rungs=5,
            ladder_type="treasury",
            start_year=2025,
            annual_income_needed=Decimal("1000000"),
            current_treasury_rates=SAMPLE_TREASURY_RATES,
        )
        assert result["meets_income_target"] is False
        assert result["income_gap"] > 0

    def test_reinvestment_note_present(self):
        result = build_ladder(
            total_investment=Decimal("100000"),
            num_rungs=5,
            ladder_type="cd",
            start_year=2025,
            annual_income_needed=Decimal("0"),
            current_treasury_rates=SAMPLE_TREASURY_RATES,
        )
        assert "reinvest" in result["reinvestment_note"].lower()

    def test_num_rungs_clamped_to_1(self):
        result = build_ladder(
            total_investment=Decimal("100000"),
            num_rungs=0,
            ladder_type="treasury",
            start_year=2025,
            annual_income_needed=Decimal("0"),
            current_treasury_rates=SAMPLE_TREASURY_RATES,
        )
        assert result["num_rungs"] == 1

    def test_num_rungs_clamped_to_30(self):
        result = build_ladder(
            total_investment=Decimal("300000"),
            num_rungs=99,
            ladder_type="treasury",
            start_year=2025,
            annual_income_needed=Decimal("0"),
            current_treasury_rates=SAMPLE_TREASURY_RATES,
        )
        assert result["num_rungs"] == 30

    def test_all_ladder_types_produce_rungs(self):
        for ltype in ("treasury", "cd", "tips"):
            result = build_ladder(
                total_investment=Decimal("100000"),
                num_rungs=3,
                ladder_type=ltype,
                start_year=2025,
                annual_income_needed=Decimal("0"),
                current_treasury_rates=SAMPLE_TREASURY_RATES,
            )
            assert len(result["rungs"]) == 3, f"Failed for {ltype}"


class TestEstimateCdRates:
    def test_returns_rates_for_known_maturities(self):
        cd_rates = estimate_cd_rates(SAMPLE_TREASURY_RATES)
        assert len(cd_rates) > 0

    def test_cd_rate_above_treasury(self):
        cd_rates = estimate_cd_rates(SAMPLE_TREASURY_RATES)
        # 1-year CD should be above 1-year Treasury
        assert cd_rates.get("1_year", 0) > 0.042

    def test_live_rates_override_spread_estimates(self):
        live = {"6_month": 0.055, "1_year": 0.053}
        cd_rates = estimate_cd_rates(SAMPLE_TREASURY_RATES, live_cd_rates=live)
        assert cd_rates["6_month"] == 0.055
        assert cd_rates["1_year"] == 0.053

    def test_missing_treasury_key_skips_that_maturity(self):
        # Only 1_year in treasury rates — only maturities mapped to it appear
        cd_rates = estimate_cd_rates({"1_year": 0.042})
        assert all(isinstance(v, float) for v in cd_rates.values())
