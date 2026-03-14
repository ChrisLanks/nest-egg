"""Unit tests for app/services/tax_lot_service.py."""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.tax_lot import CostBasisMethod
from app.services.tax_lot_service import (
    TaxLotService,
    _determine_holding_period,
    tax_lot_service,
)


def _make_lot(
    lot_id=None,
    holding_id=None,
    org_id=None,
    account_id=None,
    acquisition_date=None,
    quantity=Decimal("10"),
    cost_basis_per_share=Decimal("100"),
    remaining_quantity=None,
    is_closed=False,
    closed_at=None,
    sale_proceeds=None,
    realized_gain_loss=None,
    holding_period=None,
):
    lot = MagicMock()
    lot.id = lot_id or uuid4()
    lot.holding_id = holding_id or uuid4()
    lot.organization_id = org_id or uuid4()
    lot.account_id = account_id or uuid4()
    lot.acquisition_date = acquisition_date or date(2023, 1, 15)
    lot.quantity = quantity
    lot.cost_basis_per_share = cost_basis_per_share
    lot.total_cost_basis = (quantity * cost_basis_per_share).quantize(Decimal("0.01"))
    lot.remaining_quantity = remaining_quantity if remaining_quantity is not None else quantity
    lot.is_closed = is_closed
    lot.closed_at = closed_at
    lot.sale_proceeds = sale_proceeds
    lot.realized_gain_loss = realized_gain_loss
    lot.holding_period = holding_period
    return lot


def _make_holding(
    holding_id=None,
    org_id=None,
    account_id=None,
    ticker="AAPL",
    shares=Decimal("10"),
    cost_basis_per_share=Decimal("150"),
    current_price_per_share=Decimal("175"),
    created_at=None,
):
    h = MagicMock()
    h.id = holding_id or uuid4()
    h.organization_id = org_id or uuid4()
    h.account_id = account_id or uuid4()
    h.ticker = ticker
    h.shares = shares
    h.cost_basis_per_share = cost_basis_per_share
    h.current_price_per_share = current_price_per_share
    h.created_at = created_at or datetime(2023, 6, 1, 12, 0, 0)
    return h


@pytest.mark.unit
class TestDetermineHoldingPeriod:
    def test_short_term_one_day(self):
        assert _determine_holding_period(date(2024, 1, 1), date(2024, 1, 2)) == "SHORT_TERM"

    def test_short_term_365_days(self):
        assert _determine_holding_period(date(2024, 1, 1), date(2024, 12, 31)) == "SHORT_TERM"

    def test_long_term_366_days(self):
        assert _determine_holding_period(date(2023, 1, 1), date(2024, 1, 2)) == "LONG_TERM"

    def test_long_term_multiple_years(self):
        assert _determine_holding_period(date(2020, 1, 1), date(2024, 6, 15)) == "LONG_TERM"

    def test_same_day(self):
        assert _determine_holding_period(date(2024, 6, 1), date(2024, 6, 1)) == "SHORT_TERM"


@pytest.mark.unit
class TestRecordPurchase:
    @pytest.mark.asyncio
    async def test_creates_lot_and_flushes(self):
        svc = TaxLotService()
        db = AsyncMock()
        org_id, holding_id, account_id = uuid4(), uuid4(), uuid4()

        await svc.record_purchase(
            db=db,
            org_id=org_id,
            holding_id=holding_id,
            account_id=account_id,
            quantity=Decimal("5"),
            price_per_share=Decimal("150.00"),
            acquisition_date=date(2024, 3, 1),
        )

        db.add.assert_called_once()
        db.flush.assert_awaited_once()
        db.refresh.assert_awaited_once()
        added = db.add.call_args[0][0]
        assert added.organization_id == org_id
        assert added.holding_id == holding_id
        assert added.quantity == Decimal("5")
        assert added.total_cost_basis == Decimal("750.00")
        assert added.remaining_quantity == Decimal("5")
        assert added.is_closed is False

    @pytest.mark.asyncio
    async def test_cost_basis_rounds_to_cents(self):
        svc = TaxLotService()
        db = AsyncMock()
        await svc.record_purchase(
            db=db,
            org_id=uuid4(),
            holding_id=uuid4(),
            account_id=uuid4(),
            quantity=Decimal("3"),
            price_per_share=Decimal("33.333"),
            acquisition_date=date(2024, 1, 1),
        )
        added = db.add.call_args[0][0]
        assert added.total_cost_basis == Decimal("100.00")


