"""Unit tests for contribution API endpoints."""

from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.contributions import (
    create_contribution,
    delete_contribution,
    get_contribution,
    list_contributions,
    update_contribution,
)
from app.models.account import Account
from app.models.user import User


def _mock_user():
    user = Mock(spec=User)
    user.id = uuid4()
    user.organization_id = uuid4()
    return user


def _mock_account():
    account = Mock(spec=Account)
    account.id = uuid4()
    account.organization_id = uuid4()
    return account


def _mock_contribution_create():
    """Mock ContributionCreate schema."""
    c = Mock()
    c.model_dump.return_value = {
        "amount": Decimal("500.00"),
        "frequency": "monthly",
        "is_active": True,
    }
    return c


def _mock_contribution_update():
    c = Mock()
    c.model_dump.return_value = {"amount": Decimal("600.00")}
    return c


@pytest.mark.unit
class TestCreateContribution:
    @pytest.mark.asyncio
    async def test_creates_contribution(self):
        mock_db = AsyncMock()
        user = _mock_user()
        account = _mock_account()

        with patch("app.api.v1.contributions.AccountContribution") as MockModel:
            MockModel.return_value = Mock()
            await create_contribution(
                contribution_data=_mock_contribution_create(),
                account=account,
                current_user=user,
                db=mock_db,
            )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()


@pytest.mark.unit
class TestListContributions:
    @pytest.mark.asyncio
    async def test_list_active_only(self):
        mock_db = AsyncMock()
        user = _mock_user()
        account = _mock_account()
        contributions = [Mock(), Mock()]

        scalars_mock = Mock()
        scalars_mock.all.return_value = contributions
        result_mock = Mock()
        result_mock.scalars.return_value = scalars_mock
        mock_db.execute.return_value = result_mock

        result = await list_contributions(
            include_inactive=False,
            account=account,
            current_user=user,
            db=mock_db,
        )

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_include_inactive(self):
        mock_db = AsyncMock()
        user = _mock_user()
        account = _mock_account()

        scalars_mock = Mock()
        scalars_mock.all.return_value = []
        result_mock = Mock()
        result_mock.scalars.return_value = scalars_mock
        mock_db.execute.return_value = result_mock

        result = await list_contributions(
            include_inactive=True,
            account=account,
            current_user=user,
            db=mock_db,
        )

        assert result == []


@pytest.mark.unit
class TestGetContribution:
    @pytest.mark.asyncio
    async def test_found(self):
        mock_db = AsyncMock()
        user = _mock_user()
        contribution = Mock()

        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = contribution
        mock_db.execute.return_value = result_mock

        result = await get_contribution(contribution_id=uuid4(), current_user=user, db=mock_db)

        assert result == contribution

    @pytest.mark.asyncio
    async def test_not_found_raises_404(self):
        mock_db = AsyncMock()
        user = _mock_user()

        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock

        with pytest.raises(HTTPException) as exc_info:
            await get_contribution(contribution_id=uuid4(), current_user=user, db=mock_db)
        assert exc_info.value.status_code == 404


@pytest.mark.unit
class TestUpdateContribution:
    @pytest.mark.asyncio
    async def test_update_success(self):
        mock_db = AsyncMock()
        user = _mock_user()
        contribution = Mock()

        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = contribution
        mock_db.execute.return_value = result_mock

        update_data = Mock()
        update_data.model_dump.return_value = {"amount": Decimal("600.00")}

        await update_contribution(
            contribution_id=uuid4(),
            contribution_update=update_data,
            current_user=user,
            db=mock_db,
        )

        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_not_found(self):
        mock_db = AsyncMock()
        user = _mock_user()

        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock

        update_data = Mock()
        update_data.model_dump.return_value = {}

        with pytest.raises(HTTPException) as exc_info:
            await update_contribution(
                contribution_id=uuid4(),
                contribution_update=update_data,
                current_user=user,
                db=mock_db,
            )
        assert exc_info.value.status_code == 404


@pytest.mark.unit
class TestDeleteContribution:
    @pytest.mark.asyncio
    async def test_delete_success(self):
        mock_db = AsyncMock()
        user = _mock_user()
        contribution = Mock()

        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = contribution
        mock_db.execute.return_value = result_mock

        result = await delete_contribution(contribution_id=uuid4(), current_user=user, db=mock_db)

        mock_db.delete.assert_awaited_once_with(contribution)
        mock_db.commit.assert_awaited_once()
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_not_found(self):
        mock_db = AsyncMock()
        user = _mock_user()

        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock

        with pytest.raises(HTTPException) as exc_info:
            await delete_contribution(contribution_id=uuid4(), current_user=user, db=mock_db)
        assert exc_info.value.status_code == 404
