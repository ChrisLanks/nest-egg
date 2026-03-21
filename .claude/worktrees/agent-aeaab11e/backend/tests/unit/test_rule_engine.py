"""Unit tests for rule engine."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import uuid4

import pytest

from app.models.rule import ConditionField, ConditionOperator, RuleCondition
from app.models.transaction import Transaction
from app.services.rule_engine import RuleEngine


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

    # ── Amount edge cases ──────────────────────────────────────────────────

    def test_evaluate_amount_equals(self):
        """Test amount equals condition (within 0.01 tolerance)."""
        transaction = Transaction(merchant_name="Test", amount=Decimal("-50.00"), date=date.today())
        condition = RuleCondition(
            field=ConditionField.AMOUNT,
            operator=ConditionOperator.EQUALS,
            value="50.00",
        )
        assert self.engine.evaluate_condition(transaction, condition) is True

    def test_evaluate_amount_less_than(self):
        """Test amount less than condition."""
        transaction = Transaction(merchant_name="Test", amount=Decimal("-30.00"), date=date.today())
        condition = RuleCondition(
            field=ConditionField.AMOUNT,
            operator=ConditionOperator.LESS_THAN,
            value="50.00",
        )
        assert self.engine.evaluate_condition(transaction, condition) is True

    def test_evaluate_amount_between_no_max(self):
        """Amount BETWEEN with no value_max should return False."""
        transaction = Transaction(merchant_name="Test", amount=Decimal("-75.00"), date=date.today())
        condition = RuleCondition(
            field=ConditionField.AMOUNT,
            operator=ConditionOperator.BETWEEN,
            value="50.00",
            value_max=None,
        )
        assert self.engine.evaluate_condition(transaction, condition) is False

    def test_evaluate_amount_invalid_value(self):
        """Invalid amount value should return False."""
        transaction = Transaction(merchant_name="Test", amount=Decimal("-50.00"), date=date.today())
        condition = RuleCondition(
            field=ConditionField.AMOUNT,
            operator=ConditionOperator.EQUALS,
            value="not-a-number",
        )
        assert self.engine.evaluate_condition(transaction, condition) is False

    def test_evaluate_amount_exact_field(self):
        """Test AMOUNT_EXACT uses raw transaction.amount (not abs)."""
        transaction = Transaction(merchant_name="Test", amount=Decimal("-50.00"), date=date.today())
        condition = RuleCondition(
            field=ConditionField.AMOUNT_EXACT,
            operator=ConditionOperator.EQUALS,
            value="-50.00",
        )
        assert self.engine.evaluate_condition(transaction, condition) is True

    def test_evaluate_amount_unsupported_operator(self):
        """Unsupported operator for amount returns False."""
        transaction = Transaction(merchant_name="Test", amount=Decimal("-50.00"), date=date.today())
        condition = RuleCondition(
            field=ConditionField.AMOUNT,
            operator=ConditionOperator.CONTAINS,
            value="50.00",
        )
        assert self.engine.evaluate_condition(transaction, condition) is False

    # ── Date condition edge cases ──────────────────────────────────────────

    def test_evaluate_date_greater_than(self):
        """Test date greater than condition."""
        transaction = Transaction(
            merchant_name="Test", amount=Decimal("-50.00"), date=date(2024, 6, 15)
        )
        condition = RuleCondition(
            field=ConditionField.DATE,
            operator=ConditionOperator.GREATER_THAN,
            value="2024-01-01",
        )
        assert self.engine.evaluate_condition(transaction, condition) is True

    def test_evaluate_date_less_than(self):
        """Test date less than condition."""
        transaction = Transaction(
            merchant_name="Test", amount=Decimal("-50.00"), date=date(2024, 1, 15)
        )
        condition = RuleCondition(
            field=ConditionField.DATE,
            operator=ConditionOperator.LESS_THAN,
            value="2024-06-01",
        )
        assert self.engine.evaluate_condition(transaction, condition) is True

    def test_evaluate_date_between(self):
        """Test date between condition."""
        transaction = Transaction(
            merchant_name="Test", amount=Decimal("-50.00"), date=date(2024, 3, 15)
        )
        condition = RuleCondition(
            field=ConditionField.DATE,
            operator=ConditionOperator.BETWEEN,
            value="2024-01-01",
            value_max="2024-06-30",
        )
        assert self.engine.evaluate_condition(transaction, condition) is True

    def test_evaluate_date_between_no_max(self):
        """Date BETWEEN with no value_max should return False."""
        transaction = Transaction(
            merchant_name="Test", amount=Decimal("-50.00"), date=date(2024, 3, 15)
        )
        condition = RuleCondition(
            field=ConditionField.DATE,
            operator=ConditionOperator.BETWEEN,
            value="2024-01-01",
            value_max=None,
        )
        assert self.engine.evaluate_condition(transaction, condition) is False

    def test_evaluate_date_no_date_on_transaction(self):
        """Transaction with None date should return False."""
        transaction = Transaction(merchant_name="Test", amount=Decimal("-50.00"), date=None)
        condition = RuleCondition(
            field=ConditionField.DATE,
            operator=ConditionOperator.EQUALS,
            value="2024-01-01",
        )
        assert self.engine.evaluate_condition(transaction, condition) is False

    # ── Numeric date fields (month/year/day_of_week) ──────────────────────

    def test_evaluate_month_greater_than(self):
        """Test month greater than condition."""
        transaction = Transaction(
            merchant_name="Test", amount=Decimal("-50.00"), date=date(2024, 6, 15)
        )
        condition = RuleCondition(
            field=ConditionField.MONTH,
            operator=ConditionOperator.GREATER_THAN,
            value="3",
        )
        assert self.engine.evaluate_condition(transaction, condition) is True

    def test_evaluate_month_less_than(self):
        """Test month less than condition."""
        transaction = Transaction(
            merchant_name="Test", amount=Decimal("-50.00"), date=date(2024, 2, 15)
        )
        condition = RuleCondition(
            field=ConditionField.MONTH,
            operator=ConditionOperator.LESS_THAN,
            value="6",
        )
        assert self.engine.evaluate_condition(transaction, condition) is True

    def test_evaluate_month_between(self):
        """Test month between condition."""
        transaction = Transaction(
            merchant_name="Test", amount=Decimal("-50.00"), date=date(2024, 4, 15)
        )
        condition = RuleCondition(
            field=ConditionField.MONTH,
            operator=ConditionOperator.BETWEEN,
            value="3",
            value_max="6",
        )
        assert self.engine.evaluate_condition(transaction, condition) is True

    def test_evaluate_month_between_no_max(self):
        """Month BETWEEN with no value_max should return False."""
        transaction = Transaction(
            merchant_name="Test", amount=Decimal("-50.00"), date=date(2024, 4, 15)
        )
        condition = RuleCondition(
            field=ConditionField.MONTH,
            operator=ConditionOperator.BETWEEN,
            value="3",
            value_max=None,
        )
        assert self.engine.evaluate_condition(transaction, condition) is False

    def test_evaluate_month_no_date_returns_false(self):
        """Transaction with None date should return False for month check."""
        transaction = Transaction(merchant_name="Test", amount=Decimal("-50.00"), date=None)
        condition = RuleCondition(
            field=ConditionField.MONTH,
            operator=ConditionOperator.EQUALS,
            value="1",
        )
        assert self.engine.evaluate_condition(transaction, condition) is False

    def test_evaluate_month_invalid_value(self):
        """Invalid month value should return False."""
        transaction = Transaction(
            merchant_name="Test", amount=Decimal("-50.00"), date=date(2024, 2, 15)
        )
        condition = RuleCondition(
            field=ConditionField.MONTH,
            operator=ConditionOperator.EQUALS,
            value="not-a-number",
        )
        assert self.engine.evaluate_condition(transaction, condition) is False

    # ── Account conditions ────────────────────────────────────────────────

    def test_evaluate_account_id_equals(self):
        """Test account_id equals condition."""
        acc_id = uuid4()
        transaction = Transaction(
            merchant_name="Test",
            amount=Decimal("-50.00"),
            date=date.today(),
            account_id=acc_id,
        )
        condition = RuleCondition(
            field=ConditionField.ACCOUNT_ID,
            operator=ConditionOperator.EQUALS,
            value=str(acc_id),
        )
        assert self.engine.evaluate_condition(transaction, condition) is True

    def test_evaluate_account_id_contains_multiple(self):
        """Test account_id CONTAINS with comma-separated IDs."""
        acc_id = uuid4()
        other_id = uuid4()
        transaction = Transaction(
            merchant_name="Test",
            amount=Decimal("-50.00"),
            date=date.today(),
            account_id=acc_id,
        )
        condition = RuleCondition(
            field=ConditionField.ACCOUNT_ID,
            operator=ConditionOperator.CONTAINS,
            value=f"{other_id},{acc_id}",
        )
        assert self.engine.evaluate_condition(transaction, condition) is True

    def test_evaluate_account_type_with_loaded_account(self):
        """Test account_type condition when account is loaded."""
        from app.models.account import AccountType

        # Use a fully mocked transaction to avoid SQLAlchemy relationship issues
        transaction = Mock(spec=Transaction)
        transaction.merchant_name = "Test"
        transaction.amount = Decimal("-50.00")
        transaction.date = date.today()

        account_mock = Mock()
        account_mock.account_type = AccountType.CHECKING
        transaction.account = account_mock

        condition = RuleCondition(
            field=ConditionField.ACCOUNT_TYPE,
            operator=ConditionOperator.EQUALS,
            value="checking",
        )
        assert self.engine.evaluate_condition(transaction, condition) is True

    def test_evaluate_account_type_not_loaded(self):
        """Test account_type condition when account is not loaded returns False."""
        transaction = Mock(spec=Transaction)
        transaction.merchant_name = "Test"
        transaction.amount = Decimal("-50.00")
        transaction.date = date.today()
        transaction.account = None

        condition = RuleCondition(
            field=ConditionField.ACCOUNT_TYPE,
            operator=ConditionOperator.EQUALS,
            value="checking",
        )
        assert self.engine.evaluate_condition(transaction, condition) is False

    # ── String operator branches ──────────────────────────────────────────

    def test_evaluate_merchant_equals(self):
        """Test merchant name exact equals."""
        transaction = Transaction(
            merchant_name="walmart", amount=Decimal("-50.00"), date=date.today()
        )
        condition = RuleCondition(
            field=ConditionField.MERCHANT_NAME,
            operator=ConditionOperator.EQUALS,
            value="walmart",
        )
        assert self.engine.evaluate_condition(transaction, condition) is True

    def test_evaluate_merchant_starts_with(self):
        """Test merchant name starts_with."""
        transaction = Transaction(
            merchant_name="Starbucks Coffee", amount=Decimal("-5.00"), date=date.today()
        )
        condition = RuleCondition(
            field=ConditionField.MERCHANT_NAME,
            operator=ConditionOperator.STARTS_WITH,
            value="starbucks",
        )
        assert self.engine.evaluate_condition(transaction, condition) is True

    def test_evaluate_merchant_ends_with(self):
        """Test merchant name ends_with."""
        transaction = Transaction(
            merchant_name="Store Coffee", amount=Decimal("-5.00"), date=date.today()
        )
        condition = RuleCondition(
            field=ConditionField.MERCHANT_NAME,
            operator=ConditionOperator.ENDS_WITH,
            value="coffee",
        )
        assert self.engine.evaluate_condition(transaction, condition) is True

    def test_evaluate_regex_too_long(self):
        """Regex patterns over 200 chars should return False."""
        transaction = Transaction(
            merchant_name="Test",
            amount=Decimal("-50.00"),
            date=date.today(),
            description="Test description",
        )
        condition = RuleCondition(
            field=ConditionField.DESCRIPTION,
            operator=ConditionOperator.REGEX,
            value="a" * 201,
        )
        assert self.engine.evaluate_condition(transaction, condition) is False

    def test_evaluate_null_merchant_name(self):
        """Null merchant_name should be treated as empty string."""
        transaction = Transaction(merchant_name=None, amount=Decimal("-50.00"), date=date.today())
        condition = RuleCondition(
            field=ConditionField.MERCHANT_NAME,
            operator=ConditionOperator.CONTAINS,
            value="test",
        )
        assert self.engine.evaluate_condition(transaction, condition) is False

    def test_evaluate_unknown_field(self):
        """Unknown field should return False."""
        transaction = Transaction(merchant_name="Test", amount=Decimal("-50.00"), date=date.today())
        condition = RuleCondition(
            field="nonexistent_field",
            operator=ConditionOperator.EQUALS,
            value="test",
        )
        assert self.engine.evaluate_condition(transaction, condition) is False


@pytest.mark.unit
@pytest.mark.rules
class TestRuleMatching:
    """Test rule-level matching logic (matches_rule)."""

    def setup_method(self):
        self.engine = RuleEngine(db=Mock())

    def test_no_conditions_returns_false(self):
        """Rule with empty conditions should not match."""
        rule = Mock()
        rule.conditions = []
        transaction = Transaction(merchant_name="Test", amount=Decimal("-50.00"), date=date.today())
        assert self.engine.matches_rule(transaction, rule) is False

    def test_match_type_all_requires_all_conditions(self):
        """ALL match type: all conditions must pass."""
        from app.models.rule import RuleMatchType

        rule = Mock()
        rule.match_type = RuleMatchType.ALL
        rule.conditions = [
            RuleCondition(
                field=ConditionField.MERCHANT_NAME,
                operator=ConditionOperator.CONTAINS,
                value="starbucks",
            ),
            RuleCondition(
                field=ConditionField.AMOUNT,
                operator=ConditionOperator.GREATER_THAN,
                value="100.00",
            ),
        ]
        transaction = Transaction(
            merchant_name="Starbucks", amount=Decimal("-5.00"), date=date.today()
        )
        # Merchant matches but amount (5) < 100, so should fail
        assert self.engine.matches_rule(transaction, rule) is False

    def test_match_type_any_requires_one_condition(self):
        """ANY match type: just one condition must pass."""
        from app.models.rule import RuleMatchType

        rule = Mock()
        rule.match_type = RuleMatchType.ANY
        rule.conditions = [
            RuleCondition(
                field=ConditionField.MERCHANT_NAME,
                operator=ConditionOperator.CONTAINS,
                value="starbucks",
            ),
            RuleCondition(
                field=ConditionField.AMOUNT,
                operator=ConditionOperator.GREATER_THAN,
                value="100.00",
            ),
        ]
        transaction = Transaction(
            merchant_name="Starbucks", amount=Decimal("-5.00"), date=date.today()
        )
        # Merchant matches, so should pass
        assert self.engine.matches_rule(transaction, rule) is True


@pytest.mark.unit
@pytest.mark.rules
class TestRuleActions:
    """Test action application logic."""

    def setup_method(self):
        from unittest.mock import AsyncMock

        self.db = AsyncMock()
        self.engine = RuleEngine(db=self.db)

    @pytest.mark.asyncio
    async def test_set_category_action(self):
        """SET_CATEGORY action should update transaction.category_primary."""
        from app.models.rule import ActionType, RuleAction

        transaction = Transaction(merchant_name="Test", amount=Decimal("-50.00"), date=date.today())
        action = RuleAction(
            action_type=ActionType.SET_CATEGORY,
            action_value="Groceries",
        )
        result = await self.engine.apply_action(transaction, action, "rule-123")
        assert result is True
        assert transaction.category_primary == "Groceries"

    @pytest.mark.asyncio
    async def test_set_merchant_action(self):
        """SET_MERCHANT action should update transaction.merchant_name."""
        from app.models.rule import ActionType, RuleAction

        transaction = Transaction(
            merchant_name="SQ *Cafe", amount=Decimal("-5.00"), date=date.today()
        )
        action = RuleAction(
            action_type=ActionType.SET_MERCHANT,
            action_value="Local Cafe",
        )
        result = await self.engine.apply_action(transaction, action, "rule-123")
        assert result is True
        assert transaction.merchant_name == "Local Cafe"

    @pytest.mark.asyncio
    async def test_add_label_action_label_not_found(self):
        """ADD_LABEL should return False if label doesn't exist."""
        from uuid import uuid4

        from app.models.rule import ActionType, RuleAction

        org_id = uuid4()
        transaction = Transaction(merchant_name="Test", amount=Decimal("-50.00"), date=date.today())
        transaction.organization_id = org_id
        transaction.id = uuid4()

        action = RuleAction(
            action_type=ActionType.ADD_LABEL,
            action_value=str(uuid4()),
        )

        # Mock: label not found
        label_result = MagicMock()
        label_result.scalar_one_or_none.return_value = None
        self.db.execute.return_value = label_result

        result = await self.engine.apply_action(transaction, action, "rule-123")
        assert result is False

    @pytest.mark.asyncio
    async def test_remove_label_action_not_found(self):
        """REMOVE_LABEL should return False if label not applied."""
        from uuid import uuid4

        from app.models.rule import ActionType, RuleAction

        transaction = Transaction(merchant_name="Test", amount=Decimal("-50.00"), date=date.today())
        transaction.id = uuid4()

        action = RuleAction(
            action_type=ActionType.REMOVE_LABEL,
            action_value=str(uuid4()),
        )

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        self.db.execute.return_value = result_mock

        result = await self.engine.apply_action(transaction, action, "rule-123")
        assert result is False

    @pytest.mark.asyncio
    async def test_remove_label_action_found(self):
        """REMOVE_LABEL should delete label and return True."""
        from uuid import uuid4

        from app.models.rule import ActionType, RuleAction

        transaction = Transaction(merchant_name="Test", amount=Decimal("-50.00"), date=date.today())
        transaction.id = uuid4()

        action = RuleAction(
            action_type=ActionType.REMOVE_LABEL,
            action_value=str(uuid4()),
        )

        existing_label = MagicMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = existing_label
        self.db.execute.return_value = result_mock

        result = await self.engine.apply_action(transaction, action, "rule-123")
        assert result is True
        self.db.delete.assert_called_once_with(existing_label)


