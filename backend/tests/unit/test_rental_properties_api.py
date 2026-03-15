"""Unit tests for rental properties API endpoints."""

from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.rental_properties import (
    RentalFieldsUpdate,
    get_properties_summary,
    get_property_pnl,
    list_rental_properties,
    update_rental_fields,
)
from app.models.user import User


def _mock_user():
    user = Mock(spec=User)
    user.id = uuid4()
    user.organization_id = uuid4()
    return user


@pytest.mark.unit
class TestListRentalProperties:
    @pytest.mark.asyncio
    async def test_returns_properties(self):
        mock_db = AsyncMock()
        user = _mock_user()
        properties = [{"account_id": str(uuid4()), "name": "Beach House"}]

        with patch("app.api.v1.rental_properties.RentalPropertyService") as MockSvc:
            instance = MockSvc.return_value
            instance.get_rental_properties = AsyncMock(return_value=properties)
            result = await list_rental_properties(user_id=None, current_user=user, db=mock_db)

        assert result == properties
        instance.get_rental_properties.assert_awaited_once_with(user.organization_id, None)

    @pytest.mark.asyncio
    async def test_with_user_id_calls_verify_household_member(self):
        mock_db = AsyncMock()
        user = _mock_user()
        target_user_id = uuid4()

        with (
            patch("app.api.v1.rental_properties.RentalPropertyService") as MockSvc,
            patch("app.api.v1.rental_properties.verify_household_member") as mock_verify,
        ):
            mock_verify.return_value = None
            instance = MockSvc.return_value
            instance.get_rental_properties = AsyncMock(return_value=[])
            await list_rental_properties(user_id=target_user_id, current_user=user, db=mock_db)

        mock_verify.assert_awaited_once_with(mock_db, target_user_id, user.organization_id)
        instance.get_rental_properties.assert_awaited_once_with(
            user.organization_id, target_user_id
        )

    @pytest.mark.asyncio
    async def test_without_user_id_skips_verify(self):
        mock_db = AsyncMock()
        user = _mock_user()

        with (
            patch("app.api.v1.rental_properties.RentalPropertyService") as MockSvc,
            patch("app.api.v1.rental_properties.verify_household_member") as mock_verify,
        ):
            instance = MockSvc.return_value
            instance.get_rental_properties = AsyncMock(return_value=[])
            await list_rental_properties(user_id=None, current_user=user, db=mock_db)

        mock_verify.assert_not_awaited()


@pytest.mark.unit
class TestGetPropertiesSummary:
    @pytest.mark.asyncio
    async def test_returns_summary(self):
        mock_db = AsyncMock()
        user = _mock_user()
        summary = {
            "total_income": Decimal("24000"),
            "total_expenses": Decimal("18000"),
            "net_income": Decimal("6000"),
        }

        with patch("app.api.v1.rental_properties.RentalPropertyService") as MockSvc:
            instance = MockSvc.return_value
            instance.get_all_properties_summary = AsyncMock(return_value=summary)
            result = await get_properties_summary(
                year=2025, user_id=None, current_user=user, db=mock_db
            )

        assert result == summary
        instance.get_all_properties_summary.assert_awaited_once_with(
            user.organization_id, 2025, None
        )

    @pytest.mark.asyncio
    async def test_defaults_year_to_current(self):
        mock_db = AsyncMock()
        user = _mock_user()

        with (
            patch("app.api.v1.rental_properties.RentalPropertyService") as MockSvc,
            patch("app.api.v1.rental_properties.date") as mock_date,
        ):
            mock_date.today.return_value.year = 2026
            instance = MockSvc.return_value
            instance.get_all_properties_summary = AsyncMock(return_value={})
            await get_properties_summary(year=None, user_id=None, current_user=user, db=mock_db)

        instance.get_all_properties_summary.assert_awaited_once_with(
            user.organization_id, 2026, None
        )

    @pytest.mark.asyncio
    async def test_with_user_id_calls_verify(self):
        mock_db = AsyncMock()
        user = _mock_user()
        target_user_id = uuid4()

        with (
            patch("app.api.v1.rental_properties.RentalPropertyService") as MockSvc,
            patch("app.api.v1.rental_properties.verify_household_member") as mock_verify,
        ):
            mock_verify.return_value = None
            instance = MockSvc.return_value
            instance.get_all_properties_summary = AsyncMock(return_value={})
            await get_properties_summary(
                year=2025, user_id=target_user_id, current_user=user, db=mock_db
            )

        mock_verify.assert_awaited_once_with(mock_db, target_user_id, user.organization_id)


