"""Tests for rule template service — validates template rules are created correctly."""

import pytest

from app.models.rule import ActionType, ConditionField, ConditionOperator, RuleMatchType


@pytest.mark.asyncio
class TestRuleTemplateService:
    """Tests for each rule template."""

    async def test_create_coffee_shops_rule(self, db_session, test_user):
        from app.services.rule_template_service import rule_template_service

        rule = await rule_template_service.create_coffee_shops_rule(db=db_session, user=test_user)

        assert rule.name == "Coffee Shops"
        assert rule.match_type == RuleMatchType.ANY
        assert rule.is_active is True
        assert rule.organization_id == test_user.organization_id

        # Should have multiple merchant conditions
        assert len(rule.conditions) >= 5
        for cond in rule.conditions:
            assert cond.field == ConditionField.MERCHANT_NAME
            assert cond.operator == ConditionOperator.CONTAINS
            assert len(cond.value) > 0

        # Should have one ADD_LABEL action
        assert len(rule.actions) == 1
        assert rule.actions[0].action_type == ActionType.ADD_LABEL
        assert rule.actions[0].action_value == "Coffee"

    async def test_create_subscriptions_rule(self, db_session, test_user):
        from app.services.rule_template_service import rule_template_service

        rule = await rule_template_service.create_subscriptions_rule(db=db_session, user=test_user)

        assert rule.name == "Subscriptions"
        assert rule.match_type == RuleMatchType.ANY
        assert len(rule.conditions) >= 5

        merchants = {c.value for c in rule.conditions}
        assert "netflix" in merchants
        assert "spotify" in merchants

        assert len(rule.actions) == 1
        assert rule.actions[0].action_type == ActionType.ADD_LABEL
        assert rule.actions[0].action_value == "Subscription"

    async def test_create_large_purchase_alert_rule(self, db_session, test_user):
        from app.services.rule_template_service import rule_template_service

        rule = await rule_template_service.create_large_purchase_alert_rule(
            db=db_session, user=test_user
        )

        assert rule.name == "Large Purchases"
        assert rule.match_type == RuleMatchType.ALL
        assert len(rule.conditions) == 1

        cond = rule.conditions[0]
        assert cond.field == ConditionField.AMOUNT
        assert cond.operator == ConditionOperator.LESS_THAN
        assert cond.value == "-500"

        assert len(rule.actions) == 1
        assert rule.actions[0].action_type == ActionType.ADD_LABEL
        assert rule.actions[0].action_value == "Large Purchase"
