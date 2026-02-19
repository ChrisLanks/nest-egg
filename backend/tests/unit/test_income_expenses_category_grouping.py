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

        # Mock per-category has_children checks: one find + one count per unique category
        # Unique categories in results: "Food"
        food_cat_result = Mock()
        food_cat_id = uuid4()
        food_cat_result.scalar_one_or_none.return_value = food_cat_id
        food_children_count_result = Mock()
        food_children_count_result.scalar.return_value = 2  # Food has children

        mock_db.execute.side_effect = [
            income_total,  # Total income (accounts already patched via get_all_household_accounts)
            expense_total,  # Total expenses
            debug_result,  # Debug categories
            income_cats_result,  # Income categories
            expense_cats_result,  # Expense categories
            food_cat_result,  # Find "Food" category by name
            food_children_count_result,  # Count children of "Food"
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

        # Mock per-category has_children checks for "Food"
        food_cat_result = Mock()
        food_cat_result.scalar_one_or_none.return_value = uuid4()
        food_children_count_result = Mock()
        food_children_count_result.scalar.return_value = 1  # Food has children

        mock_db.execute.side_effect = [
            income_total,  # Total income (accounts already patched via get_all_household_accounts)
            expense_total,
            debug_result,
            income_cats_result,
            expense_cats_result,
            food_cat_result,  # Find "Food" category by name
            food_children_count_result,  # Count children of "Food"
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

        # Mock per-category has_children checks: "Salary" and "Utilities" (no children)
        salary_cat_result = Mock()
        salary_cat_result.scalar_one_or_none.return_value = uuid4()
        salary_children_count_result = Mock()
        salary_children_count_result.scalar.return_value = 0  # No children

        utilities_cat_result = Mock()
        utilities_cat_result.scalar_one_or_none.return_value = uuid4()
        utilities_children_count_result = Mock()
        utilities_children_count_result.scalar.return_value = 0  # No children

        mock_db.execute.side_effect = [
            income_total,  # Total income (accounts already patched via get_all_household_accounts)
            expense_total,
            debug_result,
            income_cats_result,
            expense_cats_result,
            salary_cat_result,  # Find "Salary" category
            salary_children_count_result,  # Count children of "Salary"
            utilities_cat_result,  # Find "Utilities" category
            utilities_children_count_result,  # Count children of "Utilities"
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

        # Mock per-category has_children checks: 4 unique categories, none found in DB
        def make_not_found_result():
            r = Mock()
            r.scalar_one_or_none.return_value = None
            return r

        mock_db.execute.side_effect = [
            income_total,  # Total income (accounts already patched via get_all_household_accounts)
            expense_total,
            debug_result,
            income_cats_result,
            expense_cats_result,
            make_not_found_result(),  # "Category A" not found in DB
            make_not_found_result(),  # "Category B" not found in DB
            make_not_found_result(),  # "Category X" not found in DB
            make_not_found_result(),  # "Category Y" not found in DB
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

        # No categories → no per-category has_children checks needed
        mock_db.execute.side_effect = [
            income_total,  # Total income (accounts already patched via get_all_household_accounts)
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

        # Mock child categories query (uses scalars().all())
        restaurants_cat = Mock(spec=Category)
        restaurants_cat.id = uuid4()
        restaurants_cat.name = "Restaurants"
        groceries_cat = Mock(spec=Category)
        groceries_cat.id = uuid4()
        groceries_cat.name = "Groceries"

        children_result = Mock()
        children_result.scalars.return_value.all.return_value = [
            restaurants_cat,
            groceries_cat,
        ]

        # Mock parent income total
        income_total_result = Mock()
        income_total_result.scalar.return_value = 2000

        # Mock parent expense total
        expense_total_result = Mock()
        expense_total_result.scalar.return_value = -2000

        # Mock income children breakdown (fields: .name, .total, .count)
        # Note: 'name' is special in Mock (use configure_mock or set attr after creation)
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

        # Mock expense children breakdown (fields: .name, .total, .count)
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
            category_result,   # Find parent category (accounts already patched)
            children_result,   # Get children
            income_total_result,   # Parent income total
            expense_total_result,  # Parent expense total
            income_children_result,   # Income by children
            expense_children_result,  # Expenses by children
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

        # Mock child categories query (no children - leaf category, uses scalars().all())
        children_result = Mock()
        children_result.scalars.return_value.all.return_value = []

        # Leaf category: income and expense use one_or_none()
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
            category_result,   # Find category (accounts already patched)
            children_result,   # No children
            income_result,     # Income for leaf
            expense_result,    # Expenses for leaf
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

        # For leaf category, function returns single breakdown for the leaf itself
        assert len(result.income_categories) == 1
        assert result.income_categories[0].category == leaf_category
        assert result.expense_categories[0].category == leaf_category

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

        # Provider category not found: income/expense use one_or_none()
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
            category_result,  # Category not found (accounts already patched)
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

        # Should return single entry for the provider category itself
        assert len(result.income_categories) == 1
        assert result.income_categories[0].category == provider_category
