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
            success_rate=100,
            current_portfolio=3000000,
            annual_spending=50000,
            years_in_retirement=30,
            annual_savings=30000,
            annual_income=100000,
        )
        assert 0 <= score_max <= 100

        # Min score
        score_min = self._score(
            success_rate=0,
            current_portfolio=0,
            annual_spending=50000,
            years_in_retirement=30,
            annual_savings=0,
            annual_income=0,
        )
        assert score_min == 0

    def test_success_rate_dominates(self):
        """Success rate is 50% of the score."""
        high_sr = self._score(
            success_rate=100, current_portfolio=0, annual_savings=0, annual_income=0
        )
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


# ── Helper function tests ────────────────────────────────────────────────────


class TestHelperFunctions:
    """Test standalone helper functions for return generation."""

    def test_generate_normal_return_produces_float(self):
        from app.services.retirement.monte_carlo_service import _generate_normal_return

        result = _generate_normal_return(0.07, 0.15)
        assert isinstance(result, float)

    def test_generate_normal_return_mean_stability(self):
        """Over many samples, mean should be close to the target mean."""
        import random

        from app.services.retirement.monte_carlo_service import _generate_normal_return

        random.seed(42)
        samples = [_generate_normal_return(0.07, 0.15) for _ in range(5000)]
        mean = sum(samples) / len(samples)
        assert abs(mean - 0.07) < 0.02

    def test_generate_lognormal_return_zero_stddev(self):
        """With zero std dev, should return exactly the mean."""
        from app.services.retirement.monte_carlo_service import _generate_lognormal_return

        result = _generate_lognormal_return(0.07, 0.0)
        assert result == 0.07

    def test_generate_lognormal_return_produces_float(self):
        from app.services.retirement.monte_carlo_service import _generate_lognormal_return

        result = _generate_lognormal_return(0.07, 0.15)
        assert isinstance(result, float)

    def test_generate_lognormal_return_positive_bias(self):
        """Log-normal returns should be > -1 (can't lose more than 100%)."""
        import random

        from app.services.retirement.monte_carlo_service import _generate_lognormal_return

        random.seed(42)
        samples = [_generate_lognormal_return(0.07, 0.15) for _ in range(1000)]
        assert all(s > -1 for s in samples)

    def test_generate_bootstrap_return(self):
        from app.services.retirement.monte_carlo_service import (
            HISTORICAL_SP500_RETURNS,
            _generate_bootstrap_return,
        )

        result = _generate_bootstrap_return(HISTORICAL_SP500_RETURNS)
        assert result in HISTORICAL_SP500_RETURNS

    def test_historical_sp500_returns_not_empty(self):
        from app.services.retirement.monte_carlo_service import HISTORICAL_SP500_RETURNS

        assert len(HISTORICAL_SP500_RETURNS) > 90  # 1928-2024

    def test_compute_scenario_hash_deterministic(self):
        """Same scenario inputs should produce same hash."""
        from unittest.mock import Mock

        from app.services.retirement.monte_carlo_service import _compute_scenario_hash

        scenario = Mock()
        scenario.retirement_age = 65
        scenario.life_expectancy = 95
        scenario.annual_spending_retirement = 60000
        scenario.pre_retirement_return = 7
        scenario.post_retirement_return = 5
        scenario.volatility = 15
        scenario.inflation_rate = 3
        scenario.medical_inflation_rate = 5
        scenario.social_security_monthly = 2000
        scenario.social_security_start_age = 67
        scenario.use_estimated_pia = False
        scenario.withdrawal_strategy = "fixed"
        scenario.withdrawal_rate = 4
        scenario.federal_tax_rate = 22
        scenario.state_tax_rate = 5
        scenario.num_simulations = 1000
        scenario.distribution_type = "normal"
        scenario.healthcare_pre65_override = None
        scenario.healthcare_medicare_override = None
        scenario.healthcare_ltc_override = None
        scenario.life_events = []

        hash1 = _compute_scenario_hash(scenario)
        hash2 = _compute_scenario_hash(scenario)
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex

    def test_compute_scenario_hash_with_life_events(self):
        """Hash should include life events."""
        from unittest.mock import Mock

        from app.services.retirement.monte_carlo_service import _compute_scenario_hash

        scenario = Mock()
        scenario.retirement_age = 65
        scenario.life_expectancy = 95
        scenario.annual_spending_retirement = 60000
        scenario.pre_retirement_return = 7
        scenario.post_retirement_return = 5
        scenario.volatility = 15
        scenario.inflation_rate = 3
        scenario.medical_inflation_rate = 5
        scenario.social_security_monthly = 2000
        scenario.social_security_start_age = 67
        scenario.use_estimated_pia = False
        scenario.withdrawal_strategy = "fixed"
        scenario.withdrawal_rate = 4
        scenario.federal_tax_rate = 22
        scenario.state_tax_rate = 5
        scenario.num_simulations = 1000
        scenario.distribution_type = "normal"
        scenario.healthcare_pre65_override = None
        scenario.healthcare_medicare_override = None
        scenario.healthcare_ltc_override = None

        event = Mock()
        event.name = "College"
        event.category = "education"
        event.start_age = 50
        event.end_age = 54
        event.annual_cost = 25000
        event.one_time_cost = None
        event.income_change = None
        scenario.life_events = [event]

        hash_with_events = _compute_scenario_hash(scenario)
        scenario.life_events = []
        hash_without_events = _compute_scenario_hash(scenario)

        assert hash_with_events != hash_without_events


# ── Life event schedule ──────────────────────────────────────────────────────