@pytest.mark.unit
@pytest.mark.rules
class TestApplyRuleToTransaction:
    """Test apply_rule_to_transaction method."""

    def setup_method(self):
        from unittest.mock import AsyncMock

        self.db = AsyncMock()
        self.engine = RuleEngine(db=self.db)

    @pytest.mark.asyncio
    async def test_inactive_rule_not_applied(self):
        """Inactive rules should not be applied."""
        rule = Mock()
        rule.is_active = False
        transaction = Transaction(merchant_name="Test", amount=Decimal("-50.00"), date=date.today())
        result = await self.engine.apply_rule_to_transaction(transaction, rule)
        assert result is False

    @pytest.mark.asyncio
    async def test_non_matching_rule_not_applied(self):
        """Rule that doesn't match should not apply actions."""
        from app.models.rule import RuleMatchType

        rule = Mock()
        rule.is_active = True
        rule.match_type = RuleMatchType.ALL
        rule.conditions = [
            RuleCondition(
                field=ConditionField.MERCHANT_NAME,
                operator=ConditionOperator.CONTAINS,
                value="nonexistent",
            ),
        ]
        transaction = Transaction(merchant_name="Test", amount=Decimal("-50.00"), date=date.today())
        result = await self.engine.apply_rule_to_transaction(transaction, rule)
        assert result is False

    @pytest.mark.asyncio
    async def test_matching_rule_applies_actions(self):
        """Matching rule with SET_CATEGORY action should apply it."""
        from app.models.rule import ActionType, RuleAction, RuleMatchType

        rule = Mock()
        rule.is_active = True
        rule.id = "rule-999"
        rule.match_type = RuleMatchType.ALL
        rule.conditions = [
            RuleCondition(
                field=ConditionField.MERCHANT_NAME,
                operator=ConditionOperator.CONTAINS,
                value="star",
            ),
        ]
        rule.actions = [
            RuleAction(
                action_type=ActionType.SET_CATEGORY,
                action_value="Coffee",
            ),
        ]
        transaction = Transaction(
            merchant_name="Starbucks", amount=Decimal("-5.00"), date=date.today()
        )
        result = await self.engine.apply_rule_to_transaction(transaction, rule)
        assert result is True
        assert transaction.category_primary == "Coffee"


