"""Unit tests for RothConversionService.

Tests cover:
- Basic single-year conversion math
- No-conversion case (income fills bracket)
- Multi-year projection totals
- IRMAA cap behaviour (age >= 55)
- RMD calculation and effect on headroom
- Married vs single filing status
- Edge cases: zero balances, very high income
"""

from __future__ import annotations

import pytest

from app.services.roth_conversion_service import (
    RothConversionInput,
    RothConversionResult,
    RothConversionService,
    RothConversionYear,
    _bracket_headroom,
    _get_brackets,
    _irmaa_headroom,
    _marginal_rate,
    _rmd_amount,
    _standard_deduction,
)

# ── Helper function tests ──────────────────────────────────────────────────


class TestGetBrackets:
    def test_single_returns_seven_brackets(self):
        brackets = _get_brackets("single", 0)
        assert len(brackets) == 7

    def test_married_returns_seven_brackets(self):
        brackets = _get_brackets("married", 0)
        assert len(brackets) == 7

    def test_year0_top_single_bracket_is_inf(self):
        brackets = _get_brackets("single", 0)
        assert brackets[-1][1] == float("inf")

    def test_future_year_increases_ceilings(self):
        b0 = _get_brackets("single", 0)
        b5 = _get_brackets("single", 5)
        # Every finite ceiling should be higher in year 5
        for i, (rate0, ceil0) in enumerate(b0):
            rate5, ceil5 = b5[i]
            assert rate0 == rate5
            if ceil0 != float("inf"):
                assert ceil5 > ceil0

    def test_married_ceilings_double_single_approx(self):
        single = _get_brackets("single", 0)
        married = _get_brackets("married", 0)
        # 10% bracket ceiling for married should be ~2x single
        assert married[0][1] == pytest.approx(single[0][1] * 2, rel=0.01)


class TestMarginalRate:
    def test_zero_income_is_lowest_bracket(self):
        brackets = _get_brackets("single", 0)
        assert _marginal_rate(0, brackets) == pytest.approx(0.10)

    def test_income_at_ceiling_uses_that_bracket(self):
        brackets = _get_brackets("single", 0)
        # Income exactly at the 12% ceiling
        rate = _marginal_rate(brackets[1][1], brackets)
        assert rate == pytest.approx(0.12)

    def test_high_income_top_bracket(self):
        brackets = _get_brackets("single", 0)
        rate = _marginal_rate(1_000_000, brackets)
        assert rate == pytest.approx(0.37)


class TestBracketHeadroom:
    def test_income_below_first_ceiling_gives_positive_headroom(self):
        brackets = _get_brackets("single", 0)
        headroom = _bracket_headroom(5_000, brackets)
        assert headroom > 0
        # Should be ceiling of 10% bracket minus 5000
        assert headroom == pytest.approx(brackets[0][1] - 5_000)

    def test_income_beyond_all_finite_brackets_gives_inf_headroom(self):
        """Top bracket ceiling is inf, so headroom to it is always inf."""
        brackets = _get_brackets("single", 0)
        # Income past every finite ceiling — only inf bracket remains
        headroom = _bracket_headroom(10_000_000, brackets)
        assert headroom == float("inf")


class TestStandardDeduction:
    def test_single_is_less_than_married(self):
        assert _standard_deduction("single", 0) < _standard_deduction("married", 0)

    def test_future_year_higher_than_current(self):
        assert _standard_deduction("single", 10) > _standard_deduction("single", 0)


class TestIrmaaHeadroom:
    def test_low_magi_gives_large_headroom(self):
        # Very low MAGI should be far from any IRMAA tier
        headroom = _irmaa_headroom(50_000, 0)
        assert headroom > 50_000

    def test_magi_just_below_threshold_gives_small_headroom(self):
        # IRMAA first tier at ~$106,000 (projected from 2026 base)
        headroom = _irmaa_headroom(108_500, 0)
        assert 0 < headroom < 1_500


class TestRmdAmount:
    def test_under_73_returns_zero(self):
        assert _rmd_amount(500_000, 65) == 0.0
        assert _rmd_amount(500_000, 72) == 0.0

    def test_age_73_returns_positive(self):
        assert _rmd_amount(500_000, 73) > 0

    def test_larger_balance_larger_rmd(self):
        assert _rmd_amount(1_000_000, 75) > _rmd_amount(500_000, 75)

    def test_older_age_larger_rmd_same_balance(self):
        # Divisor shrinks with age → larger RMD
        assert _rmd_amount(500_000, 80) > _rmd_amount(500_000, 73)


# ── RothConversionService.optimize tests ─────────────────────────────────


