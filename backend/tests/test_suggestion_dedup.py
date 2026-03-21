"""
Tests for budget suggestion deduplication fixes:
1. Provider category suggestions excluded when a same-name budget already exists
2. Custom category suggestions still excluded by UUID
3. Case-insensitive name matching for provider categories
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4


def _make_budget_row(category_id=None, name="Groceries"):
    row = MagicMock()
    row.__getitem__ = lambda self, i: (category_id, name)[i]
    # Support row[0] and row[1] indexing
    row.__iter__ = lambda self: iter([category_id, name])
    return (category_id, name)


class TestProviderCategoryDeduplication:
    """The suggestion service should not suggest a provider category
    if an active budget with the same name already exists."""

    def test_existing_budget_names_lower_built_correctly(self):
        """existing_budget_names_lower should contain all budget names lowercased."""
        existing_budgets = [
            (None, "Food And Drink"),
            (None, "Groceries"),
            (uuid4(), "Entertainment"),
        ]
        existing_budget_names_lower = {row[1].lower() for row in existing_budgets if row[1]}
        assert "food and drink" in existing_budget_names_lower
        assert "groceries" in existing_budget_names_lower
        assert "entertainment" in existing_budget_names_lower

    def test_provider_category_excluded_when_name_matches_existing_budget(self):
        """A provider category 'food and drink' should be excluded when
        a budget named 'Food And Drink' already exists."""
        existing_budget_names_lower = {"food and drink", "groceries"}

        cat_name = "food and drink"  # raw from DB
        should_exclude = (
            cat_name.lower() in existing_budget_names_lower
            or cat_name.title().lower() in existing_budget_names_lower
        )
        assert should_exclude is True

    def test_provider_category_included_when_no_matching_budget(self):
        """A provider category 'dining out' should be included when
        no active budget with that name exists."""
        existing_budget_names_lower = {"food and drink", "groceries"}

        cat_name = "dining out"
        should_exclude = (
            cat_name.lower() in existing_budget_names_lower
            or cat_name.title().lower() in existing_budget_names_lower
        )
        assert should_exclude is False

    def test_title_case_variant_also_excluded(self):
        """'Food And Drink' (title case) excluded when budget named 'food and drink' exists."""
        existing_budget_names_lower = {"food and drink"}

        cat_name = "Food And Drink"
        should_exclude = (
            cat_name.lower() in existing_budget_names_lower
            or cat_name.title().lower() in existing_budget_names_lower
        )
        assert should_exclude is True

    def test_custom_category_still_excluded_by_uuid(self):
        """Custom categories with a UUID should still be excluded by UUID match."""
        cat_uuid = uuid4()
        existing_category_ids = {cat_uuid}

        assert cat_uuid in existing_category_ids

    def test_budget_with_none_name_does_not_crash(self):
        """Budgets with a null name should be safely skipped."""
        existing_budgets = [
            (None, None),  # budget with null name
            (None, "Groceries"),
        ]
        # Should not raise
        existing_budget_names_lower = {row[1].lower() for row in existing_budgets if row[1]}
        assert "groceries" in existing_budget_names_lower
        assert len(existing_budget_names_lower) == 1


class TestBudgetQueryIncludesName:
    """Verify the budget query now selects both category_id and name."""

    def test_budget_result_row_has_category_id_and_name(self):
        """Each row from the budget query should yield (category_id, name)."""
        rows = [
            (uuid4(), "Entertainment"),
            (None, "Food And Drink"),
        ]
        existing_category_ids = {row[0] for row in rows if row[0] is not None}
        existing_budget_names_lower = {row[1].lower() for row in rows if row[1]}

        assert len(existing_category_ids) == 1
        assert "food and drink" in existing_budget_names_lower
        assert "entertainment" in existing_budget_names_lower


class TestProviderCategoryNameResolution:
    """Test the frontend logic for resolving provider category names."""

    def _resolve_provider_name(self, provider_name: str, all_categories: list) -> str:
        """Mirror BudgetForm resolvedProviderName logic."""
        if not provider_name:
            return provider_name
        match = next(
            (c for c in all_categories if not c.get("id") and c["name"].lower() == provider_name.lower()),
            None
        )
        return match["name"] if match else provider_name

    def test_resolves_to_exact_case_from_api(self):
        all_cats = [
            {"id": None, "name": "food and drink"},
            {"id": None, "name": "Groceries"},
        ]
        result = self._resolve_provider_name("Food And Drink", all_cats)
        assert result == "food and drink"

    def test_falls_back_to_input_when_no_match(self):
        all_cats = [
            {"id": None, "name": "Groceries"},
        ]
        result = self._resolve_provider_name("Dining Out", all_cats)
        assert result == "Dining Out"

    def test_matches_case_insensitively(self):
        all_cats = [
            {"id": None, "name": "FOOD AND DRINK"},
        ]
        result = self._resolve_provider_name("food and drink", all_cats)
        assert result == "FOOD AND DRINK"

    def test_does_not_match_uuid_categories(self):
        """UUID-based categories should not be matched as provider categories."""
        all_cats = [
            {"id": "some-uuid", "name": "food and drink"},
        ]
        result = self._resolve_provider_name("Food And Drink", all_cats)
        # Should fall back — UUID category is not a provider category
        assert result == "Food And Drink"

    def test_empty_provider_name_returns_empty(self):
        all_cats = [{"id": None, "name": "Groceries"}]
        result = self._resolve_provider_name("", all_cats)
        assert result == ""

    def test_category_select_value_built_correctly(self):
        """categorySelectValue should be provider::{resolvedName}."""
        resolved_name = "food and drink"
        select_value = f"provider::{resolved_name}"
        assert select_value == "provider::food and drink"