# ---------------------------------------------------------------------------
# Coverage: amount BETWEEN invalid max (lines 94-95)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.rules
class TestAmountBetweenInvalidMax:
    """Cover amount BETWEEN with non-numeric max value."""

    def setup_method(self):
        self.engine = RuleEngine(db=Mock())

    def test_amount_between_invalid_max_value(self):
        """Amount BETWEEN with non-numeric value_max returns False."""
        transaction = Transaction(merchant_name="Test", amount=Decimal("-75.00"), date=date.today())
        condition = RuleCondition(
            field=ConditionField.AMOUNT,
            operator=ConditionOperator.BETWEEN,
            value="50.00",
            value_max="not-a-number",
        )
        assert self.engine.evaluate_condition(transaction, condition) is False


# ---------------------------------------------------------------------------
# Coverage: date condition with non-string value (line 111)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.rules
class TestDateConditionNonString:
    """Cover date condition where condition.value is not a string."""

    def setup_method(self):
        self.engine = RuleEngine(db=Mock())

    def test_date_condition_value_is_date_object(self):
        """When condition.value is already a date, use it directly."""
        test_date = date(2024, 2, 15)
        transaction = Transaction(merchant_name="Test", amount=Decimal("-50.00"), date=test_date)
        condition = RuleCondition(
            field=ConditionField.DATE,
            operator=ConditionOperator.EQUALS,
            value=test_date,  # date object, not string
        )
        assert self.engine.evaluate_condition(transaction, condition) is True