@pytest.mark.unit
class TestRecordSaleFIFO:
    @pytest.mark.asyncio
    async def test_fifo_sells_oldest_first(self):
        svc = TaxLotService()
        db = AsyncMock()
        org_id, holding_id, account_id = uuid4(), uuid4(), uuid4()

        lot_old = _make_lot(
            org_id=org_id,
            holding_id=holding_id,
            account_id=account_id,
            acquisition_date=date(2022, 1, 1),
            cost_basis_per_share=Decimal("50"),
            remaining_quantity=Decimal("10"),
        )
        lot_new = _make_lot(
            org_id=org_id,
            holding_id=holding_id,
            account_id=account_id,
            acquisition_date=date(2024, 1, 1),
            cost_basis_per_share=Decimal("100"),
            remaining_quantity=Decimal("10"),
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [lot_new, lot_old]
        db.execute = AsyncMock(return_value=mock_result)

        result = await svc.record_sale(
            db=db,
            org_id=org_id,
            holding_id=holding_id,
            account_id=account_id,
            quantity=Decimal("5"),
            sale_price_per_share=Decimal("75"),
            sale_date=date(2024, 6, 1),
            method=CostBasisMethod.FIFO,
        )

        assert lot_old.remaining_quantity == Decimal("5")
        assert result["lots_affected"] == 1
        assert result["total_proceeds"] == Decimal("375.00")
        assert result["total_cost_basis"] == Decimal("250.00")
        assert result["realized_gain_loss"] == Decimal("125.00")

    @pytest.mark.asyncio
    async def test_fifo_spans_multiple_lots(self):
        svc = TaxLotService()
        db = AsyncMock()
        org_id, holding_id, account_id = uuid4(), uuid4(), uuid4()

        lot1 = _make_lot(
            org_id=org_id,
            holding_id=holding_id,
            account_id=account_id,
            acquisition_date=date(2022, 1, 1),
            quantity=Decimal("3"),
            cost_basis_per_share=Decimal("50"),
            remaining_quantity=Decimal("3"),
        )
        lot2 = _make_lot(
            org_id=org_id,
            holding_id=holding_id,
            account_id=account_id,
            acquisition_date=date(2023, 6, 1),
            quantity=Decimal("10"),
            cost_basis_per_share=Decimal("80"),
            remaining_quantity=Decimal("10"),
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [lot1, lot2]
        db.execute = AsyncMock(return_value=mock_result)

        result = await svc.record_sale(
            db=db,
            org_id=org_id,
            holding_id=holding_id,
            account_id=account_id,
            quantity=Decimal("5"),
            sale_price_per_share=Decimal("100"),
            sale_date=date(2024, 6, 1),
            method=CostBasisMethod.FIFO,
        )

        assert lot1.remaining_quantity == Decimal("0")
        assert lot1.is_closed is True
        assert lot2.remaining_quantity == Decimal("8")
        assert result["lots_affected"] == 2
        assert result["total_proceeds"] == Decimal("500.00")
        assert result["total_cost_basis"] == Decimal("310.00")


@pytest.mark.unit
class TestRecordSaleLIFO:
    @pytest.mark.asyncio
    async def test_lifo_sells_newest_first(self):
        svc = TaxLotService()
        db = AsyncMock()
        org_id, holding_id, account_id = uuid4(), uuid4(), uuid4()

        lot_old = _make_lot(
            org_id=org_id,
            holding_id=holding_id,
            account_id=account_id,
            acquisition_date=date(2022, 1, 1),
            cost_basis_per_share=Decimal("50"),
            remaining_quantity=Decimal("10"),
        )
        lot_new = _make_lot(
            org_id=org_id,
            holding_id=holding_id,
            account_id=account_id,
            acquisition_date=date(2024, 1, 1),
            cost_basis_per_share=Decimal("100"),
            remaining_quantity=Decimal("10"),
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [lot_old, lot_new]
        db.execute = AsyncMock(return_value=mock_result)

        result = await svc.record_sale(
            db=db,
            org_id=org_id,
            holding_id=holding_id,
            account_id=account_id,
            quantity=Decimal("5"),
            sale_price_per_share=Decimal("120"),
            sale_date=date(2024, 6, 1),
            method=CostBasisMethod.LIFO,
        )

        assert lot_new.remaining_quantity == Decimal("5")
        assert lot_old.remaining_quantity == Decimal("10")
        assert result["total_cost_basis"] == Decimal("500.00")
        assert result["total_proceeds"] == Decimal("600.00")


@pytest.mark.unit
class TestRecordSaleHIFO:
    @pytest.mark.asyncio
    async def test_hifo_sells_highest_cost_first(self):
        svc = TaxLotService()
        db = AsyncMock()
        org_id, holding_id, account_id = uuid4(), uuid4(), uuid4()

        lot_low = _make_lot(
            org_id=org_id,
            holding_id=holding_id,
            account_id=account_id,
            acquisition_date=date(2022, 1, 1),
            cost_basis_per_share=Decimal("50"),
            remaining_quantity=Decimal("10"),
        )
        lot_high = _make_lot(
            org_id=org_id,
            holding_id=holding_id,
            account_id=account_id,
            acquisition_date=date(2023, 1, 1),
            cost_basis_per_share=Decimal("200"),
            remaining_quantity=Decimal("10"),
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [lot_low, lot_high]
        db.execute = AsyncMock(return_value=mock_result)

        result = await svc.record_sale(
            db=db,
            org_id=org_id,
            holding_id=holding_id,
            account_id=account_id,
            quantity=Decimal("5"),
            sale_price_per_share=Decimal("150"),
            sale_date=date(2024, 6, 1),
            method=CostBasisMethod.HIFO,
        )

        assert lot_high.remaining_quantity == Decimal("5")
        assert lot_low.remaining_quantity == Decimal("10")
        assert result["total_cost_basis"] == Decimal("1000.00")
        assert result["realized_gain_loss"] == Decimal("-250.00")


@pytest.mark.unit
class TestRecordSaleSpecificID:
    @pytest.mark.asyncio
    async def test_specific_id_uses_selected_lots(self):
        svc = TaxLotService()
        db = AsyncMock()
        org_id, holding_id, account_id, lot_id = uuid4(), uuid4(), uuid4(), uuid4()

        lot = _make_lot(
            lot_id=lot_id,
            org_id=org_id,
            holding_id=holding_id,
            account_id=account_id,
            acquisition_date=date(2023, 6, 1),
            cost_basis_per_share=Decimal("80"),
            remaining_quantity=Decimal("10"),
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [lot]
        db.execute = AsyncMock(return_value=mock_result)

        result = await svc.record_sale(
            db=db,
            org_id=org_id,
            holding_id=holding_id,
            account_id=account_id,
            quantity=Decimal("4"),
            sale_price_per_share=Decimal("100"),
            sale_date=date(2024, 6, 1),
            method=CostBasisMethod.SPECIFIC_ID,
            specific_lot_ids=[lot_id],
        )

        assert lot.remaining_quantity == Decimal("6")
        assert result["total_proceeds"] == Decimal("400.00")
        assert result["total_cost_basis"] == Decimal("320.00")


@pytest.mark.unit
class TestRecordSaleDefaultMethod:
    @pytest.mark.asyncio
    async def test_uses_account_default_method(self):
        svc = TaxLotService()
        db = AsyncMock()
        org_id, holding_id, account_id = uuid4(), uuid4(), uuid4()

        lot = _make_lot(
            org_id=org_id,
            holding_id=holding_id,
            account_id=account_id,
            acquisition_date=date(2023, 1, 1),
            cost_basis_per_share=Decimal("100"),
            remaining_quantity=Decimal("10"),
        )

        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = "fifo"
        lots_result = MagicMock()
        lots_result.scalars.return_value.all.return_value = [lot]
        db.execute = AsyncMock(side_effect=[account_result, lots_result])

        result = await svc.record_sale(
            db=db,
            org_id=org_id,
            holding_id=holding_id,
            account_id=account_id,
            quantity=Decimal("2"),
            sale_price_per_share=Decimal("120"),
            sale_date=date(2024, 6, 1),
            method=None,
        )

        assert result["lots_affected"] == 1
        assert result["total_proceeds"] == Decimal("240.00")

    @pytest.mark.asyncio
    async def test_defaults_to_fifo_when_no_account_method(self):
        svc = TaxLotService()
        db = AsyncMock()
        org_id, holding_id, account_id = uuid4(), uuid4(), uuid4()

        lot = _make_lot(
            org_id=org_id,
            holding_id=holding_id,
            account_id=account_id,
            acquisition_date=date(2023, 1, 1),
            cost_basis_per_share=Decimal("100"),
            remaining_quantity=Decimal("10"),
        )

        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = None
        lots_result = MagicMock()
        lots_result.scalars.return_value.all.return_value = [lot]
        db.execute = AsyncMock(side_effect=[account_result, lots_result])

        result = await svc.record_sale(
            db=db,
            org_id=org_id,
            holding_id=holding_id,
            account_id=account_id,
            quantity=Decimal("2"),
            sale_price_per_share=Decimal("120"),
            sale_date=date(2024, 6, 1),
            method=None,
        )

        assert result["lots_affected"] == 1


@pytest.mark.unit
class TestRecordSaleInsufficientShares:
    @pytest.mark.asyncio
    async def test_raises_when_insufficient(self):
        svc = TaxLotService()
        db = AsyncMock()
        lot = _make_lot(remaining_quantity=Decimal("3"))
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [lot]
        db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="Insufficient shares"):
            await svc.record_sale(
                db=db,
                org_id=uuid4(),
                holding_id=uuid4(),
                account_id=uuid4(),
                quantity=Decimal("10"),
                sale_price_per_share=Decimal("100"),
                sale_date=date(2024, 6, 1),
                method=CostBasisMethod.FIFO,
            )


@pytest.mark.unit
class TestRecordSaleHoldingPeriod:
    @pytest.mark.asyncio
    async def test_short_term_gain(self):
        svc = TaxLotService()
        db = AsyncMock()
        lot = _make_lot(
            acquisition_date=date(2024, 3, 1),
            cost_basis_per_share=Decimal("100"),
            remaining_quantity=Decimal("10"),
        )
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [lot]
        db.execute = AsyncMock(return_value=mock_result)

        result = await svc.record_sale(
            db=db,
            org_id=uuid4(),
            holding_id=uuid4(),
            account_id=uuid4(),
            quantity=Decimal("5"),
            sale_price_per_share=Decimal("120"),
            sale_date=date(2024, 6, 1),
            method=CostBasisMethod.FIFO,
        )

        assert result["short_term_gain_loss"] == Decimal("100.00")
        assert result["long_term_gain_loss"] == Decimal("0")

    @pytest.mark.asyncio
    async def test_long_term_gain(self):
        svc = TaxLotService()
        db = AsyncMock()
        lot = _make_lot(
            acquisition_date=date(2020, 1, 1),
            cost_basis_per_share=Decimal("50"),
            remaining_quantity=Decimal("10"),
        )
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [lot]
        db.execute = AsyncMock(return_value=mock_result)

        result = await svc.record_sale(
            db=db,
            org_id=uuid4(),
            holding_id=uuid4(),
            account_id=uuid4(),
            quantity=Decimal("5"),
            sale_price_per_share=Decimal("100"),
            sale_date=date(2024, 6, 1),
            method=CostBasisMethod.FIFO,
        )

        assert result["long_term_gain_loss"] == Decimal("250.00")
        assert result["short_term_gain_loss"] == Decimal("0")

    @pytest.mark.asyncio
    async def test_lot_fully_closed(self):
        svc = TaxLotService()
        db = AsyncMock()
        lot = _make_lot(
            acquisition_date=date(2023, 1, 1),
            quantity=Decimal("5"),
            cost_basis_per_share=Decimal("100"),
            remaining_quantity=Decimal("5"),
        )
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [lot]
        db.execute = AsyncMock(return_value=mock_result)

        await svc.record_sale(
            db=db,
            org_id=uuid4(),
            holding_id=uuid4(),
            account_id=uuid4(),
            quantity=Decimal("5"),
            sale_price_per_share=Decimal("120"),
            sale_date=date(2024, 6, 1),
            method=CostBasisMethod.FIFO,
        )

        assert lot.remaining_quantity == Decimal("0")
        assert lot.is_closed is True
        assert lot.closed_at is not None


@pytest.mark.unit
class TestGetLots:
    @pytest.mark.asyncio
    async def test_returns_open_lots_by_default(self):
        svc = TaxLotService()
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [_make_lot(), _make_lot()]
        db.execute = AsyncMock(return_value=mock_result)
        result = await svc.get_lots(db=db, holding_id=uuid4())
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_include_closed(self):
        svc = TaxLotService()
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(return_value=mock_result)
        await svc.get_lots(db=db, holding_id=uuid4(), include_closed=True)
        db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_empty_result(self):
        svc = TaxLotService()
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(return_value=mock_result)
        result = await svc.get_lots(db=db, holding_id=uuid4())
        assert result == []


@pytest.mark.unit
class TestGetUnrealizedGains:
    @pytest.mark.asyncio
    async def test_calculates_unrealized_gains(self):
        svc = TaxLotService()
        db = AsyncMock()
        account_id, holding_id = uuid4(), uuid4()

        lot = _make_lot(
            holding_id=holding_id,
            acquisition_date=date(2020, 1, 1),
            cost_basis_per_share=Decimal("100"),
            remaining_quantity=Decimal("10"),
        )
        holding = _make_holding(holding_id=holding_id, current_price_per_share=Decimal("150"))

        lots_result = MagicMock()
        lots_result.scalars.return_value.all.return_value = [lot]
        holdings_result = MagicMock()
        holdings_result.scalars.return_value.all.return_value = [holding]
        db.execute = AsyncMock(side_effect=[lots_result, holdings_result])

        result = await svc.get_unrealized_gains(db=db, account_id=account_id)

        assert result["account_id"] == account_id
        assert result["total_unrealized_gain_loss"] == Decimal("500.00")
        assert result["long_term_unrealized"] == Decimal("500.00")
        assert result["short_term_unrealized"] == Decimal("0")
        assert result["lots"][0]["ticker"] == "AAPL"

    @pytest.mark.asyncio
    async def test_no_current_price(self):
        svc = TaxLotService()
        db = AsyncMock()
        account_id, holding_id = uuid4(), uuid4()

        lot = _make_lot(
            holding_id=holding_id,
            acquisition_date=date(2024, 1, 1),
            remaining_quantity=Decimal("5"),
            cost_basis_per_share=Decimal("100"),
        )
        holding = _make_holding(holding_id=holding_id, current_price_per_share=None)

        lots_result = MagicMock()
        lots_result.scalars.return_value.all.return_value = [lot]
        holdings_result = MagicMock()
        holdings_result.scalars.return_value.all.return_value = [holding]
        db.execute = AsyncMock(side_effect=[lots_result, holdings_result])

        result = await svc.get_unrealized_gains(db=db, account_id=account_id)

        assert result["total_unrealized_gain_loss"] == Decimal("0")
        assert result["lots"][0]["unrealized_gain_loss"] is None

    @pytest.mark.asyncio
    async def test_holding_not_found(self):
        svc = TaxLotService()
        db = AsyncMock()
        lot = _make_lot(
            holding_id=uuid4(), acquisition_date=date(2024, 1, 1), remaining_quantity=Decimal("5")
        )
        lots_result = MagicMock()
        lots_result.scalars.return_value.all.return_value = [lot]
        holdings_result = MagicMock()
        holdings_result.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(side_effect=[lots_result, holdings_result])

        result = await svc.get_unrealized_gains(db=db, account_id=uuid4())
        assert result["lots"][0]["ticker"] == "UNKNOWN"

    @pytest.mark.asyncio
    async def test_empty_lots(self):
        svc = TaxLotService()
        db = AsyncMock()
        lots_result = MagicMock()
        lots_result.scalars.return_value.all.return_value = []
        holdings_result = MagicMock()
        holdings_result.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(side_effect=[lots_result, holdings_result])

        result = await svc.get_unrealized_gains(db=db, account_id=uuid4())
        assert result["total_unrealized_gain_loss"] == Decimal("0")
        assert result["lots"] == []

    @pytest.mark.asyncio
    async def test_short_term_unrealized_gain(self):
        svc = TaxLotService()
        db = AsyncMock()
        account_id, holding_id = uuid4(), uuid4()

        lot = _make_lot(
            holding_id=holding_id,
            acquisition_date=date(2026, 1, 1),
            remaining_quantity=Decimal("10"),
            cost_basis_per_share=Decimal("100"),
        )
        holding = _make_holding(holding_id=holding_id, current_price_per_share=Decimal("120"))

        lots_result = MagicMock()
        lots_result.scalars.return_value.all.return_value = [lot]
        holdings_result = MagicMock()
        holdings_result.scalars.return_value.all.return_value = [holding]
        db.execute = AsyncMock(side_effect=[lots_result, holdings_result])

        result = await svc.get_unrealized_gains(db=db, account_id=account_id)
        assert result["short_term_unrealized"] == Decimal("200.00")
        assert result["long_term_unrealized"] == Decimal("0")


@pytest.mark.unit
class TestGetRealizedGainsSummary:
    @pytest.mark.asyncio
    async def test_returns_summary_for_tax_year(self):
        svc = TaxLotService()
        db = AsyncMock()

        lot_st = _make_lot(
            holding_period="SHORT_TERM",
            realized_gain_loss=Decimal("500"),
            sale_proceeds=Decimal("2000"),
            is_closed=True,
        )
        lot_st.total_cost_basis = Decimal("1500")
        lot_lt = _make_lot(
            holding_period="LONG_TERM",
            realized_gain_loss=Decimal("1000"),
            sale_proceeds=Decimal("5000"),
            is_closed=True,
        )
        lot_lt.total_cost_basis = Decimal("4000")

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [lot_st, lot_lt]
        db.execute = AsyncMock(return_value=mock_result)

        result = await svc.get_realized_gains_summary(db=db, org_id=uuid4(), tax_year=2024)

        assert result["tax_year"] == 2024
        assert result["total_realized_gain_loss"] == Decimal("1500")
        assert result["short_term_gain_loss"] == Decimal("500")
        assert result["long_term_gain_loss"] == Decimal("1000")
        assert result["total_proceeds"] == Decimal("7000")
        assert result["lots_closed"] == 2

    @pytest.mark.asyncio
    async def test_handles_null_fields(self):
        svc = TaxLotService()
        db = AsyncMock()
        lot = _make_lot(
            holding_period="SHORT_TERM", realized_gain_loss=None, sale_proceeds=None, is_closed=True
        )
        lot.total_cost_basis = None
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [lot]
        db.execute = AsyncMock(return_value=mock_result)

        result = await svc.get_realized_gains_summary(db=db, org_id=uuid4(), tax_year=2024)
        assert result["total_realized_gain_loss"] == Decimal("0")
        assert result["total_proceeds"] == Decimal("0")

    @pytest.mark.asyncio
    async def test_empty_year(self):
        svc = TaxLotService()
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(return_value=mock_result)

        result = await svc.get_realized_gains_summary(db=db, org_id=uuid4(), tax_year=2024)
        assert result["lots_closed"] == 0

    @pytest.mark.asyncio
    async def test_defaults_unknown_period_to_long_term(self):
        svc = TaxLotService()
        db = AsyncMock()
        lot = _make_lot(
            holding_period=None,
            realized_gain_loss=Decimal("200"),
            sale_proceeds=Decimal("1000"),
            is_closed=True,
        )
        lot.total_cost_basis = Decimal("800")
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [lot]
        db.execute = AsyncMock(return_value=mock_result)

        result = await svc.get_realized_gains_summary(db=db, org_id=uuid4(), tax_year=2024)
        assert result["long_term_gain_loss"] == Decimal("200")
        assert result["short_term_gain_loss"] == Decimal("0")


@pytest.mark.unit
class TestImportLotsFromHolding:
    @pytest.mark.asyncio
    async def test_imports_lot_from_holding(self):
        svc = TaxLotService()
        db = AsyncMock()
        holding_id = uuid4()
        holding = _make_holding(
            holding_id=holding_id, shares=Decimal("25"), cost_basis_per_share=Decimal("100")
        )

        holding_result = MagicMock()
        holding_result.scalar_one_or_none.return_value = holding
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(side_effect=[holding_result, existing_result])

        await svc.import_lots_from_holding(db=db, holding_id=holding_id)

        db.add.assert_called_once()
        added = db.add.call_args[0][0]
        assert added.quantity == Decimal("25")
        assert added.cost_basis_per_share == Decimal("100")

    @pytest.mark.asyncio
    async def test_returns_none_when_holding_not_found(self):
        svc = TaxLotService()
        db = AsyncMock()
        holding_result = MagicMock()
        holding_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=holding_result)
        result = await svc.import_lots_from_holding(db=db, holding_id=uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_cost_basis(self):
        svc = TaxLotService()
        db = AsyncMock()
        holding = _make_holding(cost_basis_per_share=None, shares=Decimal("10"))
        holding_result = MagicMock()
        holding_result.scalar_one_or_none.return_value = holding
        db.execute = AsyncMock(return_value=holding_result)
        result = await svc.import_lots_from_holding(db=db, holding_id=uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_shares(self):
        svc = TaxLotService()
        db = AsyncMock()
        holding = _make_holding(cost_basis_per_share=Decimal("100"), shares=None)
        holding_result = MagicMock()
        holding_result.scalar_one_or_none.return_value = holding
        db.execute = AsyncMock(return_value=holding_result)
        result = await svc.import_lots_from_holding(db=db, holding_id=uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_skips_when_lots_already_exist(self):
        svc = TaxLotService()
        db = AsyncMock()
        holding = _make_holding(shares=Decimal("10"), cost_basis_per_share=Decimal("100"))
        holding_result = MagicMock()
        holding_result.scalar_one_or_none.return_value = holding
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = uuid4()
        db.execute = AsyncMock(side_effect=[holding_result, existing_result])

        result = await svc.import_lots_from_holding(db=db, holding_id=uuid4())
        assert result is None
        db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_uses_created_at_date(self):
        svc = TaxLotService()
        db = AsyncMock()
        holding = _make_holding(
            shares=Decimal("10"),
            cost_basis_per_share=Decimal("100"),
            created_at=datetime(2023, 3, 15, 10, 30, 0),
        )
        holding_result = MagicMock()
        holding_result.scalar_one_or_none.return_value = holding
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(side_effect=[holding_result, existing_result])

        await svc.import_lots_from_holding(db=db, holding_id=uuid4())
        added = db.add.call_args[0][0]
        assert added.acquisition_date == date(2023, 3, 15)

    @pytest.mark.asyncio
    async def test_uses_today_when_no_created_at(self):
        svc = TaxLotService()
        db = AsyncMock()
        holding = _make_holding(shares=Decimal("10"), cost_basis_per_share=Decimal("100"))
        holding.created_at = None
        holding_result = MagicMock()
        holding_result.scalar_one_or_none.return_value = holding
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(side_effect=[holding_result, existing_result])

        await svc.import_lots_from_holding(db=db, holding_id=uuid4())
        added = db.add.call_args[0][0]
        assert added.acquisition_date == date.today()


@pytest.mark.unit
class TestModuleSingleton:
    def test_tax_lot_service_is_instance(self):
        assert isinstance(tax_lot_service, TaxLotService)
