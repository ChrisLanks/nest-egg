"""Tests for Monte Carlo simulation service.

Covers:
- Quick simulation (no DB)
- Readiness score calculation
- Percentile band ordering
- Depletion detection
- Edge cases
"""

import pytest
from app.services.retirement.monte_carlo_service import RetirementMonteCarloService


# ── Quick simulation ──────────────────────────────────────────────────────────


class TestQuickSimulation:
    def test_returns_all_fields(self):
        result = RetirementMonteCarloService.run_quick_simulation(
            current_portfolio=500000,
            annual_contributions=20000,
            current_age=35,
            retirement_age=65,
            life_expectancy=95,
            annual_spending=60000,
            num_sims=100,
        )
        assert "success_rate" in result
        assert "readiness_score" in result
        assert "projections" in result
        assert "median_depletion_age" in result

    def test_projections_cover_all_years(self):
        result = RetirementMonteCarloService.run_quick_simulation(
            current_portfolio=500000,
            annual_contributions=20000,
            current_age=35,
            retirement_age=65,
            life_expectancy=95,
            annual_spending=60000,
            num_sims=50,
        )
        # Should have projections from age 35 to 95 → 61 points
        assert len(result["projections"]) == 61

    def test_percentile_ordering(self):
        """p10 <= p25 <= p50 <= p75 <= p90 at every age."""
        result = RetirementMonteCarloService.run_quick_simulation(
            current_portfolio=500000,
            annual_contributions=20000,
            current_age=35,
            retirement_age=65,
            life_expectancy=95,
            annual_spending=60000,
            num_sims=200,
        )
        for point in result["projections"]:
            assert point["p10"] <= point["p25"], f"p10 > p25 at age {point['age']}"
            assert point["p25"] <= point["p50"], f"p25 > p50 at age {point['age']}"
            assert point["p50"] <= point["p75"], f"p50 > p75 at age {point['age']}"
            assert point["p75"] <= point["p90"], f"p75 > p90 at age {point['age']}"

    def test_first_projection_is_current_portfolio(self):
        result = RetirementMonteCarloService.run_quick_simulation(
            current_portfolio=500000,
            annual_contributions=20000,
            current_age=35,
            retirement_age=65,
            life_expectancy=95,
            annual_spending=60000,
            num_sims=50,
        )
        first = result["projections"][0]
        assert first["age"] == 35
        # All percentiles should equal current portfolio at year 0
        assert first["p50"] == 500000

    def test_success_rate_range(self):
        result = RetirementMonteCarloService.run_quick_simulation(
            current_portfolio=500000,
            annual_contributions=20000,
            current_age=35,
            retirement_age=65,
            life_expectancy=95,
            annual_spending=60000,
            num_sims=100,
        )
        assert 0 <= result["success_rate"] <= 100

    def test_readiness_score_range(self):
        result = RetirementMonteCarloService.run_quick_simulation(
            current_portfolio=500000,
            annual_contributions=20000,
            current_age=35,
            retirement_age=65,
            life_expectancy=95,
            annual_spending=60000,
            num_sims=100,
        )
        assert 0 <= result["readiness_score"] <= 100

    def test_zero_portfolio_low_success(self):
        """No savings and high spending should have very low success rate."""
        result = RetirementMonteCarloService.run_quick_simulation(
            current_portfolio=0,
            annual_contributions=0,
            current_age=60,
            retirement_age=65,
            life_expectancy=95,
            annual_spending=80000,
            num_sims=100,
        )
        assert result["success_rate"] < 10

    def test_wealthy_high_success(self):
        """Very high portfolio with low spending should have high success rate."""
        result = RetirementMonteCarloService.run_quick_simulation(
            current_portfolio=5000000,
            annual_contributions=50000,
            current_age=35,
            retirement_age=65,
            life_expectancy=95,
            annual_spending=40000,
            num_sims=100,
        )
        assert result["success_rate"] > 80

    def test_social_security_improves_outcomes(self):
        """Adding SS income should improve success rate."""
        base = RetirementMonteCarloService.run_quick_simulation(
            current_portfolio=300000,
            annual_contributions=10000,
            current_age=55,
            retirement_age=65,
            life_expectancy=95,
            annual_spending=50000,
            social_security_monthly=0,
            num_sims=200,
        )
        with_ss = RetirementMonteCarloService.run_quick_simulation(
            current_portfolio=300000,
            annual_contributions=10000,
            current_age=55,
            retirement_age=65,
            life_expectancy=95,
            annual_spending=50000,
            social_security_monthly=2000,
            social_security_start_age=67,
            num_sims=200,
        )
        assert with_ss["success_rate"] >= base["success_rate"]

    def test_invalid_ages_returns_empty(self):
        """Life expectancy <= current age should return empty result."""
        result = RetirementMonteCarloService.run_quick_simulation(
            current_portfolio=500000,
            annual_contributions=20000,
            current_age=95,
            retirement_age=65,
            life_expectancy=90,
            annual_spending=60000,
        )
        assert result["success_rate"] == 0
        assert result["projections"] == []

    def test_depletion_pct_increases_over_time(self):
        """Depletion percentage should generally not decrease after retirement."""
        result = RetirementMonteCarloService.run_quick_simulation(
            current_portfolio=200000,
            annual_contributions=5000,
            current_age=55,
            retirement_age=65,
            life_expectancy=95,
            annual_spending=60000,
            num_sims=200,
        )
        # Check that depletion % is non-decreasing after retirement
        post_retirement = [p for p in result["projections"] if p["age"] >= 65]
        for i in range(1, len(post_retirement)):
            assert post_retirement[i]["depletion_pct"] >= post_retirement[i - 1]["depletion_pct"]


