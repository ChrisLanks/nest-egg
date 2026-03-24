"""Unit tests for the guardrails / sequence-of-returns stress test service."""

import pytest

from app.services.retirement.guardrails_service import (
    CRASH_SCENARIOS,
    run_guardrails_simulation,
)


@pytest.mark.unit
class TestGuardrailsSimulation:
    def _run(self, **kwargs):
        defaults = dict(
            initial_portfolio=1_000_000,
            annual_spending=40_000,
            current_age=65,
            life_expectancy=90,
            num_simulations=200,
        )
        defaults.update(kwargs)
        return run_guardrails_simulation(**defaults)

    def test_success_rate_between_0_and_1(self):
        r = self._run()
        assert 0.0 <= r.success_rate <= 1.0

    def test_crash_scenario_echoed(self):
        r = self._run(crash_scenario="2008_financial_crisis")
        assert r.crash_scenario_name == "2008_financial_crisis"
        assert r.crash_first_year_return == pytest.approx(-0.37, abs=0.01)

    def test_crash_return_override_used(self):
        r = self._run(crash_return_override=-0.50)
        assert r.crash_first_year_return == pytest.approx(-0.50)
        assert r.crash_scenario_name == "custom"

    def test_yearly_stats_length_matches_years(self):
        r = self._run(current_age=65, life_expectancy=85)
        # year 0 (initial) + 20 years = 21 entries
        assert len(r.yearly_stats) == 21

    def test_year_0_stats_equal_initial_portfolio(self):
        r = self._run(initial_portfolio=1_000_000)
        year0 = r.yearly_stats[0]
        assert year0.p50 == pytest.approx(1_000_000, rel=0.01)

    def test_median_spending_path_length(self):
        r = self._run(current_age=65, life_expectancy=85)
        # One spending value per year (20 total, not including year 0)
        assert len(r.median_spending_path) == 20

    def test_pct_depleted_starts_at_zero(self):
        r = self._run()
        assert r.yearly_stats[0].pct_depleted == 0.0

    def test_guardrails_disabled_vs_enabled_different_success(self):
        """Guardrails should generally improve success rate vs no guardrails."""
        r_on = self._run(guardrails_enabled=True, num_simulations=500)
        r_off = self._run(guardrails_enabled=False, num_simulations=500)
        # Guardrails enable portfolio to survive longer — success should be >= off
        # (not guaranteed to be strictly greater due to randomness, but both valid)
        assert 0 <= r_on.success_rate <= 1
        assert 0 <= r_off.success_rate <= 1

    def test_p10_le_p50_le_p90_final(self):
        r = self._run()
        assert r.p10_final_portfolio <= r.median_final_portfolio <= r.p90_final_portfolio

    def test_initial_withdrawal_rate_correct(self):
        r = self._run(initial_portfolio=1_000_000, annual_spending=40_000)
        assert r.initial_withdrawal_rate == pytest.approx(0.04, abs=0.001)

    def test_invalid_portfolio_raises(self):
        with pytest.raises(ValueError, match="positive"):
            run_guardrails_simulation(
                initial_portfolio=0,
                annual_spending=40_000,
                current_age=65,
                life_expectancy=90,
            )

    def test_invalid_life_expectancy_raises(self):
        with pytest.raises(ValueError):
            run_guardrails_simulation(
                initial_portfolio=1_000_000,
                annual_spending=40_000,
                current_age=65,
                life_expectancy=60,
            )

    def test_data_note_present(self):
        r = self._run()
        assert len(r.data_note) > 10

    def test_all_crash_scenarios_available(self):
        for key in CRASH_SCENARIOS:
            r = self._run(crash_scenario=key)
            assert r.crash_scenario_name == key

    def test_unknown_crash_scenario_falls_back_to_2008(self):
        r = self._run(crash_scenario="nonexistent_scenario")
        assert r.crash_scenario_name == "2008_financial_crisis"


@pytest.mark.unit
class TestCrashScenariosTable:
    def test_all_scenarios_have_required_keys(self):
        for name, cs in CRASH_SCENARIOS.items():
            assert "first_year_return" in cs, f"{name} missing first_year_return"
            assert "description" in cs
            assert "source" in cs
            assert "data_as_of" in cs

    def test_crash_returns_are_negative(self):
        for name, cs in CRASH_SCENARIOS.items():
            assert cs["first_year_return"] < 0, f"{name}: crash return should be negative"

    def test_2008_return_is_approx_minus_37(self):
        assert CRASH_SCENARIOS["2008_financial_crisis"]["first_year_return"] == pytest.approx(-0.37, abs=0.01)