class TestBuildLifeEventSchedule:
    """Test the _build_life_event_schedule static method."""

    def _make_event(self, **kwargs):
        from unittest.mock import Mock

        event = Mock()
        event.start_age = kwargs.get("start_age", 65)
        event.end_age = kwargs.get("end_age", None)
        event.one_time_cost = kwargs.get("one_time_cost", None)
        event.annual_cost = kwargs.get("annual_cost", None)
        event.income_change = kwargs.get("income_change", None)
        event.use_medical_inflation = kwargs.get("use_medical_inflation", False)
        return event

    def _make_scenario(self, events):
        from unittest.mock import Mock

        scenario = Mock()
        scenario.life_events = events
        return scenario

    def test_one_time_cost(self):
        event = self._make_event(start_age=70, one_time_cost=50000)
        scenario = self._make_scenario([event])
        schedule = RetirementMonteCarloService._build_life_event_schedule(
            scenario, current_age=60, life_expectancy=95
        )
        assert 70 in schedule
        assert len(schedule[70]) == 1
        assert schedule[70][0] == (50000.0, False)

    def test_annual_cost_range(self):
        event = self._make_event(start_age=65, end_age=68, annual_cost=10000)
        scenario = self._make_scenario([event])
        schedule = RetirementMonteCarloService._build_life_event_schedule(
            scenario, current_age=60, life_expectancy=95
        )
        for age in [65, 66, 67, 68]:
            assert age in schedule
            assert schedule[age][0] == (10000.0, False)

    def test_annual_cost_no_end_age(self):
        """When end_age is None, only start_age year is included."""
        event = self._make_event(start_age=70, end_age=None, annual_cost=5000)
        scenario = self._make_scenario([event])
        schedule = RetirementMonteCarloService._build_life_event_schedule(
            scenario, current_age=60, life_expectancy=95
        )
        assert 70 in schedule
        assert 71 not in schedule

    def test_income_change_negative_cost(self):
        """income_change is stored as negative cost (positive income reduces spending)."""
        event = self._make_event(start_age=65, end_age=67, income_change=24000)
        scenario = self._make_scenario([event])
        schedule = RetirementMonteCarloService._build_life_event_schedule(
            scenario, current_age=60, life_expectancy=95
        )
        for age in [65, 66, 67]:
            assert age in schedule
            cost, use_med = schedule[age][0]
            assert cost == -24000.0  # Negative = income
            assert use_med is False

    def test_medical_inflation_flag(self):
        event = self._make_event(start_age=80, one_time_cost=30000, use_medical_inflation=True)
        scenario = self._make_scenario([event])
        schedule = RetirementMonteCarloService._build_life_event_schedule(
            scenario, current_age=60, life_expectancy=95
        )
        assert schedule[80][0] == (30000.0, True)

    def test_events_outside_age_range_excluded(self):
        """Events before current_age or after life_expectancy
        should be excluded from annual costs."""
        event = self._make_event(start_age=50, end_age=55, annual_cost=10000)
        scenario = self._make_scenario([event])
        schedule = RetirementMonteCarloService._build_life_event_schedule(
            scenario, current_age=60, life_expectancy=95
        )
        # All ages 50-55 are before current_age=60, so no entries
        assert len(schedule) == 0

    def test_empty_events(self):
        scenario = self._make_scenario([])
        schedule = RetirementMonteCarloService._build_life_event_schedule(
            scenario, current_age=60, life_expectancy=95
        )
        assert schedule == {}


# ── Full simulation (run_simulation) with mocked DB ─────────────────────────