# ---------------------------------------------------------------------------
# Coverage: date BETWEEN with string max (lines 122-126), invalid date (127-128)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.rules
class TestDateBetweenExtended:
    """Cover date BETWEEN with string value_max and invalid date."""

    def setup_method(self):
        self.engine = RuleEngine(db=Mock())

    def test_date_between_string_max(self):
        """Date BETWEEN with string value_max should parse and compare."""
        transaction = Transaction(
            merchant_name="Test", amount=Decimal("-50.00"), date=date(2024, 3, 15)
        )
        condition = RuleCondition(
            field=ConditionField.DATE,
            operator=ConditionOperator.BETWEEN,
            value="2024-01-01",
            value_max="2024-06-30",
        )
        assert self.engine.evaluate_condition(transaction, condition) is True

    def test_date_between_non_string_max(self):
        """Date BETWEEN with date object value_max."""
        transaction = Transaction(
            merchant_name="Test", amount=Decimal("-50.00"), date=date(2024, 3, 15)
        )
        condition = RuleCondition(
            field=ConditionField.DATE,
            operator=ConditionOperator.BETWEEN,
            value="2024-01-01",
            value_max=date(2024, 6, 30),
        )
        assert self.engine.evaluate_condition(transaction, condition) is True

    def test_date_invalid_value_returns_false(self):
        """Invalid date value should return False."""
        transaction = Transaction(
            merchant_name="Test", amount=Decimal("-50.00"), date=date(2024, 3, 15)
        )
        condition = RuleCondition(
            field=ConditionField.DATE,
            operator=ConditionOperator.EQUALS,
            value="not-a-date",
        )
        assert self.engine.evaluate_condition(transaction, condition) is False


