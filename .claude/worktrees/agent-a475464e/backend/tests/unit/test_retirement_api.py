"""Unit tests for retirement planning API endpoints."""

import json
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.retirement import (
    _format_simulation_result,
    add_life_event,
    add_life_event_from_preset,
    compare_scenarios,
    create_default_scenario,
    create_scenario,
    delete_life_event,
    delete_scenario,
    duplicate_scenario,
    export_projections_csv,
    get_account_data,
    get_healthcare_estimate,
    get_latest_results,
    get_scenario,
    get_social_security_estimate,
    list_life_event_presets,
    list_scenarios,
    quick_simulate,
    run_simulation,
    update_life_event,
    update_scenario,
)
from app.models.user import User

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(*, birthdate=None):
    user = Mock(spec=User)
    user.id = uuid4()
    user.organization_id = uuid4()
    user.birthdate = birthdate or date(1980, 6, 15)
    return user


def _make_scenario(user, *, scenario_id=None):
    scenario = Mock(spec=[])  # spec=[] prevents auto-attribute generation
    scenario.id = scenario_id or uuid4()
    scenario.user_id = user.id
    scenario.organization_id = user.organization_id
    scenario.name = "Test Scenario"
    scenario.description = None
    scenario.is_default = False
    scenario.retirement_age = 65
    scenario.life_expectancy = 90
    scenario.current_annual_income = Decimal("100000")
    scenario.annual_spending_retirement = Decimal("50000")
    scenario.pre_retirement_return = Decimal("0.07")
    scenario.post_retirement_return = Decimal("0.05")
    scenario.volatility = Decimal("0.15")
    scenario.inflation_rate = Decimal("0.03")
    scenario.medical_inflation_rate = Decimal("0.05")
    scenario.social_security_monthly = Decimal("2000")
    scenario.social_security_start_age = 67
    scenario.use_estimated_pia = False
    scenario.spouse_social_security_monthly = None
    scenario.spouse_social_security_start_age = None
    scenario.withdrawal_strategy = "simple_rate"
    scenario.withdrawal_rate = Decimal("0.04")
    scenario.federal_tax_rate = Decimal("0.22")
    scenario.state_tax_rate = Decimal("0.05")
    scenario.capital_gains_rate = Decimal("0.15")
    scenario.healthcare_pre65_override = None
    scenario.healthcare_medicare_override = None
    scenario.healthcare_ltc_override = None
    scenario.num_simulations = 1000
    scenario.inflation_adjusted = True
    scenario.distribution_type = "normal"
    scenario.is_shared = False
    scenario.include_all_members = False
    scenario.household_member_hash = None
    scenario.household_member_ids = None
    scenario.is_archived = False
    scenario.archived_at = None
    scenario.archived_reason = None
    scenario.life_events = []
    scenario.created_at = datetime(2024, 1, 1, 12, 0, 0)
    scenario.updated_at = datetime(2024, 1, 1, 12, 0, 0)
    return scenario


def _make_simulation_result(scenario_id):
    result = Mock()
    result.id = uuid4()
    result.scenario_id = scenario_id
    result.computed_at = datetime(2024, 1, 1, 12, 0, 0)
    result.num_simulations = 1000
    result.compute_time_ms = 150
    result.success_rate = Decimal("85.5")
    result.readiness_score = 78
    result.median_portfolio_at_retirement = Decimal("1500000")
    result.median_portfolio_at_end = Decimal("500000")
    result.median_depletion_age = 92
    result.estimated_pia = Decimal("2500")
    result.projections_json = json.dumps(
        [
            {
                "age": 65,
                "p10": 100000,
                "p25": 200000,
                "p50": 300000,
                "p75": 400000,
                "p90": 500000,
                "depletion_pct": 5.0,
            }
        ]
    )
    result.withdrawal_comparison_json = None
    return result


# ---------------------------------------------------------------------------
# Scenario CRUD
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCreateScenario:
    """Test create_scenario endpoint."""

    @pytest.mark.asyncio
    async def test_create_scenario_success(self):
        user = _make_user()
        db = AsyncMock()
        scenario = _make_scenario(user)

        data = Mock()
        data.model_dump.return_value = {"name": "My Plan", "retirement_age": 67}

        with patch(
            "app.api.v1.retirement.RetirementPlannerService.create_scenario",
            new_callable=AsyncMock,
            return_value=scenario,
        ):
            result = await create_scenario(data=data, current_user=user, db=db)

        assert result.name == "Test Scenario"
        db.commit.assert_awaited_once()