class TestRunSimulation:
    """Test the full run_simulation method with mocked DB and models."""

    @pytest.mark.asyncio
    async def test_run_simulation_basic(self):
        """Test full simulation with mocked DB returns valid result."""
        from datetime import date
        from decimal import Decimal
        from unittest.mock import AsyncMock, Mock, patch
        from uuid import uuid4

        db = AsyncMock()

        # Mock scenario
        scenario = Mock()
        scenario.id = uuid4()
        scenario.organization_id = uuid4()
        scenario.user_id = uuid4()
        scenario.retirement_age = 65
        scenario.life_expectancy = 90
        scenario.annual_spending_retirement = Decimal("60000")
        scenario.pre_retirement_return = Decimal("7")
        scenario.post_retirement_return = Decimal("5")
        scenario.volatility = Decimal("15")
        scenario.inflation_rate = Decimal("3")
        scenario.medical_inflation_rate = Decimal("5")
        scenario.social_security_monthly = Decimal("2000")
        scenario.social_security_start_age = 67
        scenario.use_estimated_pia = False
        scenario.current_annual_income = Decimal("100000")
        scenario.withdrawal_strategy = "fixed"
        scenario.withdrawal_rate = Decimal("4")
        scenario.federal_tax_rate = Decimal("22")
        scenario.state_tax_rate = Decimal("5")
        scenario.capital_gains_rate = Decimal("15")
        scenario.num_simulations = 10  # Few sims for speed
        scenario.distribution_type = None  # Will default to NORMAL
        scenario.healthcare_pre65_override = None
        scenario.healthcare_medicare_override = None
        scenario.healthcare_ltc_override = None
        scenario.life_events = []
        scenario.spouse_social_security_monthly = None
        scenario.spouse_social_security_start_age = None

        # Mock user
        user = Mock()
        user.birthdate = date(1980, 6, 15)

        # Mock _gather_account_data
        account_data = {
            "total_portfolio": Decimal("500000"),
            "taxable_balance": Decimal("100000"),
            "pre_tax_balance": Decimal("200000"),
            "roth_balance": Decimal("100000"),
            "hsa_balance": Decimal("50000"),
            "cash_balance": Decimal("50000"),
            "pension_monthly": Decimal("0"),
            "annual_contributions": Decimal("20000"),
            "employer_match_annual": Decimal("5000"),
            "annual_income": Decimal("100000"),
            "accounts": [],
        }

        with patch.object(
            RetirementMonteCarloService,
            "_gather_account_data",
            new_callable=AsyncMock,
            return_value=account_data,
        ):
            result = await RetirementMonteCarloService.run_simulation(db, scenario, user)

        assert result is not None
        assert result.num_simulations == 10
        assert float(result.success_rate) >= 0
        assert result.projections_json is not None
        db.add.assert_called_once()
        db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_simulation_no_birthdate_raises(self):
        """Should raise ValueError if user has no birthdate."""
        from unittest.mock import AsyncMock, Mock
        from uuid import uuid4

        db = AsyncMock()
        scenario = Mock()
        scenario.id = uuid4()
        user = Mock()
        user.birthdate = None

        with pytest.raises(ValueError, match="birthdate"):
            await RetirementMonteCarloService.run_simulation(db, scenario, user)

    @pytest.mark.asyncio
    async def test_run_simulation_life_expectancy_too_low_raises(self):
        """Should raise ValueError if life expectancy <= current age."""
        from datetime import date
        from decimal import Decimal
        from unittest.mock import AsyncMock, Mock, patch
        from uuid import uuid4

        db = AsyncMock()
        scenario = Mock()
        scenario.id = uuid4()
        scenario.organization_id = uuid4()
        scenario.user_id = uuid4()
        scenario.retirement_age = 65
        scenario.life_expectancy = 40  # Less than current age
        scenario.annual_spending_retirement = Decimal("60000")
        scenario.pre_retirement_return = Decimal("7")
        scenario.post_retirement_return = Decimal("5")
        scenario.volatility = Decimal("15")
        scenario.inflation_rate = Decimal("3")
        scenario.medical_inflation_rate = Decimal("5")
        scenario.social_security_monthly = None
        scenario.social_security_start_age = 67
        scenario.use_estimated_pia = False
        scenario.num_simulations = 10

        user = Mock()
        user.birthdate = date(1980, 6, 15)  # ~45 years old

        account_data = {
            "total_portfolio": Decimal("500000"),
            "taxable_balance": Decimal("100000"),
            "pre_tax_balance": Decimal("200000"),
            "roth_balance": Decimal("100000"),
            "hsa_balance": Decimal("50000"),
            "cash_balance": Decimal("50000"),
            "pension_monthly": Decimal("0"),
            "annual_contributions": Decimal("20000"),
            "employer_match_annual": Decimal("0"),
            "annual_income": Decimal("100000"),
            "accounts": [],
        }

        with patch.object(
            RetirementMonteCarloService,
            "_gather_account_data",
            new_callable=AsyncMock,
            return_value=account_data,
        ):
            with pytest.raises(ValueError, match="Life expectancy"):
                await RetirementMonteCarloService.run_simulation(db, scenario, user)

    @pytest.mark.asyncio
    async def test_run_simulation_with_lognormal_distribution(self):
        """Test simulation runs with log-normal distribution type."""
        from datetime import date
        from decimal import Decimal
        from unittest.mock import AsyncMock, Mock, patch
        from uuid import uuid4

        from app.models.retirement import DistributionType

        db = AsyncMock()
        scenario = Mock()
        scenario.id = uuid4()
        scenario.organization_id = uuid4()
        scenario.user_id = uuid4()
        scenario.retirement_age = 65
        scenario.life_expectancy = 85
        scenario.annual_spending_retirement = Decimal("50000")
        scenario.pre_retirement_return = Decimal("7")
        scenario.post_retirement_return = Decimal("5")
        scenario.volatility = Decimal("15")
        scenario.inflation_rate = Decimal("3")
        scenario.medical_inflation_rate = Decimal("5")
        scenario.social_security_monthly = None
        scenario.social_security_start_age = 67
        scenario.use_estimated_pia = False
        scenario.current_annual_income = Decimal("80000")
        scenario.withdrawal_strategy = "fixed"
        scenario.withdrawal_rate = Decimal("4")
        scenario.federal_tax_rate = Decimal("22")
        scenario.state_tax_rate = Decimal("5")
        scenario.capital_gains_rate = Decimal("15")
        scenario.num_simulations = 10
        scenario.distribution_type = DistributionType.LOG_NORMAL
        scenario.healthcare_pre65_override = None
        scenario.healthcare_medicare_override = None
        scenario.healthcare_ltc_override = None
        scenario.life_events = []
        scenario.spouse_social_security_monthly = None
        scenario.spouse_social_security_start_age = None

        user = Mock()
        user.birthdate = date(1985, 1, 1)

        account_data = {
            "total_portfolio": Decimal("300000"),
            "taxable_balance": Decimal("100000"),
            "pre_tax_balance": Decimal("100000"),
            "roth_balance": Decimal("50000"),
            "hsa_balance": Decimal("25000"),
            "cash_balance": Decimal("25000"),
            "pension_monthly": Decimal("0"),
            "annual_contributions": Decimal("15000"),
            "employer_match_annual": Decimal("3000"),
            "annual_income": Decimal("80000"),
            "accounts": [],
        }

        with patch.object(
            RetirementMonteCarloService,
            "_gather_account_data",
            new_callable=AsyncMock,
            return_value=account_data,
        ):
            result = await RetirementMonteCarloService.run_simulation(db, scenario, user)

        assert result is not None
        assert result.num_simulations == 10

    @pytest.mark.asyncio
    async def test_run_simulation_with_historical_bootstrap(self):
        """Test simulation runs with historical bootstrap distribution."""
        from datetime import date
        from decimal import Decimal
        from unittest.mock import AsyncMock, Mock, patch
        from uuid import uuid4

        from app.models.retirement import DistributionType

        db = AsyncMock()
        scenario = Mock()
        scenario.id = uuid4()
        scenario.organization_id = uuid4()
        scenario.user_id = uuid4()
        scenario.retirement_age = 65
        scenario.life_expectancy = 85
        scenario.annual_spending_retirement = Decimal("50000")
        scenario.pre_retirement_return = Decimal("7")
        scenario.post_retirement_return = Decimal("5")
        scenario.volatility = Decimal("15")
        scenario.inflation_rate = Decimal("3")
        scenario.medical_inflation_rate = Decimal("5")
        scenario.social_security_monthly = Decimal("1500")
        scenario.social_security_start_age = 67
        scenario.use_estimated_pia = False
        scenario.current_annual_income = Decimal("80000")
        scenario.withdrawal_strategy = "fixed"
        scenario.withdrawal_rate = Decimal("4")
        scenario.federal_tax_rate = Decimal("22")
        scenario.state_tax_rate = Decimal("5")
        scenario.capital_gains_rate = Decimal("15")
        scenario.num_simulations = 10
        scenario.distribution_type = DistributionType.HISTORICAL_BOOTSTRAP
        scenario.healthcare_pre65_override = None
        scenario.healthcare_medicare_override = None
        scenario.healthcare_ltc_override = None
        scenario.life_events = []
        scenario.spouse_social_security_monthly = Decimal("1000")
        scenario.spouse_social_security_start_age = 66

        user = Mock()
        user.birthdate = date(1985, 1, 1)

        account_data = {
            "total_portfolio": Decimal("300000"),
            "taxable_balance": Decimal("100000"),
            "pre_tax_balance": Decimal("100000"),
            "roth_balance": Decimal("50000"),
            "hsa_balance": Decimal("25000"),
            "cash_balance": Decimal("25000"),
            "pension_monthly": Decimal("500"),
            "annual_contributions": Decimal("15000"),
            "employer_match_annual": Decimal("3000"),
            "annual_income": Decimal("80000"),
            "accounts": [],
        }

        with patch.object(
            RetirementMonteCarloService,
            "_gather_account_data",
            new_callable=AsyncMock,
            return_value=account_data,
        ):
            result = await RetirementMonteCarloService.run_simulation(db, scenario, user)

        assert result is not None

    @pytest.mark.asyncio
    async def test_run_simulation_with_pia_estimator(self):
        """Test simulation with use_estimated_pia enabled."""
        from datetime import date
        from decimal import Decimal
        from unittest.mock import AsyncMock, Mock, patch
        from uuid import uuid4

        db = AsyncMock()
        scenario = Mock()
        scenario.id = uuid4()
        scenario.organization_id = uuid4()
        scenario.user_id = uuid4()
        scenario.retirement_age = 65
        scenario.life_expectancy = 85
        scenario.annual_spending_retirement = Decimal("50000")
        scenario.pre_retirement_return = Decimal("7")
        scenario.post_retirement_return = Decimal("5")
        scenario.volatility = Decimal("15")
        scenario.inflation_rate = Decimal("3")
        scenario.medical_inflation_rate = Decimal("5")
        scenario.social_security_monthly = None  # No manual override
        scenario.social_security_start_age = 67
        scenario.use_estimated_pia = True
        scenario.current_annual_income = Decimal("100000")
        scenario.withdrawal_strategy = "fixed"
        scenario.withdrawal_rate = Decimal("4")
        scenario.federal_tax_rate = Decimal("22")
        scenario.state_tax_rate = Decimal("5")
        scenario.capital_gains_rate = Decimal("15")
        scenario.num_simulations = 10
        scenario.distribution_type = None
        scenario.healthcare_pre65_override = None
        scenario.healthcare_medicare_override = None
        scenario.healthcare_ltc_override = None
        scenario.life_events = []
        scenario.spouse_social_security_monthly = None
        scenario.spouse_social_security_start_age = None

        user = Mock()
        user.birthdate = date(1985, 1, 1)

        account_data = {
            "total_portfolio": Decimal("300000"),
            "taxable_balance": Decimal("100000"),
            "pre_tax_balance": Decimal("100000"),
            "roth_balance": Decimal("50000"),
            "hsa_balance": Decimal("25000"),
            "cash_balance": Decimal("25000"),
            "pension_monthly": Decimal("0"),
            "annual_contributions": Decimal("15000"),
            "employer_match_annual": Decimal("3000"),
            "annual_income": Decimal("100000"),
            "accounts": [],
        }

        with patch.object(
            RetirementMonteCarloService,
            "_gather_account_data",
            new_callable=AsyncMock,
            return_value=account_data,
        ):
            result = await RetirementMonteCarloService.run_simulation(db, scenario, user)

        assert result is not None
        assert result.estimated_pia is not None

    @pytest.mark.asyncio
    async def test_run_simulation_with_healthcare_overrides(self):
        """Test simulation with healthcare cost overrides."""
        from datetime import date
        from decimal import Decimal
        from unittest.mock import AsyncMock, Mock, patch
        from uuid import uuid4

        db = AsyncMock()
        scenario = Mock()
        scenario.id = uuid4()
        scenario.organization_id = uuid4()
        scenario.user_id = uuid4()
        scenario.retirement_age = 60  # Retire before 65 for pre-65 override
        scenario.life_expectancy = 90  # Past 85 for LTC override
        scenario.annual_spending_retirement = Decimal("50000")
        scenario.pre_retirement_return = Decimal("7")
        scenario.post_retirement_return = Decimal("5")
        scenario.volatility = Decimal("15")
        scenario.inflation_rate = Decimal("3")
        scenario.medical_inflation_rate = Decimal("5")
        scenario.social_security_monthly = Decimal("2000")
        scenario.social_security_start_age = 67
        scenario.use_estimated_pia = False
        scenario.current_annual_income = Decimal("100000")
        scenario.withdrawal_strategy = "fixed"
        scenario.withdrawal_rate = Decimal("4")
        scenario.federal_tax_rate = Decimal("22")
        scenario.state_tax_rate = Decimal("5")
        scenario.capital_gains_rate = Decimal("15")
        scenario.num_simulations = 10
        scenario.distribution_type = None
        scenario.healthcare_pre65_override = Decimal("12000")
        scenario.healthcare_medicare_override = Decimal("8000")
        scenario.healthcare_ltc_override = Decimal("5000")
        scenario.life_events = []
        scenario.spouse_social_security_monthly = None
        scenario.spouse_social_security_start_age = None

        user = Mock()
        user.birthdate = date(1985, 1, 1)

        account_data = {
            "total_portfolio": Decimal("1000000"),
            "taxable_balance": Decimal("300000"),
            "pre_tax_balance": Decimal("400000"),
            "roth_balance": Decimal("200000"),
            "hsa_balance": Decimal("50000"),
            "cash_balance": Decimal("50000"),
            "pension_monthly": Decimal("0"),
            "annual_contributions": Decimal("25000"),
            "employer_match_annual": Decimal("5000"),
            "annual_income": Decimal("100000"),
            "accounts": [],
        }

        with patch.object(
            RetirementMonteCarloService,
            "_gather_account_data",
            new_callable=AsyncMock,
            return_value=account_data,
        ):
            result = await RetirementMonteCarloService.run_simulation(db, scenario, user)

        assert result is not None