# ---------------------------------------------------------------------------
# Coverage: month BETWEEN invalid max (lines 156-157)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.rules
class TestMonthBetweenInvalidMax:
    """Cover month BETWEEN with non-numeric value_max."""

    def setup_method(self):
        self.engine = RuleEngine(db=Mock())

    def test_month_between_invalid_max(self):
        """Month BETWEEN with non-numeric max returns False."""
        transaction = Transaction(
            merchant_name="Test", amount=Decimal("-50.00"), date=date(2024, 4, 15)
        )
        condition = RuleCondition(
            field=ConditionField.MONTH,
            operator=ConditionOperator.BETWEEN,
            value="3",
            value_max="not-a-number",
        )
        assert self.engine.evaluate_condition(transaction, condition) is False


# ---------------------------------------------------------------------------
# Coverage: add_label success (lines 236-253)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.rules
class TestAddLabelSuccess:
    """Cover ADD_LABEL when label exists and is not already applied."""

    def setup_method(self):
        from unittest.mock import AsyncMock

        self.db = AsyncMock()
        self.engine = RuleEngine(db=self.db)

    @pytest.mark.asyncio
    async def test_add_label_success(self):
        from uuid import uuid4

        from app.models.rule import ActionType, RuleAction

        org_id = uuid4()
        transaction = Transaction(merchant_name="Test", amount=Decimal("-50.00"), date=date.today())
        transaction.organization_id = org_id
        transaction.id = uuid4()

        action = RuleAction(
            action_type=ActionType.ADD_LABEL,
            action_value=str(uuid4()),
        )

        # First query: label exists
        label_mock = MagicMock()
        label_result = MagicMock()
        label_result.scalar_one_or_none.return_value = label_mock

        # Second query: label not yet applied
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = None

        self.db.execute = AsyncMock(side_effect=[label_result, existing_result])

        result = await self.engine.apply_action(transaction, action, "rule-123")
        assert result is True
        self.db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_label_already_applied(self):
        """ADD_LABEL should return False when label already exists on txn."""
        from uuid import uuid4

        from app.models.rule import ActionType, RuleAction

        org_id = uuid4()
        transaction = Transaction(merchant_name="Test", amount=Decimal("-50.00"), date=date.today())
        transaction.organization_id = org_id
        transaction.id = uuid4()

        action = RuleAction(
            action_type=ActionType.ADD_LABEL,
            action_value=str(uuid4()),
        )

        label_mock = MagicMock()
        label_result = MagicMock()
        label_result.scalar_one_or_none.return_value = label_mock

        # Already applied
        existing_mock = MagicMock()
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = existing_mock

        self.db.execute = AsyncMock(side_effect=[label_result, existing_result])

        result = await self.engine.apply_action(transaction, action, "rule-123")
        assert result is False


