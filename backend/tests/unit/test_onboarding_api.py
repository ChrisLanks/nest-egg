"""Unit tests for onboarding API endpoints."""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.onboarding import (
    OnboardingStepUpdate,
    complete_onboarding,
    get_onboarding_status,
    update_onboarding_step,
)
from app.models.user import User


@pytest.mark.unit
class TestGetOnboardingStatus:
    """Test get_onboarding_status endpoint."""

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.onboarding_completed = False
        user.onboarding_step = "profile"
        return user

    @pytest.mark.asyncio
    async def test_returns_correct_status(self, mock_user):
        """Should return current onboarding state for the user."""
        result = await get_onboarding_status(current_user=mock_user)

        assert result.onboarding_completed is False
        assert result.onboarding_step == "profile"

    @pytest.mark.asyncio
    async def test_returns_completed_status(self, mock_user):
        """Should return completed status when onboarding is done."""
        mock_user.onboarding_completed = True
        mock_user.onboarding_step = None

        result = await get_onboarding_status(current_user=mock_user)

        assert result.onboarding_completed is True
        assert result.onboarding_step is None


@pytest.mark.unit
class TestUpdateOnboardingStep:
    """Test update_onboarding_step endpoint."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.onboarding_completed = False
        user.onboarding_step = "profile"
        return user

    @pytest.mark.asyncio
    async def test_valid_step_updates_successfully(self, mock_db, mock_user):
        """Should update the onboarding step for a valid step name."""
        body = OnboardingStepUpdate(step="accounts")

        result = await update_onboarding_step(body=body, current_user=mock_user, db=mock_db)

        assert mock_user.onboarding_step == "accounts"
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once_with(mock_user)
        assert result.onboarding_completed is False

    @pytest.mark.asyncio
    @pytest.mark.parametrize("step", ["profile", "accounts", "budget", "goals"])
    async def test_all_valid_steps_accepted(self, mock_db, mock_user, step):
        """Should accept all valid step names."""
        body = OnboardingStepUpdate(step=step)

        await update_onboarding_step(body=body, current_user=mock_user, db=mock_db)

        assert mock_user.onboarding_step == step

    @pytest.mark.asyncio
    async def test_invalid_step_returns_400(self, mock_db, mock_user):
        """Should raise 400 for an invalid step name."""
        body = OnboardingStepUpdate(step="invalid_step")

        with pytest.raises(HTTPException) as exc_info:
            await update_onboarding_step(body=body, current_user=mock_user, db=mock_db)

        assert exc_info.value.status_code == 400
        assert "Invalid step" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_already_completed_returns_409(self, mock_db, mock_user):
        """Should raise 409 when onboarding is already completed."""
        mock_user.onboarding_completed = True
        body = OnboardingStepUpdate(step="profile")

        with pytest.raises(HTTPException) as exc_info:
            await update_onboarding_step(body=body, current_user=mock_user, db=mock_db)

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
        user.id = uuid4()
        user.onboarding_completed = False
        user.onboarding_step = "goals"
        return user

    @pytest.mark.asyncio
    async def test_completes_onboarding_successfully(self, mock_db, mock_user):
        """Should mark onboarding as complete."""
        result = await complete_onboarding(current_user=mock_user, db=mock_db)

        assert mock_user.onboarding_completed is True
        assert mock_user.onboarding_step is None
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once_with(mock_user)
        assert result.onboarding_completed is True
        assert result.onboarding_step is None

    @pytest.mark.asyncio
    async def test_already_completed_returns_409(self, mock_db, mock_user):
        """Should raise 409 when onboarding is already completed."""
        mock_user.onboarding_completed = True

        with pytest.raises(HTTPException) as exc_info:
            await complete_onboarding(current_user=mock_user, db=mock_db)

        assert exc_info.value.status_code == 409
        assert "already been completed" in exc_info.value.detail