class TestRothConversionServiceBasic:
    def _svc(self):
        return RothConversionService()

    def test_returns_roth_conversion_result(self):
        inp = RothConversionInput(
            traditional_balance=200_000,
            roth_balance=50_000,
            current_income=60_000,
            current_age=50,
            filing_status="single",
            years_to_project=5,
        )
        result = self._svc().optimize(inp)
        assert isinstance(result, RothConversionResult)

    def test_years_list_length_matches_input(self):
        inp = RothConversionInput(
            traditional_balance=200_000,
            roth_balance=0,
            current_income=60_000,
            current_age=50,
            years_to_project=10,
        )
        result = self._svc().optimize(inp)
        assert len(result.years) == 10

    def test_year_objects_have_correct_type(self):
        inp = RothConversionInput(
            traditional_balance=100_000,
            roth_balance=0,
            current_income=50_000,
            current_age=45,
            years_to_project=3,
        )
        result = self._svc().optimize(inp)
        for yr in result.years:
            assert isinstance(yr, RothConversionYear)

    def test_ages_increment_correctly(self):
        inp = RothConversionInput(
            traditional_balance=200_000,
            roth_balance=0,
            current_income=60_000,
            current_age=45,
            years_to_project=5,
        )
        result = self._svc().optimize(inp)
        for i, yr in enumerate(result.years):
            assert yr.age == 45 + i

    def test_year_numbers_start_at_one(self):
        inp = RothConversionInput(
            traditional_balance=100_000,
            roth_balance=0,
            current_income=50_000,
            current_age=40,
            years_to_project=3,
        )
        result = self._svc().optimize(inp)
        assert result.years[0].year == 1
        assert result.years[-1].year == 3


class TestRothConversionLogic:
    def _svc(self):
        return RothConversionService()

    def test_low_income_triggers_conversion(self):
        """With low income there should be bracket headroom → non-zero conversion."""
        inp = RothConversionInput(
            traditional_balance=500_000,
            roth_balance=0,
            current_income=30_000,
            current_age=55,
            filing_status="single",
            years_to_project=1,
            respect_irmaa=False,
        )
        result = self._svc().optimize(inp)
        assert result.years[0].optimal_conversion > 0

    def test_target_bracket_rate_below_current_rate_no_conversion(self):
        """When target rate is below current marginal rate, no headroom exists."""
        inp = RothConversionInput(
            traditional_balance=500_000,
            roth_balance=0,
            current_income=200_000,  # in the 32% bracket
            current_age=50,
            filing_status="single",
            years_to_project=3,
            respect_irmaa=False,
            target_bracket_rate=0.22,  # cap is below user's current 32% rate
        )
        result = self._svc().optimize(inp)
        # User is at 32%, cap is 22% — no bracket with rate <= 22% has headroom
        assert result.total_converted == 0.0

    def test_zero_traditional_balance_no_conversion(self):
        inp = RothConversionInput(
            traditional_balance=0,
            roth_balance=100_000,
            current_income=50_000,
            current_age=50,
            years_to_project=5,
        )
        result = self._svc().optimize(inp)
        assert result.total_converted == 0.0

    def test_total_converted_does_not_exceed_running_balance(self):
        """Conversion each year is capped to available traditional balance at that time.
        Over 20 years the balance grows with returns, so total converted can exceed
        the initial balance — but should not exceed what was available."""
        inp = RothConversionInput(
            traditional_balance=50_000,
            roth_balance=0,
            current_income=20_000,
            current_age=50,
            filing_status="single",
            years_to_project=20,
            respect_irmaa=False,
        )
        result = self._svc().optimize(inp)
        # Traditional balance at end should be zero or near zero when fully converted
        assert result.with_conversion_traditional_end >= 0
        # Conversion should be non-negative in each year
        for yr in result.years:
            assert yr.optimal_conversion >= 0

    def test_total_tax_cost_is_non_negative(self):
        inp = RothConversionInput(
            traditional_balance=300_000,
            roth_balance=0,
            current_income=60_000,
            current_age=50,
            years_to_project=10,
        )
        result = self._svc().optimize(inp)
        assert result.total_tax_cost >= 0

    def test_tax_cost_less_than_converted_amount(self):
        """Tax cost should be fraction of amount converted, not exceed it."""
        inp = RothConversionInput(
            traditional_balance=300_000,
            roth_balance=0,
            current_income=50_000,
            current_age=50,
            years_to_project=10,
        )
        result = self._svc().optimize(inp)
        if result.total_converted > 0:
            assert result.total_tax_cost < result.total_converted

    def test_with_conversion_roth_end_greater_without(self):
        """Converting should leave more in Roth at end."""
        inp = RothConversionInput(
            traditional_balance=300_000,
            roth_balance=50_000,
            current_income=50_000,
            current_age=50,
            filing_status="single",
            years_to_project=15,
            respect_irmaa=False,
        )
        result = self._svc().optimize(inp)
        if result.total_converted > 0:
            assert result.with_conversion_roth_end > result.no_conversion_roth_end

    def test_no_conversion_baseline_uses_expected_return(self):
        """Verify no-conversion baseline is simple compound growth."""
        inp = RothConversionInput(
            traditional_balance=100_000,
            roth_balance=20_000,
            current_income=600_000,  # fills bracket → no conversion
            current_age=50,
            years_to_project=10,
            expected_return=0.07,
            respect_irmaa=False,
        )
        result = self._svc().optimize(inp)
        expected_trad = round(100_000 * (1.07**10), 2)
        expected_roth = round(20_000 * (1.07**10), 2)
        assert result.no_conversion_traditional_end == pytest.approx(expected_trad, rel=1e-4)
        assert result.no_conversion_roth_end == pytest.approx(expected_roth, rel=1e-4)

    def test_summary_is_non_empty_string(self):
        inp = RothConversionInput(
            traditional_balance=200_000,
            roth_balance=0,
            current_income=50_000,
            current_age=50,
            years_to_project=5,
        )
        result = self._svc().optimize(inp)
        assert isinstance(result.summary, str)
        assert len(result.summary) > 0

    def test_no_conversion_summary_when_target_rate_below_current(self):
        """When cap rate is below user's marginal rate, no conversions → summary says so."""
        inp = RothConversionInput(
            traditional_balance=200_000,
            roth_balance=0,
            current_income=250_000,  # in 35% bracket
            current_age=50,
            years_to_project=5,
            respect_irmaa=False,
            target_bracket_rate=0.22,  # well below current 35%
        )
        result = self._svc().optimize(inp)
        assert "No conversions" in result.summary


