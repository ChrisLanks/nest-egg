"""Unit tests for budgets API endpoints."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4
from decimal import Decimal
from datetime import datetime

from fastapi import HTTPException

from app.api.v1.budgets import (
    create_budget,
    list_budgets,
    get_budget,
    update_budget,
    delete_budget,
    get_budget_spending,
    check_budget_alerts,
    router,
)
from app.models.user import User
from app.models.budget import Budget, BudgetPeriod
from app.schemas.budget import BudgetCreate, BudgetUpdate


@pytest.mark.unit
class TestCreateBudget:
    """Test create_budget endpoint."""

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
    def budget_create_data(self):
        return BudgetCreate(
            name="Groceries Budget",
            amount=Decimal("500.00"),
            period=BudgetPeriod.MONTHLY,
            category_primary="Food and Drink",
            alert_threshold=Decimal("0.80"),
            is_active=True,
        )

    @pytest.mark.asyncio
    async def test_creates_budget_successfully(
        self, mock_db, mock_user, budget_create_data
    ):
        """Should create a new budget."""
        expected_budget = Mock(spec=Budget)
        expected_budget.id = uuid4()
        expected_budget.name = "Groceries Budget"
        expected_budget.amount = Decimal("500.00")

        with patch(
            "app.api.v1.budgets.budget_service.create_budget",
            return_value=expected_budget,
        ) as mock_create:
            result = await create_budget(
                budget_data=budget_create_data,
                current_user=mock_user,
                db=mock_db,
            )

            assert result.id == expected_budget.id
            assert result.name == "Groceries Budget"
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_passes_all_fields_to_service(
        self, mock_db, mock_user, budget_create_data
    ):
        """Should pass all budget fields to service."""
        expected_budget = Mock(spec=Budget)

        with patch(
            "app.api.v1.budgets.budget_service.create_budget",
            return_value=expected_budget,
        ) as mock_create:
            await create_budget(
                budget_data=budget_create_data,
                current_user=mock_user,
                db=mock_db,
            )

            call_kwargs = mock_create.call_args.kwargs
            assert call_kwargs["db"] == mock_db
            assert call_kwargs["user"] == mock_user
            assert call_kwargs["name"] == "Groceries Budget"
            assert call_kwargs["amount"] == Decimal("500.00")
            assert call_kwargs["period"] == BudgetPeriod.MONTHLY


@pytest.mark.unit
class TestListBudgets:
    """Test list_budgets endpoint."""

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
    async def test_lists_all_budgets(self, mock_db, mock_user):
        """Should list all budgets for organization."""
        budget1 = Mock(spec=Budget)
        budget1.id = uuid4()
        budget1.name = "Groceries"

        budget2 = Mock(spec=Budget)
        budget2.id = uuid4()
        budget2.name = "Dining Out"

        with patch(
            "app.api.v1.budgets.budget_service.get_budgets",
            return_value=[budget1, budget2],
        ):
            result = await list_budgets(
                is_active=None,
                current_user=mock_user,
                db=mock_db,
            )

            assert len(result) == 2
            assert result[0].name == "Groceries"
            assert result[1].name == "Dining Out"

    @pytest.mark.asyncio
    async def test_filters_by_active_status(self, mock_db, mock_user):
        """Should filter budgets by is_active when provided."""
        active_budget = Mock(spec=Budget)
        active_budget.id = uuid4()
        active_budget.name = "Active Budget"
        active_budget.is_active = True

        with patch(
            "app.api.v1.budgets.budget_service.get_budgets",
            return_value=[active_budget],
        ) as mock_get:
            result = await list_budgets(
                is_active=True,
                current_user=mock_user,
                db=mock_db,
            )

            assert len(result) == 1
            assert result[0].is_active is True
            mock_get.assert_called_once_with(
                db=mock_db,
                user=mock_user,
                is_active=True,
            )

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_budgets(self, mock_db, mock_user):
        """Should return empty list when no budgets exist."""
        with patch(
            "app.api.v1.budgets.budget_service.get_budgets",
            return_value=[],
        ):
            result = await list_budgets(
                is_active=None,
                current_user=mock_user,
                db=mock_db,
            )

            assert result == []


@pytest.mark.unit
class TestGetBudget:
    """Test get_budget endpoint."""

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
    async def test_returns_budget_successfully(self, mock_db, mock_user):
        """Should return budget when found."""
        budget_id = uuid4()
        expected_budget = Mock(spec=Budget)
        expected_budget.id = budget_id
        expected_budget.name = "Groceries"

        with patch(
            "app.api.v1.budgets.budget_service.get_budget",
            return_value=expected_budget,
        ):
            result = await get_budget(
                budget_id=budget_id,
                current_user=mock_user,
                db=mock_db,
            )

            assert result.id == budget_id
            assert result.name == "Groceries"

    @pytest.mark.asyncio
    async def test_raises_404_when_budget_not_found(self, mock_db, mock_user):
        """Should raise 404 when budget doesn't exist."""
        budget_id = uuid4()

        with patch(
            "app.api.v1.budgets.budget_service.get_budget",
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_budget(
                    budget_id=budget_id,
                    current_user=mock_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404
            assert "Budget not found" in exc_info.value.detail


@pytest.mark.unit
class TestUpdateBudget:
    """Test update_budget endpoint."""

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
    async def test_updates_budget_successfully(self, mock_db, mock_user):
        """Should update budget fields."""
        budget_id = uuid4()
        update_data = BudgetUpdate(
            name="Updated Budget Name",
            amount=Decimal("750.00"),
        )

        updated_budget = Mock(spec=Budget)
        updated_budget.id = budget_id
        updated_budget.name = "Updated Budget Name"
        updated_budget.amount = Decimal("750.00")

        with patch(
            "app.api.v1.budgets.budget_service.update_budget",
            return_value=updated_budget,
        ):
            result = await update_budget(
                budget_id=budget_id,
                budget_data=update_data,
                current_user=mock_user,
                db=mock_db,
            )

            assert result.id == budget_id
            assert result.name == "Updated Budget Name"
            assert result.amount == Decimal("750.00")

    @pytest.mark.asyncio
    async def test_passes_only_set_fields(self, mock_db, mock_user):
        """Should pass only explicitly set fields to service."""
        budget_id = uuid4()
        update_data = BudgetUpdate(name="New Name")  # Only name set

        updated_budget = Mock(spec=Budget)

        with patch(
            "app.api.v1.budgets.budget_service.update_budget",
            return_value=updated_budget,
        ) as mock_update:
            await update_budget(
                budget_id=budget_id,
                budget_data=update_data,
                current_user=mock_user,
                db=mock_db,
            )

            call_kwargs = mock_update.call_args.kwargs
            assert "name" in call_kwargs
            assert call_kwargs["name"] == "New Name"
            # Amount should not be in kwargs since it wasn't set
            assert "amount" not in call_kwargs or call_kwargs.get("amount") is None

    @pytest.mark.asyncio
    async def test_raises_404_when_budget_not_found(self, mock_db, mock_user):
        """Should raise 404 when budget doesn't exist."""
        budget_id = uuid4()
        update_data = BudgetUpdate(name="New Name")

        with patch(
            "app.api.v1.budgets.budget_service.update_budget",
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await update_budget(
                    budget_id=budget_id,
                    budget_data=update_data,
                    current_user=mock_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404
            assert "Budget not found" in exc_info.value.detail


@pytest.mark.unit
class TestDeleteBudget:
    """Test delete_budget endpoint."""

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
    async def test_deletes_budget_successfully(self, mock_db, mock_user):
        """Should delete budget and return None."""
        budget_id = uuid4()

        with patch(
            "app.api.v1.budgets.budget_service.delete_budget",
            return_value=True,
        ):
            result = await delete_budget(
                budget_id=budget_id,
                current_user=mock_user,
                db=mock_db,
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_raises_404_when_budget_not_found(self, mock_db, mock_user):
        """Should raise 404 when budget doesn't exist."""
        budget_id = uuid4()

        with patch(
            "app.api.v1.budgets.budget_service.delete_budget",
            return_value=False,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await delete_budget(
                    budget_id=budget_id,
                    current_user=mock_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404
            assert "Budget not found" in exc_info.value.detail


@pytest.mark.unit
class TestGetBudgetSpending:
    """Test get_budget_spending endpoint."""

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
    async def test_returns_spending_successfully(self, mock_db, mock_user):
        """Should return budget spending data."""
        budget_id = uuid4()

        spending_data = {
            "budget_id": budget_id,
            "budget_name": "Groceries",
            "budget_amount": Decimal("500.00"),
            "period": BudgetPeriod.MONTHLY,
            "current_spending": Decimal("350.00"),
            "remaining": Decimal("150.00"),
            "percentage_used": 70.0,
            "period_start": datetime(2024, 2, 1),
            "period_end": datetime(2024, 2, 29),
        }

        with patch(
            "app.api.v1.budgets.budget_service.get_budget_spending",
            return_value=spending_data,
        ):
            result = await get_budget_spending(
                budget_id=budget_id,
                current_user=mock_user,
                db=mock_db,
            )

            assert result["budget_id"] == budget_id
            assert result["budget_name"] == "Groceries"
            assert result["current_spending"] == Decimal("350.00")
            assert result["percentage_used"] == 70.0

    @pytest.mark.asyncio
    async def test_raises_404_when_budget_not_found(self, mock_db, mock_user):
        """Should raise 404 when budget doesn't exist."""
        budget_id = uuid4()

        with patch(
            "app.api.v1.budgets.budget_service.get_budget_spending",
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_budget_spending(
                    budget_id=budget_id,
                    current_user=mock_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404
            assert "Budget not found" in exc_info.value.detail


@pytest.mark.unit
class TestCheckBudgetAlerts:
    """Test check_budget_alerts endpoint."""

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
    async def test_returns_created_alerts(self, mock_db, mock_user):
        """Should return list of budgets that triggered alerts."""
        budget_id_1 = uuid4()
        budget_id_2 = uuid4()

        alerts = [
            {
                "budget_id": budget_id_1,
                "budget_name": "Groceries",
                "current_spending": Decimal("450.00"),
                "budget_amount": Decimal("500.00"),
                "percentage_used": 90.0,
            },
            {
                "budget_id": budget_id_2,
                "budget_name": "Dining",
                "current_spending": Decimal("210.00"),
                "budget_amount": Decimal("200.00"),
                "percentage_used": 105.0,
            },
        ]

        with patch(
            "app.api.v1.budgets.budget_service.check_budget_alerts",
            return_value=alerts,
        ):
            result = await check_budget_alerts(
                current_user=mock_user,
                db=mock_db,
            )

            assert result["alerts_created"] == 2
            assert len(result["budgets_alerted"]) == 2
            assert result["budgets_alerted"][0]["budget_name"] == "Groceries"
            assert result["budgets_alerted"][1]["percentage_used"] == 105.0

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_alerts(self, mock_db, mock_user):
        """Should return empty list when no budgets exceed threshold."""
        with patch(
            "app.api.v1.budgets.budget_service.check_budget_alerts",
            return_value=[],
        ):
            result = await check_budget_alerts(
                current_user=mock_user,
                db=mock_db,
            )

            assert result["alerts_created"] == 0
            assert result["budgets_alerted"] == []
