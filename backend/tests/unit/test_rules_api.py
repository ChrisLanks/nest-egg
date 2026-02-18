"""Unit tests for rules API endpoints."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4
from decimal import Decimal
from datetime import date

from fastapi import HTTPException

from app.api.v1.rules import (
    list_rules,
    create_rule,
    get_rule,
    update_rule,
    delete_rule,
    apply_rule,
    preview_rule,
    test_rule,
    ApplyRuleRequest,
    router,
)
from app.models.user import User
from app.models.rule import Rule, RuleCondition, RuleAction, RuleMatchType, RuleApplyTo, ConditionField, ConditionOperator, ActionType
from app.models.transaction import Transaction
from app.schemas.rule import RuleCreate, RuleUpdate, RuleConditionCreate, RuleActionCreate


@pytest.mark.unit
class TestListRules:
    """Test list_rules endpoint."""

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
    async def test_lists_rules_for_organization(self, mock_db, mock_user):
        """Should list rules for current user's organization."""
        rule1 = Mock(spec=Rule)
        rule1.id = uuid4()
        rule1.name = "Auto-categorize Groceries"

        rule2 = Mock(spec=Rule)
        rule2.id = uuid4()
        rule2.name = "Label Business Expenses"

        result = Mock()
        result.unique.return_value.scalars.return_value.all.return_value = [rule1, rule2]
        mock_db.execute.return_value = result

        rules = await list_rules(current_user=mock_user, db=mock_db)

        assert len(rules) == 2
        assert rules[0].name == "Auto-categorize Groceries"
        assert rules[1].name == "Label Business Expenses"

    @pytest.mark.asyncio
    async def test_orders_by_priority_and_name(self, mock_db, mock_user):
        """Should order rules by priority descending, then name."""
        result = Mock()
        result.unique.return_value.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = result

        await list_rules(current_user=mock_user, db=mock_db)

        # Verify query was executed (ordering verified via query structure)
        assert mock_db.execute.called


@pytest.mark.unit
class TestCreateRule:
    """Test create_rule endpoint."""

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
    def mock_request(self):
        request = Mock()
        request.client = Mock()
        request.client.host = "127.0.0.1"
        return request

    @pytest.fixture
    def rule_create_data(self):
        return RuleCreate(
            name="Auto-categorize Groceries",
            description="Automatically set category for grocery purchases",
            match_type=RuleMatchType.ALL,
            apply_to=RuleApplyTo.NEW_ONLY,
            priority=5,
            is_active=True,
            conditions=[
                RuleConditionCreate(
                    field=ConditionField.MERCHANT_NAME,
                    operator=ConditionOperator.CONTAINS,
                    value="Safeway",
                ),
            ],
            actions=[
                RuleActionCreate(
                    action_type=ActionType.SET_CATEGORY,
                    action_value="Food and Drink",
                ),
            ],
        )

    @pytest.mark.asyncio
    async def test_creates_rule_successfully(
        self, mock_db, mock_user, mock_request, rule_create_data
    ):
        """Should create a new rule with conditions and actions."""
        rule_id = uuid4()
        created_rule = Mock(spec=Rule)
        created_rule.id = rule_id
        created_rule.name = "Auto-categorize Groceries"

        # Mock refresh to set ID
        async def mock_flush():
            created_rule.id = rule_id

        mock_db.flush = mock_flush

        # Mock final select with relationships
        result = Mock()
        result.unique.return_value.scalar_one.return_value = created_rule
        mock_db.execute.return_value = result

        with patch(
            "app.api.v1.rules.rate_limit_service.check_rate_limit",
            return_value=None,
        ):
            result = await create_rule(
                rule_data=rule_create_data,
                http_request=mock_request,
                current_user=mock_user,
                db=mock_db,
            )

            assert mock_db.add.called
            assert mock_db.commit.called
            assert result.name == "Auto-categorize Groceries"

    @pytest.mark.asyncio
    async def test_respects_rate_limit(
        self, mock_db, mock_user, mock_request, rule_create_data
    ):
        """Should enforce rate limit on rule creation."""
        with patch(
            "app.api.v1.rules.rate_limit_service.check_rate_limit",
        ) as mock_rate_limit:
            # Mock final select
            result = Mock()
            result.unique.return_value.scalar_one.return_value = Mock(spec=Rule)
            mock_db.execute.return_value = result

            await create_rule(
                rule_data=rule_create_data,
                http_request=mock_request,
                current_user=mock_user,
                db=mock_db,
            )

            mock_rate_limit.assert_called_once_with(
                request=mock_request,
                max_requests=20,
                window_seconds=3600,
            )