@pytest.mark.unit
class TestListScenarios:
    """Test list_scenarios endpoint."""

    @pytest.mark.asyncio
    async def test_list_scenarios_for_self(self):
        user = _make_user()
        db = AsyncMock()
        scenarios = [_make_scenario(user)]
        summaries = [{"name": "Test Scenario", "id": str(scenarios[0].id)}]

        with patch(
            "app.api.v1.retirement.RetirementPlannerService.list_scenarios",
            new_callable=AsyncMock,
            return_value=scenarios,
        ):
            with patch(
                "app.api.v1.retirement.RetirementPlannerService.get_scenario_summary_with_scores",
                new_callable=AsyncMock,
                return_value=summaries,
            ):
                result = await list_scenarios(user_id=None, current_user=user, db=db)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_list_scenarios_for_other_user_same_org(self):
        user = _make_user()
        other_user_id = str(uuid4())
        db = AsyncMock()

        # Mock the target user lookup
        target = Mock()
        target.organization_id = user.organization_id
        db.get = AsyncMock(return_value=target)

        with patch(
            "app.api.v1.retirement.RetirementPlannerService.list_scenarios",
            new_callable=AsyncMock,
            return_value=[],
        ):
            with patch(
                "app.api.v1.retirement.RetirementPlannerService.get_scenario_summary_with_scores",
                new_callable=AsyncMock,
                return_value=[],
            ):
                result = await list_scenarios(user_id=other_user_id, current_user=user, db=db)

        assert result == []

    @pytest.mark.asyncio
    async def test_list_scenarios_for_other_org_raises_403(self):
        user = _make_user()
        other_user_id = str(uuid4())
        db = AsyncMock()

        target = Mock()
        target.organization_id = uuid4()  # Different org
        db.get = AsyncMock(return_value=target)

        with pytest.raises(HTTPException) as exc_info:
            await list_scenarios(user_id=other_user_id, current_user=user, db=db)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_list_scenarios_target_not_found_raises_403(self):
        user = _make_user()
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await list_scenarios(user_id=str(uuid4()), current_user=user, db=db)

        assert exc_info.value.status_code == 403


@pytest.mark.unit
class TestCreateDefaultScenario:
    """Test create_default_scenario endpoint."""

    @pytest.mark.asyncio
    async def test_create_default_success(self):
        user = _make_user(birthdate=date(1985, 3, 20))
        db = AsyncMock()
        scenario = _make_scenario(user)

        with patch(
            "app.api.v1.retirement.RetirementPlannerService.create_default_scenario",
            new_callable=AsyncMock,
            return_value=scenario,
        ):
            result = await create_default_scenario(current_user=user, db=db)

        assert result.name == "Test Scenario"
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_default_no_birthdate_raises_400(self):
        user = _make_user()
        user.birthdate = None
        db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await create_default_scenario(current_user=user, db=db)

        assert exc_info.value.status_code == 400
        assert "birthdate" in exc_info.value.detail.lower()


