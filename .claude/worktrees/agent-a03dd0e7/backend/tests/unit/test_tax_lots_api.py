"""Tests for app.api.v1.tax_lots API endpoints."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.tax_lots import (
    _get_verified_holding,
    create_tax_lot,
    get_realized_gains,
    get_unrealized_gains,
    import_lots_from_holding,
    list_tax_lots,
    record_sale,
    update_cost_basis_method,
)


class TestGetVerifiedHolding:
    """Test the _get_verified_holding helper."""

    @pytest.mark.asyncio
    async def test_returns_holding_when_found(self):
        db = AsyncMock()
        holding = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = holding
        db.execute = AsyncMock(return_value=mock_result)

        user = MagicMock()
        user.organization_id = uuid4()

        result = await _get_verified_holding(uuid4(), user, db)
        assert result is holding

    @pytest.mark.asyncio
    async def test_raises_404_when_not_found(self):
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)

        user = MagicMock()
        user.organization_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await _get_verified_holding(uuid4(), user, db)
        assert exc_info.value.status_code == 404


class TestListTaxLots:
    """Test list_tax_lots endpoint."""

    @pytest.mark.asyncio
    async def test_list_tax_lots_success(self):
        holding_id = uuid4()
        db = AsyncMock()
        user = MagicMock()
        user.organization_id = uuid4()

        mock_lots = [MagicMock(), MagicMock()]

        with patch(
            "app.api.v1.tax_lots._get_verified_holding",
            new_callable=AsyncMock,
        ):
            with patch(
                "app.api.v1.tax_lots.tax_lot_service.get_lots",
                new_callable=AsyncMock,
                return_value=mock_lots,
            ):
                result = await list_tax_lots(
                    holding_id=holding_id,
                    include_closed=False,
                    current_user=user,
                    db=db,
                )
                assert result == mock_lots


class TestCreateTaxLot:
    """Test create_tax_lot endpoint."""

    @pytest.mark.asyncio
    async def test_create_tax_lot_success(self):
        from datetime import date

        holding_id = uuid4()
        db = AsyncMock()
        user = MagicMock()
        user.organization_id = uuid4()

        mock_holding = MagicMock()
        mock_holding.id = holding_id
        mock_holding.account_id = uuid4()

        mock_lot = MagicMock()

        body = MagicMock()
        body.quantity = Decimal("100")
        body.cost_basis_per_share = Decimal("50.00")
        body.acquisition_date = date(2024, 1, 1)

        with patch(
            "app.api.v1.tax_lots._get_verified_holding",
            new_callable=AsyncMock,
            return_value=mock_holding,
        ):
            with patch(
                "app.api.v1.tax_lots.tax_lot_service.record_purchase",
                new_callable=AsyncMock,
                return_value=mock_lot,
            ):
                result = await create_tax_lot(
                    body=body,
                    holding_id=holding_id,
                    current_user=user,
                    db=db,
                )
                assert result is mock_lot
                db.commit.assert_called_once()
                db.refresh.assert_called_once_with(mock_lot)


class TestRecordSale:
    """Test record_sale endpoint."""

    @pytest.mark.asyncio
    async def test_record_sale_success_default_method(self):
        from datetime import date

        holding_id = uuid4()
        db = AsyncMock()
        user = MagicMock()
        user.organization_id = uuid4()

        mock_holding = MagicMock()
        mock_holding.id = holding_id
        mock_holding.account_id = uuid4()

        lot1 = MagicMock()
        sale_result = {
            "total_proceeds": Decimal("5000"),
            "total_cost_basis": Decimal("3000"),
            "realized_gain_loss": Decimal("2000"),
            "short_term_gain_loss": Decimal("2000"),
            "long_term_gain_loss": Decimal("0"),
            "lots_affected": 1,
            "lot_details": [lot1],
        }

        body = MagicMock()
        body.quantity = Decimal("100")
        body.sale_price_per_share = Decimal("50.00")
        body.sale_date = date(2024, 6, 1)
        body.cost_basis_method = None
        body.specific_lot_ids = None

        with patch(
            "app.api.v1.tax_lots._get_verified_holding",
            new_callable=AsyncMock,
            return_value=mock_holding,
        ):
            with patch(
                "app.api.v1.tax_lots.tax_lot_service.record_sale",
                new_callable=AsyncMock,
                return_value=sale_result,
            ):
                result = await record_sale(
                    body=body,
                    holding_id=holding_id,
                    current_user=user,
                    db=db,
                )
                assert result == sale_result

    @pytest.mark.asyncio
    async def test_record_sale_invalid_method(self):
        from datetime import date

        holding_id = uuid4()
        db = AsyncMock()
        user = MagicMock()
        user.organization_id = uuid4()

        mock_holding = MagicMock()
        mock_holding.id = holding_id
        mock_holding.account_id = uuid4()

        body = MagicMock()
        body.quantity = Decimal("100")
        body.sale_price_per_share = Decimal("50.00")
        body.sale_date = date(2024, 6, 1)
        body.cost_basis_method = "invalid_method"
        body.specific_lot_ids = None

        with patch(
            "app.api.v1.tax_lots._get_verified_holding",
            new_callable=AsyncMock,
            return_value=mock_holding,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await record_sale(
                    body=body,
                    holding_id=holding_id,
                    current_user=user,
                    db=db,
                )
            assert exc_info.value.status_code == 400
            assert "Invalid cost basis method" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_record_sale_specific_id_without_lot_ids(self):
        from datetime import date

        holding_id = uuid4()
        db = AsyncMock()
        user = MagicMock()
        user.organization_id = uuid4()

        mock_holding = MagicMock()
        mock_holding.id = holding_id
        mock_holding.account_id = uuid4()

        body = MagicMock()
        body.quantity = Decimal("100")
        body.sale_price_per_share = Decimal("50.00")
        body.sale_date = date(2024, 6, 1)
        body.cost_basis_method = "specific_id"
        body.specific_lot_ids = None

        with patch(
            "app.api.v1.tax_lots._get_verified_holding",
            new_callable=AsyncMock,
            return_value=mock_holding,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await record_sale(
                    body=body,
                    holding_id=holding_id,
                    current_user=user,
                    db=db,
                )
            assert exc_info.value.status_code == 400
            assert "specific_lot_ids required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_record_sale_value_error_from_service(self):
        from datetime import date

        holding_id = uuid4()
        db = AsyncMock()
        user = MagicMock()
        user.organization_id = uuid4()

        mock_holding = MagicMock()
        mock_holding.id = holding_id
        mock_holding.account_id = uuid4()

        body = MagicMock()
        body.quantity = Decimal("10000")
        body.sale_price_per_share = Decimal("50.00")
        body.sale_date = date(2024, 6, 1)
        body.cost_basis_method = "fifo"
        body.specific_lot_ids = None

        with patch(
            "app.api.v1.tax_lots._get_verified_holding",
            new_callable=AsyncMock,
            return_value=mock_holding,
        ):
            with patch(
                "app.api.v1.tax_lots.tax_lot_service.record_sale",
                new_callable=AsyncMock,
                side_effect=ValueError("Insufficient quantity"),
            ):
                with pytest.raises(HTTPException) as exc_info:
                    await record_sale(
                        body=body,
                        holding_id=holding_id,
                        current_user=user,
                        db=db,
                    )
                assert exc_info.value.status_code == 400


class TestImportLotsFromHolding:
    """Test import_lots_from_holding endpoint."""

    @pytest.mark.asyncio
    async def test_import_lots_success(self):
        holding_id = uuid4()
        db = AsyncMock()
        user = MagicMock()
        user.organization_id = uuid4()

        mock_lot = MagicMock()

        with patch(
            "app.api.v1.tax_lots._get_verified_holding",
            new_callable=AsyncMock,
        ):
            with patch(
                "app.api.v1.tax_lots.tax_lot_service.import_lots_from_holding",
                new_callable=AsyncMock,
                return_value=mock_lot,
            ):
                result = await import_lots_from_holding(
                    holding_id=holding_id,
                    current_user=user,
                    db=db,
                )
                assert result is mock_lot
                db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_import_lots_409_when_already_exist(self):
        holding_id = uuid4()
        db = AsyncMock()
        user = MagicMock()
        user.organization_id = uuid4()

        with patch(
            "app.api.v1.tax_lots._get_verified_holding",
            new_callable=AsyncMock,
        ):
            with patch(
                "app.api.v1.tax_lots.tax_lot_service.import_lots_from_holding",
                new_callable=AsyncMock,
                return_value=None,
            ):
                with pytest.raises(HTTPException) as exc_info:
                    await import_lots_from_holding(
                        holding_id=holding_id,
                        current_user=user,
                        db=db,
                    )
                assert exc_info.value.status_code == 409


class TestGetUnrealizedGains:
    """Test get_unrealized_gains endpoint."""

    @pytest.mark.asyncio
    async def test_success(self):
        account_id = uuid4()
        db = AsyncMock()
        user = MagicMock()
        user.organization_id = uuid4()

        mock_account = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_account
        db.execute = AsyncMock(return_value=mock_result)

        mock_summary = MagicMock()

        with patch(
            "app.api.v1.tax_lots.tax_lot_service.get_unrealized_gains",
            new_callable=AsyncMock,
            return_value=mock_summary,
        ):
            result = await get_unrealized_gains(
                account_id=account_id,
                current_user=user,
                db=db,
            )
            assert result is mock_summary

    @pytest.mark.asyncio
    async def test_account_not_found(self):
        db = AsyncMock()
        user = MagicMock()
        user.organization_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await get_unrealized_gains(
                account_id=uuid4(),
                current_user=user,
                db=db,
            )
        assert exc_info.value.status_code == 404


class TestGetRealizedGains:
    """Test get_realized_gains endpoint."""

    @pytest.mark.asyncio
    async def test_success(self):
        account_id = uuid4()
        db = AsyncMock()
        user = MagicMock()
        user.organization_id = uuid4()

        mock_account = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_account
        db.execute = AsyncMock(return_value=mock_result)

        mock_summary = MagicMock()

        with patch(
            "app.api.v1.tax_lots.tax_lot_service.get_realized_gains_summary",
            new_callable=AsyncMock,
            return_value=mock_summary,
        ):
            result = await get_realized_gains(
                account_id=account_id,
                year=2024,
                current_user=user,
                db=db,
            )
            assert result is mock_summary

    @pytest.mark.asyncio
    async def test_account_not_found(self):
        db = AsyncMock()
        user = MagicMock()
        user.organization_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await get_realized_gains(
                account_id=uuid4(),
                year=2024,
                current_user=user,
                db=db,
            )
        assert exc_info.value.status_code == 404


class TestUpdateCostBasisMethod:
    """Test update_cost_basis_method endpoint."""

    @pytest.mark.asyncio
    async def test_success(self):
        account_id = uuid4()
        db = AsyncMock()
        user = MagicMock()
        user.organization_id = uuid4()

        mock_account = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_account
        db.execute = AsyncMock(return_value=mock_result)

        body = MagicMock()
        body.cost_basis_method = "fifo"

        result = await update_cost_basis_method(
            body=body,
            account_id=account_id,
            current_user=user,
            db=db,
        )
        assert result["account_id"] == str(account_id)
        assert result["cost_basis_method"] == "fifo"
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_method(self):
        db = AsyncMock()
        user = MagicMock()
        user.organization_id = uuid4()

        body = MagicMock()
        body.cost_basis_method = "invalid_method"

        with pytest.raises(HTTPException) as exc_info:
            await update_cost_basis_method(
                body=body,
                account_id=uuid4(),
                current_user=user,
                db=db,
            )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_account_not_found(self):
        db = AsyncMock()
        user = MagicMock()
        user.organization_id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)

        body = MagicMock()
        body.cost_basis_method = "fifo"

        with pytest.raises(HTTPException) as exc_info:
            await update_cost_basis_method(
                body=body,
                account_id=uuid4(),
                current_user=user,
                db=db,
            )
        assert exc_info.value.status_code == 404
