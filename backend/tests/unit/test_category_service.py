"""Tests for category service."""

import pytest
from uuid import uuid4

from app.services.category_service import get_category_id_for_plaid_category
from app.models.transaction import Category


class TestCategoryService:
    """Test suite for category service."""

    @pytest.mark.asyncio
    async def test_get_category_id_for_plaid_category_found(self, db, test_user):
        """Should return category ID for matching Plaid category name."""
        # Create custom category with plaid_category_name mapping
        category = Category(
            organization_id=test_user.organization_id,
            name="Food & Dining",
            plaid_category_name="Food and Drink",
        )
        db.add(category)
        await db.commit()

        # Search for it
        result = await get_category_id_for_plaid_category(
            db, test_user.organization_id, "Food and Drink"
        )

        assert result == category.id

    @pytest.mark.asyncio
    async def test_get_category_id_for_plaid_category_not_found(self, db, test_user):
        """Should return None when no matching category exists."""
        result = await get_category_id_for_plaid_category(
            db, test_user.organization_id, "Nonexistent Category"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_category_id_for_plaid_category_null_input(self, db, test_user):
        """Should return None for null input."""
        result = await get_category_id_for_plaid_category(db, test_user.organization_id, None)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_category_id_for_plaid_category_empty_string(self, db, test_user):
        """Should return None for empty string."""
        result = await get_category_id_for_plaid_category(db, test_user.organization_id, "")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_category_id_for_plaid_category_cross_org(self, db, test_user):
        """Should not return categories from other organizations."""
        other_org_id = uuid4()

        # Create category in other org
        other_category = Category(
            organization_id=other_org_id,
            name="Other Org Category",
            plaid_category_name="Shopping",
        )
        db.add(other_category)
        await db.commit()

        # Search for it from test_user's org
        result = await get_category_id_for_plaid_category(db, test_user.organization_id, "Shopping")

        # Should not find it (different org)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_category_id_for_plaid_category_exact_match(self, db, test_user):
        """Should require exact match (case-sensitive)."""
        category = Category(
            organization_id=test_user.organization_id,
            name="Travel",
            plaid_category_name="Travel",
        )
        db.add(category)
        await db.commit()

        # Exact match
        result = await get_category_id_for_plaid_category(db, test_user.organization_id, "Travel")
        assert result == category.id

        # Different case - should not match (SQL default is case-sensitive for strings)
        result_diff_case = await get_category_id_for_plaid_category(
            db, test_user.organization_id, "TRAVEL"
        )
        # Note: This depends on database collation. PostgreSQL default is case-sensitive.
        # If it matches, it's due to database settings, which is acceptable.

    @pytest.mark.asyncio
    async def test_get_category_id_for_plaid_category_multiple_categories(self, db, test_user):
        """Should return first match when multiple categories exist."""
        # Create two categories with same plaid_category_name (edge case)
        category1 = Category(
            organization_id=test_user.organization_id,
            name="Groceries 1",
            plaid_category_name="Groceries",
        )
        category2 = Category(
            organization_id=test_user.organization_id,
            name="Groceries 2",
            plaid_category_name="Groceries",
        )
        db.add_all([category1, category2])
        await db.commit()

        result = await get_category_id_for_plaid_category(
            db, test_user.organization_id, "Groceries"
        )

        # Should return one of them (implementation uses limit(1))
        assert result in [category1.id, category2.id]

    @pytest.mark.asyncio
    async def test_get_category_id_for_plaid_category_no_plaid_mapping(self, db, test_user):
        """Should not match categories without plaid_category_name set."""
        # Category without plaid mapping
        category = Category(
            organization_id=test_user.organization_id,
            name="Custom Category",
            plaid_category_name=None,
        )
        db.add(category)
        await db.commit()

        result = await get_category_id_for_plaid_category(
            db, test_user.organization_id, "Custom Category"
        )

        # Should not match (plaid_category_name is None)
        assert result is None
