"""Unit tests for savings goals API endpoints."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4
from decimal import Decimal
from datetime import date

from fastapi import HTTPException

from app.api.v1.savings_goals import (
    create_goal,
    list_goals,
    get_goal,
    update_goal,
    delete_goal,
    sync_goal_from_account,
    get_goal_progress,
    router,
)
from app.models.user import User
from app.models.savings_goal import SavingsGoal
from app.schemas.savings_goal import SavingsGoalCreate, SavingsGoalUpdate


@pytest.mark.unit
class TestCreateGoal:
    """Test create_goal endpoint."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        return user

    @pytest.fixture
    def goal_create_data(self):
        return SavingsGoalCreate(
            name="Vacation Fund",
            target_amount=Decimal("5000.00"),
            current_amount=Decimal("500.00"),
            target_date=date(2025, 6, 1),
            account_id=None,
        )

    @pytest.mark.asyncio
    async def test_creates_goal_successfully(
        self, mock_db, mock_user, goal_create_data
    ):
        """Should create a new savings goal."""
        expected_goal = Mock(spec=SavingsGoal)
        expected_goal.id = uuid4()
        expected_goal.name = "Vacation Fund"
        expected_goal.target_amount = Decimal("5000.00")

        with patch(
            "app.api.v1.savings_goals.savings_goal_service.create_goal",
            return_value=expected_goal,
        ) as mock_create:
            result = await create_goal(
                goal_data=goal_create_data,
                current_user=mock_user,
                db=mock_db,
            )

            assert result.name == "Vacation Fund"
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_passes_all_fields_to_service(
        self, mock_db, mock_user, goal_create_data
    ):
        """Should pass all goal fields to service."""
        expected_goal = Mock(spec=SavingsGoal)

        with patch(
            "app.api.v1.savings_goals.savings_goal_service.create_goal",
            return_value=expected_goal,
        ) as mock_create:
            await create_goal(
                goal_data=goal_create_data,
                current_user=mock_user,
                db=mock_db,
            )

            call_kwargs = mock_create.call_args.kwargs
            assert call_kwargs["db"] == mock_db
            assert call_kwargs["user"] == mock_user
            assert call_kwargs["name"] == "Vacation Fund"
            assert call_kwargs["target_amount"] == Decimal("5000.00")


