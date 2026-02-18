"""Unit tests for categories API endpoints."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4
from datetime import datetime

from fastapi import HTTPException

from app.api.v1.categories import (
    list_categories,
    create_category,
    update_category,
    delete_category,
)
from app.models.user import User
from app.models.transaction import Category
from app.schemas.transaction import CategoryCreate, CategoryUpdate


@pytest.mark.unit
class TestListCategories:
    """Test list_categories endpoint."""

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
    async def test_lists_custom_categories(self, mock_db, mock_user):
        """Should list custom categories from categories table."""
        category = Mock(spec=Category)
        category.id = uuid4()
        category.organization_id = mock_user.organization_id
        category.name = "Groceries"
        category.color = "#FF5733"
        category.parent_category_id = None
        category.plaid_category_name = None
        category.created_at = datetime.utcnow()
        category.updated_at = datetime.utcnow()

        # Mock custom categories query result
        custom_result = Mock()
        custom_result.all.return_value = [(category, 5)]  # 5 transactions

        # Mock Plaid categories query result
        plaid_result = Mock()
        plaid_result.all.return_value = []

        mock_db.execute.side_effect = [custom_result, plaid_result]

        result = await list_categories(current_user=mock_user, db=mock_db)

        assert len(result) == 1
        assert result[0].name == "Groceries"
        assert result[0].is_custom is True
        assert result[0].transaction_count == 5
        assert result[0].color == "#FF5733"

    @pytest.mark.asyncio
    async def test_lists_plaid_categories_from_transactions(self, mock_db, mock_user):
        """Should list Plaid categories from transaction data."""
        # Mock custom categories (empty)
        custom_result = Mock()
        custom_result.all.return_value = []

        # Mock Plaid categories from transactions
        plaid_result = Mock()
        plaid_result.all.return_value = [
            ("Food and Drink", 10),
            ("Shopping", 7),
        ]

        mock_db.execute.side_effect = [custom_result, plaid_result]

        result = await list_categories(current_user=mock_user, db=mock_db)

        assert len(result) == 2
        assert result[0].name == "Food and Drink"
        assert result[0].is_custom is False
        assert result[0].transaction_count == 10
        assert result[0].id is None
        assert result[1].name == "Shopping"

    @pytest.mark.asyncio
    async def test_combines_custom_and_plaid_categories(self, mock_db, mock_user):
        """Should combine custom and Plaid categories, avoiding duplicates."""
        # Mock custom category
        category = Mock(spec=Category)
        category.id = uuid4()
        category.organization_id = mock_user.organization_id
        category.name = "Groceries"
        category.color = "#FF5733"
        category.parent_category_id = None
        category.plaid_category_name = "Food and Drink"
        category.created_at = datetime.utcnow()
        category.updated_at = datetime.utcnow()

        custom_result = Mock()
        custom_result.all.return_value = [(category, 5)]

        # Mock Plaid categories - "Groceries" should be excluded since it's custom
        plaid_result = Mock()
        plaid_result.all.return_value = [
            ("Groceries", 3),  # Should be excluded (duplicate)
            ("Shopping", 7),  # Should be included
        ]

        mock_db.execute.side_effect = [custom_result, plaid_result]

        result = await list_categories(current_user=mock_user, db=mock_db)

        # Should have 2 categories: custom "Groceries" and Plaid "Shopping"
        assert len(result) == 2
        category_names = [cat.name for cat in result]
        assert "Groceries" in category_names
        assert "Shopping" in category_names

        # Groceries should be the custom one with ID
        groceries = next(cat for cat in result if cat.name == "Groceries")
        assert groceries.is_custom is True
        assert groceries.id is not None

    @pytest.mark.asyncio
    async def test_sorts_categories_alphabetically(self, mock_db, mock_user):
        """Should sort all categories alphabetically by name."""
        custom_result = Mock()
        custom_result.all.return_value = []

        plaid_result = Mock()
        plaid_result.all.return_value = [
            ("Zebra", 1),
            ("Apple", 2),
            ("Mango", 3),
        ]

        mock_db.execute.side_effect = [custom_result, plaid_result]

        result = await list_categories(current_user=mock_user, db=mock_db)

        assert len(result) == 3
        assert result[0].name == "Apple"
        assert result[1].name == "Mango"
        assert result[2].name == "Zebra"


@pytest.mark.unit
class TestCreateCategory:
    """Test create_category endpoint."""

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
    def category_create_data(self):
        return CategoryCreate(
            name="Groceries",
            color="#FF5733",
            parent_category_id=None,
            plaid_category_name="Food and Drink",
        )

    @pytest.mark.asyncio
    async def test_creates_category_successfully(
        self, mock_db, mock_user, category_create_data
    ):
        """Should create a new category."""
        with patch(
            "app.api.v1.categories.hierarchy_validation_service.validate_parent",
            return_value=None,
        ):
            result = await create_category(
                category_data=category_create_data,
                current_user=mock_user,
                db=mock_db,
            )

            assert result.name == "Groceries"
            assert result.color == "#FF5733"
            assert result.organization_id == mock_user.organization_id
            assert mock_db.add.called
            assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_validates_parent_category(
        self, mock_db, mock_user
    ):
        """Should validate parent category when provided."""
        parent_id = uuid4()
        category_data = CategoryCreate(
            name="Subcategory",
            color="#00FF00",
            parent_category_id=parent_id,
        )

        with patch(
            "app.api.v1.categories.hierarchy_validation_service.validate_parent",
            return_value=None,
        ) as mock_validate:
            await create_category(
                category_data=category_data,
                current_user=mock_user,
                db=mock_db,
            )

            mock_validate.assert_called_once_with(
                parent_id,
                mock_user.organization_id,
                mock_db,
                Category,
                parent_field_name="parent_category_id",
                entity_name="category",
            )


@pytest.mark.unit
class TestUpdateCategory:
    """Test update_category endpoint."""

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
    def mock_category(self):
        category = Mock(spec=Category)
        category.id = uuid4()
        category.name = "Original Name"
        category.color = "#FF0000"
        category.parent_category_id = None
        category.plaid_category_name = None
        return category

    @pytest.mark.asyncio
    async def test_updates_category_name(self, mock_db, mock_user, mock_category):
        """Should update category name."""
        category_id = mock_category.id
        update_data = CategoryUpdate(name="New Name")

        # Mock category lookup
        category_result = Mock()
        category_result.scalar_one_or_none.return_value = mock_category
        mock_db.execute.return_value = category_result

        result = await update_category(
            category_id=category_id,
            category_data=update_data,
            current_user=mock_user,
            db=mock_db,
        )

        assert result.name == "New Name"
        assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_raises_404_when_category_not_found(self, mock_db, mock_user):
        """Should raise 404 when category doesn't exist."""
        category_id = uuid4()
        update_data = CategoryUpdate(name="New Name")

        category_result = Mock()
        category_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = category_result

        with pytest.raises(HTTPException) as exc_info:
            await update_category(
                category_id=category_id,
                category_data=update_data,
                current_user=mock_user,
                db=mock_db,
            )

        assert exc_info.value.status_code == 404
        assert "Category not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_prevents_self_as_parent(self, mock_db, mock_user, mock_category):
        """Should prevent setting category as its own parent."""
        category_id = mock_category.id
        update_data = CategoryUpdate(parent_category_id=category_id)

        category_result = Mock()
        category_result.scalar_one_or_none.return_value = mock_category
        mock_db.execute.return_value = category_result

        with pytest.raises(HTTPException) as exc_info:
            await update_category(
                category_id=category_id,
                category_data=update_data,
                current_user=mock_user,
                db=mock_db,
            )

        assert exc_info.value.status_code == 400
        assert "own parent" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_prevents_parent_when_has_children(
        self, mock_db, mock_user, mock_category
    ):
        """Should prevent assigning parent to category that has children."""
        category_id = mock_category.id
        parent_id = uuid4()
        update_data = CategoryUpdate(parent_category_id=parent_id)

        # Mock category lookup
        category_result = Mock()
        category_result.scalar_one_or_none.return_value = mock_category

        # Mock children check - has children
        children_result = Mock()
        children_result.scalar_one_or_none.return_value = uuid4()  # Child exists

        mock_db.execute.side_effect = [category_result, children_result]

        with pytest.raises(HTTPException) as exc_info:
            await update_category(
                category_id=category_id,
                category_data=update_data,
                current_user=mock_user,
                db=mock_db,
            )

        assert exc_info.value.status_code == 400
        assert "already has children" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_allows_parent_when_no_children(
        self, mock_db, mock_user, mock_category
    ):
        """Should allow assigning parent when category has no children."""
        category_id = mock_category.id
        parent_id = uuid4()
        update_data = CategoryUpdate(parent_category_id=parent_id)

        # Mock category lookup
        category_result = Mock()
        category_result.scalar_one_or_none.return_value = mock_category

        # Mock children check - no children
        children_result = Mock()
        children_result.scalar_one_or_none.return_value = None  # No children

        mock_db.execute.side_effect = [category_result, children_result]

        with patch(
            "app.api.v1.categories.hierarchy_validation_service.validate_parent",
            return_value=None,
        ):
            result = await update_category(
                category_id=category_id,
                category_data=update_data,
                current_user=mock_user,
                db=mock_db,
            )

            assert result.parent_category_id == parent_id

    @pytest.mark.asyncio
    async def test_updates_multiple_fields(self, mock_db, mock_user, mock_category):
        """Should update multiple fields at once."""
        category_id = mock_category.id
        update_data = CategoryUpdate(
            name="New Name",
            color="#00FF00",
            plaid_category_name="New Plaid Category",
        )

        category_result = Mock()
        category_result.scalar_one_or_none.return_value = mock_category
        mock_db.execute.return_value = category_result

        result = await update_category(
            category_id=category_id,
            category_data=update_data,
            current_user=mock_user,
            db=mock_db,
        )

        assert result.name == "New Name"
        assert result.color == "#00FF00"
        assert result.plaid_category_name == "New Plaid Category"


@pytest.mark.unit
class TestDeleteCategory:
    """Test delete_category endpoint."""

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
    async def test_deletes_category_successfully(self, mock_db, mock_user):
        """Should delete category and return None."""
        category_id = uuid4()
        category = Mock(spec=Category)
        category.id = category_id

        category_result = Mock()
        category_result.scalar_one_or_none.return_value = category
        mock_db.execute.return_value = category_result

        result = await delete_category(
            category_id=category_id,
            current_user=mock_user,
            db=mock_db,
        )

        assert result is None
        assert mock_db.delete.called
        assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_raises_404_when_category_not_found(self, mock_db, mock_user):
        """Should raise 404 when category doesn't exist."""
        category_id = uuid4()

        category_result = Mock()
        category_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = category_result

        with pytest.raises(HTTPException) as exc_info:
            await delete_category(
                category_id=category_id,
                current_user=mock_user,
                db=mock_db,
            )

        assert exc_info.value.status_code == 404
        assert "Category not found" in exc_info.value.detail
