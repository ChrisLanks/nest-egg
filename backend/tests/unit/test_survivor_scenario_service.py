"""Unit tests for the survivor income scenario service."""

import pytest

from app.services.survivor_scenario_service import (
    _SURVIVOR_AT_60,
    _SURVIVOR_AT_FRA,
    _SURVIVOR_FLOOR,
    compute_survivor_scenario,
)


def _run(**kwargs):
    defaults = dict(
        death_age=70,
        deceased_ss_monthly=2_000,
        deceased_pia=2_200,
        survivor_current_age=65,
        survivor_life_expectancy=90,
        survivor_own_ss_monthly=0,
        survivor_ss_claiming_age=65,
        current_portfolio=500_000,
        joint_annual_income=80_000,
        joint_annual_spending=60_000,
        num_simulations=50,
    )
    defaults.update(kwargs)
    return compute_survivor_scenario(**defaults)


@pytest.mark.unit
class TestSurvivorSsBenefitCalculation:
    def test_survivor_benefit_at_60_is_71_5_pct(self):
        result = _run(
            survivor_ss_claiming_age=60,
            survivor_own_ss_monthly=0,
            deceased_ss_monthly=2_000,
            deceased_pia=2_000,
        )
        # floor = 2000 * 0.825 = 1650; raw = 2000 * 0.715 = 1430 → floor wins
        expected = max(2_000 * _SURVIVOR_AT_60, 2_000 * _SURVIVOR_FLOOR)
        assert result.survivor_ss_benefit == pytest.approx(expected, abs=0.02)

    def test_survivor_benefit_at_fra_is_100_pct(self):
        result = _run(
            survivor_ss_claiming_age=67,
            survivor_own_ss_monthly=0,
            deceased_ss_monthly=2_000,
            deceased_pia=2_000,
        )
        # raw at FRA = 2000; floor = 1650 → raw wins
        assert result.survivor_ss_benefit == pytest.approx(2_000.0, abs=0.02)

    def test_survivor_benefit_interpolated_between_60_and_fra(self):
        # claiming at 65 (between 60 and FRA=67) should be between 71.5% and 100%
        result = _run(
            survivor_ss_claiming_age=65,
            survivor_own_ss_monthly=0,
            deceased_ss_monthly=2_000,
            deceased_pia=1_000,
            survivor_current_age=60,
        )
        # Benefit must be strictly between age-60 rate and FRA rate
        at_60 = max(2_000 * _SURVIVOR_AT_60, 1_000 * _SURVIVOR_FLOOR)
        at_fra = max(2_000 * _SURVIVOR_AT_FRA, 1_000 * _SURVIVOR_FLOOR)
        assert at_60 < result.survivor_ss_benefit < at_fra

    def test_floor_applies_when_raw_below_82_5_pct(self):
        result = _run(
            survivor_ss_claiming_age=60,
            survivor_own_ss_monthly=0,
            deceased_ss_monthly=1_000,
            deceased_pia=1_000,
        )
        # raw = 1000 * 0.715 = 715; floor = 1000 * 0.825 = 825 → floor wins
        assert result.survivor_ss_benefit == pytest.approx(825.0, abs=0.02)

    def test_survivor_takes_own_ss_when_higher(self):
        result = _run(
            survivor_ss_claiming_age=67,
            survivor_own_ss_monthly=3_000,
            deceased_ss_monthly=2_000,
            deceased_pia=2_000,
        )
        assert result.survivor_ss_is_own is True
        assert result.survivor_ss_benefit == pytest.approx(3_000.0, abs=0.02)

    def test_survivor_takes_deceased_benefit_when_higher(self):
        result = _run(
            survivor_ss_claiming_age=67,
            survivor_own_ss_monthly=500,
            deceased_ss_monthly=2_000,
            deceased_pia=2_000,
        )
        assert result.survivor_ss_is_own is False
        assert result.survivor_ss_benefit == pytest.approx(2_000.0, abs=0.02)


@pytest.mark.unit
class TestSurvivorProjection:
    def test_projection_length_matches_years(self):
        result = _run(
            survivor_current_age=65,
            survivor_life_expectancy=85,
        )
        # year 0 through 20 inclusive = 21 entries
        assert len(result.projection) == 21

    def test_projection_ages_are_sequential(self):
        result = _run(
            survivor_current_age=65,
            survivor_life_expectancy=75,
        )
        for i, entry in enumerate(result.projection):
            assert entry.survivor_age == 65 + i

    def test_monthly_income_in_projection_is_positive_when_claiming(self):
        result = _run(
            survivor_current_age=65,
            survivor_life_expectancy=70,
            survivor_ss_claiming_age=65,
            survivor_own_ss_monthly=0,
            deceased_ss_monthly=2_000,
            deceased_pia=2_000,
        )
        # After year 0, income should be positive since age >= claiming age
        for entry in result.projection[1:]:
            assert entry.annual_income > 0

    def test_year_0_portfolio_equals_input_portfolio(self):
        result = _run(
            current_portfolio=750_000,
            portfolio_share_pct=1.0,
        )
        assert result.projection[0].portfolio_value == pytest.approx(750_000, rel=0.01)

    def test_data_note_present(self):
        result = _run()
        assert len(result.data_note) > 20

    def test_success_rate_between_0_and_1(self):
        result = _run(num_simulations=100)
        assert 0.0 <= result.success_rate <= 1.0

    def test_spending_reduced_by_default_20_pct(self):
        result = _run(joint_annual_spending=60_000, spending_reduction_pct=0.20)
        assert result.survivor_annual_spending == pytest.approx(48_000, abs=0.01)


@pytest.mark.unit
class TestSurvivorEdgeCases:
    def test_large_own_ss_overrides_survivor_benefit(self):
        result = _run(
            survivor_own_ss_monthly=5_000,
            deceased_ss_monthly=500,
            deceased_pia=500,
            survivor_ss_claiming_age=67,
        )
        assert result.survivor_ss_is_own is True
        assert result.survivor_ss_benefit == pytest.approx(5_000, abs=0.02)

    def test_portfolio_share_applied(self):
        result = _run(current_portfolio=1_000_000, portfolio_share_pct=0.5)
        assert result.joint_portfolio_at_death == pytest.approx(500_000, abs=0.01)

    def test_inputs_echoed_on_result(self):
        result = _run(death_age=72, survivor_current_age=68, survivor_life_expectancy=88)
        assert result.death_age_of_deceased == 72
        assert result.survivor_current_age == 68
        assert result.survivor_life_expectancy == 88