@pytest.mark.unit
class TestListGoals:
    """Test list_goals endpoint."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        return user

    @pytest.mark.asyncio
    async def test_lists_all_goals(self, mock_db, mock_user):
        """Should list all savings goals for organization."""
        goal1 = Mock(spec=SavingsGoal)
        goal1.id = uuid4()
        goal1.name = "Vacation"

        goal2 = Mock(spec=SavingsGoal)
        goal2.id = uuid4()
        goal2.name = "Emergency Fund"

        with patch(
            "app.api.v1.savings_goals.savings_goal_service.get_goals",
            return_value=[goal1, goal2],
        ):
            result = await list_goals(
                is_completed=None,
                current_user=mock_user,
                db=mock_db,
            )

            assert len(result) == 2
            assert result[0].name == "Vacation"
            assert result[1].name == "Emergency Fund"

    @pytest.mark.asyncio
    async def test_filters_by_completion_status(self, mock_db, mock_user):
        """Should filter goals by is_completed when provided."""
        completed_goal = Mock(spec=SavingsGoal)
        completed_goal.id = uuid4()
        completed_goal.name = "Completed Goal"

        with patch(
            "app.api.v1.savings_goals.savings_goal_service.get_goals",
            return_value=[completed_goal],
        ) as mock_get:
            result = await list_goals(
                is_completed=True,
                current_user=mock_user,
                db=mock_db,
            )

            assert len(result) == 1
            mock_get.assert_called_once_with(
                db=mock_db,
                user=mock_user,
                is_completed=True,
            )

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_goals(self, mock_db, mock_user):
        """Should return empty list when no goals exist."""
        with patch(
            "app.api.v1.savings_goals.savings_goal_service.get_goals",
            return_value=[],
        ):
            result = await list_goals(
                is_completed=None,
                current_user=mock_user,
                db=mock_db,
            )

            assert result == []


@pytest.mark.unit
class TestGetGoal:
    """Test get_goal endpoint."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        return user

    @pytest.mark.asyncio
    async def test_returns_goal_successfully(self, mock_db, mock_user):
        """Should return goal when found."""
        goal_id = uuid4()
        expected_goal = Mock(spec=SavingsGoal)
        expected_goal.id = goal_id
        expected_goal.name = "Vacation"

        with patch(
            "app.api.v1.savings_goals.savings_goal_service.get_goal",
            return_value=expected_goal,
        ):
            result = await get_goal(
                goal_id=goal_id,
                current_user=mock_user,
                db=mock_db,
            )

            assert result.id == goal_id
            assert result.name == "Vacation"

    @pytest.mark.asyncio
    async def test_raises_404_when_goal_not_found(self, mock_db, mock_user):
        """Should raise 404 when goal doesn't exist."""
        goal_id = uuid4()

        with patch(
            "app.api.v1.savings_goals.savings_goal_service.get_goal",
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_goal(
                    goal_id=goal_id,
                    current_user=mock_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404
            assert "not found" in exc_info.value.detail


@pytest.mark.unit
class TestUpdateGoal:
    """Test update_goal endpoint."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        return user

    @pytest.mark.asyncio
    async def test_updates_goal_successfully(self, mock_db, mock_user):
        """Should update goal fields."""
        goal_id = uuid4()
        update_data = SavingsGoalUpdate(
            name="Updated Goal Name",
            target_amount=Decimal("7500.00"),
        )

        updated_goal = Mock(spec=SavingsGoal)
        updated_goal.id = goal_id
        updated_goal.name = "Updated Goal Name"
        updated_goal.target_amount = Decimal("7500.00")

        with patch(
            "app.api.v1.savings_goals.savings_goal_service.update_goal",
            return_value=updated_goal,
        ):
            result = await update_goal(
                goal_id=goal_id,
                goal_data=update_data,
                current_user=mock_user,
                db=mock_db,
            )

            assert result.id == goal_id
            assert result.name == "Updated Goal Name"
            assert result.target_amount == Decimal("7500.00")

    @pytest.mark.asyncio
    async def test_passes_only_set_fields(self, mock_db, mock_user):
        """Should pass only explicitly set fields to service."""
        goal_id = uuid4()
        update_data = SavingsGoalUpdate(name="New Name")  # Only name set

        updated_goal = Mock(spec=SavingsGoal)

        with patch(
            "app.api.v1.savings_goals.savings_goal_service.update_goal",
            return_value=updated_goal,
        ) as mock_update:
            await update_goal(
                goal_id=goal_id,
                goal_data=update_data,
                current_user=mock_user,
                db=mock_db,
            )

            call_kwargs = mock_update.call_args.kwargs
            assert "name" in call_kwargs
            assert call_kwargs["name"] == "New Name"

    @pytest.mark.asyncio
    async def test_raises_404_when_goal_not_found(self, mock_db, mock_user):
        """Should raise 404 when goal doesn't exist."""
        goal_id = uuid4()
        update_data = SavingsGoalUpdate(name="New Name")

        with patch(
            "app.api.v1.savings_goals.savings_goal_service.update_goal",
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await update_goal(
                    goal_id=goal_id,
                    goal_data=update_data,
                    current_user=mock_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404


@pytest.mark.unit
class TestDeleteGoal:
    """Test delete_goal endpoint."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        return user

    @pytest.mark.asyncio
    async def test_deletes_goal_successfully(self, mock_db, mock_user):
        """Should delete goal and return None."""
        goal_id = uuid4()

        with patch(
            "app.api.v1.savings_goals.savings_goal_service.delete_goal",
            return_value=True,
        ):
            result = await delete_goal(
                goal_id=goal_id,
                current_user=mock_user,
                db=mock_db,
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_raises_404_when_goal_not_found(self, mock_db, mock_user):
        """Should raise 404 when goal doesn't exist."""
        goal_id = uuid4()

        with patch(
            "app.api.v1.savings_goals.savings_goal_service.delete_goal",
            return_value=False,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await delete_goal(
                    goal_id=goal_id,
                    current_user=mock_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404


@pytest.mark.unit
class TestSyncGoalFromAccount:
    """Test sync_goal_from_account endpoint."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        return user

    @pytest.mark.asyncio
    async def test_syncs_goal_successfully(self, mock_db, mock_user):
        """Should sync goal's current amount from linked account."""
        goal_id = uuid4()

        synced_goal = Mock(spec=SavingsGoal)
        synced_goal.id = goal_id
        synced_goal.current_amount = Decimal("2500.00")  # Updated from account

        with patch(
            "app.api.v1.savings_goals.savings_goal_service.sync_goal_from_account",
            return_value=synced_goal,
        ):
            result = await sync_goal_from_account(
                goal_id=goal_id,
                current_user=mock_user,
                db=mock_db,
            )

            assert result.current_amount == Decimal("2500.00")

    @pytest.mark.asyncio
    async def test_raises_404_when_goal_not_found(self, mock_db, mock_user):
        """Should raise 404 when goal doesn't exist."""
        goal_id = uuid4()

        with patch(
            "app.api.v1.savings_goals.savings_goal_service.sync_goal_from_account",
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await sync_goal_from_account(
                    goal_id=goal_id,
                    current_user=mock_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404
            assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_raises_404_when_no_account_linked(self, mock_db, mock_user):
        """Should raise 404 when goal has no linked account."""
        goal_id = uuid4()

        with patch(
            "app.api.v1.savings_goals.savings_goal_service.sync_goal_from_account",
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await sync_goal_from_account(
                    goal_id=goal_id,
                    current_user=mock_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404


@pytest.mark.unit
class TestGetGoalProgress:
    """Test get_goal_progress endpoint."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        return user

    @pytest.mark.asyncio
    async def test_returns_progress_successfully(self, mock_db, mock_user):
        """Should return goal progress metrics."""
        goal_id = uuid4()

        progress_data = {
            "goal_id": goal_id,
            "goal_name": "Vacation",
            "target_amount": Decimal("5000.00"),
            "current_amount": Decimal("2500.00"),
            "remaining_amount": Decimal("2500.00"),
            "progress_percentage": 50.0,
            "is_completed": False,
            "target_date": date(2025, 6, 1),
            "days_remaining": 150,
        }

        with patch(
            "app.api.v1.savings_goals.savings_goal_service.get_goal_progress",
            return_value=progress_data,
        ):
            result = await get_goal_progress(
                goal_id=goal_id,
                current_user=mock_user,
                db=mock_db,
            )

            assert result["goal_id"] == goal_id
            assert result["goal_name"] == "Vacation"
            assert result["current_amount"] == Decimal("2500.00")
            assert result["progress_percentage"] == 50.0

    @pytest.mark.asyncio
    async def test_raises_404_when_goal_not_found(self, mock_db, mock_user):
        """Should raise 404 when goal doesn't exist."""
        goal_id = uuid4()

        with patch(
            "app.api.v1.savings_goals.savings_goal_service.get_goal_progress",
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_goal_progress(
                    goal_id=goal_id,
                    current_user=mock_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404