@pytest.mark.unit
class TestGetScenario:
    """Test get_scenario endpoint."""

    @pytest.mark.asyncio
    async def test_get_scenario_success(self):
        user = _make_user()
        scenario_id = uuid4()
        scenario = _make_scenario(user, scenario_id=scenario_id)
        db = AsyncMock()

        with patch(
            "app.api.v1.retirement.RetirementPlannerService.get_scenario",
            new_callable=AsyncMock,
            return_value=scenario,
        ):
            result = await get_scenario(scenario_id=scenario_id, current_user=user, db=db)

        assert result.id == scenario_id

    @pytest.mark.asyncio
    async def test_get_scenario_not_found(self):
        user = _make_user()
        db = AsyncMock()

        with patch(
            "app.api.v1.retirement.RetirementPlannerService.get_scenario",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_scenario(scenario_id=uuid4(), current_user=user, db=db)

        assert exc_info.value.status_code == 404


@pytest.mark.unit
class TestUpdateScenario:
    """Test update_scenario endpoint."""

    @pytest.mark.asyncio
    async def test_update_scenario_success(self):
        user = _make_user()
        scenario = _make_scenario(user)
        db = AsyncMock()

        data = Mock()
        data.model_dump.return_value = {"name": "Updated Plan"}

        with patch(
            "app.api.v1.retirement.RetirementPlannerService.get_scenario",
            new_callable=AsyncMock,
            return_value=scenario,
        ):
            with patch(
                "app.api.v1.retirement.RetirementPlannerService.update_scenario",
                new_callable=AsyncMock,
                return_value=scenario,
            ):
                await update_scenario(scenario_id=scenario.id, data=data, current_user=user, db=db)

        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_scenario_not_found(self):
        user = _make_user()
        db = AsyncMock()
        data = Mock()
        data.model_dump.return_value = {}

        with patch(
            "app.api.v1.retirement.RetirementPlannerService.get_scenario",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await update_scenario(scenario_id=uuid4(), data=data, current_user=user, db=db)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_scenario_wrong_user_raises_403(self):
        user = _make_user()
        scenario = _make_scenario(user)
        scenario.user_id = uuid4()  # Different user
        db = AsyncMock()
        data = Mock()
        data.model_dump.return_value = {}

        with patch(
            "app.api.v1.retirement.RetirementPlannerService.get_scenario",
            new_callable=AsyncMock,
            return_value=scenario,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await update_scenario(scenario_id=scenario.id, data=data, current_user=user, db=db)

        assert exc_info.value.status_code == 403


@pytest.mark.unit
class TestDeleteScenario:
    """Test delete_scenario endpoint."""

    @pytest.mark.asyncio
    async def test_delete_scenario_success(self):
        user = _make_user()
        scenario = _make_scenario(user)
        db = AsyncMock()

        with patch(
            "app.api.v1.retirement.RetirementPlannerService.get_scenario",
            new_callable=AsyncMock,
            return_value=scenario,
        ):
            with patch(
                "app.api.v1.retirement.RetirementPlannerService.delete_scenario",
                new_callable=AsyncMock,
            ) as mock_delete:
                await delete_scenario(scenario_id=scenario.id, current_user=user, db=db)

        mock_delete.assert_awaited_once()
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_scenario_not_found(self):
        user = _make_user()
        db = AsyncMock()

        with patch(
            "app.api.v1.retirement.RetirementPlannerService.get_scenario",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await delete_scenario(scenario_id=uuid4(), current_user=user, db=db)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_scenario_wrong_user_raises_403(self):
        user = _make_user()
        scenario = _make_scenario(user)
        scenario.user_id = uuid4()
        db = AsyncMock()

        with patch(
            "app.api.v1.retirement.RetirementPlannerService.get_scenario",
            new_callable=AsyncMock,
            return_value=scenario,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await delete_scenario(scenario_id=scenario.id, current_user=user, db=db)

        assert exc_info.value.status_code == 403


@pytest.mark.unit
class TestDuplicateScenario:
    """Test duplicate_scenario endpoint."""

    @pytest.mark.asyncio
    async def test_duplicate_success(self):
        user = _make_user()
        scenario = _make_scenario(user)
        dup = _make_scenario(user)
        dup.name = "Copy of Test"
        db = AsyncMock()

        with patch(
            "app.api.v1.retirement.RetirementPlannerService.get_scenario",
            new_callable=AsyncMock,
            return_value=scenario,
        ):
            with patch(
                "app.api.v1.retirement.RetirementPlannerService.duplicate_scenario",
                new_callable=AsyncMock,
                return_value=dup,
            ):
                result = await duplicate_scenario(
                    scenario_id=scenario.id, name=None, current_user=user, db=db
                )

        assert result.name == "Copy of Test"
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_duplicate_not_found(self):
        user = _make_user()
        db = AsyncMock()

        with patch(
            "app.api.v1.retirement.RetirementPlannerService.get_scenario",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await duplicate_scenario(scenario_id=uuid4(), name=None, current_user=user, db=db)

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Life Events
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLifeEvents:
    """Test life event CRUD endpoints."""

    @pytest.mark.asyncio
    async def test_add_life_event_success(self):
        user = _make_user()
        scenario = _make_scenario(user)
        db = AsyncMock()

        data = Mock()
        data.model_dump.return_value = {
            "name": "Buy House",
            "category": "home_purchase",
            "start_age": 35,
            "end_age": 65,
            "annual_cost": 12000,
        }

        with patch(
            "app.api.v1.retirement.RetirementPlannerService.get_scenario",
            new_callable=AsyncMock,
            return_value=scenario,
        ):
            await add_life_event(scenario_id=scenario.id, data=data, current_user=user, db=db)

        db.add.assert_called_once()
        db.flush.assert_awaited_once()
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_add_life_event_scenario_not_found(self):
        user = _make_user()
        db = AsyncMock()
        data = Mock()

        with patch(
            "app.api.v1.retirement.RetirementPlannerService.get_scenario",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await add_life_event(scenario_id=uuid4(), data=data, current_user=user, db=db)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_add_life_event_wrong_user(self):
        user = _make_user()
        scenario = _make_scenario(user)
        scenario.user_id = uuid4()
        db = AsyncMock()
        data = Mock()

        with patch(
            "app.api.v1.retirement.RetirementPlannerService.get_scenario",
            new_callable=AsyncMock,
            return_value=scenario,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await add_life_event(scenario_id=scenario.id, data=data, current_user=user, db=db)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_update_life_event_success(self):
        user = _make_user()
        scenario = _make_scenario(user)
        event = Mock()
        event.id = uuid4()
        event.scenario_id = scenario.id
        db = AsyncMock()
        db.get = AsyncMock(return_value=event)

        data = Mock()
        data.model_dump.return_value = {"name": "Updated Event"}

        with patch(
            "app.api.v1.retirement.RetirementPlannerService.get_scenario",
            new_callable=AsyncMock,
            return_value=scenario,
        ):
            await update_life_event(event_id=event.id, data=data, current_user=user, db=db)

        db.flush.assert_awaited_once()
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_life_event_not_found(self):
        user = _make_user()
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)
        data = Mock()

        with pytest.raises(HTTPException) as exc_info:
            await update_life_event(event_id=uuid4(), data=data, current_user=user, db=db)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_life_event_scenario_not_found(self):
        user = _make_user()
        event = Mock()
        event.id = uuid4()
        event.scenario_id = uuid4()
        db = AsyncMock()
        db.get = AsyncMock(return_value=event)
        data = Mock()

        with patch(
            "app.api.v1.retirement.RetirementPlannerService.get_scenario",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await update_life_event(event_id=event.id, data=data, current_user=user, db=db)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_life_event_wrong_user(self):
        user = _make_user()
        scenario = _make_scenario(user)
        scenario.user_id = uuid4()  # Different user
        event = Mock()
        event.id = uuid4()
        event.scenario_id = scenario.id
        db = AsyncMock()
        db.get = AsyncMock(return_value=event)
        data = Mock()
        data.model_dump.return_value = {}

        with patch(
            "app.api.v1.retirement.RetirementPlannerService.get_scenario",
            new_callable=AsyncMock,
            return_value=scenario,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await update_life_event(event_id=event.id, data=data, current_user=user, db=db)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_life_event_success(self):
        user = _make_user()
        scenario = _make_scenario(user)
        event = Mock()
        event.id = uuid4()
        event.scenario_id = scenario.id
        db = AsyncMock()
        db.get = AsyncMock(return_value=event)

        with patch(
            "app.api.v1.retirement.RetirementPlannerService.get_scenario",
            new_callable=AsyncMock,
            return_value=scenario,
        ):
            await delete_life_event(event_id=event.id, current_user=user, db=db)

        db.delete.assert_awaited_once_with(event)
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_life_event_not_found(self):
        user = _make_user()
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await delete_life_event(event_id=uuid4(), current_user=user, db=db)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_life_event_wrong_user(self):
        user = _make_user()
        scenario = _make_scenario(user)
        scenario.user_id = uuid4()
        event = Mock()
        event.id = uuid4()
        event.scenario_id = scenario.id
        db = AsyncMock()
        db.get = AsyncMock(return_value=event)

        with patch(
            "app.api.v1.retirement.RetirementPlannerService.get_scenario",
            new_callable=AsyncMock,
            return_value=scenario,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await delete_life_event(event_id=event.id, current_user=user, db=db)

        assert exc_info.value.status_code == 403


@pytest.mark.unit
class TestLifeEventPresets:
    """Test life event preset endpoints."""

    @pytest.mark.asyncio
    async def test_list_presets(self):
        user = _make_user()

        with patch(
            "app.api.v1.retirement.get_all_presets",
            return_value=[
                {
                    "key": "buy_house",
                    "name": "Buy a House",
                    "description": "Down payment and closing costs",
                    "category": "home_purchase",
                    "one_time_cost": 60000,
                    "icon": "home",
                },
            ],
        ):
            result = await list_life_event_presets(current_user=user)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_add_from_preset_success(self):
        user = _make_user()
        scenario = _make_scenario(user)
        db = AsyncMock()

        data = Mock()
        data.preset_key = "buy_house"
        data.start_age = 35

        event_data = {
            "name": "Buy House",
            "category": "home_purchase",
            "start_age": 35,
            "one_time_cost": 50000,
        }

        with patch(
            "app.api.v1.retirement.RetirementPlannerService.get_scenario",
            new_callable=AsyncMock,
            return_value=scenario,
        ):
            with patch(
                "app.api.v1.retirement.create_life_event_from_preset",
                return_value=event_data,
            ):
                await add_life_event_from_preset(
                    scenario_id=scenario.id, data=data, current_user=user, db=db
                )

        db.add.assert_called_once()
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_add_from_preset_unknown_raises_400(self):
        user = _make_user()
        scenario = _make_scenario(user)
        db = AsyncMock()

        data = Mock()
        data.preset_key = "unknown_preset"
        data.start_age = None

        with patch(
            "app.api.v1.retirement.RetirementPlannerService.get_scenario",
            new_callable=AsyncMock,
            return_value=scenario,
        ):
            with patch(
                "app.api.v1.retirement.create_life_event_from_preset",
                return_value=None,
            ):
                with pytest.raises(HTTPException) as exc_info:
                    await add_life_event_from_preset(
                        scenario_id=scenario.id, data=data, current_user=user, db=db
                    )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_add_from_preset_scenario_not_found(self):
        user = _make_user()
        db = AsyncMock()
        data = Mock()
        data.preset_key = "buy_house"
        data.start_age = None

        with patch(
            "app.api.v1.retirement.RetirementPlannerService.get_scenario",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await add_life_event_from_preset(
                    scenario_id=uuid4(), data=data, current_user=user, db=db
                )

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Social Security & Healthcare
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSocialSecurityEstimate:
    """Test social security estimate endpoint."""

    @pytest.mark.asyncio
    async def test_estimate_success(self):
        user = _make_user(birthdate=date(1980, 6, 15))

        with patch(
            "app.api.v1.retirement.calculate_age",
            return_value=44,
        ):
            with patch(
                "app.api.v1.retirement.estimate_social_security",
                return_value={
                    "estimated_pia": 2800,
                    "monthly_at_62": 1960,
                    "monthly_at_fra": 2800,
                    "monthly_at_70": 3472,
                    "fra_age": 67.0,
                    "claiming_age": 67,
                    "monthly_benefit": 2800,
                },
            ):
                result = await get_social_security_estimate(
                    claiming_age=67,
                    override_salary=None,
                    override_pia=None,
                    user_id=None,
                    current_user=user,
                    db=AsyncMock(),
                )

        assert result.monthly_benefit == 2800

    @pytest.mark.asyncio
    async def test_estimate_no_birthdate_raises_400(self):
        user = _make_user()
        user.birthdate = None

        with pytest.raises(HTTPException) as exc_info:
            await get_social_security_estimate(
                claiming_age=67,
                override_salary=None,
                override_pia=None,
                user_id=None,
                current_user=user,
                db=AsyncMock(),
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_estimate_with_salary_override(self):
        user = _make_user(birthdate=date(1980, 6, 15))

        with patch("app.api.v1.retirement.calculate_age", return_value=44):
            with patch(
                "app.api.v1.retirement.estimate_social_security",
                return_value={
                    "estimated_pia": 3200,
                    "monthly_at_62": 2240,
                    "monthly_at_fra": 3200,
                    "monthly_at_70": 3968,
                    "fra_age": 67.0,
                    "claiming_age": 67,
                    "monthly_benefit": 3200,
                },
            ) as mock_estimate:
                await get_social_security_estimate(
                    claiming_age=67,
                    override_salary=100000.0,
                    override_pia=None,
                    user_id=None,
                    current_user=user,
                    db=AsyncMock(),
                )

        # Verify the salary override was passed
        call_kwargs = mock_estimate.call_args.kwargs
        assert call_kwargs["current_salary"] == 100000.0


@pytest.mark.unit
class TestHealthcareEstimate:
    """Test healthcare cost estimate endpoint."""

    @pytest.mark.asyncio
    async def test_estimate_success(self):
        user = _make_user(birthdate=date(1970, 1, 1))

        with patch("app.api.v1.retirement.calculate_age", return_value=54):
            with patch(
                "app.api.v1.retirement.estimate_annual_healthcare_cost",
                return_value={
                    "premium": 5000,
                    "out_of_pocket": 2000,
                    "long_term_care": 0,
                    "total": 7000,
                },
            ):
                result = await get_healthcare_estimate(
                    retirement_income=50000.0,
                    medical_inflation_rate=6.0,
                    include_ltc=True,
                    user_id=None,
                    current_user=user,
                    db=AsyncMock(),
                )

        assert result.total_lifetime > 0

    @pytest.mark.asyncio
    async def test_estimate_no_birthdate_raises_400(self):
        user = _make_user()
        user.birthdate = None

        with pytest.raises(HTTPException) as exc_info:
            await get_healthcare_estimate(
                retirement_income=50000.0,
                medical_inflation_rate=6.0,
                include_ltc=True,
                user_id=None,
                current_user=user,
                db=AsyncMock(),
            )

        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# Account Data
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetAccountData:
    """Test get_account_data endpoint."""

    @pytest.mark.asyncio
    async def test_account_data_success(self):
        user = _make_user()
        db = AsyncMock()

        account_data = {
            "total_portfolio": Decimal("500000"),
            "taxable_balance": Decimal("100000"),
            "pre_tax_balance": Decimal("300000"),
            "roth_balance": Decimal("50000"),
            "hsa_balance": Decimal("10000"),
            "cash_balance": Decimal("40000"),
            "pension_monthly": Decimal("0"),
            "annual_contributions": Decimal("25000"),
            "employer_match_annual": Decimal("5000"),
            "annual_income": Decimal("100000"),
            "accounts": [],
        }

        with patch(
            "app.api.v1.retirement.RetirementMonteCarloService._gather_account_data",
            new_callable=AsyncMock,
            return_value=account_data,
        ):
            result = await get_account_data(user_id=None, member_ids=None, current_user=user, db=db)

        assert result.total_portfolio == 500000.0
        assert result.annual_contributions == 25000.0

    @pytest.mark.asyncio
    async def test_account_data_for_other_user_different_org_raises_403(self):
        user = _make_user()
        other_user_id = str(uuid4())
        db = AsyncMock()

        target = Mock()
        target.organization_id = uuid4()  # Different org
        db.get = AsyncMock(return_value=target)

        with pytest.raises(HTTPException) as exc_info:
            await get_account_data(user_id=other_user_id, member_ids=None, current_user=user, db=db)

        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRunSimulation:
    """Test run_simulation endpoint."""

    @pytest.mark.asyncio
    async def test_run_simulation_success(self):
        user = _make_user(birthdate=date(1980, 6, 15))
        scenario = _make_scenario(user)
        sim_result = _make_simulation_result(scenario.id)
        db = AsyncMock()

        with patch(
            "app.api.v1.retirement.RetirementPlannerService.get_scenario",
            new_callable=AsyncMock,
            return_value=scenario,
        ):
            with patch(
                "app.api.v1.retirement.RetirementPlannerService.run_or_get_cached_simulation",
                new_callable=AsyncMock,
                return_value=sim_result,
            ):
                result = await run_simulation(scenario_id=scenario.id, current_user=user, db=db)

        assert result.success_rate == 85.5
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_run_simulation_not_found(self):
        user = _make_user()
        db = AsyncMock()

        with patch(
            "app.api.v1.retirement.RetirementPlannerService.get_scenario",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await run_simulation(scenario_id=uuid4(), current_user=user, db=db)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_run_simulation_no_birthdate(self):
        user = _make_user()
        user.birthdate = None
        scenario = _make_scenario(user)
        db = AsyncMock()

        with patch(
            "app.api.v1.retirement.RetirementPlannerService.get_scenario",
            new_callable=AsyncMock,
            return_value=scenario,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await run_simulation(scenario_id=scenario.id, current_user=user, db=db)

        assert exc_info.value.status_code == 400


@pytest.mark.unit
class TestGetLatestResults:
    """Test get_latest_results endpoint."""

    @pytest.mark.asyncio
    async def test_get_results_success(self):
        user = _make_user()
        scenario = _make_scenario(user)
        sim_result = _make_simulation_result(scenario.id)
        db = AsyncMock()

        with patch(
            "app.api.v1.retirement.RetirementPlannerService.get_scenario",
            new_callable=AsyncMock,
            return_value=scenario,
        ):
            with patch(
                "app.api.v1.retirement.RetirementPlannerService.get_latest_result",
                new_callable=AsyncMock,
                return_value=sim_result,
            ):
                result = await get_latest_results(scenario_id=scenario.id, current_user=user, db=db)

        assert result.readiness_score == 78

    @pytest.mark.asyncio
    async def test_get_results_no_simulation(self):
        user = _make_user()
        scenario = _make_scenario(user)
        db = AsyncMock()

        with patch(
            "app.api.v1.retirement.RetirementPlannerService.get_scenario",
            new_callable=AsyncMock,
            return_value=scenario,
        ):
            with patch(
                "app.api.v1.retirement.RetirementPlannerService.get_latest_result",
                new_callable=AsyncMock,
                return_value=None,
            ):
                with pytest.raises(HTTPException) as exc_info:
                    await get_latest_results(scenario_id=scenario.id, current_user=user, db=db)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_results_scenario_not_found(self):
        user = _make_user()
        db = AsyncMock()

        with patch(
            "app.api.v1.retirement.RetirementPlannerService.get_scenario",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_latest_results(scenario_id=uuid4(), current_user=user, db=db)

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Quick Simulate
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestQuickSimulate:
    """Test quick_simulate endpoint."""

    @pytest.mark.asyncio
    async def test_quick_simulate_success(self):
        user = _make_user()

        data = Mock()
        data.current_portfolio = Decimal("500000")
        data.annual_contributions = Decimal("25000")
        data.current_age = 40
        data.retirement_age = 65
        data.life_expectancy = 95
        data.annual_spending = Decimal("50000")
        data.pre_retirement_return = 0.07
        data.post_retirement_return = 0.05
        data.volatility = 0.15
        data.inflation_rate = 0.03
        data.social_security_monthly = 2500
        data.social_security_start_age = 67

        mock_result = {
            "success_rate": 87.5,
            "readiness_score": 80,
            "projections": [
                {
                    "age": 65,
                    "p10": 100,
                    "p25": 200,
                    "p50": 300,
                    "p75": 400,
                    "p90": 500,
                    "depletion_pct": 5,
                }
            ],
            "median_depletion_age": 92,
        }

        with patch(
            "app.api.v1.retirement.RetirementMonteCarloService.run_quick_simulation",
            return_value=mock_result,
        ):
            result = await quick_simulate(data=data, current_user=user)

        assert result.success_rate == 87.5
        assert result.readiness_score == 80


# ---------------------------------------------------------------------------
# Compare Scenarios
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCompareScenarios:
    """Test compare_scenarios endpoint."""

    @pytest.mark.asyncio
    async def test_compare_success(self):
        user = _make_user()
        scenario1 = _make_scenario(user)
        scenario2 = _make_scenario(user)
        result1 = _make_simulation_result(scenario1.id)
        result2 = _make_simulation_result(scenario2.id)
        db = AsyncMock()

        data = Mock()
        data.scenario_ids = [scenario1.id, scenario2.id]

        scenarios = {str(scenario1.id): scenario1, str(scenario2.id): scenario2}
        results = {str(scenario1.id): result1, str(scenario2.id): result2}

        async def mock_get_scenario(db, scenario_id, organization_id):
            return scenarios.get(str(scenario_id))

        async def mock_get_result(db, scenario_id):
            return results.get(str(scenario_id))

        with patch(
            "app.api.v1.retirement.RetirementPlannerService.get_scenario",
            side_effect=mock_get_scenario,
        ):
            with patch(
                "app.api.v1.retirement.RetirementPlannerService.get_latest_result",
                side_effect=mock_get_result,
            ):
                result = await compare_scenarios(data=data, current_user=user, db=db)

        assert len(result.scenarios) == 2

    @pytest.mark.asyncio
    async def test_compare_scenario_not_found(self):
        user = _make_user()
        db = AsyncMock()

        data = Mock()
        data.scenario_ids = [uuid4()]

        with patch(
            "app.api.v1.retirement.RetirementPlannerService.get_scenario",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await compare_scenarios(data=data, current_user=user, db=db)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_compare_no_results(self):
        user = _make_user()
        scenario = _make_scenario(user)
        db = AsyncMock()

        data = Mock()
        data.scenario_ids = [scenario.id]

        with patch(
            "app.api.v1.retirement.RetirementPlannerService.get_scenario",
            new_callable=AsyncMock,
            return_value=scenario,
        ):
            with patch(
                "app.api.v1.retirement.RetirementPlannerService.get_latest_result",
                new_callable=AsyncMock,
                return_value=None,
            ):
                with pytest.raises(HTTPException) as exc_info:
                    await compare_scenarios(data=data, current_user=user, db=db)

        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# CSV Export
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExportProjectionsCsv:
    """Test export_projections_csv endpoint."""

    @pytest.mark.asyncio
    async def test_export_csv_success(self):
        user = _make_user()
        scenario = _make_scenario(user)
        sim_result = _make_simulation_result(scenario.id)
        db = AsyncMock()

        with patch(
            "app.api.v1.retirement.RetirementPlannerService.get_scenario",
            new_callable=AsyncMock,
            return_value=scenario,
        ):
            with patch(
                "app.api.v1.retirement.RetirementPlannerService.get_latest_result",
                new_callable=AsyncMock,
                return_value=sim_result,
            ):
                response = await export_projections_csv(
                    scenario_id=scenario.id, current_user=user, db=db
                )

        assert response.media_type == "text/csv"

    @pytest.mark.asyncio
    async def test_export_csv_scenario_not_found(self):
        user = _make_user()
        db = AsyncMock()

        with patch(
            "app.api.v1.retirement.RetirementPlannerService.get_scenario",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await export_projections_csv(scenario_id=uuid4(), current_user=user, db=db)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_export_csv_no_results(self):
        user = _make_user()
        scenario = _make_scenario(user)
        db = AsyncMock()

        with patch(
            "app.api.v1.retirement.RetirementPlannerService.get_scenario",
            new_callable=AsyncMock,
            return_value=scenario,
        ):
            with patch(
                "app.api.v1.retirement.RetirementPlannerService.get_latest_result",
                new_callable=AsyncMock,
                return_value=None,
            ):
                with pytest.raises(HTTPException) as exc_info:
                    await export_projections_csv(scenario_id=scenario.id, current_user=user, db=db)

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Helper function
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFormatSimulationResult:
    """Test _format_simulation_result helper."""

    def test_format_with_all_fields(self):
        result = _make_simulation_result(uuid4())
        formatted = _format_simulation_result(result)

        assert formatted.success_rate == 85.5
        assert formatted.readiness_score == 78
        assert len(formatted.projections) == 1
        assert formatted.withdrawal_comparison is None

    def test_format_with_withdrawal_comparison(self):
        result = _make_simulation_result(uuid4())
        result.withdrawal_comparison_json = json.dumps(
            {"strategy_4pct": {"success_rate": 90}, "strategy_dynamic": {"success_rate": 95}}
        )
        formatted = _format_simulation_result(result)

        assert formatted.withdrawal_comparison is not None
        assert "strategy_4pct" in formatted.withdrawal_comparison

    def test_format_with_none_optional_fields(self):
        result = _make_simulation_result(uuid4())
        result.median_portfolio_at_retirement = None
        result.median_portfolio_at_end = None
        result.estimated_pia = None
        result.median_depletion_age = None

        formatted = _format_simulation_result(result)

        assert formatted.median_portfolio_at_retirement is None
        assert formatted.median_portfolio_at_end is None
        assert formatted.estimated_pia is None
