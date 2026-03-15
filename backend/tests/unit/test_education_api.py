"""Unit tests for education planning and FIRE API endpoint functionality."""

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from app.api.v1.education import get_education_projection, list_education_plans
from app.api.v1.fire import get_fire_metrics
from app.models.user import User


def _make_user(**overrides):
    user = Mock(spec=User)
    user.id = overrides.get("id", uuid4())
    user.organization_id = overrides.get("organization_id", uuid4())
    user.is_org_admin = overrides.get("is_org_admin", False)
    return user


def _make_plan(**overrides):
    return {
        "account_id": overrides.get("account_id", str(uuid4())),
        "account_name": overrides.get("account_name", "Child 529"),
        "current_balance": overrides.get("current_balance", 25000.0),
        "monthly_contribution": overrides.get("monthly_contribution", 500.0),
        "user_id": overrides.get("user_id", str(uuid4())),
    }


def _make_fire_metrics(**overrides):
    return {
        "fi_ratio": {
            "fi_ratio": 0.5,
            "investable_assets": 100000.0,
            "annual_expenses": 50000.0,
            "fi_number": 1250000.0,
        },
        "savings_rate": {
            "savings_rate": 0.3,
            "income": 10000.0,
            "spending": 7000.0,
            "savings": 3000.0,
            "months": 12,
        },
        "years_to_fi": {
            "years_to_fi": 15.0,
            "fi_number": 1250000.0,
            "investable_assets": 100000.0,
            "annual_savings": 36000.0,
            "withdrawal_rate": 0.04,
            "expected_return": 0.07,
            "already_fi": False,
        },
        "coast_fi": {
            "coast_fi_number": 300000.0,
            "fi_number": 1250000.0,
            "investable_assets": 100000.0,
            "is_coast_fi": False,
            "retirement_age": 65,
            "years_until_retirement": 30,
            "expected_return": 0.07,
        },
        **overrides,
    }


# ------------------------------------------------------------------
# Education Plans
# ------------------------------------------------------------------


@pytest.mark.unit
class TestListEducationPlans:
    """Tests for list_education_plans endpoint."""

    @pytest.mark.asyncio
    async def test_returns_plans_and_total(self):
        """Should return plans list and computed total_529_savings."""
        mock_db = AsyncMock()
        user = _make_user()
        plans = [
            _make_plan(account_name="Alice 529", current_balance=10000.0),
            _make_plan(account_name="Bob 529", current_balance=15000.0),
        ]

        with patch(
            "app.api.v1.education.education_planning_service.get_education_plans",
            new=AsyncMock(return_value=plans),
        ):
            result = await list_education_plans(user_id=None, current_user=user, db=mock_db)

        assert len(result.plans) == 2
        assert result.plans[0].account_name == "Alice 529"
        assert result.plans[1].account_name == "Bob 529"
        assert result.total_529_savings == 25000.0

    @pytest.mark.asyncio
    async def test_empty_plans(self):
        """Should return empty list and zero total when no plans exist."""
        mock_db = AsyncMock()
        user = _make_user()

        with patch(
            "app.api.v1.education.education_planning_service.get_education_plans",
            new=AsyncMock(return_value=[]),
        ):
            result = await list_education_plans(user_id=None, current_user=user, db=mock_db)

        assert len(result.plans) == 0
        assert result.total_529_savings == 0.0

    @pytest.mark.asyncio
    async def test_passes_organization_id_to_service(self):
        """Should pass current_user.organization_id to the service."""
        mock_db = AsyncMock()
        org_id = uuid4()
        user = _make_user(organization_id=org_id)

        with patch(
            "app.api.v1.education.education_planning_service.get_education_plans",
            new=AsyncMock(return_value=[]),
        ) as mock_get:
            await list_education_plans(user_id=None, current_user=user, db=mock_db)
            mock_get.assert_called_once_with(
                db=mock_db,
                organization_id=org_id,
                user_id=None,
            )

    @pytest.mark.asyncio
    async def test_with_user_id_calls_verify_and_permission(self):
        """Should verify household member and check permissions when user_id given."""
        mock_db = AsyncMock()
        org_id = uuid4()
        user = _make_user(organization_id=org_id)
        target_id = uuid4()

        with (
            patch(
                "app.api.v1.education.verify_household_member",
                new=AsyncMock(),
            ) as mock_verify,
            patch(
                "app.api.v1.education.permission_service.require",
                new=AsyncMock(),
            ) as mock_require,
            patch(
                "app.api.v1.education.education_planning_service.get_education_plans",
                new=AsyncMock(return_value=[]),
            ) as mock_get,
        ):
            await list_education_plans(user_id=target_id, current_user=user, db=mock_db)

            mock_verify.assert_called_once_with(mock_db, target_id, org_id)
            mock_require.assert_called_once_with(
                mock_db,
                actor=user,
                action="read",
                resource_type="education_plan",
                owner_id=target_id,
            )
            mock_get.assert_called_once_with(
                db=mock_db,
                organization_id=org_id,
                user_id=target_id,
            )

    @pytest.mark.asyncio
    async def test_total_rounds_to_two_decimals(self):
        """Should round total_529_savings to 2 decimal places."""
        mock_db = AsyncMock()
        user = _make_user()
        plans = [
            _make_plan(current_balance=10000.333),
            _make_plan(current_balance=5000.669),
        ]

        with patch(
            "app.api.v1.education.education_planning_service.get_education_plans",
            new=AsyncMock(return_value=plans),
        ):
            result = await list_education_plans(user_id=None, current_user=user, db=mock_db)

        assert result.total_529_savings == 15001.0


