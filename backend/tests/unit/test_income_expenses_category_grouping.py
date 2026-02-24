"""Unit tests for income-expenses category grouping functionality."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4
from datetime import date
from decimal import Decimal

from app.api.v1.income_expenses import get_income_expense_summary, get_category_drill_down
from app.models.user import User
from app.models.transaction import Transaction, Category
from app.models.account import Account


@pytest.mark.unit
class TestCategoryHierarchicalGrouping:
    """Test hierarchical category grouping in income/expense summary."""

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
    def date_range(self):
        return {
            "start_date": date(2024, 1, 1),
            "end_date": date(2024, 12, 31),
        }

    @pytest.mark.asyncio
    async def test_groups_child_categories_under_parent(
        self, mock_db, mock_user, date_range
    ):
        """Should group child categories under their parent category."""
        # Query 1: Combined totals (.one() → .total_income, .total_expenses)
        totals_result = Mock()
        totals_row = Mock(total_income=5000, total_expenses=3000)
        totals_result.one.return_value = totals_row

        # Query 2: Combined categories (iterable rows with category_name, income, expenses, income_count, expense_count)
        cat_row = Mock(category_name="Food", income=2000, expenses=2500, income_count=15, expense_count=20)
        category_result = Mock()
        category_result.__iter__ = lambda self: iter([cat_row])

        # Query 3: Batch has_children (.all() → rows with .name, .child_count)
        has_children_result = Mock()
        has_children_result.all.return_value = [Mock(name="Food", child_count=2)]

        mock_db.execute.side_effect = [
            totals_result,
            category_result,
            has_children_result,
        ]

        with patch("app.api.v1.income_expenses.get_all_household_accounts") as mock_accounts:
            mock_accounts.return_value = [
                Mock(id=uuid4(), is_active=True, exclude_from_cash_flow=False)
            ]

            result = await get_income_expense_summary(
                start_date=date_range["start_date"],
                end_date=date_range["end_date"],
                user_id=None,
                current_user=mock_user,
                db=mock_db,
            )

        # Should show "Food" as parent category
        income_food = next((c for c in result.income_categories if c.category == "Food"), None)
        assert income_food is not None
        assert income_food.amount == 2000
        assert income_food.count == 15

        expense_food = next((c for c in result.expense_categories if c.category == "Food"), None)
        assert expense_food is not None
        assert abs(expense_food.amount) == 2500
        assert expense_food.count == 20

    @pytest.mark.asyncio
    async def test_shows_parent_category_for_provider_categories(
        self, mock_db, mock_user, date_range
    ):
        """Should match provider categories by name and show parent if mapped."""
        totals_result = Mock()
        totals_result.one.return_value = Mock(total_income=1000, total_expenses=800)

        cat_row = Mock(category_name="Food", income=1000, expenses=800, income_count=10, expense_count=8)
        category_result = Mock()
        category_result.__iter__ = lambda self: iter([cat_row])

        has_children_result = Mock()
        has_children_result.all.return_value = [Mock(name="Food", child_count=1)]

        mock_db.execute.side_effect = [
            totals_result,
            category_result,
            has_children_result,
        ]

        with patch("app.api.v1.income_expenses.get_all_household_accounts") as mock_accounts:
            mock_accounts.return_value = [
                Mock(id=uuid4(), is_active=True, exclude_from_cash_flow=False)
            ]

            result = await get_income_expense_summary(
                start_date=date_range["start_date"],
                end_date=date_range["end_date"],
                user_id=None,
                current_user=mock_user,
                db=mock_db,
            )

        assert any(c.category == "Food" for c in result.income_categories)
        assert any(c.category == "Food" for c in result.expense_categories)

    @pytest.mark.asyncio
    async def test_shows_root_categories_without_parents(
        self, mock_db, mock_user, date_range
    ):
        """Should show root categories (without parents) as-is."""
        totals_result = Mock()
        totals_result.one.return_value = Mock(total_income=2000, total_expenses=1500)

        salary_row = Mock(category_name="Salary", income=2000, expenses=0, income_count=2, expense_count=0)
        utils_row = Mock(category_name="Utilities", income=0, expenses=1500, income_count=0, expense_count=5)
        category_result = Mock()
        category_result.__iter__ = lambda self: iter([salary_row, utils_row])

        has_children_result = Mock()
        has_children_result.all.return_value = [
            Mock(name="Salary", child_count=0),
            Mock(name="Utilities", child_count=0),
        ]

        mock_db.execute.side_effect = [
            totals_result,
            category_result,
            has_children_result,
        ]

        with patch("app.api.v1.income_expenses.get_all_household_accounts") as mock_accounts:
            mock_accounts.return_value = [
                Mock(id=uuid4(), is_active=True, exclude_from_cash_flow=False)
            ]

            result = await get_income_expense_summary(
                start_date=date_range["start_date"],
                end_date=date_range["end_date"],
                user_id=None,
                current_user=mock_user,
                db=mock_db,
            )

        assert any(c.category == "Salary" for c in result.income_categories)
        assert any(c.category == "Utilities" for c in result.expense_categories)

    @pytest.mark.asyncio
    async def test_calculates_percentages_correctly(
        self, mock_db, mock_user, date_range
    ):
        """Should calculate correct percentages for categories."""
        totals_result = Mock()
        totals_result.one.return_value = Mock(total_income=1000, total_expenses=1000)

        cat_a = Mock(category_name="Category A", income=600, expenses=0, income_count=5, expense_count=0)
        cat_b = Mock(category_name="Category B", income=400, expenses=0, income_count=3, expense_count=0)
        cat_x = Mock(category_name="Category X", income=0, expenses=700, income_count=0, expense_count=7)
        cat_y = Mock(category_name="Category Y", income=0, expenses=300, income_count=0, expense_count=3)
        category_result = Mock()
        category_result.__iter__ = lambda self: iter([cat_a, cat_b, cat_x, cat_y])

        has_children_result = Mock()
        has_children_result.all.return_value = []  # None found in DB

        mock_db.execute.side_effect = [
            totals_result,
            category_result,
            has_children_result,
        ]

        with patch("app.api.v1.income_expenses.get_all_household_accounts") as mock_accounts:
            mock_accounts.return_value = [
                Mock(id=uuid4(), is_active=True, exclude_from_cash_flow=False)
            ]

            result = await get_income_expense_summary(
                start_date=date_range["start_date"],
                end_date=date_range["end_date"],
                user_id=None,
                current_user=mock_user,
                db=mock_db,
            )

        ca = next(c for c in result.income_categories if c.category == "Category A")
        assert ca.percentage == pytest.approx(60.0, rel=0.01)

        cb = next(c for c in result.income_categories if c.category == "Category B")
        assert cb.percentage == pytest.approx(40.0, rel=0.01)

        cx = next(c for c in result.expense_categories if c.category == "Category X")
        assert cx.percentage == pytest.approx(70.0, rel=0.01)

        cy = next(c for c in result.expense_categories if c.category == "Category Y")
        assert cy.percentage == pytest.approx(30.0, rel=0.01)

    @pytest.mark.asyncio
    async def test_handles_zero_total_gracefully(
        self, mock_db, mock_user, date_range
    ):
        """Should handle zero total without division errors."""
        totals_result = Mock()
        totals_result.one.return_value = Mock(total_income=0, total_expenses=0)

        category_result = Mock()
        category_result.__iter__ = lambda self: iter([])

        # No categories → empty has_children result
        has_children_result = Mock()
        has_children_result.all.return_value = []

        mock_db.execute.side_effect = [
            totals_result,
            category_result,
            has_children_result,
        ]

        with patch("app.api.v1.income_expenses.get_all_household_accounts") as mock_accounts:
            mock_accounts.return_value = [
                Mock(id=uuid4(), is_active=True, exclude_from_cash_flow=False)
            ]

            result = await get_income_expense_summary(
                start_date=date_range["start_date"],
                end_date=date_range["end_date"],
                user_id=None,
                current_user=mock_user,
                db=mock_db,
            )

        assert result.total_income == 0
        assert result.total_expenses == 0
        assert result.net == 0
        assert len(result.income_categories) == 0
        assert len(result.expense_categories) == 0


@pytest.mark.unit
class TestCategoryDrillDown:
    """Test category drill-down endpoint."""

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
    def date_range(self):
        return {
            "start_date": date(2024, 1, 1),
            "end_date": date(2024, 12, 31),
        }

    @pytest.mark.asyncio
    async def test_returns_child_categories_for_parent(
        self, mock_db, mock_user, date_range
    ):
        """Should return child categories when drilling into parent."""
        parent_category = "Food"

        # Mock category lookup (find Food category)
        category_result = Mock()
        food_category = Mock(spec=Category)
        food_category.id = uuid4()
        food_category.name = "Food"
        food_category.parent_category_id = None
        category_result.scalar_one_or_none.return_value = food_category

        # Mock child categories query
        restaurants_cat = Mock(spec=Category)
        restaurants_cat.id = uuid4()
        restaurants_cat.name = "Restaurants"
        groceries_cat = Mock(spec=Category)
        groceries_cat.id = uuid4()
        groceries_cat.name = "Groceries"

        children_result = Mock()
        children_result.scalars.return_value.all.return_value = [
            restaurants_cat, groceries_cat,
        ]

        # Mock parent income total
        income_total_result = Mock()
        income_total_result.scalar.return_value = 2000

        # Mock parent expense total
        expense_total_result = Mock()
        expense_total_result.scalar.return_value = -2000

        # Mock income children breakdown
        income_row_1 = Mock()
        income_row_1.name = "Restaurants"
        income_row_1.total = 800
        income_row_1.count = 10
        income_row_2 = Mock()
        income_row_2.name = "Groceries"
        income_row_2.total = 1200
        income_row_2.count = 15

        income_children_result = Mock()
        income_children_result.__iter__ = lambda self: iter([income_row_1, income_row_2])

        expense_row_1 = Mock()
        expense_row_1.name = "Restaurants"
        expense_row_1.total = -900
        expense_row_1.count = 12
        expense_row_2 = Mock()
        expense_row_2.name = "Groceries"
        expense_row_2.total = -1100
        expense_row_2.count = 14

        expense_children_result = Mock()
        expense_children_result.__iter__ = lambda self: iter([expense_row_1, expense_row_2])

        mock_db.execute.side_effect = [
            category_result,
            children_result,
            income_total_result,
            expense_total_result,
            income_children_result,
            expense_children_result,
        ]

        with patch("app.api.v1.income_expenses.get_all_household_accounts") as mock_accounts:
            mock_accounts.return_value = [
                Mock(id=uuid4(), is_active=True, exclude_from_cash_flow=False)
            ]

            result = await get_category_drill_down(
                parent_category=parent_category,
                start_date=date_range["start_date"],
                end_date=date_range["end_date"],
                user_id=None,
                current_user=mock_user,
                db=mock_db,
            )

        assert len(result.income_categories) == 2
        assert any(c.category == "Restaurants" for c in result.income_categories)
        assert any(c.category == "Groceries" for c in result.income_categories)
        assert len(result.expense_categories) == 2

    @pytest.mark.asyncio
    async def test_returns_merchants_for_leaf_category(
        self, mock_db, mock_user, date_range
    ):
        """Should return merchants when drilling into leaf category (no children)."""
        leaf_category = "Restaurants"

        category_result = Mock()
        restaurants_category = Mock(spec=Category)
        restaurants_category.id = uuid4()
        restaurants_category.name = "Restaurants"
        restaurants_category.parent_category_id = uuid4()
        category_result.scalar_one_or_none.return_value = restaurants_category

        children_result = Mock()
        children_result.scalars.return_value.all.return_value = []

        income_row = Mock()
        income_row.total = Decimal("125.00")
        income_row.count = 5
        income_result = Mock()
        income_result.one_or_none.return_value = income_row

        expense_row = Mock()
        expense_row.total = Decimal("-200.00")
        expense_row.count = 15
        expense_result = Mock()
        expense_result.one_or_none.return_value = expense_row

        mock_db.execute.side_effect = [
            category_result,
            children_result,
            income_result,
            expense_result,
        ]

        with patch("app.api.v1.income_expenses.get_all_household_accounts") as mock_accounts:
            mock_accounts.return_value = [
                Mock(id=uuid4(), is_active=True, exclude_from_cash_flow=False)
            ]

            result = await get_category_drill_down(
                parent_category=leaf_category,
                start_date=date_range["start_date"],
                end_date=date_range["end_date"],
                user_id=None,
                current_user=mock_user,
                db=mock_db,
            )

        assert len(result.income_categories) == 1
        assert result.income_categories[0].category == leaf_category
        assert result.expense_categories[0].category == leaf_category

    @pytest.mark.asyncio
    async def test_handles_provider_category_without_custom_mapping(
        self, mock_db, mock_user, date_range
    ):
        """Should handle provider categories that don't have custom mappings."""
        provider_category = "Food and Drink"

        category_result = Mock()
        category_result.scalar_one_or_none.return_value = None

        income_row = Mock()
        income_row.total = Decimal("100.00")
        income_row.count = 5
        income_result = Mock()
        income_result.one_or_none.return_value = income_row

        expense_row = Mock()
        expense_row.total = Decimal("-150.00")
        expense_row.count = 7
        expense_result = Mock()
        expense_result.one_or_none.return_value = expense_row

        mock_db.execute.side_effect = [
            category_result,
            income_result,
            expense_result,
        ]

        with patch("app.api.v1.income_expenses.get_all_household_accounts") as mock_accounts:
            mock_accounts.return_value = [
                Mock(id=uuid4(), is_active=True, exclude_from_cash_flow=False)
            ]

            result = await get_category_drill_down(
                parent_category=provider_category,
                start_date=date_range["start_date"],
                end_date=date_range["end_date"],
                user_id=None,
                current_user=mock_user,
                db=mock_db,
            )

        assert len(result.income_categories) == 1
        assert result.income_categories[0].category == provider_category
