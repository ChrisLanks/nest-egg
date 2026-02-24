"""Advanced rule engine tests — multi-condition matching (AND/OR), action application."""

import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, MagicMock
from uuid import uuid4

from app.services.rule_engine import RuleEngine
from app.models.rule import (
    ConditionField,
    ConditionOperator,
    ActionType,
    RuleMatchType,
)
from app.models.transaction import Transaction


def _make_condition(field, operator, value, value_max=None):
    cond = MagicMock()
    cond.field = field
    cond.operator = operator
    cond.value = value
    cond.value_max = value_max
    return cond


def _make_rule(conditions, match_type=RuleMatchType.ALL, actions=None):
    rule = MagicMock()
    rule.conditions = conditions
    rule.match_type = match_type
    rule.actions = actions or []
    rule.id = uuid4()
    rule.priority = 1
    rule.stop_on_match = False
    return rule


@pytest.fixture
def engine():
    return RuleEngine(db=AsyncMock())


class TestMatchesRuleAND:
    """AND logic (match_type=ALL): all conditions must match."""

    def test_all_conditions_match(self, engine):
        txn = Transaction(
            merchant_name="Starbucks Coffee",
            amount=Decimal("-25.00"),
            date=date(2024, 3, 15),
        )
        rule = _make_rule(
            conditions=[
                _make_condition(ConditionField.MERCHANT_NAME, ConditionOperator.CONTAINS, "starbucks"),
                _make_condition(ConditionField.AMOUNT, ConditionOperator.GREATER_THAN, "10.00"),
            ],
            match_type=RuleMatchType.ALL,
        )
        assert engine.matches_rule(txn, rule) is True

    def test_one_condition_fails(self, engine):
        txn = Transaction(
            merchant_name="Starbucks Coffee",
            amount=Decimal("-5.00"),
            date=date(2024, 3, 15),
        )
        rule = _make_rule(
            conditions=[
                _make_condition(ConditionField.MERCHANT_NAME, ConditionOperator.CONTAINS, "starbucks"),
                _make_condition(ConditionField.AMOUNT, ConditionOperator.GREATER_THAN, "10.00"),
            ],
            match_type=RuleMatchType.ALL,
        )
        assert engine.matches_rule(txn, rule) is False


class TestMatchesRuleOR:
    """OR logic (match_type=ANY): any condition can match."""

    def test_first_matches(self, engine):
        txn = Transaction(
            merchant_name="Starbucks Coffee",
            amount=Decimal("-5.00"),
            date=date(2024, 3, 15),
        )
        rule = _make_rule(
            conditions=[
                _make_condition(ConditionField.MERCHANT_NAME, ConditionOperator.CONTAINS, "starbucks"),
                _make_condition(ConditionField.AMOUNT, ConditionOperator.GREATER_THAN, "100.00"),
            ],
            match_type=RuleMatchType.ANY,
        )
        assert engine.matches_rule(txn, rule) is True

    def test_second_matches(self, engine):
        txn = Transaction(
            merchant_name="Amazon",
            amount=Decimal("-150.00"),
            date=date(2024, 3, 15),
        )
        rule = _make_rule(
            conditions=[
                _make_condition(ConditionField.MERCHANT_NAME, ConditionOperator.CONTAINS, "starbucks"),
                _make_condition(ConditionField.AMOUNT, ConditionOperator.GREATER_THAN, "100.00"),
            ],
            match_type=RuleMatchType.ANY,
        )
        assert engine.matches_rule(txn, rule) is True

    def test_none_match(self, engine):
        txn = Transaction(
            merchant_name="Amazon",
            amount=Decimal("-5.00"),
            date=date(2024, 3, 15),
        )
        rule = _make_rule(
            conditions=[
                _make_condition(ConditionField.MERCHANT_NAME, ConditionOperator.CONTAINS, "starbucks"),
                _make_condition(ConditionField.AMOUNT, ConditionOperator.GREATER_THAN, "100.00"),
            ],
            match_type=RuleMatchType.ANY,
        )
        assert engine.matches_rule(txn, rule) is False


class TestEmptyConditions:
    def test_no_conditions_returns_false(self, engine):
        txn = Transaction(
            merchant_name="Test",
            amount=Decimal("-10.00"),
            date=date.today(),
        )
        rule = _make_rule(conditions=[])
        assert engine.matches_rule(txn, rule) is False


class TestApplyAction:
    @pytest.mark.asyncio
    async def test_set_category(self, engine):
        txn = Transaction(
            merchant_name="Starbucks",
            amount=Decimal("-5.00"),
            date=date.today(),
            category_primary=None,
        )
        action = MagicMock()
        action.action_type = ActionType.SET_CATEGORY
        action.action_value = "Food & Drink"

        result = await engine.apply_action(txn, action, str(uuid4()))
        assert result is True
        assert txn.category_primary == "Food & Drink"

    @pytest.mark.asyncio
    async def test_set_merchant(self, engine):
        txn = Transaction(
            merchant_name="STRBCKS*12345",
            amount=Decimal("-5.00"),
            date=date.today(),
        )
        action = MagicMock()
        action.action_type = ActionType.SET_MERCHANT
        action.action_value = "Starbucks"

        result = await engine.apply_action(txn, action, str(uuid4()))
        assert result is True
        assert txn.merchant_name == "Starbucks"