# ------------------------------------------------------------------
# Education Projection
# ------------------------------------------------------------------


@pytest.mark.unit
class TestGetEducationProjection:
    """Tests for get_education_projection endpoint."""

    @pytest.mark.asyncio
    async def test_returns_projection(self):
        """Should return full projection response from service."""
        user = _make_user()
        projection_result = {
            "current_balance": 20000.0,
            "monthly_contribution": 500.0,
            "years_until_college": 10,
            "college_type": "public_in_state",
            "annual_return": 0.06,
            "projected_balance": 120000.0,
            "total_college_cost": 100000.0,
            "funding_percentage": 120.0,
            "funding_gap": 0.0,
            "funding_surplus": 20000.0,
            "recommended_monthly_to_close_gap": 0.0,
            "projections": [
                {"year": 1, "projected_savings": 27200.0},
                {"year": 2, "projected_savings": 34832.0},
            ],
        }

        with patch(
            "app.api.v1.education.education_planning_service.project_529",
            new=AsyncMock(return_value=projection_result),
        ):
            result = await get_education_projection(
                current_balance=20000.0,
                monthly_contribution=500.0,
                years_until_college=10,
                college_type="public_in_state",
                annual_return=0.06,
                current_user=user,
            )

        assert result.current_balance == 20000.0
        assert result.projected_balance == 120000.0
        assert result.funding_surplus == 20000.0
        assert len(result.projections) == 2
        assert result.projections[0].year == 1

    @pytest.mark.asyncio
    async def test_passes_params_to_service(self):
        """Should pass all parameters to project_529."""
        user = _make_user()
        projection_result = {
            "current_balance": 5000.0,
            "monthly_contribution": 200.0,
            "years_until_college": 15,
            "college_type": "private",
            "annual_return": 0.08,
            "projected_balance": 80000.0,
            "total_college_cost": 200000.0,
            "funding_percentage": 40.0,
            "funding_gap": 120000.0,
            "funding_surplus": 0.0,
            "recommended_monthly_to_close_gap": 450.0,
            "projections": [],
        }

        with patch(
            "app.api.v1.education.education_planning_service.project_529",
            new=AsyncMock(return_value=projection_result),
        ) as mock_project:
            await get_education_projection(
                current_balance=5000.0,
                monthly_contribution=200.0,
                years_until_college=15,
                college_type="private",
                annual_return=0.08,
                current_user=user,
            )

            mock_project.assert_called_once_with(
                current_balance=5000.0,
                monthly_contribution=200.0,
                years_until_college=15,
                college_type="private",
                annual_return=0.08,
            )

    @pytest.mark.asyncio
    async def test_invalid_college_type_falls_back(self):
        """Should fall back to public_in_state for invalid college_type."""
        user = _make_user()
        projection_result = {
            "current_balance": 10000.0,
            "monthly_contribution": 300.0,
            "years_until_college": 8,
            "college_type": "public_in_state",
            "annual_return": 0.06,
            "projected_balance": 60000.0,
            "total_college_cost": 80000.0,
            "funding_percentage": 75.0,
            "funding_gap": 20000.0,
            "funding_surplus": 0.0,
            "recommended_monthly_to_close_gap": 200.0,
            "projections": [],
        }

        with patch(
            "app.api.v1.education.education_planning_service.project_529",
            new=AsyncMock(return_value=projection_result),
        ) as mock_project:
            await get_education_projection(
                current_balance=10000.0,
                monthly_contribution=300.0,
                years_until_college=8,
                college_type="invalid_type",
                annual_return=0.06,
                current_user=user,
            )

            mock_project.assert_called_once_with(
                current_balance=10000.0,
                monthly_contribution=300.0,
                years_until_college=8,
                college_type="public_in_state",
                annual_return=0.06,
            )