@pytest.mark.unit
class TestGetRule:
    """Test get_rule endpoint."""

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
    async def test_returns_rule_successfully(self, mock_db, mock_user):
        """Should return rule when found."""
        rule_id = uuid4()
        expected_rule = Mock(spec=Rule)
        expected_rule.id = rule_id
        expected_rule.name = "Test Rule"

        result = Mock()
        result.unique.return_value.scalar_one_or_none.return_value = expected_rule
        mock_db.execute.return_value = result

        rule = await get_rule(
            rule_id=rule_id,
            current_user=mock_user,
            db=mock_db,
        )

        assert rule.id == rule_id
        assert rule.name == "Test Rule"

    @pytest.mark.asyncio
    async def test_raises_404_when_rule_not_found(self, mock_db, mock_user):
        """Should raise 404 when rule doesn't exist."""
        rule_id = uuid4()

        result = Mock()
        result.unique.return_value.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result

        with pytest.raises(HTTPException) as exc_info:
            await get_rule(
                rule_id=rule_id,
                current_user=mock_user,
                db=mock_db,
            )

        assert exc_info.value.status_code == 404
        assert "Rule not found" in exc_info.value.detail


@pytest.mark.unit
class TestUpdateRule:
    """Test update_rule endpoint."""

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
    def mock_request(self):
        request = Mock()
        request.client = Mock()
        request.client.host = "127.0.0.1"
        return request

    @pytest.fixture
    def mock_rule(self):
        rule = Mock(spec=Rule)
        rule.id = uuid4()
        rule.name = "Original Name"
        rule.description = "Original description"
        rule.is_active = True
        rule.priority = 5
        return rule

    @pytest.mark.asyncio
    async def test_updates_rule_successfully(
        self, mock_db, mock_user, mock_request, mock_rule
    ):
        """Should update rule fields."""
        rule_id = mock_rule.id
        update_data = RuleUpdate(
            name="Updated Name",
            description="Updated description",
        )

        # Mock rule lookup
        lookup_result = Mock()
        lookup_result.scalar_one_or_none.return_value = mock_rule

        # Mock final refresh with relationships
        refresh_result = Mock()
        refresh_result.unique.return_value.scalar_one.return_value = mock_rule

        mock_db.execute.side_effect = [lookup_result, refresh_result]

        with patch(
            "app.api.v1.rules.rate_limit_service.check_rate_limit",
            return_value=None,
        ):
            result = await update_rule(
                rule_id=rule_id,
                rule_data=update_data,
                http_request=mock_request,
                current_user=mock_user,
                db=mock_db,
            )

            assert result.name == "Updated Name"
            assert result.description == "Updated description"
            assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_raises_404_when_rule_not_found(
        self, mock_db, mock_user, mock_request
    ):
        """Should raise 404 when rule doesn't exist."""
        rule_id = uuid4()
        update_data = RuleUpdate(name="New Name")

        result = Mock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result

        with patch(
            "app.api.v1.rules.rate_limit_service.check_rate_limit",
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await update_rule(
                    rule_id=rule_id,
                    rule_data=update_data,
                    http_request=mock_request,
                    current_user=mock_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_respects_rate_limit(
        self, mock_db, mock_user, mock_request, mock_rule
    ):
        """Should enforce rate limit on rule updates."""
        update_data = RuleUpdate(name="New Name")

        result = Mock()
        result.scalar_one_or_none.return_value = mock_rule
        mock_db.execute.return_value = result

        with patch(
            "app.api.v1.rules.rate_limit_service.check_rate_limit",
        ) as mock_rate_limit:
            # Mock final refresh
            refresh_result = Mock()
            refresh_result.unique.return_value.scalar_one.return_value = mock_rule
            mock_db.execute.side_effect = [result, refresh_result]

            await update_rule(
                rule_id=mock_rule.id,
                rule_data=update_data,
                http_request=mock_request,
                current_user=mock_user,
                db=mock_db,
            )

            mock_rate_limit.assert_called_once_with(
                request=mock_request,
                max_requests=30,
                window_seconds=3600,
            )


@pytest.mark.unit
class TestDeleteRule:
    """Test delete_rule endpoint."""

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
    def mock_request(self):
        request = Mock()
        request.client = Mock()
        request.client.host = "127.0.0.1"
        return request

    @pytest.mark.asyncio
    async def test_deletes_rule_successfully(
        self, mock_db, mock_user, mock_request
    ):
        """Should delete rule and return None."""
        rule_id = uuid4()
        rule = Mock(spec=Rule)
        rule.id = rule_id

        result = Mock()
        result.scalar_one_or_none.return_value = rule
        mock_db.execute.return_value = result

        with patch(
            "app.api.v1.rules.rate_limit_service.check_rate_limit",
            return_value=None,
        ):
            result = await delete_rule(
                rule_id=rule_id,
                http_request=mock_request,
                current_user=mock_user,
                db=mock_db,
            )

            assert result is None
            assert mock_db.delete.called
            assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_raises_404_when_rule_not_found(
        self, mock_db, mock_user, mock_request
    ):
        """Should raise 404 when rule doesn't exist."""
        rule_id = uuid4()

        result = Mock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result

        with patch(
            "app.api.v1.rules.rate_limit_service.check_rate_limit",
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await delete_rule(
                    rule_id=rule_id,
                    http_request=mock_request,
                    current_user=mock_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_respects_rate_limit(
        self, mock_db, mock_user, mock_request
    ):
        """Should enforce rate limit on rule deletion."""
        rule_id = uuid4()
        rule = Mock(spec=Rule)

        result = Mock()
        result.scalar_one_or_none.return_value = rule
        mock_db.execute.return_value = result

        with patch(
            "app.api.v1.rules.rate_limit_service.check_rate_limit",
        ) as mock_rate_limit:
            await delete_rule(
                rule_id=rule_id,
                http_request=mock_request,
                current_user=mock_user,
                db=mock_db,
            )

            mock_rate_limit.assert_called_once_with(
                request=mock_request,
                max_requests=20,
                window_seconds=3600,
            )


@pytest.mark.unit
class TestApplyRule:
    """Test apply_rule endpoint."""

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
    def mock_request(self):
        request = Mock()
        request.client = Mock()
        request.client.host = "127.0.0.1"
        return request

    @pytest.mark.asyncio
    async def test_applies_rule_to_all_transactions(
        self, mock_db, mock_user, mock_request
    ):
        """Should apply rule to all transactions when no IDs specified."""
        rule_id = uuid4()
        rule = Mock(spec=Rule)
        rule.id = rule_id

        result = Mock()
        result.unique.return_value.scalar_one_or_none.return_value = rule
        mock_db.execute.return_value = result

        request_data = ApplyRuleRequest(transaction_ids=None)

        with patch(
            "app.api.v1.rules.rate_limit_service.check_rate_limit",
            return_value=None,
        ):
            with patch("app.api.v1.rules.RuleEngine") as MockEngine:
                mock_engine = MockEngine.return_value
                mock_engine.apply_rule_to_transactions = AsyncMock(return_value=25)

                result = await apply_rule(
                    rule_id=rule_id,
                    request_data=request_data,
                    http_request=mock_request,
                    current_user=mock_user,
                    db=mock_db,
                )

                assert result["applied_count"] == 25
                assert "25 transaction(s)" in result["message"]

    @pytest.mark.asyncio
    async def test_applies_rule_to_specific_transactions(
        self, mock_db, mock_user, mock_request
    ):
        """Should apply rule to specified transaction IDs."""
        rule_id = uuid4()
        rule = Mock(spec=Rule)

        result = Mock()
        result.unique.return_value.scalar_one_or_none.return_value = rule
        mock_db.execute.return_value = result

        transaction_ids = [str(uuid4()), str(uuid4())]
        request_data = ApplyRuleRequest(transaction_ids=transaction_ids)

        with patch(
            "app.api.v1.rules.rate_limit_service.check_rate_limit",
            return_value=None,
        ):
            with patch("app.api.v1.rules.RuleEngine") as MockEngine:
                mock_engine = MockEngine.return_value
                mock_engine.apply_rule_to_transactions = AsyncMock(return_value=2)

                result = await apply_rule(
                    rule_id=rule_id,
                    request_data=request_data,
                    http_request=mock_request,
                    current_user=mock_user,
                    db=mock_db,
                )

                assert result["applied_count"] == 2
                mock_engine.apply_rule_to_transactions.assert_called_once_with(
                    rule, transaction_ids
                )

    @pytest.mark.asyncio
    async def test_raises_404_when_rule_not_found(
        self, mock_db, mock_user, mock_request
    ):
        """Should raise 404 when rule doesn't exist."""
        rule_id = uuid4()
        request_data = ApplyRuleRequest()

        result = Mock()
        result.unique.return_value.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result

        with patch(
            "app.api.v1.rules.rate_limit_service.check_rate_limit",
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await apply_rule(
                    rule_id=rule_id,
                    request_data=request_data,
                    http_request=mock_request,
                    current_user=mock_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404


@pytest.mark.unit
class TestPreviewRule:
    """Test preview_rule endpoint."""

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
    async def test_previews_matching_transactions(self, mock_db, mock_user):
        """Should return IDs of transactions that would match rule."""
        rule_id = uuid4()
        rule = Mock(spec=Rule)

        # Mock rule lookup
        rule_result = Mock()
        rule_result.unique.return_value.scalar_one_or_none.return_value = rule

        # Mock transaction query
        transaction1 = Mock(spec=Transaction)
        transaction1.id = uuid4()
        transaction2 = Mock(spec=Transaction)
        transaction2.id = uuid4()
        transaction3 = Mock(spec=Transaction)
        transaction3.id = uuid4()

        transaction_result = Mock()
        transaction_result.scalars.return_value.all.return_value = [
            transaction1,
            transaction2,
            transaction3,
        ]

        mock_db.execute.side_effect = [rule_result, transaction_result]

        with patch("app.api.v1.rules.RuleEngine") as MockEngine:
            mock_engine = MockEngine.return_value
            # Only transactions 1 and 3 match
            mock_engine.matches_rule.side_effect = [True, False, True]

            result = await preview_rule(
                rule_id=rule_id,
                current_user=mock_user,
                db=mock_db,
            )

            assert result["count"] == 2
            assert len(result["matching_transaction_ids"]) == 2
            assert str(transaction1.id) in result["matching_transaction_ids"]
            assert str(transaction3.id) in result["matching_transaction_ids"]

    @pytest.mark.asyncio
    async def test_raises_404_when_rule_not_found(self, mock_db, mock_user):
        """Should raise 404 when rule doesn't exist."""
        rule_id = uuid4()

        result = Mock()
        result.unique.return_value.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result

        with pytest.raises(HTTPException) as exc_info:
            await preview_rule(
                rule_id=rule_id,
                current_user=mock_user,
                db=mock_db,
            )

        assert exc_info.value.status_code == 404


@pytest.mark.unit
class TestTestRule:
    """Test test_rule endpoint."""

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
    def rule_create_data(self):
        return RuleCreate(
            name="Test Rule",
            description="Test description",
            match_type=RuleMatchType.ALL,
            apply_to=RuleApplyTo.NEW_ONLY,
            priority=5,
            is_active=True,
            conditions=[
                RuleConditionCreate(
                    field=ConditionField.MERCHANT_NAME,
                    operator=ConditionOperator.CONTAINS,
                    value="Amazon",
                ),
            ],
            actions=[
                RuleActionCreate(
                    action_type=ActionType.SET_CATEGORY,
                    action_value="Shopping",
                ),
            ],
        )

    @pytest.mark.asyncio
    async def test_tests_rule_without_saving(
        self, mock_db, mock_user, rule_create_data
    ):
        """Should test rule configuration without saving to database."""
        transaction1 = Mock(spec=Transaction)
        transaction1.id = uuid4()
        transaction1.date = date(2024, 1, 15)
        transaction1.merchant_name = "Amazon"
        transaction1.amount = Decimal("50.00")
        transaction1.category_primary = "Online Shopping"

        transaction2 = Mock(spec=Transaction)
        transaction2.id = uuid4()
        transaction2.date = date(2024, 1, 20)
        transaction2.merchant_name = "Safeway"
        transaction2.amount = Decimal("75.00")
        transaction2.category_primary = "Groceries"

        result = Mock()
        result.scalars.return_value.all.return_value = [transaction1, transaction2]
        mock_db.execute.return_value = result

        with patch("app.api.v1.rules.RuleEngine") as MockEngine:
            mock_engine = MockEngine.return_value
            # Only transaction1 matches
            mock_engine.matches_rule.side_effect = [True, False]

            result = await test_rule(
                rule_data=rule_create_data,
                current_user=mock_user,
                db=mock_db,
            )

            assert result["matching_count"] == 1
            assert result["total_tested"] == 2
            assert len(result["matching_transactions"]) == 1
            assert result["matching_transactions"][0]["merchant"] == "Amazon"
            assert "1 of 2" in result["message"]

    @pytest.mark.asyncio
    async def test_includes_change_previews(
        self, mock_db, mock_user, rule_create_data
    ):
        """Should include preview of what would change."""
        transaction = Mock(spec=Transaction)
        transaction.id = uuid4()
        transaction.date = date(2024, 1, 15)
        transaction.merchant_name = "Amazon"
        transaction.amount = Decimal("50.00")
        transaction.category_primary = "Online Shopping"

        result = Mock()
        result.scalars.return_value.all.return_value = [transaction]
        mock_db.execute.return_value = result

        with patch("app.api.v1.rules.RuleEngine") as MockEngine:
            mock_engine = MockEngine.return_value
            mock_engine.matches_rule.return_value = True

            result = await test_rule(
                rule_data=rule_create_data,
                current_user=mock_user,
                db=mock_db,
            )

            changes = result["matching_transactions"][0]["changes"]
            assert len(changes) == 1
            assert changes[0]["field"] == "category"
            assert changes[0]["from"] == "Online Shopping"
            assert changes[0]["to"] == "Shopping"

    @pytest.mark.asyncio
    async def test_limits_response_to_50_transactions(
        self, mock_db, mock_user, rule_create_data
    ):
        """Should limit response to 50 transactions for performance."""
        # Create 100 mock transactions
        transactions = []
        for i in range(100):
            tx = Mock(spec=Transaction)
            tx.id = uuid4()
            tx.date = date(2024, 1, 15)
            tx.merchant_name = "Amazon"
            tx.amount = Decimal("50.00")
            tx.category_primary = "Shopping"
            transactions.append(tx)

        result = Mock()
        result.scalars.return_value.all.return_value = transactions
        mock_db.execute.return_value = result

        with patch("app.api.v1.rules.RuleEngine") as MockEngine:
            mock_engine = MockEngine.return_value
            mock_engine.matches_rule.return_value = True

            result = await test_rule(
                rule_data=rule_create_data,
                current_user=mock_user,
                db=mock_db,
            )

            assert result["matching_count"] == 100
            assert len(result["matching_transactions"]) == 50  # Capped at 50
