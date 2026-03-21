"""Tests for permission checks on education and FIRE endpoints."""

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.education import list_education_plans
from app.api.v1.fire import get_fire_metrics
from app.models.user import User


def _make_user(**overrides):
    user = Mock(spec=User)
    user.id = overrides.get("id", uuid4())
    user.organization_id = overrides.get("organization_id", uuid4())
    user.is_org_admin = overrides.get("is_org_admin", False)
    return user


@pytest.mark.unit
class TestEducationPermissions:
    """Permission checks for education planning endpoints."""

    @pytest.mark.asyncio
    async def test_own_data_no_permission_check(self):
        """Accessing own data (user_id=None) should not trigger permission check."""
        mock_db = AsyncMock()
        user = _make_user()

        with (
            patch(
                "app.api.v1.education.education_planning_service.get_education_plans",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "app.api.v1.education.permission_service.require",
                new=AsyncMock(),
            ) as mock_require,
        ):
            await list_education_plans(user_id=None, current_user=user, db=mock_db)
            mock_require.assert_not_called()

    @pytest.mark.asyncio
    async def test_other_user_triggers_permission_check(self):
        """Accessing another user's data should check education_plan permission."""
        mock_db = AsyncMock()
        org_id = uuid4()
        user = _make_user(organization_id=org_id)
        target_id = uuid4()

        with (
            patch(
                "app.api.v1.education.verify_household_member",
                new=AsyncMock(),
            ),
            patch(
                "app.api.v1.education.permission_service.require",
                new=AsyncMock(),
            ) as mock_require,
            patch(
                "app.api.v1.education.education_planning_service.get_education_plans",
                new=AsyncMock(return_value=[]),
            ),
        ):
            await list_education_plans(user_id=target_id, current_user=user, db=mock_db)
            mock_require.assert_called_once_with(
                mock_db,
                actor=user,
                action="read",
                resource_type="education_plan",
                owner_id=target_id,
            )

    @pytest.mark.asyncio
    async def test_denied_permission_raises_403(self):
        """Should raise 403 when permission is denied."""
        mock_db = AsyncMock()
        org_id = uuid4()
        user = _make_user(organization_id=org_id)
        target_id = uuid4()

        with (
            patch(
                "app.api.v1.education.verify_household_member",
                new=AsyncMock(),
            ),
            patch(
                "app.api.v1.education.permission_service.require",
                new=AsyncMock(
                    side_effect=HTTPException(status_code=403, detail="Insufficient permissions")
                ),
            ),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await list_education_plans(user_id=target_id, current_user=user, db=mock_db)
            assert exc_info.value.status_code == 403


@pytest.mark.unit
class TestFirePermissions:
    """Permission checks for FIRE metrics endpoint."""

    @pytest.mark.asyncio
    async def test_own_data_no_permission_check(self):
        """Accessing own data (user_id=None) should not trigger permission check."""
        mock_db = AsyncMock()
        user = _make_user()

        mock_metrics = {
            "fi_ratio": {
                "fi_ratio": 0.5,
                "investable_assets": 100000,
                "annual_expenses": 50000,
                "fi_number": 1250000,
            },
            "savings_rate": {
                "savings_rate": 0.3,
                "income": 10000,
                "spending": 7000,
                "savings": 3000,
                "months": 12,
            },
            "years_to_fi": {
                "years_to_fi": 15.0,
                "fi_number": 1250000,
                "investable_assets": 100000,
                "annual_savings": 36000,
                "withdrawal_rate": 0.04,
                "expected_return": 0.07,
                "already_fi": False,
            },
            "coast_fi": {
                "coast_fi_number": 300000,
                "fi_number": 1250000,
                "investable_assets": 100000,
                "is_coast_fi": False,
                "retirement_age": 65,
                "years_until_retirement": 30,
                "expected_return": 0.07,
            },
        }

        with (
            patch(
                "app.api.v1.fire.FireService",
            ) as MockService,
            patch(
                "app.api.v1.fire.permission_service.require",
                new=AsyncMock(),
            ) as mock_require,
        ):
            MockService.return_value.get_fire_dashboard = AsyncMock(return_value=mock_metrics)
            await get_fire_metrics(
                user_id=None,
                withdrawal_rate=0.04,
                expected_return=0.07,
                retirement_age=65,
                current_user=user,
                db=mock_db,
            )
            mock_require.assert_not_called()

    @pytest.mark.asyncio
    async def test_other_user_triggers_permission_check(self):
        """Accessing another user's data should check fire_plan permission."""
        mock_db = AsyncMock()
        org_id = uuid4()
        user = _make_user(organization_id=org_id)
        target_id = uuid4()

        mock_metrics = {
            "fi_ratio": {
                "fi_ratio": 0.5,
                "investable_assets": 100000,
                "annual_expenses": 50000,
                "fi_number": 1250000,
            },
            "savings_rate": {
                "savings_rate": 0.3,
                "income": 10000,
                "spending": 7000,
                "savings": 3000,
                "months": 12,
            },
            "years_to_fi": {
                "years_to_fi": 15.0,
                "fi_number": 1250000,
                "investable_assets": 100000,
                "annual_savings": 36000,
                "withdrawal_rate": 0.04,
                "expected_return": 0.07,
                "already_fi": False,
            },
            "coast_fi": {
                "coast_fi_number": 300000,
                "fi_number": 1250000,
                "investable_assets": 100000,
                "is_coast_fi": False,
                "retirement_age": 65,
                "years_until_retirement": 30,
                "expected_return": 0.07,
            },
        }

        with (
            patch("app.api.v1.fire.verify_household_member", new=AsyncMock()),
            patch("app.api.v1.fire.permission_service.require", new=AsyncMock()) as mock_require,
            patch("app.api.v1.fire.FireService") as MockService,
        ):
            MockService.return_value.get_fire_dashboard = AsyncMock(return_value=mock_metrics)
            await get_fire_metrics(
                user_id=target_id,
                withdrawal_rate=0.04,
                expected_return=0.07,
                retirement_age=65,
                current_user=user,
                db=mock_db,
            )
            mock_require.assert_called_once_with(
                mock_db,
                actor=user,
                action="read",
                resource_type="fire_plan",
                owner_id=target_id,
            )

    @pytest.mark.asyncio
    async def test_denied_permission_raises_403(self):
        """Should raise 403 when permission is denied."""
        mock_db = AsyncMock()
        org_id = uuid4()
        user = _make_user(organization_id=org_id)
        target_id = uuid4()

        with (
            patch("app.api.v1.fire.verify_household_member", new=AsyncMock()),
            patch(
                "app.api.v1.fire.permission_service.require",
                new=AsyncMock(
                    side_effect=HTTPException(status_code=403, detail="Insufficient permissions")
                ),
            ),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_fire_metrics(
                    user_id=target_id,
                    withdrawal_rate=0.04,
                    expected_return=0.07,
                    retirement_age=65,
                    current_user=user,
                    db=mock_db,
                )
            assert exc_info.value.status_code == 403