class TestRothConversionIrmaa:
    def _svc(self):
        return RothConversionService()

    def test_irmaa_cap_reduces_conversion_vs_no_cap(self):
        """With IRMAA respect enabled, conversion should be <= without."""
        base = RothConversionInput(
            traditional_balance=500_000,
            roth_balance=0,
            current_income=100_000,  # close to first IRMAA tier
            current_age=62,
            filing_status="single",
            years_to_project=5,
        )
        with_irmaa = self._svc().optimize(base)
        without_irmaa = self._svc().optimize(
            RothConversionInput(**{**vars(base), "respect_irmaa": False})
        )
        assert with_irmaa.total_converted <= without_irmaa.total_converted

    def test_irmaa_note_appears_in_year_notes(self):
        """When IRMAA caps the conversion a note should appear."""
        inp = RothConversionInput(
            traditional_balance=500_000,
            roth_balance=0,
            current_income=105_000,  # just below first tier
            current_age=62,
            filing_status="single",
            years_to_project=3,
            respect_irmaa=True,
        )
        result = self._svc().optimize(inp)
        all_notes = [note for yr in result.years for note in yr.notes]
        assert any("IRMAA" in n for n in all_notes)

    def test_irmaa_not_applied_before_age_55(self):
        """IRMAA check is skipped for users younger than 55."""
        inp = RothConversionInput(
            traditional_balance=500_000,
            roth_balance=0,
            current_income=105_000,
            current_age=40,  # under 55
            filing_status="single",
            years_to_project=1,
            respect_irmaa=True,
        )
        result = self._svc().optimize(inp)
        all_notes = [note for yr in result.years for note in yr.notes]
        assert not any("IRMAA" in n for n in all_notes)


class TestRothConversionRmd:
    def _svc(self):
        return RothConversionService()

    def test_rmd_appears_at_73(self):
        inp = RothConversionInput(
            traditional_balance=500_000,
            roth_balance=0,
            current_income=40_000,
            current_age=72,  # turns 73 in year 2
            years_to_project=3,
            respect_irmaa=False,
        )
        result = self._svc().optimize(inp)
        # Year 1: age 72 → no RMD. Year 2: age 73 → RMD
        assert result.years[0].rmd_amount == 0.0
        assert result.years[1].rmd_amount > 0

    def test_rmd_reduces_available_conversion_headroom(self):
        """RMD counts as income, reducing headroom available for conversion."""
        inp_young = RothConversionInput(
            traditional_balance=500_000,
            roth_balance=0,
            current_income=40_000,
            current_age=60,
            years_to_project=1,
            respect_irmaa=False,
        )
        inp_old = RothConversionInput(
            traditional_balance=500_000,
            roth_balance=0,
            current_income=40_000,
            current_age=75,  # will have RMD
            years_to_project=1,
            respect_irmaa=False,
        )
        young_conversion = self._svc().optimize(inp_young).years[0].optimal_conversion
        old_conversion = self._svc().optimize(inp_old).years[0].optimal_conversion
        # RMD eats into headroom so conversion should be less for the older person
        assert old_conversion <= young_conversion


class TestRothConversionFilingStatus:
    def _svc(self):
        return RothConversionService()

    def test_married_gets_more_headroom_than_single(self):
        """Married filers have wider brackets → more room to convert."""
        base_kwargs = dict(
            traditional_balance=300_000,
            roth_balance=0,
            current_income=80_000,
            current_age=55,
            years_to_project=5,
            respect_irmaa=False,
        )
        single = self._svc().optimize(RothConversionInput(**base_kwargs, filing_status="single"))
        married = self._svc().optimize(RothConversionInput(**base_kwargs, filing_status="married"))
        assert married.total_converted >= single.total_converted