# ---------------------------------------------------------------------------
# Coverage: apply_action error handling (lines 269-273)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.rules
class TestApplyActionErrorAndFallthrough:
    """Cover apply_action error path and unknown action type."""

    def setup_method(self):
        from unittest.mock import AsyncMock

        self.db = AsyncMock()
        self.engine = RuleEngine(db=self.db)

    @pytest.mark.asyncio
    async def test_apply_action_exception_returns_false(self):
        """Error during action application should return False."""
        from app.models.rule import ActionType, RuleAction

        action = RuleAction(
            action_type=ActionType.SET_CATEGORY,
            action_value="Food",
        )
        # transaction with no category_primary attribute to force error
        transaction = Mock()
        type(transaction).category_primary = property(
            lambda self: (_ for _ in ()).throw(RuntimeError("boom"))
        )

        result = await self.engine.apply_action(transaction, action, "rule-123")
        assert result is False


# ---------------------------------------------------------------------------
# Coverage: apply_rule_to_transactions (lines 299-335)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.rules
class TestApplyRuleToTransactions:
    """Cover apply_rule_to_transactions batch processing."""

    def setup_method(self):
        from unittest.mock import AsyncMock

        self.db = AsyncMock()
        self.engine = RuleEngine(db=self.db)

    @pytest.mark.asyncio
    async def test_apply_rule_to_transactions_with_matches(self):
        """Should process batches and update rule stats."""
        from uuid import uuid4

        from app.models.rule import ActionType, RuleAction, RuleMatchType

        rule = MagicMock()
        rule.organization_id = uuid4()
        rule.is_active = True
        rule.match_type = RuleMatchType.ALL
        rule.conditions = [
            RuleCondition(
                field=ConditionField.MERCHANT_NAME,
                operator=ConditionOperator.CONTAINS,
                value="coffee",
            ),
        ]
        rule.actions = [
            RuleAction(
                action_type=ActionType.SET_CATEGORY,
                action_value="Coffee",
            ),
        ]
        rule.times_applied = 0
        rule.last_applied_at = None

        txn1 = Transaction(merchant_name="Coffee Shop", amount=Decimal("-5"), date=date.today())
        txn2 = Transaction(merchant_name="Gas Station", amount=Decimal("-40"), date=date.today())

        # First batch returns two txns, second batch returns empty
        batch1_result = MagicMock()
        batch1_result.scalars.return_value.all.return_value = [txn1, txn2]
        batch2_result = MagicMock()
        batch2_result.scalars.return_value.all.return_value = []

        self.db.execute = AsyncMock(side_effect=[batch1_result, batch2_result])

        count = await self.engine.apply_rule_to_transactions(rule)

        assert count == 1  # Only txn1 matches
        assert rule.times_applied == 1
        assert rule.last_applied_at is not None
        self.db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_apply_rule_to_transactions_no_matches(self):
        """No matches should not update stats."""
        from uuid import uuid4

        from app.models.rule import RuleMatchType

        rule = MagicMock()
        rule.organization_id = uuid4()
        rule.is_active = True
        rule.match_type = RuleMatchType.ALL
        rule.conditions = [
            RuleCondition(
                field=ConditionField.MERCHANT_NAME,
                operator=ConditionOperator.CONTAINS,
                value="nonexistent",
            ),
        ]
        rule.actions = []
        rule.times_applied = 0

        batch_result = MagicMock()
        batch_result.scalars.return_value.all.return_value = []
        self.db.execute = AsyncMock(return_value=batch_result)

        count = await self.engine.apply_rule_to_transactions(rule)

        assert count == 0
        self.db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_apply_rule_to_transactions_with_ids(self):
        """Should filter by transaction IDs when provided."""
        from uuid import uuid4

        from app.models.rule import RuleMatchType

        rule = MagicMock()
        rule.organization_id = uuid4()
        rule.is_active = True
        rule.match_type = RuleMatchType.ALL
        rule.conditions = [
            RuleCondition(
                field=ConditionField.MERCHANT_NAME,
                operator=ConditionOperator.CONTAINS,
                value="nonexistent",
            ),
        ]
        rule.actions = []
        rule.times_applied = 0

        batch_result = MagicMock()
        batch_result.scalars.return_value.all.return_value = []
        self.db.execute = AsyncMock(return_value=batch_result)

        count = await self.engine.apply_rule_to_transactions(rule, transaction_ids=[str(uuid4())])
        assert count == 0