@pytest.mark.unit
class TestGetPropertyPnl:
    @pytest.mark.asyncio
    async def test_returns_pnl(self):
        mock_db = AsyncMock()
        user = _mock_user()
        account_id = uuid4()
        pnl_data = {
            "gross_income": Decimal("12000"),
            "total_expenses": Decimal("8000"),
            "net_income": Decimal("4000"),
        }

        with patch("app.api.v1.rental_properties.RentalPropertyService") as MockSvc:
            instance = MockSvc.return_value
            instance.get_property_pnl = AsyncMock(return_value=pnl_data)
            result = await get_property_pnl(
                account_id=account_id, year=2025, current_user=user, db=mock_db
            )

        assert result == pnl_data
        instance.get_property_pnl.assert_awaited_once_with(user.organization_id, account_id, 2025)

    @pytest.mark.asyncio
    async def test_defaults_year_to_current(self):
        mock_db = AsyncMock()
        user = _mock_user()
        account_id = uuid4()

        with (
            patch("app.api.v1.rental_properties.RentalPropertyService") as MockSvc,
            patch("app.api.v1.rental_properties.date") as mock_date,
        ):
            mock_date.today.return_value.year = 2026
            instance = MockSvc.return_value
            instance.get_property_pnl = AsyncMock(return_value={})
            await get_property_pnl(account_id=account_id, year=None, current_user=user, db=mock_db)

        instance.get_property_pnl.assert_awaited_once_with(user.organization_id, account_id, 2026)

    @pytest.mark.asyncio
    async def test_raises_404_when_error_in_result(self):
        mock_db = AsyncMock()
        user = _mock_user()
        account_id = uuid4()

        with patch("app.api.v1.rental_properties.RentalPropertyService") as MockSvc:
            instance = MockSvc.return_value
            instance.get_property_pnl = AsyncMock(return_value={"error": "Property not found"})

            with pytest.raises(HTTPException) as exc_info:
                await get_property_pnl(
                    account_id=account_id, year=2025, current_user=user, db=mock_db
                )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Property not found"


@pytest.mark.unit
class TestUpdateRentalFields:
    @pytest.mark.asyncio
    async def test_updates_successfully(self):
        mock_db = AsyncMock()
        user = _mock_user()
        account_id = uuid4()
        body = RentalFieldsUpdate(
            is_rental_property=True,
            rental_monthly_income=Decimal("2000"),
            rental_address="123 Main St",
        )
        updated = {"account_id": str(account_id), "is_rental_property": True}

        with patch("app.api.v1.rental_properties.RentalPropertyService") as MockSvc:
            instance = MockSvc.return_value
            instance.update_rental_fields = AsyncMock(return_value=updated)
            result = await update_rental_fields(
                account_id=account_id, body=body, current_user=user, db=mock_db
            )

        assert result == updated
        instance.update_rental_fields.assert_awaited_once_with(
            organization_id=user.organization_id,
            account_id=account_id,
            is_rental_property=True,
            rental_monthly_income=Decimal("2000"),
            rental_address="123 Main St",
        )

    @pytest.mark.asyncio
    async def test_raises_404_when_error_in_result(self):
        mock_db = AsyncMock()
        user = _mock_user()
        account_id = uuid4()
        body = RentalFieldsUpdate(is_rental_property=True)

        with patch("app.api.v1.rental_properties.RentalPropertyService") as MockSvc:
            instance = MockSvc.return_value
            instance.update_rental_fields = AsyncMock(return_value={"error": "Account not found"})

            with pytest.raises(HTTPException) as exc_info:
                await update_rental_fields(
                    account_id=account_id, body=body, current_user=user, db=mock_db
                )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Account not found"

    @pytest.mark.asyncio
    async def test_partial_update_with_none_fields(self):
        mock_db = AsyncMock()
        user = _mock_user()
        account_id = uuid4()
        body = RentalFieldsUpdate(rental_address="456 Oak Ave")
        updated = {"account_id": str(account_id), "rental_address": "456 Oak Ave"}

        with patch("app.api.v1.rental_properties.RentalPropertyService") as MockSvc:
            instance = MockSvc.return_value
            instance.update_rental_fields = AsyncMock(return_value=updated)
            result = await update_rental_fields(
                account_id=account_id, body=body, current_user=user, db=mock_db
            )

        assert result == updated
        instance.update_rental_fields.assert_awaited_once_with(
            organization_id=user.organization_id,
            account_id=account_id,
            is_rental_property=None,
            rental_monthly_income=None,
            rental_address="456 Oak Ave",
        )