# ------------------------------------------------------------------
# FIRE Metrics
# ------------------------------------------------------------------


@pytest.mark.unit
class TestGetFireMetrics:
    """Tests for get_fire_metrics endpoint."""

    @pytest.mark.asyncio
    async def test_returns_all_metric_sections(self):
        """Should return fi_ratio, savings_rate, years_to_fi, coast_fi."""
        mock_db = AsyncMock()
        user = _make_user()
        metrics = _make_fire_metrics()

        with patch("app.api.v1.fire.FireService") as MockService:
            MockService.return_value.get_fire_dashboard = AsyncMock(return_value=metrics)
            result = await get_fire_metrics(
                user_id=None,
                withdrawal_rate=0.04,
                expected_return=0.07,
                retirement_age=65,
                current_user=user,
                db=mock_db,
            )

        assert result.fi_ratio.fi_ratio == 0.5
        assert result.fi_ratio.investable_assets == 100000.0
        assert result.fi_ratio.annual_expenses == 50000.0
        assert result.fi_ratio.fi_number == 1250000.0

        assert result.savings_rate.savings_rate == 0.3
        assert result.savings_rate.income == 10000.0
        assert result.savings_rate.spending == 7000.0
        assert result.savings_rate.savings == 3000.0
        assert result.savings_rate.months == 12

        assert result.years_to_fi.years_to_fi == 15.0
        assert result.years_to_fi.already_fi is False
        assert result.years_to_fi.annual_savings == 36000.0

        assert result.coast_fi.coast_fi_number == 300000.0
        assert result.coast_fi.is_coast_fi is False
        assert result.coast_fi.retirement_age == 65

    @pytest.mark.asyncio
    async def test_passes_params_to_service(self):
        """Should instantiate FireService with db and pass params to get_fire_dashboard."""
        mock_db = AsyncMock()
        org_id = uuid4()
        user = _make_user(organization_id=org_id)
        metrics = _make_fire_metrics()

        with patch("app.api.v1.fire.FireService") as MockService:
            MockService.return_value.get_fire_dashboard = AsyncMock(return_value=metrics)
            await get_fire_metrics(
                user_id=None,
                withdrawal_rate=0.05,
                expected_return=0.08,
                retirement_age=60,
                current_user=user,
                db=mock_db,
            )

            MockService.assert_called_once_with(mock_db)
            MockService.return_value.get_fire_dashboard.assert_called_once_with(
                organization_id=org_id,
                user_id=None,
                withdrawal_rate=0.05,
                expected_return=0.08,
                retirement_age=60,
            )

    @pytest.mark.asyncio
    async def test_with_user_id_calls_verify_and_permission(self):
        """Should verify household and check fire_plan permission when user_id given."""
        mock_db = AsyncMock()
        org_id = uuid4()
        user = _make_user(organization_id=org_id)
        target_id = uuid4()
        metrics = _make_fire_metrics()

        with (
            patch("app.api.v1.fire.verify_household_member", new=AsyncMock()) as mock_verify,
            patch("app.api.v1.fire.permission_service.require", new=AsyncMock()) as mock_require,
            patch("app.api.v1.fire.FireService") as MockService,
        ):
            MockService.return_value.get_fire_dashboard = AsyncMock(return_value=metrics)
            await get_fire_metrics(
                user_id=target_id,
                withdrawal_rate=0.04,
                expected_return=0.07,
                retirement_age=65,
                current_user=user,
                db=mock_db,
            )

            mock_verify.assert_called_once_with(mock_db, target_id, org_id)
            mock_require.assert_called_once_with(
                mock_db,
                actor=user,
                action="read",
                resource_type="fire_plan",
                owner_id=target_id,
            )

    @pytest.mark.asyncio
    async def test_already_fi_scenario(self):
        """Should handle already_fi=True and years_to_fi=None."""
        mock_db = AsyncMock()
        user = _make_user()
        metrics = _make_fire_metrics()
        metrics["years_to_fi"]["already_fi"] = True
        metrics["years_to_fi"]["years_to_fi"] = None
        metrics["fi_ratio"]["fi_ratio"] = 1.2

        with patch("app.api.v1.fire.FireService") as MockService:
            MockService.return_value.get_fire_dashboard = AsyncMock(return_value=metrics)
            result = await get_fire_metrics(
                user_id=None,
                withdrawal_rate=0.04,
                expected_return=0.07,
                retirement_age=65,
                current_user=user,
                db=mock_db,
            )

        assert result.years_to_fi.already_fi is True
        assert result.years_to_fi.years_to_fi is None
        assert result.fi_ratio.fi_ratio == 1.2
