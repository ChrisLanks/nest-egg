"""Unit tests for household leave and onboarding API endpoints."""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.household import leave_household
from app.api.v1.onboarding import (
    OnboardingStepUpdate,
    complete_onboarding,
    get_onboarding_status,
    update_onboarding_step,
)
from app.models.user import User

# ---------------------------------------------------------------------------
# leave_household
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLeaveHousehold:
    """Test leave_household endpoint."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        user.email = "member@example.com"
        user.display_name = "Member"
        user.first_name = "Member"
        user.is_primary_household_member = False
        return user

    @pytest.mark.asyncio
    async def test_solo_member_cannot_leave(self, mock_db, mock_user):
        """Should return 400 when user is the only household member."""
        # member_count query returns 1
        count_result = Mock()
        count_result.scalar.return_value = 1
        mock_db.execute.return_value = count_result

        with pytest.raises(HTTPException) as exc_info:
            await leave_household(current_user=mock_user, db=mock_db)

        assert exc_info.value.status_code == 400
        assert "only member" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_primary_member_cannot_leave(self, mock_db, mock_user):
        """Should return 400 when the primary household member tries to leave."""
        mock_user.is_primary_household_member = True

        # member_count query returns 2 (multi-member household)
        count_result = Mock()
        count_result.scalar.return_value = 2
        mock_db.execute.return_value = count_result

        with pytest.raises(HTTPException) as exc_info:
            await leave_household(current_user=mock_user, db=mock_db)

        assert exc_info.value.status_code == 400
        assert "primary" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_non_primary_member_leaves_successfully(self, mock_db, mock_user):
        """Should succeed for a non-primary member in a multi-member household."""
        # member_count query returns 3
        count_result = Mock()
        count_result.scalar.return_value = 3

        # expire pending invitations (update result)
        update_result = Mock()

        # user_accounts query returns empty list (no accounts to migrate)
        accounts_result = Mock()
        accounts_result.scalars.return_value.all.return_value = []

        # shared budgets query returns empty list
        budgets_result = Mock()
        budgets_result.scalars.return_value.all.return_value = []

        # shared goals query returns empty list
        goals_result = Mock()
        goals_result.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [
            count_result,
            update_result,
            accounts_result,
            budgets_result,
            goals_result,
        ]

        result = await leave_household(current_user=mock_user, db=mock_db)

        assert "left the household" in result["message"].lower()
        assert mock_db.add.called  # new Organization added
        assert mock_db.commit.called
        # User should be re-homed as primary admin of their new org
        assert mock_user.is_primary_household_member is True
        assert mock_user.is_org_admin is True


# ---------------------------------------------------------------------------
# Onboarding endpoints
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetOnboardingStatus:
    """Test get_onboarding_status endpoint."""

    @pytest.mark.asyncio
    async def test_returns_onboarding_state(self):
        """Should return current onboarding status."""
        user = Mock(spec=User)
        user.onboarding_completed = False
        user.onboarding_step = "accounts"

        result = await get_onboarding_status(current_user=user)

        assert result.onboarding_completed is False
        assert result.onboarding_step == "accounts"


@pytest.mark.unit
class TestUpdateOnboardingStep:
    """Test update_onboarding_step endpoint."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.onboarding_completed = False
        user.onboarding_step = "profile"
        return user

    @pytest.mark.asyncio
    async def test_valid_step_succeeds(self, mock_db, mock_user):
        """Should update step when step name is valid."""
        body = OnboardingStepUpdate(step="budget")

        # After commit + refresh, the user's step is updated
        async def fake_refresh(obj):
            obj.onboarding_step = "budget"

        mock_db.refresh = fake_refresh

        result = await update_onboarding_step(
            body=body,
            current_user=mock_user,
            db=mock_db,
        )

        assert result.onboarding_step == "budget"
        assert result.onboarding_completed is False
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_step_returns_400(self, mock_db, mock_user):
        """Should return 400 for an unrecognised step name."""
        body = OnboardingStepUpdate(step="invalid_step")

        with pytest.raises(HTTPException) as exc_info:
            await update_onboarding_step(
                body=body,
                current_user=mock_user,
                db=mock_db,
            )

        assert exc_info.value.status_code == 400
        assert "Invalid step" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_already_completed_returns_409(self, mock_db, mock_user):
        """Should return 409 when onboarding is already completed."""
        mock_user.onboarding_completed = True
        body = OnboardingStepUpdate(step="budget")

        with pytest.raises(HTTPException) as exc_info:
            await update_onboarding_step(
                body=body,
                current_user=mock_user,
                db=mock_db,
            )

        assert exc_info.value.status_code == 409
        assert "already been completed" in exc_info.value.detail


@pytest.mark.unit
class TestCompleteOnboarding:
    """Test complete_onboarding endpoint."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.onboarding_completed = False
        user.onboarding_step = "goals"
        return user

    @pytest.mark.asyncio
    async def test_marks_onboarding_done(self, mock_db, mock_user):
        """Should set onboarding_completed to True and clear step."""

        async def fake_refresh(obj):
            obj.onboarding_completed = True
            obj.onboarding_step = None

        mock_db.refresh = fake_refresh

        result = await complete_onboarding(current_user=mock_user, db=mock_db)

        assert result.onboarding_completed is True
        assert result.onboarding_step is None
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_already_completed_returns_409(self, mock_db, mock_user):
        """Should return 409 when onboarding was already completed."""
        mock_user.onboarding_completed = True

        with pytest.raises(HTTPException) as exc_info:
            await complete_onboarding(current_user=mock_user, db=mock_db)

        assert exc_info.value.status_code == 409
        assert "already been completed" in exc_info.value.detail