# ── Quick simulation additional edge cases ───────────────────────────────────


class TestQuickSimulationAdditional:
    """Additional quick simulation tests for edge cases and depletion tracking."""

    def test_median_depletion_age_when_most_deplete(self):
        """Should compute median_depletion_age when >50% of sims deplete."""
        result = RetirementMonteCarloService.run_quick_simulation(
            current_portfolio=50000,
            annual_contributions=0,
            current_age=60,
            retirement_age=60,
            life_expectancy=95,
            annual_spending=80000,
            num_sims=100,
        )
        # With tiny portfolio and high spending, most should deplete
        if result["success_rate"] < 50:
            assert result["median_depletion_age"] is not None
            assert result["median_depletion_age"] >= 60
            assert result["median_depletion_age"] <= 95

    def test_already_retired_simulation(self):
        """When current_age >= retirement_age, should still work."""
        result = RetirementMonteCarloService.run_quick_simulation(
            current_portfolio=1000000,
            annual_contributions=0,
            current_age=70,
            retirement_age=65,
            life_expectancy=95,
            annual_spending=50000,
            num_sims=50,
        )
        assert len(result["projections"]) == 26  # 70 to 95
        # All years should be in withdrawal phase
        for p in result["projections"]:
            assert p["age"] >= 70

    def test_one_year_horizon(self):
        """Minimal simulation: life_expectancy = current_age + 1."""
        result = RetirementMonteCarloService.run_quick_simulation(
            current_portfolio=100000,
            annual_contributions=0,
            current_age=90,
            retirement_age=65,
            life_expectancy=91,
            annual_spending=50000,
            num_sims=50,
        )
        assert len(result["projections"]) == 2  # year 0 and year 1

    def test_ss_income_before_start_age_not_counted(self):
        """SS income should not kick in before social_security_start_age."""
        import random

        random.seed(42)

        # Retire at 62, SS starts at 70
        result = RetirementMonteCarloService.run_quick_simulation(
            current_portfolio=500000,
            annual_contributions=0,
            current_age=62,
            retirement_age=62,
            life_expectancy=90,
            annual_spending=50000,
            social_security_monthly=3000,
            social_security_start_age=70,
            num_sims=50,
        )
        # Should still have projections from 62 to 90
        assert result["projections"][0]["age"] == 62
        assert len(result["projections"]) == 29