# ── Readiness score ───────────────────────────────────────────────────────────


class TestReadinessScore:
    def _score(self, **kwargs):
        defaults = dict(
            success_rate=80,
            current_portfolio=500000,
            annual_spending=50000,
            years_in_retirement=30,
            annual_savings=20000,
            annual_income=100000,
        )
        defaults.update(kwargs)
        return RetirementMonteCarloService._calculate_readiness_score(**defaults)

    def test_range_0_to_100(self):
        # Max score
        score_max = self._score(
            success_rate=100, current_portfolio=3000000,
            annual_spending=50000, years_in_retirement=30,
            annual_savings=30000, annual_income=100000,
        )
        assert 0 <= score_max <= 100

        # Min score
        score_min = self._score(
            success_rate=0, current_portfolio=0,
            annual_spending=50000, years_in_retirement=30,
            annual_savings=0, annual_income=0,
        )
        assert score_min == 0

    def test_success_rate_dominates(self):
        """Success rate is 50% of the score."""
        high_sr = self._score(success_rate=100, current_portfolio=0, annual_savings=0, annual_income=0)
        low_sr = self._score(success_rate=0, current_portfolio=0, annual_savings=0, annual_income=0)
        assert high_sr - low_sr == pytest.approx(50, abs=2)

    def test_coverage_component(self):
        """Higher portfolio relative to spending needs → higher score."""
        low = self._score(current_portfolio=100000, annual_spending=50000, years_in_retirement=30)
        high = self._score(current_portfolio=1500000, annual_spending=50000, years_in_retirement=30)
        assert high > low

    def test_savings_rate_component(self):
        """Higher savings rate → higher score."""
        low = self._score(annual_savings=5000, annual_income=100000)
        high = self._score(annual_savings=30000, annual_income=100000)
        assert high > low

    def test_no_income_with_savings(self):
        """If saving with no income data, should still get partial credit."""
        score = self._score(annual_savings=20000, annual_income=0)
        # Should be > 0 because of savings heuristic (0.5 * 100 * 0.2 = 10)
        assert score > 0

    def test_zero_years_no_crash(self):
        """Zero years in retirement should not crash."""
        score = self._score(years_in_retirement=0)
        assert 0 <= score <= 100