# ---------------------------------------------------------------------------
# Coverage: apply_all_rules_to_transaction (lines 340-357)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.rules
class TestApplyAllRulesToTransaction:
    """Cover apply_all_rules_to_transaction."""

    def setup_method(self):
        from unittest.mock import AsyncMock

        self.db = AsyncMock()
        self.engine = RuleEngine(db=self.db)

    @pytest.mark.asyncio
    async def test_apply_all_rules_returns_applied_ids(self):
        """Should return list of applied rule IDs."""
        from uuid import uuid4

        from app.models.rule import ActionType, RuleAction, RuleMatchType

        rule1 = MagicMock()
        rule1.id = uuid4()
        rule1.is_active = True
        rule1.match_type = RuleMatchType.ALL
        rule1.conditions = [
            RuleCondition(
                field=ConditionField.MERCHANT_NAME,
                operator=ConditionOperator.CONTAINS,
                value="star",
            ),
        ]
        rule1.actions = [
            RuleAction(action_type=ActionType.SET_CATEGORY, action_value="Coffee"),
        ]

        rule2 = MagicMock()
        rule2.id = uuid4()
        rule2.is_active = True
        rule2.match_type = RuleMatchType.ALL
        rule2.conditions = [
            RuleCondition(
                field=ConditionField.MERCHANT_NAME,
                operator=ConditionOperator.CONTAINS,
                value="nonexistent",
            ),
        ]
        rule2.actions = []

        # Mock DB returning rules
        rules_result = MagicMock()
        rules_result.unique.return_value.scalars.return_value.all.return_value = [rule1, rule2]
        self.db.execute = AsyncMock(return_value=rules_result)

        org_id = uuid4()
        transaction = Transaction(
            merchant_name="Starbucks", amount=Decimal("-5.00"), date=date.today()
        )
        transaction.organization_id = org_id

        applied = await self.engine.apply_all_rules_to_transaction(transaction)

        assert str(rule1.id) in applied
        assert str(rule2.id) not in applied
        self.db.commit.assert_awaited_once()