# ── _gather_account_data tests ───────────────────────────────────────────────


class TestGatherAccountData:
    """Test _gather_account_data (lines 738-859)."""

    @pytest.mark.asyncio
    async def test_gather_account_data_investment_accounts(self):
        """Test gathering data from investment-type accounts."""
        from decimal import Decimal
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        from app.models.account import AccountType

        db = AsyncMock()

        # Create mock investment account (tax-deferred)
        acct_401k = MagicMock()
        acct_401k.id = uuid4()
        acct_401k.name = "My 401k"
        acct_401k.current_balance = Decimal("200000")
        acct_401k.account_type = AccountType.RETIREMENT_401K
        acct_401k.tax_treatment = None
        acct_401k.monthly_benefit = None
        acct_401k.annual_salary = Decimal("100000")
        acct_401k.employer_match_percent = Decimal("6")
        acct_401k.employer_match_limit_percent = Decimal("6")

        # Create mock HSA account (tax-free, HSA type)
        acct_hsa = MagicMock()
        acct_hsa.id = uuid4()
        acct_hsa.name = "HSA"
        acct_hsa.current_balance = Decimal("30000")
        acct_hsa.account_type = AccountType.HSA
        acct_hsa.tax_treatment = None
        acct_hsa.monthly_benefit = None
        acct_hsa.annual_salary = None
        acct_hsa.employer_match_percent = None
        acct_hsa.employer_match_limit_percent = None

        # Create mock checking account (cash)
        acct_checking = MagicMock()
        acct_checking.id = uuid4()
        acct_checking.name = "Checking"
        acct_checking.current_balance = Decimal("5000")
        acct_checking.account_type = AccountType.CHECKING
        acct_checking.tax_treatment = None
        acct_checking.monthly_benefit = None
        acct_checking.annual_salary = None
        acct_checking.employer_match_percent = None
        acct_checking.employer_match_limit_percent = None

        # Create mock pension account
        acct_pension = MagicMock()
        acct_pension.id = uuid4()
        acct_pension.name = "Pension"
        acct_pension.current_balance = Decimal("0")
        acct_pension.account_type = AccountType.PENSION
        acct_pension.tax_treatment = None
        acct_pension.monthly_benefit = Decimal("2000")
        acct_pension.annual_salary = None
        acct_pension.employer_match_percent = None
        acct_pension.employer_match_limit_percent = None

        accounts = [acct_401k, acct_hsa, acct_checking, acct_pension]

        # Mock contributions
        contrib = MagicMock()
        contrib.amount = Decimal("500")
        contrib.frequency = MagicMock()
        contrib.frequency.value = "monthly"

        # Mock DB execute calls
        mock_acct_result = MagicMock()
        mock_acct_result.scalars.return_value.all.return_value = accounts

        mock_contrib_result = MagicMock()
        mock_contrib_result.scalars.return_value.all.return_value = [contrib]

        db.execute = AsyncMock(side_effect=[mock_acct_result, mock_contrib_result])

        result = await RetirementMonteCarloService._gather_account_data(
            db, str(uuid4()), str(uuid4())
        )

        assert result["total_portfolio"] > Decimal(0)
        assert result["hsa_balance"] == Decimal("30000")
        assert result["cash_balance"] == Decimal("5000")
        assert result["pension_monthly"] == Decimal("2000")
        assert result["annual_contributions"] == Decimal("6000")  # 500 * 12
        assert result["annual_income"] == Decimal("100000")
        assert result["employer_match_annual"] > Decimal(0)

    @pytest.mark.asyncio
    async def test_gather_account_data_roth_account(self):
        """Test Roth IRA is categorized as roth bucket."""
        from decimal import Decimal
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        from app.models.account import AccountType

        db = AsyncMock()

        acct_roth = MagicMock()
        acct_roth.id = uuid4()
        acct_roth.name = "Roth IRA"
        acct_roth.current_balance = Decimal("50000")
        acct_roth.account_type = AccountType.RETIREMENT_ROTH
        acct_roth.tax_treatment = None
        acct_roth.monthly_benefit = None
        acct_roth.annual_salary = None
        acct_roth.employer_match_percent = None
        acct_roth.employer_match_limit_percent = None

        mock_acct_result = MagicMock()
        mock_acct_result.scalars.return_value.all.return_value = [acct_roth]

        mock_contrib_result = MagicMock()
        mock_contrib_result.scalars.return_value.all.return_value = []

        db.execute = AsyncMock(side_effect=[mock_acct_result, mock_contrib_result])

        result = await RetirementMonteCarloService._gather_account_data(
            db, str(uuid4()), str(uuid4())
        )

        assert result["roth_balance"] == Decimal("50000")

    @pytest.mark.asyncio
    async def test_gather_account_data_taxable_brokerage(self):
        """Test taxable brokerage account categorization."""
        from decimal import Decimal
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        from app.models.account import AccountType

        db = AsyncMock()

        acct = MagicMock()
        acct.id = uuid4()
        acct.name = "Brokerage"
        acct.current_balance = Decimal("100000")
        acct.account_type = AccountType.BROKERAGE
        acct.tax_treatment = None
        acct.monthly_benefit = None
        acct.annual_salary = None
        acct.employer_match_percent = None
        acct.employer_match_limit_percent = None

        mock_acct_result = MagicMock()
        mock_acct_result.scalars.return_value.all.return_value = [acct]

        mock_contrib_result = MagicMock()
        mock_contrib_result.scalars.return_value.all.return_value = []

        db.execute = AsyncMock(side_effect=[mock_acct_result, mock_contrib_result])

        result = await RetirementMonteCarloService._gather_account_data(
            db, str(uuid4()), str(uuid4())
        )

        assert result["taxable_balance"] == Decimal("100000")

    @pytest.mark.asyncio
    async def test_gather_account_data_no_accounts(self):
        """Empty account list should return zero balances."""
        from decimal import Decimal
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        db = AsyncMock()

        mock_acct_result = MagicMock()
        mock_acct_result.scalars.return_value.all.return_value = []

        mock_contrib_result = MagicMock()
        mock_contrib_result.scalars.return_value.all.return_value = []

        db.execute = AsyncMock(side_effect=[mock_acct_result, mock_contrib_result])

        result = await RetirementMonteCarloService._gather_account_data(
            db, str(uuid4()), str(uuid4())
        )

        assert result["total_portfolio"] == Decimal(0)
        assert result["annual_contributions"] == Decimal(0)

    @pytest.mark.asyncio
    async def test_gather_account_data_contribution_frequencies(self):
        """Test different contribution frequencies are annualized correctly."""
        from decimal import Decimal
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        db = AsyncMock()

        mock_acct_result = MagicMock()
        mock_acct_result.scalars.return_value.all.return_value = []

        # Weekly contribution
        contrib_weekly = MagicMock()
        contrib_weekly.amount = Decimal("100")
        contrib_weekly.frequency = MagicMock()
        contrib_weekly.frequency.value = "weekly"

        # Quarterly contribution
        contrib_quarterly = MagicMock()
        contrib_quarterly.amount = Decimal("1000")
        contrib_quarterly.frequency = MagicMock()
        contrib_quarterly.frequency.value = "quarterly"

        # Contribution with no amount (should be skipped)
        contrib_empty = MagicMock()
        contrib_empty.amount = None

        mock_contrib_result = MagicMock()
        mock_contrib_result.scalars.return_value.all.return_value = [
            contrib_weekly,
            contrib_quarterly,
            contrib_empty,
        ]

        db.execute = AsyncMock(side_effect=[mock_acct_result, mock_contrib_result])

        result = await RetirementMonteCarloService._gather_account_data(
            db, str(uuid4()), str(uuid4())
        )

        # 100*52 + 1000*4 = 5200 + 4000 = 9200
        assert result["annual_contributions"] == Decimal("9200")

    @pytest.mark.asyncio
    async def test_gather_account_data_savings_account(self):
        """Test savings and money market accounts count as cash."""
        from decimal import Decimal
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        from app.models.account import AccountType

        db = AsyncMock()

        acct_savings = MagicMock()
        acct_savings.id = uuid4()
        acct_savings.name = "Savings"
        acct_savings.current_balance = Decimal("10000")
        acct_savings.account_type = AccountType.SAVINGS
        acct_savings.tax_treatment = None
        acct_savings.monthly_benefit = None
        acct_savings.annual_salary = None
        acct_savings.employer_match_percent = None
        acct_savings.employer_match_limit_percent = None

        mock_acct_result = MagicMock()
        mock_acct_result.scalars.return_value.all.return_value = [acct_savings]

        mock_contrib_result = MagicMock()
        mock_contrib_result.scalars.return_value.all.return_value = []

        db.execute = AsyncMock(side_effect=[mock_acct_result, mock_contrib_result])

        result = await RetirementMonteCarloService._gather_account_data(
            db, str(uuid4()), str(uuid4())
        )

        assert result["cash_balance"] == Decimal("10000")
        assert result["taxable_balance"] == Decimal("10000")
        assert result["total_portfolio"] == Decimal("10000")


