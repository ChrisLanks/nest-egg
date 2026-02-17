"""Unit tests for rule engine."""

import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import Mock

from app.services.rule_engine import RuleEngine
from app.models.rule import ConditionField, ConditionOperator, RuleCondition
from app.models.transaction import Transaction


@pytest.mark.unit
@pytest.mark.rules
class TestRuleEngine:
    """Test rule engine condition evaluation."""

    def setup_method(self):
        """Setup test fixtures."""
        self.engine = RuleEngine(db=Mock())

    def test_evaluate_merchant_name_contains(self):
        """Test merchant name contains condition."""
        transaction = Transaction(
            merchant_name="Starbucks Coffee",
            amount=Decimal("-5.50"),
            date=date.today(),
        )

        condition = RuleCondition(
            field=ConditionField.MERCHANT_NAME,
            operator=ConditionOperator.CONTAINS,
            value="starbucks",
        )

        result = self.engine.evaluate_condition(transaction, condition)
        assert result is True

    def test_evaluate_merchant_name_case_insensitive(self):
        """Test merchant name matching is case-insensitive."""
        transaction = Transaction(
            merchant_name="STARBUCKS",
            amount=Decimal("-5.50"),
            date=date.today(),
        )

        condition = RuleCondition(
            field=ConditionField.MERCHANT_NAME,
            operator=ConditionOperator.CONTAINS,
            value="starbucks",
        )

        result = self.engine.evaluate_condition(transaction, condition)
        assert result is True

    def test_evaluate_amount_greater_than(self):
        """Test amount greater than condition."""
        transaction = Transaction(
            merchant_name="Test",
            amount=Decimal("-100.00"),
            date=date.today(),
        )

        condition = RuleCondition(
            field=ConditionField.AMOUNT,
            operator=ConditionOperator.GREATER_THAN,
            value="50.00",
        )

        result = self.engine.evaluate_condition(transaction, condition)
        assert result is True  # abs(-100) > 50

    def test_evaluate_amount_between(self):
        """Test amount between condition."""
        transaction = Transaction(
            merchant_name="Test",
            amount=Decimal("-75.00"),
            date=date.today(),
        )

        condition = RuleCondition(
            field=ConditionField.AMOUNT,
            operator=ConditionOperator.BETWEEN,
            value="50.00",
            value_max="100.00",
        )

        result = self.engine.evaluate_condition(transaction, condition)
        assert result is True  # 50 <= abs(-75) <= 100

    def test_evaluate_date_equals(self):
        """Test date equals condition."""
        test_date = date(2024, 2, 15)
        transaction = Transaction(
            merchant_name="Test",
            amount=Decimal("-50.00"),
            date=test_date,
        )

        condition = RuleCondition(
            field=ConditionField.DATE,
            operator=ConditionOperator.EQUALS,
            value="2024-02-15",
        )

        result = self.engine.evaluate_condition(transaction, condition)
        assert result is True

    def test_evaluate_month_equals(self):
        """Test month equals condition."""
        transaction = Transaction(
            merchant_name="Test",
            amount=Decimal("-50.00"),
            date=date(2024, 2, 15),  # February
        )

        condition = RuleCondition(
            field=ConditionField.MONTH,
            operator=ConditionOperator.EQUALS,
            value="2",  # February
        )

        result = self.engine.evaluate_condition(transaction, condition)
        assert result is True

    def test_evaluate_year_equals(self):
        """Test year equals condition."""
        transaction = Transaction(
            merchant_name="Test",
            amount=Decimal("-50.00"),
            date=date(2024, 2, 15),
        )

        condition = RuleCondition(
            field=ConditionField.YEAR,
            operator=ConditionOperator.EQUALS,
            value="2024",
        )

        result = self.engine.evaluate_condition(transaction, condition)
        assert result is True

    def test_evaluate_day_of_week_equals(self):
        """Test day of week condition."""
        # Feb 15, 2024 is a Thursday (weekday = 3)
        transaction = Transaction(
            merchant_name="Test",
            amount=Decimal("-50.00"),
            date=date(2024, 2, 15),
        )

        condition = RuleCondition(
            field=ConditionField.DAY_OF_WEEK,
            operator=ConditionOperator.EQUALS,
            value="3",  # Thursday (0=Monday, 6=Sunday)
        )

        result = self.engine.evaluate_condition(transaction, condition)
        assert result is True

    def test_evaluate_category_contains(self):
        """Test category contains condition."""
        transaction = Transaction(
            merchant_name="Test",
            amount=Decimal("-50.00"),
            date=date.today(),
            category_primary="Food & Dining",
        )

        condition = RuleCondition(
            field=ConditionField.CATEGORY,
            operator=ConditionOperator.CONTAINS,
            value="dining",
        )

        result = self.engine.evaluate_condition(transaction, condition)
        assert result is True

    def test_evaluate_description_regex(self):
        """Test description regex condition."""
        transaction = Transaction(
            merchant_name="Test",
            amount=Decimal("-50.00"),
            date=date.today(),
            description="Payment #12345 processed",
        )

        condition = RuleCondition(
            field=ConditionField.DESCRIPTION,
            operator=ConditionOperator.REGEX,
            value=r"#\d+",  # Match #12345
        )

        result = self.engine.evaluate_condition(transaction, condition)
        assert result is True

    def test_evaluate_condition_no_match(self):
        """Test condition that doesn't match."""
        transaction = Transaction(
            merchant_name="Amazon",
            amount=Decimal("-50.00"),
            date=date.today(),
        )

        condition = RuleCondition(
            field=ConditionField.MERCHANT_NAME,
            operator=ConditionOperator.CONTAINS,
            value="walmart",
        )

        result = self.engine.evaluate_condition(transaction, condition)
        assert result is False

    def test_evaluate_invalid_regex(self):
        """Test invalid regex returns False."""
        transaction = Transaction(
            merchant_name="Test",
            amount=Decimal("-50.00"),
            date=date.today(),
            description="Test description",
        )

        condition = RuleCondition(
            field=ConditionField.DESCRIPTION,
            operator=ConditionOperator.REGEX,
            value="[invalid(regex",  # Invalid regex
        )

        result = self.engine.evaluate_condition(transaction, condition)
        assert result is False
