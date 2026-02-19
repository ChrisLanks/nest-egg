"""Unit tests for income-expenses category grouping functionality."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4
from datetime import date, datetime
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
        # Setup: Create parent category "Food" with children "Restaurants" and "Groceries"
        food_id = uuid4()
        restaurants_id = uuid4()
        groceries_id = uuid4()

        # Mock accounts query
        accounts_result = Mock()
        accounts_result.scalars.return_value.all.return_value = [
            Mock(id=uuid4(), is_active=True, exclude_from_cash_flow=False)
        ]

        # Mock total income/expense queries
        income_total = Mock()
        income_total.scalar.return_value = 5000
        expense_total = Mock()
        expense_total.scalar.return_value = -3000

        # Mock income categories - should show "Food" (parent) for both children
        income_cats_result = Mock()
        income_cats_result.__iter__ = lambda self: iter([
            Mock(category_name="Food", total=2000, count=15),  # Aggregated from children
        ])

        # Mock expense categories
        expense_cats_result = Mock()
        expense_cats_result.__iter__ = lambda self: iter([
            Mock(category_name="Food", total=-2500, count=20),  # Aggregated from children
        ])

        # Mock debug categories query
        debug_result = Mock()
        debug_result.all.return_value = [
            Mock(name="Food", parent_name=None),
            Mock(name="Restaurants", parent_name="Food"),
            Mock(name="Groceries", parent_name="Food"),
        ]

        mock_db.execute.side_effect = [
            accounts_result,  # Account query
            income_total,  # Total income
            expense_total,  # Total expenses
            debug_result,  # Debug categories
            income_cats_result,  # Income categories
            expense_cats_result,  # Expense categories
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

        # Should show "Food" as parent category, not individual children
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
        # Setup: Transaction has category_primary="Restaurants" (from Plaid)
        # Custom category "Restaurants" exists with parent "Food"
        # Should display as "Food" (parent)

        accounts_result = Mock()
        accounts_result.scalars.return_value.all.return_value = [
            Mock(id=uuid4(), is_active=True, exclude_from_cash_flow=False)
        ]

        income_total = Mock()
        income_total.scalar.return_value = 1000
        expense_total = Mock()
        expense_total.scalar.return_value = -800

        # Provider category "Restaurants" should be grouped under "Food"
        income_cats_result = Mock()
        income_cats_result.__iter__ = lambda self: iter([
            Mock(category_name="Food", total=1000, count=10),
        ])

        expense_cats_result = Mock()
        expense_cats_result.__iter__ = lambda self: iter([
            Mock(category_name="Food", total=-800, count=8),
        ])

        debug_result = Mock()
        debug_result.all.return_value = [
            Mock(name="Food", parent_name=None),
            Mock(name="Restaurants", parent_name="Food"),
        ]

        mock_db.execute.side_effect = [
            accounts_result,
            income_total,
            expense_total,
            debug_result,
            income_cats_result,
            expense_cats_result,
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

        # Provider category should be grouped under parent
        assert any(c.category == "Food" for c in result.income_categories)
        assert any(c.category == "Food" for c in result.expense_categories)

    @pytest.mark.asyncio
    async def test_shows_root_categories_without_parents(
        self, mock_db, mock_user, date_range
    ):
        """Should show root categories (without parents) as-is."""
        accounts_result = Mock()
        accounts_result.scalars.return_value.all.return_value = [
            Mock(id=uuid4(), is_active=True, exclude_from_cash_flow=False)
        ]

        income_total = Mock()
        income_total.scalar.return_value = 2000
        expense_total = Mock()
        expense_total.scalar.return_value = -1500

        # Root categories without parents
        income_cats_result = Mock()
        income_cats_result.__iter__ = lambda self: iter([
            Mock(category_name="Salary", total=2000, count=2),
        ])

        expense_cats_result = Mock()
        expense_cats_result.__iter__ = lambda self: iter([
            Mock(category_name="Utilities", total=-1500, count=5),
        ])

        debug_result = Mock()
        debug_result.all.return_value = [
            Mock(name="Salary", parent_name=None),
            Mock(name="Utilities", parent_name=None),
        ]

        mock_db.execute.side_effect = [
            accounts_result,
            income_total,
            expense_total,
            debug_result,
            income_cats_result,
            expense_cats_result,
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

        # Root categories should appear as-is
        assert any(c.category == "Salary" for c in result.income_categories)
        assert any(c.category == "Utilities" for c in result.expense_categories)

    @pytest.mark.asyncio
    async def test_calculates_percentages_correctly(
        self, mock_db, mock_user, date_range
    ):
        """Should calculate correct percentages for categories."""
        accounts_result = Mock()
        accounts_result.scalars.return_value.all.return_value = [
            Mock(id=uuid4(), is_active=True, exclude_from_cash_flow=False)
        ]

        income_total = Mock()
        income_total.scalar.return_value = 1000
        expense_total = Mock()
        expense_total.scalar.return_value = -1000

        # Two categories: 60% and 40%
        income_cats_result = Mock()
        income_cats_result.__iter__ = lambda self: iter([
            Mock(category_name="Category A", total=600, count=5),
            Mock(category_name="Category B", total=400, count=3),
        ])

        expense_cats_result = Mock()
        expense_cats_result.__iter__ = lambda self: iter([
            Mock(category_name="Category X", total=-700, count=7),
            Mock(category_name="Category Y", total=-300, count=3),
        ])

        debug_result = Mock()
        debug_result.all.return_value = []

        mock_db.execute.side_effect = [
            accounts_result,
            income_total,
            expense_total,
            debug_result,
            income_cats_result,
            expense_cats_result,
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

        # Verify percentages
        cat_a = next(c for c in result.income_categories if c.category == "Category A")
        assert cat_a.percentage == pytest.approx(60.0, rel=0.01)

        cat_b = next(c for c in result.income_categories if c.category == "Category B")
        assert cat_b.percentage == pytest.approx(40.0, rel=0.01)

        cat_x = next(c for c in result.expense_categories if c.category == "Category X")
        assert cat_x.percentage == pytest.approx(70.0, rel=0.01)

        cat_y = next(c for c in result.expense_categories if c.category == "Category Y")
        assert cat_y.percentage == pytest.approx(30.0, rel=0.01)

    @pytest.mark.asyncio
    async def test_handles_zero_total_gracefully(
        self, mock_db, mock_user, date_range
    ):
        """Should handle zero total without division errors."""
        accounts_result = Mock()
        accounts_result.scalars.return_value.all.return_value = [
            Mock(id=uuid4(), is_active=True, exclude_from_cash_flow=False)
        ]

        income_total = Mock()
        income_total.scalar.return_value = 0  # Zero income
        expense_total = Mock()
        expense_total.scalar.return_value = 0  # Zero expenses

        income_cats_result = Mock()
        income_cats_result.__iter__ = lambda self: iter([])

        expense_cats_result = Mock()
        expense_cats_result.__iter__ = lambda self: iter([])

        debug_result = Mock()
        debug_result.all.return_value = []

        mock_db.execute.side_effect = [
            accounts_result,
            income_total,
            expense_total,
            debug_result,
            income_cats_result,
            expense_cats_result,
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

        # Should not crash, should return empty lists
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

        # Mock accounts
        accounts_result = Mock()
        accounts_result.scalars.return_value.all.return_value = [
            Mock(id=uuid4(), is_active=True, exclude_from_cash_flow=False)
        ]

        # Mock category lookup (find Food category)
        category_result = Mock()
        food_category = Mock(spec=Category)
        food_category.id = uuid4()
        food_category.name = "Food"
        food_category.parent_category_id = None
        category_result.scalar_one_or_none.return_value = food_category

        # Mock child categories query
        children_result = Mock()
        children_result.all.return_value = [
            (uuid4(), "Restaurants"),
            (uuid4(), "Groceries"),
        ]

        # Mock income aggregation
        income_result = Mock()
        income_result.__iter__ = lambda self: iter([
            Mock(category_name="Restaurants", category_id=uuid4(), total=800, count=10, has_children=False),
            Mock(category_name="Groceries", category_id=uuid4(), total=1200, count=15, has_children=False),
        ])

        # Mock expense aggregation
        expense_result = Mock()
        expense_result.__iter__ = lambda self: iter([
            Mock(category_name="Restaurants", category_id=uuid4(), total=-900, count=12, has_children=False),
            Mock(category_name="Groceries", category_id=uuid4(), total=-1100, count=14, has_children=False),
        ])

        # Mock merchants query
        merchants_result = Mock()
        merchants_result.__iter__ = lambda self: iter([])

        mock_db.execute.side_effect = [
            accounts_result,  # Get accounts
            category_result,  # Find parent category
            children_result,  # Get children
            income_result,  # Income by children
            expense_result,  # Expenses by children
            merchants_result,  # Merchants (empty for category drill-down)
        ]

        with patch("app.api.v1.income_expenses.get_all_household_accounts") as mock_accounts:
            mock_accounts.return_value = [
                Mock(id=uuid4(), is_active=True, exclude_from_cash_flow=False)
            ]

            result = await get_category_drill_down(
                category=parent_category,
                start_date=date_range["start_date"],
                end_date=date_range["end_date"],
                user_id=None,
                current_user=mock_user,
                db=mock_db,
            )

        # Should return child categories
        assert len(result.income_categories) == 2
        assert any(c.category == "Restaurants" for c in result.income_categories)
        assert any(c.category == "Groceries" for c in result.income_categories)

        assert len(result.expense_categories) == 2
        assert any(c.category == "Restaurants" for c in result.expense_categories)
        assert any(c.category == "Groceries" for c in result.expense_categories)

    @pytest.mark.asyncio
    async def test_returns_merchants_for_leaf_category(
        self, mock_db, mock_user, date_range
    ):
        """Should return merchants when drilling into leaf category (no children)."""
        leaf_category = "Restaurants"

        # Mock accounts
        accounts_result = Mock()
        accounts_result.scalars.return_value.all.return_value = [
            Mock(id=uuid4(), is_active=True, exclude_from_cash_flow=False)
        ]

        # Mock category lookup
        category_result = Mock()
        restaurants_category = Mock(spec=Category)
        restaurants_category.id = uuid4()
        restaurants_category.name = "Restaurants"
        restaurants_category.parent_category_id = uuid4()  # Has parent (Food)
        category_result.scalar_one_or_none.return_value = restaurants_category

        # Mock child categories query (no children - leaf category)
        children_result = Mock()
        children_result.all.return_value = []

        # Mock merchants for leaf category
        income_merchants = Mock()
        income_merchants.__iter__ = lambda self: iter([
            Mock(merchant_name="McDonald's", total=50, count=2),
            Mock(merchant_name="Chipotle", total=75, count=3),
        ])

        expense_merchants = Mock()
        expense_merchants.__iter__ = lambda self: iter([
            Mock(merchant_name="Starbucks", total=-120, count=10),
            Mock(merchant_name="Subway", total=-80, count=5),
        ])

        mock_db.execute.side_effect = [
            accounts_result,
            category_result,
            children_result,  # No children
            income_merchants,  # Income by merchants
            expense_merchants,  # Expenses by merchants
        ]

        with patch("app.api.v1.income_expenses.get_all_household_accounts") as mock_accounts:
            mock_accounts.return_value = [
                Mock(id=uuid4(), is_active=True, exclude_from_cash_flow=False)
            ]

            result = await get_category_drill_down(
                category=leaf_category,
                start_date=date_range["start_date"],
                end_date=date_range["end_date"],
                user_id=None,
                current_user=mock_user,
                db=mock_db,
            )

        # Should return merchants, not categories
        assert len(result.income_categories) == 2
        assert any(c.category == "McDonald's" for c in result.income_categories)
        assert any(c.category == "Chipotle" for c in result.income_categories)

    @pytest.mark.asyncio
    async def test_handles_provider_category_without_custom_mapping(
        self, mock_db, mock_user, date_range
    ):
        """Should handle provider categories that don't have custom mappings."""
        provider_category = "Food and Drink"  # Plaid category not mapped

        # Mock accounts
        accounts_result = Mock()
        accounts_result.scalars.return_value.all.return_value = [
            Mock(id=uuid4(), is_active=True, exclude_from_cash_flow=False)
        ]

        # Mock category lookup (not found - provider category)
        category_result = Mock()
        category_result.scalar_one_or_none.return_value = None

        # Mock merchants for provider category
        income_merchants = Mock()
        income_merchants.__iter__ = lambda self: iter([
            Mock(merchant_name="Restaurant A", total=100, count=5),
        ])

        expense_merchants = Mock()
        expense_merchants.__iter__ = lambda self: iter([
            Mock(merchant_name="Restaurant B", total=-150, count=7),
        ])

        mock_db.execute.side_effect = [
            accounts_result,
            category_result,  # Category not found
            income_merchants,
            expense_merchants,
        ]

        with patch("app.api.v1.income_expenses.get_all_household_accounts") as mock_accounts:
            mock_accounts.return_value = [
                Mock(id=uuid4(), is_active=True, exclude_from_cash_flow=False)
            ]

            result = await get_category_drill_down(
                category=provider_category,
                start_date=date_range["start_date"],
                end_date=date_range["end_date"],
                user_id=None,
                current_user=mock_user,
                db=mock_db,
            )

        # Should return merchants directly
        assert len(result.income_categories) == 1
        assert result.income_categories[0].category == "Restaurant A"