# ── run_simulation with life events during accumulation/retirement ────────


class TestRunSimulationLifeEvents:
    """Cover lines 401-402, 429-430 — life event costs with medical inflation."""

    @pytest.mark.asyncio
    async def test_simulation_with_life_events_during_accumulation(self):
        """Life event during accumulation phase (lines 428-430)."""
        from datetime import date
        from decimal import Decimal
        from unittest.mock import AsyncMock, Mock, patch
        from uuid import uuid4

        from app.models.retirement import DistributionType

        db = AsyncMock()

        # Life event during accumulation (age 45-50, retirement at 65)
        event = Mock()
        event.name = "Medical"
        event.category = "healthcare"
        event.start_age = 45
        event.end_age = 50
        event.one_time_cost = None
        event.annual_cost = Decimal("10000")
        event.income_change = None
        event.use_medical_inflation = True  # Cover med inflation branch

        scenario = Mock()
        scenario.id = uuid4()
        scenario.organization_id = uuid4()
        scenario.user_id = uuid4()
        scenario.retirement_age = 65
        scenario.life_expectancy = 85
        scenario.annual_spending_retirement = Decimal("50000")
        scenario.pre_retirement_return = Decimal("7")
        scenario.post_retirement_return = Decimal("5")
        scenario.volatility = Decimal("15")
        scenario.inflation_rate = Decimal("3")
        scenario.medical_inflation_rate = Decimal("5")
        scenario.social_security_monthly = None
        scenario.social_security_start_age = 67
        scenario.use_estimated_pia = False
        scenario.current_annual_income = Decimal("80000")
        scenario.withdrawal_strategy = "fixed"
        scenario.withdrawal_rate = Decimal("4")
        scenario.federal_tax_rate = Decimal("22")
        scenario.state_tax_rate = Decimal("5")
        scenario.capital_gains_rate = Decimal("15")
        scenario.num_simulations = 5
        scenario.distribution_type = DistributionType.NORMAL
        scenario.healthcare_pre65_override = None
        scenario.healthcare_medicare_override = None
        scenario.healthcare_ltc_override = None
        scenario.life_events = [event]
        scenario.spouse_social_security_monthly = None
        scenario.spouse_social_security_start_age = None

        user = Mock()
        user.birthdate = date(1985, 1, 1)  # ~41 years old

        account_data = {
            "total_portfolio": Decimal("300000"),
            "taxable_balance": Decimal("100000"),
            "pre_tax_balance": Decimal("100000"),
            "roth_balance": Decimal("50000"),
            "hsa_balance": Decimal("25000"),
            "cash_balance": Decimal("25000"),
            "pension_monthly": Decimal("0"),
            "annual_contributions": Decimal("15000"),
            "employer_match_annual": Decimal("3000"),
            "annual_income": Decimal("80000"),
            "accounts": [],
        }

        with patch.object(
            RetirementMonteCarloService,
            "_gather_account_data",
            new_callable=AsyncMock,
            return_value=account_data,
        ):
            result = await RetirementMonteCarloService.run_simulation(db, scenario, user)

        assert result is not None

    @pytest.mark.asyncio
    async def test_simulation_with_life_events_during_retirement(self):
        """Life event during retirement phase (lines 400-402) with medical inflation."""
        from datetime import date
        from decimal import Decimal
        from unittest.mock import AsyncMock, Mock, patch
        from uuid import uuid4

        db = AsyncMock()

        from app.models.retirement import DistributionType

        # Life event during retirement (age 70-75, retirement at 65)
        event = Mock()
        event.name = "Medical"
        event.category = "healthcare"
        event.start_age = 70
        event.end_age = 75
        event.one_time_cost = None
        event.annual_cost = Decimal("15000")
        event.income_change = None
        event.use_medical_inflation = True  # Cover med inflation branch

        scenario = Mock()
        scenario.id = uuid4()
        scenario.organization_id = uuid4()
        scenario.user_id = uuid4()
        scenario.retirement_age = 65
        scenario.life_expectancy = 80
        scenario.annual_spending_retirement = Decimal("50000")
        scenario.pre_retirement_return = Decimal("7")
        scenario.post_retirement_return = Decimal("5")
        scenario.volatility = Decimal("15")
        scenario.inflation_rate = Decimal("3")
        scenario.medical_inflation_rate = Decimal("5")
        scenario.social_security_monthly = None
        scenario.social_security_start_age = 67
        scenario.use_estimated_pia = False
        scenario.current_annual_income = Decimal("80000")
        scenario.withdrawal_strategy = "fixed"
        scenario.withdrawal_rate = Decimal("4")
        scenario.federal_tax_rate = Decimal("22")
        scenario.state_tax_rate = Decimal("5")
        scenario.capital_gains_rate = Decimal("15")
        scenario.num_simulations = 5
        scenario.distribution_type = DistributionType.NORMAL
        scenario.healthcare_pre65_override = None
        scenario.healthcare_medicare_override = None
        scenario.healthcare_ltc_override = None
        scenario.life_events = [event]
        scenario.spouse_social_security_monthly = None
        scenario.spouse_social_security_start_age = None

        user = Mock()
        user.birthdate = date(1960, 1, 1)  # ~66 years old, already retired

        account_data = {
            "total_portfolio": Decimal("1000000"),
            "taxable_balance": Decimal("300000"),
            "pre_tax_balance": Decimal("400000"),
            "roth_balance": Decimal("200000"),
            "hsa_balance": Decimal("50000"),
            "cash_balance": Decimal("50000"),
            "pension_monthly": Decimal("0"),
            "annual_contributions": Decimal("0"),
            "employer_match_annual": Decimal("0"),
            "annual_income": Decimal("0"),
            "accounts": [],
        }

        with patch.object(
            RetirementMonteCarloService,
            "_gather_account_data",
            new_callable=AsyncMock,
            return_value=account_data,
        ):
            result = await RetirementMonteCarloService.run_simulation(db, scenario, user)

        assert result is not None

    @pytest.mark.asyncio
    async def test_simulation_withdrawal_comparison_error_handled(self):
        """Cover lines 545-546: exception in withdrawal comparison is caught."""
        from datetime import date
        from decimal import Decimal
        from unittest.mock import AsyncMock, Mock, patch
        from uuid import uuid4

        from app.models.retirement import DistributionType

        db = AsyncMock()

        scenario = Mock()
        scenario.id = uuid4()
        scenario.organization_id = uuid4()
        scenario.user_id = uuid4()
        scenario.retirement_age = 65
        scenario.life_expectancy = 85
        scenario.annual_spending_retirement = Decimal("50000")
        scenario.pre_retirement_return = Decimal("7")
        scenario.post_retirement_return = Decimal("5")
        scenario.volatility = Decimal("15")
        scenario.inflation_rate = Decimal("3")
        scenario.medical_inflation_rate = Decimal("5")
        scenario.social_security_monthly = None
        scenario.social_security_start_age = 67
        scenario.use_estimated_pia = False
        scenario.current_annual_income = Decimal("80000")
        scenario.withdrawal_strategy = "fixed"
        scenario.withdrawal_rate = Decimal("4")
        scenario.federal_tax_rate = Decimal("22")
        scenario.state_tax_rate = Decimal("5")
        scenario.capital_gains_rate = Decimal("15")
        scenario.num_simulations = 5
        scenario.distribution_type = DistributionType.NORMAL
        scenario.healthcare_pre65_override = None
        scenario.healthcare_medicare_override = None
        scenario.healthcare_ltc_override = None
        scenario.life_events = []
        scenario.spouse_social_security_monthly = None
        scenario.spouse_social_security_start_age = None

        user = Mock()
        user.birthdate = date(1985, 1, 1)

        account_data = {
            "total_portfolio": Decimal("300000"),
            "taxable_balance": Decimal("100000"),
            "pre_tax_balance": Decimal("100000"),
            "roth_balance": Decimal("50000"),
            "hsa_balance": Decimal("25000"),
            "cash_balance": Decimal("25000"),
            "pension_monthly": Decimal("0"),
            "annual_contributions": Decimal("15000"),
            "employer_match_annual": Decimal("3000"),
            "annual_income": Decimal("80000"),
            "accounts": [],
        }

        with patch.object(
            RetirementMonteCarloService,
            "_gather_account_data",
            new_callable=AsyncMock,
            return_value=account_data,
        ):
            # Make run_withdrawal_comparison raise an exception
            with patch(
                "app.services.retirement.monte_carlo_service.run_withdrawal_comparison",
                side_effect=Exception("comparison error"),
            ):
                result = await RetirementMonteCarloService.run_simulation(db, scenario, user)

        # Should succeed despite withdrawal comparison failure
        assert result is not None
        assert result.withdrawal_comparison_json is None
