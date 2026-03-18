"""Unit tests for RetirementPlannerService."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest

from app.models.user import User
from app.services.retirement.retirement_planner_service import RetirementPlannerService


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    return db


@pytest.fixture
def mock_user():
    user = Mock(spec=User)
    user.id = uuid4()
    user.organization_id = uuid4()
    user.birthdate = None
    user.email = "test@example.com"
    return user


def _make_scenario(**kwargs):
    s = MagicMock()
    s.id = uuid4()
    s.organization_id = kwargs.get("organization_id", uuid4())
    s.user_id = kwargs.get("user_id", uuid4())
    s.name = kwargs.get("name", "Default Plan")
    s.description = kwargs.get("description", None)
    s.is_default = kwargs.get("is_default", True)
    s.retirement_age = kwargs.get("retirement_age", 67)
    s.life_expectancy = kwargs.get("life_expectancy", 95)
    s.current_annual_income = kwargs.get("current_annual_income", Decimal("100000"))
    s.annual_spending_retirement = kwargs.get("annual_spending_retirement", Decimal("60000"))
    s.pre_retirement_return = Decimal("0.07")
    s.post_retirement_return = Decimal("0.05")
    s.volatility = Decimal("0.15")
    s.inflation_rate = Decimal("0.03")
    s.medical_inflation_rate = Decimal("0.06")
    s.social_security_monthly = Decimal("2500")
    s.social_security_start_age = 67
    s.use_estimated_pia = False
    s.spouse_social_security_monthly = None
    s.spouse_social_security_start_age = 67
    s.withdrawal_strategy = "dynamic_guardrails"
    s.withdrawal_rate = Decimal("0.04")
    s.federal_tax_rate = Decimal("0.22")
    s.state_tax_rate = Decimal("0.05")
    s.capital_gains_rate = Decimal("0.15")
    s.num_simulations = 1000
    s.is_shared = False
    s.updated_at = MagicMock()
    s.life_events = []
    return s


class TestListScenarios:
    """Tests for list_scenarios."""

    @pytest.mark.asyncio
    async def test_returns_all_scenarios(self, mock_db):
        scenarios = [_make_scenario(), _make_scenario()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = scenarios
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await RetirementPlannerService.list_scenarios(mock_db, str(uuid4()))
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_filter_by_user_id(self, mock_db):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        await RetirementPlannerService.list_scenarios(mock_db, str(uuid4()), user_id=str(uuid4()))
        mock_db.execute.assert_called_once()


class TestGetScenario:
    """Tests for get_scenario."""

    @pytest.mark.asyncio
    async def test_returns_scenario(self, mock_db):
        scenario = _make_scenario()
        mock_result = MagicMock()
        mock_result.unique.return_value.scalars.return_value.first.return_value = scenario
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await RetirementPlannerService.get_scenario(
            mock_db, scenario.id, str(scenario.organization_id)
        )
        assert result == scenario

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, mock_db):
        mock_result = MagicMock()
        mock_result.unique.return_value.scalars.return_value.first.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await RetirementPlannerService.get_scenario(mock_db, uuid4(), str(uuid4()))
        assert result is None


class TestCreateScenario:
    """Tests for create_scenario."""

    @pytest.mark.asyncio
    async def test_creates_and_returns_scenario(self, mock_db):
        await RetirementPlannerService.create_scenario(
            mock_db,
            organization_id=str(uuid4()),
            user_id=str(uuid4()),
            name="Test Plan",
            retirement_age=65,
        )
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()
        mock_db.refresh.assert_called_once()


class TestUpdateScenario:
    """Tests for update_scenario."""

    @pytest.mark.asyncio
    async def test_updates_fields(self, mock_db):
        scenario = _make_scenario()
        updates = {"name": "Updated Plan", "retirement_age": 70}

        await RetirementPlannerService.update_scenario(mock_db, scenario, updates)
        assert scenario.name == "Updated Plan"
        assert scenario.retirement_age == 70
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_nonexistent_attributes(self, mock_db):
        scenario = _make_scenario()
        updates = {"nonexistent_field": "value"}

        await RetirementPlannerService.update_scenario(mock_db, scenario, updates)
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_none_values_for_non_override(self, mock_db):
        scenario = _make_scenario()
        original_name = scenario.name
        updates = {"name": None}

        await RetirementPlannerService.update_scenario(mock_db, scenario, updates)
        assert scenario.name == original_name

    @pytest.mark.asyncio
    async def test_allows_none_for_override_fields(self, mock_db):
        scenario = _make_scenario()
        # Simulate a field ending with _override
        scenario.healthcare_cost_override = Decimal("5000")
        updates = {"healthcare_cost_override": None}

        await RetirementPlannerService.update_scenario(mock_db, scenario, updates)
        assert scenario.healthcare_cost_override is None


class TestDeleteScenario:
    """Tests for delete_scenario."""

    @pytest.mark.asyncio
    async def test_deletes_scenario(self, mock_db):
        scenario = _make_scenario()
        await RetirementPlannerService.delete_scenario(mock_db, scenario)
        mock_db.delete.assert_called_once_with(scenario)
        mock_db.flush.assert_called_once()


class TestDuplicateScenario:
    """Tests for duplicate_scenario."""

    @pytest.mark.asyncio
    async def test_duplicates_with_default_name(self, mock_db):
        scenario = _make_scenario(name="Original Plan")
        scenario.life_events = []

        await RetirementPlannerService.duplicate_scenario(mock_db, scenario)
        mock_db.add.assert_called()
        mock_db.flush.assert_called()

    @pytest.mark.asyncio
    async def test_duplicates_with_custom_name(self, mock_db):
        scenario = _make_scenario(name="Original Plan")
        scenario.life_events = []

        await RetirementPlannerService.duplicate_scenario(mock_db, scenario, new_name="Custom Copy")
        mock_db.add.assert_called()

    @pytest.mark.asyncio
    async def test_duplicates_life_events(self, mock_db):
        scenario = _make_scenario(name="Plan with Events")
        event = MagicMock()
        event.name = "Travel"
        event.category = "lifestyle"
        event.start_age = 67
        event.end_age = 80
        event.annual_cost = Decimal("5000")
        event.one_time_cost = None
        event.income_change = None
        event.use_medical_inflation = False
        event.custom_inflation_rate = None
        event.is_preset = False
        event.preset_key = None
        event.sort_order = 0
        scenario.life_events = [event]

        await RetirementPlannerService.duplicate_scenario(mock_db, scenario)
        # Should add scenario + event = at least 2 calls to add
        assert mock_db.add.call_count >= 2


class TestRunOrGetCachedSimulation:
    """Tests for run_or_get_cached_simulation."""

    @pytest.mark.asyncio
    @patch("app.services.retirement.retirement_planner_service._compute_scenario_hash")
    async def test_returns_cached_result(self, mock_hash, mock_db, mock_user):
        mock_hash.return_value = "hash123"
        cached = MagicMock()

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = cached
        mock_db.execute = AsyncMock(return_value=mock_result)

        scenario = _make_scenario()
        result = await RetirementPlannerService.run_or_get_cached_simulation(
            mock_db, scenario, mock_user
        )
        assert result == cached

    @pytest.mark.asyncio
    @patch("app.services.retirement.retirement_planner_service.RetirementMonteCarloService")
    @patch("app.services.retirement.retirement_planner_service._compute_scenario_hash")
    async def test_runs_new_simulation_when_no_cache(self, mock_hash, mock_mc, mock_db, mock_user):
        mock_hash.return_value = "new_hash"

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None  # no cache
        mock_db.execute = AsyncMock(return_value=mock_result)

        new_result = MagicMock()
        mock_mc.run_simulation = AsyncMock(return_value=new_result)
        mock_mc._gather_account_data = AsyncMock(
            return_value={
                "total_portfolio": Decimal("0"),
                "taxable_balance": Decimal("0"),
                "pre_tax_balance": Decimal("0"),
                "roth_balance": Decimal("0"),
                "hsa_balance": Decimal("0"),
                "cash_balance": Decimal("0"),
                "pension_monthly": Decimal("0"),
                "annual_contributions": Decimal("0"),
                "employer_match_annual": Decimal("0"),
                "annual_income": Decimal("0"),
                "accounts": [],
            }
        )

        scenario = _make_scenario()
        result = await RetirementPlannerService.run_or_get_cached_simulation(
            mock_db, scenario, mock_user
        )
        assert result == new_result


class TestGetLatestResult:
    """Tests for get_latest_result."""

    @pytest.mark.asyncio
    async def test_returns_latest(self, mock_db):
        latest = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = latest
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await RetirementPlannerService.get_latest_result(mock_db, uuid4())
        assert result == latest

    @pytest.mark.asyncio
    async def test_returns_none_when_no_results(self, mock_db):
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await RetirementPlannerService.get_latest_result(mock_db, uuid4())
        assert result is None


class TestGetScenarioSummaryWithScores:
    """Tests for get_scenario_summary_with_scores."""

    @pytest.mark.asyncio
    async def test_enriches_with_scores(self, mock_db):
        scenario = _make_scenario()
        latest = MagicMock()
        latest.readiness_score = 85
        latest.success_rate = Decimal("0.82")

        with patch.object(
            RetirementPlannerService,
            "get_latest_result",
            new=AsyncMock(return_value=latest),
        ):
            result = await RetirementPlannerService.get_scenario_summary_with_scores(
                mock_db, [scenario]
            )

        assert len(result) == 1
        assert result[0]["readiness_score"] == 85
        assert result[0]["success_rate"] == 0.82

    @pytest.mark.asyncio
    async def test_no_latest_result(self, mock_db):
        scenario = _make_scenario()

        with patch.object(
            RetirementPlannerService,
            "get_latest_result",
            new=AsyncMock(return_value=None),
        ):
            result = await RetirementPlannerService.get_scenario_summary_with_scores(
                mock_db, [scenario]
            )

        assert result[0]["readiness_score"] is None
        assert result[0]["success_rate"] is None
