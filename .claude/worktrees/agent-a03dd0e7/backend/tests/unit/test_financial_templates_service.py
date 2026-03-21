"""Tests for financial templates service — template listing and activation status."""

import pytest

from app.services.financial_templates_service import (
    TEMPLATES,
    FinancialTemplatesService,
)


@pytest.mark.asyncio
class TestFinancialTemplatesService:
    """Tests for listing and activation detection."""

    async def test_list_returns_all_templates(self, db_session, test_user):
        result = await FinancialTemplatesService.list_templates(db=db_session, user=test_user)
        assert len(result) == len(TEMPLATES)

    async def test_all_templates_have_required_fields(self, db_session, test_user):
        result = await FinancialTemplatesService.list_templates(db=db_session, user=test_user)
        for t in result:
            assert "id" in t
            assert "category" in t
            assert "name" in t
            assert "description" in t
            assert "is_activated" in t
            assert isinstance(t["is_activated"], bool)

    async def test_fresh_user_has_no_activated_templates(self, db_session, test_user):
        result = await FinancialTemplatesService.list_templates(db=db_session, user=test_user)
        # A fresh test user shouldn't have any activated templates
        # (budget:suggestions might show as activated if they have >3 budgets,
        # but a fresh user won't)
        activated = [t for t in result if t["is_activated"]]
        assert len(activated) == 0

    async def test_goal_shows_activated_after_creation(self, db_session, test_user):
        """Creating an emergency fund goal should mark the template as activated."""
        from app.services.savings_goal_service import savings_goal_service

        await savings_goal_service.create_emergency_fund_goal(db=db_session, user=test_user)
        await db_session.flush()

        result = await FinancialTemplatesService.list_templates(db=db_session, user=test_user)
        ef_template = next(t for t in result if t["id"] == "goal:emergency_fund")
        assert ef_template["is_activated"] is True

    async def test_rule_shows_activated_after_creation(self, db_session, test_user):
        """Creating a rule template should mark it as activated."""
        from app.services.rule_template_service import rule_template_service

        await rule_template_service.create_coffee_shops_rule(db=db_session, user=test_user)
        await db_session.flush()

        result = await FinancialTemplatesService.list_templates(db=db_session, user=test_user)
        coffee_template = next(t for t in result if t["id"] == "rule:coffee_shops")
        assert coffee_template["is_activated"] is True

    async def test_template_categories_are_valid(self, db_session, test_user):
        result = await FinancialTemplatesService.list_templates(db=db_session, user=test_user)
        valid_categories = {"goal", "rule", "retirement", "budget"}
        for t in result:
            assert t["category"] in valid_categories, f"Invalid category: {t['category']}"

    async def test_template_ids_are_unique(self, db_session, test_user):
        result = await FinancialTemplatesService.list_templates(db=db_session, user=test_user)
        ids = [t["id"] for t in result]
        assert len(ids) == len(set(ids)), "Template IDs should be unique"

    async def test_template_id_format_matches_category(self, db_session, test_user):
        result = await FinancialTemplatesService.list_templates(db=db_session, user=test_user)
        for t in result:
            prefix = t["id"].split(":")[0]
            assert (
                prefix == t["category"]
            ), f"Template {t['id']} prefix doesn't match category {t['category']}"
