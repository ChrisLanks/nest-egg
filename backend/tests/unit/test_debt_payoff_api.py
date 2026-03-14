"""Unit tests for debt payoff API endpoints."""

from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.debt_payoff import (
    compare_payoff_strategies,
    get_debt_summary,
    list_debt_accounts,
)
from app.models.user import User


def _mock_user():
    user = Mock(spec=User)
    user.id = uuid4()
    user.organization_id = uuid4()
    return user


def _mock_debt(
    name="Credit Card",
    balance=Decimal("5000"),
    rate=Decimal("19.99"),
    min_payment=Decimal("100"),
    acct_type="credit_card",
):
    d = Mock()
    d.account_id = uuid4()
    d.name = name
    d.balance = balance
    d.interest_rate = rate
    d.minimum_payment = min_payment
    d.account_type = acct_type
    return d


@pytest.mark.unit
class TestListDebtAccounts:
    @pytest.mark.asyncio
    async def test_returns_debts(self):
        mock_db = AsyncMock()
        user = _mock_user()
        debts = [_mock_debt()]

        with patch("app.api.v1.debt_payoff.PayoffStrategyService") as MockSvc:
            MockSvc.get_debt_accounts = AsyncMock(return_value=debts)
            result = await list_debt_accounts(user_id=None, current_user=user, db=mock_db)

        assert len(result) == 1
        assert result[0]["name"] == "Credit Card"
        assert result[0]["balance"] == 5000.0

    @pytest.mark.asyncio
    async def test_empty_debts(self):
        mock_db = AsyncMock()
        user = _mock_user()

        with patch("app.api.v1.debt_payoff.PayoffStrategyService") as MockSvc:
            MockSvc.get_debt_accounts = AsyncMock(return_value=[])
            result = await list_debt_accounts(user_id=None, current_user=user, db=mock_db)

        assert result == []

    @pytest.mark.asyncio
    async def test_with_user_id_filter(self):
        mock_db = AsyncMock()
        user = _mock_user()
        target_user_id = uuid4()

        with (
            patch("app.api.v1.debt_payoff.PayoffStrategyService") as MockSvc,
            patch("app.api.v1.debt_payoff.verify_household_member") as mock_verify,
        ):
            mock_verify.return_value = None
            MockSvc.get_debt_accounts = AsyncMock(return_value=[])
            await list_debt_accounts(user_id=target_user_id, current_user=user, db=mock_db)

        mock_verify.assert_awaited_once()


@pytest.mark.unit
class TestComparePayoffStrategies:
    @pytest.mark.asyncio
    async def test_returns_comparison(self):
        mock_db = AsyncMock()
        user = _mock_user()
        comparison = {"snowball": {}, "avalanche": {}, "current": {}}

        with patch("app.api.v1.debt_payoff.PayoffStrategyService") as MockSvc:
            MockSvc.compare_strategies = AsyncMock(return_value=comparison)
            result = await compare_payoff_strategies(
                extra_payment=Decimal("200"),
                user_id=None,
                account_ids=None,
                current_user=user,
                db=mock_db,
            )

        assert result == comparison

    @pytest.mark.asyncio
    async def test_with_user_id_filter(self):
        mock_db = AsyncMock()
        user = _mock_user()

        with (
            patch("app.api.v1.debt_payoff.PayoffStrategyService") as MockSvc,
            patch("app.api.v1.debt_payoff.verify_household_member") as mock_verify,
        ):
            mock_verify.return_value = None
            MockSvc.compare_strategies = AsyncMock(return_value={})
            await compare_payoff_strategies(
                extra_payment=Decimal("100"),
                user_id=uuid4(),
                account_ids=None,
                current_user=user,
                db=mock_db,
            )

        mock_verify.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_with_account_ids(self):
        mock_db = AsyncMock()
        user = _mock_user()
        aid = uuid4()

        with patch("app.api.v1.debt_payoff.PayoffStrategyService") as MockSvc:
            MockSvc.compare_strategies = AsyncMock(return_value={})
            await compare_payoff_strategies(
                extra_payment=Decimal("100"),
                user_id=None,
                account_ids=str(aid),
                current_user=user,
                db=mock_db,
            )

        call_args = MockSvc.compare_strategies.call_args[0]
        assert call_args[4] == [aid]

    @pytest.mark.asyncio
    async def test_invalid_account_ids_raises_400(self):
        mock_db = AsyncMock()
        user = _mock_user()

        with pytest.raises(HTTPException) as exc_info:
            await compare_payoff_strategies(
                extra_payment=Decimal("100"),
                user_id=None,
                account_ids="not-a-uuid,invalid",
                current_user=user,
                db=mock_db,
            )
        assert exc_info.value.status_code == 400


@pytest.mark.unit
class TestGetDebtSummary:
    @pytest.mark.asyncio
    async def test_with_debts(self):
        mock_db = AsyncMock()
        user = _mock_user()
        debts = [
            _mock_debt("CC1", balance=Decimal("3000"), rate=Decimal("20")),
            _mock_debt("Loan", balance=Decimal("7000"), rate=Decimal("5")),
        ]

        with patch("app.api.v1.debt_payoff.PayoffStrategyService") as MockSvc:
            MockSvc.get_debt_accounts = AsyncMock(return_value=debts)
            result = await get_debt_summary(user_id=None, current_user=user, db=mock_db)

        assert result["total_debt"] == 10000.0
        assert result["debt_count"] == 2
        # Weighted avg: (3000*20 + 7000*5) / 10000 = 95000/10000 = 9.5
        assert result["average_interest_rate"] == 9.5

    @pytest.mark.asyncio
    async def test_no_debts(self):
        mock_db = AsyncMock()
        user = _mock_user()

        with patch("app.api.v1.debt_payoff.PayoffStrategyService") as MockSvc:
            MockSvc.get_debt_accounts = AsyncMock(return_value=[])
            result = await get_debt_summary(user_id=None, current_user=user, db=mock_db)

        assert result["total_debt"] == 0
        assert result["debt_count"] == 0
        assert result["average_interest_rate"] == 0

    @pytest.mark.asyncio
    async def test_with_user_id_filter(self):
        mock_db = AsyncMock()
        user = _mock_user()

        with (
            patch("app.api.v1.debt_payoff.PayoffStrategyService") as MockSvc,
            patch("app.api.v1.debt_payoff.verify_household_member") as mock_verify,
        ):
            mock_verify.return_value = None
            MockSvc.get_debt_accounts = AsyncMock(return_value=[])
            await get_debt_summary(user_id=uuid4(), current_user=user, db=mock_db)

        mock_verify.assert_awaited_once()
