"""Unit tests for the multi-strategy inheritance projection service."""

import datetime

import pytest

from app.services.inheritance_projection_service import (
    _ESTATE_TAX_RATE,
    _best_year_exemption,
    project_inheritance,
)


def _run(**kwargs):
    defaults = dict(
        initial_portfolio=1_000_000,
        annual_income=24_000,
        annual_spending=60_000,
        current_age=65,
        life_expectancy=85,
        expected_return=0.06,
        inflation=0.03,
    )
    defaults.update(kwargs)
    return project_inheritance(**defaults)


@pytest.mark.unit
class TestProjectInheritanceScenarios:
    def test_four_scenarios_always_returned(self):
        result = _run()
        assert len(result.scenarios) == 4

    def test_strategy_names_match_expected_strings(self):
        result = _run()
        names = [s.strategy_name for s in result.scenarios]
        assert any("4%" in n for n in names)
        assert any("Minimum" in n for n in names)
        assert any("Spend to Zero" in n for n in names)
        assert any("Legacy" in n for n in names)

    def test_life_expectancy_lte_current_age_raises_value_error(self):
        with pytest.raises(ValueError):
            _run(current_age=70, life_expectancy=65)

    def test_life_expectancy_equal_current_age_raises_value_error(self):
        with pytest.raises(ValueError):
            _run(current_age=70, life_expectancy=70)

    def test_annual_values_length_equals_years_plus_one(self):
        result = _run(current_age=65, life_expectancy=85)
        years = 85 - 65
        for scenario in result.scenarios:
            assert len(scenario.annual_values) == years + 1

    def test_spend_to_zero_final_portfolio_near_zero(self):
        result = _run(
            initial_portfolio=500_000,
            annual_income=0,
            annual_spending=30_000,
            current_age=65,
            life_expectancy=85,
        )
        stz = next(s for s in result.scenarios if "Spend to Zero" in s.strategy_name)
        # Allow within 10% of initial portfolio
        assert stz.final_portfolio <= 500_000 * 0.10

    def test_withdrawal_rate_equals_annual_withdrawal_over_portfolio(self):
        result = _run(initial_portfolio=1_000_000)
        for scenario in result.scenarios:
            expected_rate = scenario.annual_withdrawal / 1_000_000
            assert scenario.withdrawal_rate == pytest.approx(expected_rate, abs=0.0001)

    def test_estate_tax_applied_when_gross_above_exemption(self):
        exemption = _best_year_exemption(datetime.date.today().year)
        # Use a very high portfolio and minimum withdrawal to leave a large estate
        result = _run(
            initial_portfolio=exemption * 2,
            annual_income=exemption,
            annual_spending=0,
            current_age=65,
            life_expectancy=70,
        )
        min_scenario = next(s for s in result.scenarios if "Minimum" in s.strategy_name)
        if min_scenario.estate_before_tax > exemption:
            assert min_scenario.federal_estate_tax > 0

    def test_net_to_heirs_zero_tax_when_estate_below_exemption(self):
        result = _run(
            initial_portfolio=100_000,
            annual_income=0,
            annual_spending=60_000,
            current_age=65,
            life_expectancy=75,
        )
        for scenario in result.scenarios:
            if scenario.estate_before_tax == 0:
                assert scenario.federal_estate_tax == 0.0

    def test_legacy_target_none_uses_4pct_fallback(self):
        result_no_target = _run(legacy_target=None)
        result_4pct = _run()
        legacy = next(s for s in result_no_target.scenarios if "Legacy" in s.strategy_name)
        four_pct = next(s for s in result_4pct.scenarios if "4%" in s.strategy_name)
        assert legacy.annual_withdrawal == pytest.approx(four_pct.annual_withdrawal, abs=0.01)

    def test_legacy_target_scenario_name_contains_amount(self):
        result = _run(legacy_target=500_000)
        legacy = next(s for s in result.scenarios if "Legacy" in s.strategy_name)
        assert "500,000" in legacy.strategy_name

    def test_tcja_sunset_applies_true_when_projection_past_2025(self):
        today = datetime.date.today().year
        # Force projection to extend well past 2025
        life_expectancy = max(65 + (2026 - today) + 5, 70)
        result = _run(current_age=65, life_expectancy=life_expectancy)
        if today + (life_expectancy - 65) > 2025:
            assert result.tcja_sunset_applies is True

    def test_data_note_present_and_mentions_exemption(self):
        result = _run()
        assert len(result.data_note) > 20
        assert "exemption" in result.data_note.lower() or "$" in result.data_note

    def test_estate_tax_rate_echoed(self):
        result = _run()
        assert result.estate_tax_rate == pytest.approx(_ESTATE_TAX_RATE, abs=0.001)

    def test_initial_portfolio_echoed(self):
        result = _run(initial_portfolio=750_000)
        assert result.initial_portfolio == pytest.approx(750_000, abs=0.01)

    def test_annual_values_first_equals_initial_portfolio(self):
        result = _run(initial_portfolio=1_000_000)
        for scenario in result.scenarios:
            assert scenario.annual_values[0] == pytest.approx(1_000_000, abs=0.01)
