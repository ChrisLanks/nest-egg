"""Tests for tax lot service."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.tax_lot import CostBasisMethod, TaxLot
from app.services.tax_lot_service import TaxLotService, _determine_holding_period


@pytest.mark.unit
class TestDetermineHoldingPeriod:
    """Tests for _determine_holding_period pure function."""

    def test_short_term_one_day(self):
        """Should return SHORT_TERM for a 1-day hold."""
        result = _determine_holding_period(date(2024, 1, 1), date(2024, 1, 2))
        assert result == "SHORT_TERM"

    def test_short_term_365_days(self):
        """Should return SHORT_TERM for exactly 365 days."""
        result = _determine_holding_period(date(2024, 1, 1), date(2024, 12, 31))
        assert (date(2024, 12, 31) - date(2024, 1, 1)).days == 365
        assert result == "SHORT_TERM"

    def test_long_term_366_days(self):
        """Should return LONG_TERM for exactly 366 days."""
        acq = date(2024, 1, 1)
        sale = date(2025, 1, 1)
        assert (sale - acq).days == 366  # 2024 is a leap year
        result = _determine_holding_period(acq, sale)
        assert result == "LONG_TERM"

    def test_long_term_well_over_a_year(self):
        """Should return LONG_TERM for holdings well over a year."""
        result = _determine_holding_period(date(2020, 6, 15), date(2024, 6, 15))
        assert result == "LONG_TERM"

    def test_same_day(self):
        """Should return SHORT_TERM for same-day sale (0 days held)."""
        result = _determine_holding_period(date(2024, 3, 1), date(2024, 3, 1))
        assert result == "SHORT_TERM"


@pytest.mark.unit
class TestRecordPurchase:
    """Tests for TaxLotService.record_purchase."""

    @pytest.mark.asyncio
    async def test_creates_tax_lot_with_correct_fields(self):
        """Should create a TaxLot with calculated total cost and correct attributes."""
        service = TaxLotService()
        db = AsyncMock()

        org_id = uuid4()
        holding_id = uuid4()
        account_id = uuid4()
        quantity = Decimal("10")
        price = Decimal("150.50")
        acq_date = date(2024, 3, 15)

        await service.record_purchase(
            db=db,
            org_id=org_id,
            holding_id=holding_id,
            account_id=account_id,
            quantity=quantity,
            price_per_share=price,
            acquisition_date=acq_date,
        )

        # Verify db.add was called with the lot
        db.add.assert_called_once()
        added_lot = db.add.call_args[0][0]
        assert isinstance(added_lot, TaxLot)

        # Verify lot fields
        assert added_lot.organization_id == org_id
        assert added_lot.holding_id == holding_id
        assert added_lot.account_id == account_id
        assert added_lot.acquisition_date == acq_date
        assert added_lot.quantity == quantity
        assert added_lot.cost_basis_per_share == price
        assert added_lot.total_cost_basis == Decimal("1505.00")
        assert added_lot.remaining_quantity == quantity
        assert added_lot.is_closed is False

        # Verify flush and refresh called
        db.flush.assert_awaited_once()
        db.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_total_cost_rounds_to_two_decimals(self):
        """Should quantize total cost to 2 decimal places."""
        service = TaxLotService()
        db = AsyncMock()

        await service.record_purchase(
            db=db,
            org_id=uuid4(),
            holding_id=uuid4(),
            account_id=uuid4(),
            quantity=Decimal("3"),
            price_per_share=Decimal("33.3333"),
            acquisition_date=date(2024, 1, 1),
        )

        added_lot = db.add.call_args[0][0]
        # 3 * 33.3333 = 99.9999 -> quantized to 100.00
        assert added_lot.total_cost_basis == Decimal("100.00")


def _make_mock_lot(
    acquisition_date,
    remaining_quantity,
    cost_basis_per_share,
    lot_id=None,
):
    """Helper to create a mock TaxLot for sale tests."""
    lot = MagicMock(spec=TaxLot)
    lot.id = lot_id or uuid4()
    lot.acquisition_date = acquisition_date
    lot.remaining_quantity = Decimal(str(remaining_quantity))
    lot.cost_basis_per_share = Decimal(str(cost_basis_per_share))
    lot.is_closed = False
    lot.sale_proceeds = None
    lot.realized_gain_loss = None
    lot.holding_period = None
    return lot


def _build_db_mock(lots, account_method=None):
    """Build AsyncMock db that returns lots from the second execute call.

    First execute returns the account cost basis method (if method is None in the call).
    Second execute returns the lots.
    """
    db = AsyncMock()

    # Scalars result for lots query
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = lots

    lots_result = MagicMock()
    lots_result.scalars.return_value = scalars_mock

    if account_method is not None:
        # When method is None, first call fetches account method, second fetches lots
        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = account_method
        db.execute = AsyncMock(side_effect=[account_result, lots_result])
    else:
        # When method is provided, only one execute call for lots
        db.execute = AsyncMock(return_value=lots_result)

    return db


@pytest.mark.unit
class TestRecordSaleFIFO:
    """Tests for record_sale with FIFO method."""

    @pytest.mark.asyncio
    async def test_sells_oldest_lot_first(self):
        """FIFO should sell from the oldest acquisition date first."""
        service = TaxLotService()

        old_lot = _make_mock_lot(date(2022, 1, 1), 10, "100.00")
        new_lot = _make_mock_lot(date(2024, 1, 1), 10, "150.00")
        db = _build_db_mock([old_lot, new_lot])

        result = await service.record_sale(
            db=db,
            org_id=uuid4(),
            holding_id=uuid4(),
            account_id=uuid4(),
            quantity=Decimal("5"),
            sale_price_per_share=Decimal("200.00"),
            sale_date=date(2025, 6, 1),
            method=CostBasisMethod.FIFO,
        )

        # Old lot should have been partially sold
        assert old_lot.remaining_quantity == Decimal("5")
        # New lot should be untouched (remaining_quantity not reassigned)
        assert result["lots_affected"] == 1
        assert result["total_proceeds"] == Decimal("1000.00")
        assert result["total_cost_basis"] == Decimal("500.00")

    @pytest.mark.asyncio
    async def test_fifo_spans_multiple_lots(self):
        """FIFO should span across lots when selling more than one lot holds."""
        service = TaxLotService()

        lot_a = _make_mock_lot(date(2022, 1, 1), 5, "100.00")
        lot_b = _make_mock_lot(date(2023, 1, 1), 10, "120.00")
        db = _build_db_mock([lot_a, lot_b])

        result = await service.record_sale(
            db=db,
            org_id=uuid4(),
            holding_id=uuid4(),
            account_id=uuid4(),
            quantity=Decimal("8"),
            sale_price_per_share=Decimal("200.00"),
            sale_date=date(2025, 6, 1),
            method=CostBasisMethod.FIFO,
        )

        # lot_a fully sold (5 shares), lot_b partially sold (3 shares)
        assert lot_a.remaining_quantity == Decimal("0")
        assert lot_a.is_closed is True
        assert lot_b.remaining_quantity == Decimal("7")
        assert result["lots_affected"] == 2


@pytest.mark.unit
class TestRecordSaleLIFO:
    """Tests for record_sale with LIFO method."""

    @pytest.mark.asyncio
    async def test_sells_newest_lot_first(self):
        """LIFO should sell from the newest acquisition date first."""
        service = TaxLotService()

        old_lot = _make_mock_lot(date(2022, 1, 1), 10, "100.00")
        new_lot = _make_mock_lot(date(2024, 6, 1), 10, "150.00")
        db = _build_db_mock([old_lot, new_lot])

        result = await service.record_sale(
            db=db,
            org_id=uuid4(),
            holding_id=uuid4(),
            account_id=uuid4(),
            quantity=Decimal("5"),
            sale_price_per_share=Decimal("200.00"),
            sale_date=date(2025, 6, 1),
            method=CostBasisMethod.LIFO,
        )

        # New lot should be partially sold, old lot untouched
        assert new_lot.remaining_quantity == Decimal("5")
        assert result["lots_affected"] == 1
        # Cost basis should be from the new lot (150.00 * 5)
        assert result["total_cost_basis"] == Decimal("750.00")


@pytest.mark.unit
class TestRecordSaleHIFO:
    """Tests for record_sale with HIFO method."""

    @pytest.mark.asyncio
    async def test_sells_highest_cost_first(self):
        """HIFO should sell from the highest cost basis per share first."""
        service = TaxLotService()

        cheap_lot = _make_mock_lot(date(2022, 1, 1), 10, "80.00")
        mid_lot = _make_mock_lot(date(2023, 1, 1), 10, "120.00")
        expensive_lot = _make_mock_lot(date(2024, 1, 1), 10, "200.00")
        db = _build_db_mock([cheap_lot, mid_lot, expensive_lot])

        result = await service.record_sale(
            db=db,
            org_id=uuid4(),
            holding_id=uuid4(),
            account_id=uuid4(),
            quantity=Decimal("5"),
            sale_price_per_share=Decimal("250.00"),
            sale_date=date(2025, 6, 1),
            method=CostBasisMethod.HIFO,
        )

        # Expensive lot should be sold first
        assert expensive_lot.remaining_quantity == Decimal("5")
        assert result["lots_affected"] == 1
        # Cost basis from expensive lot: 200.00 * 5
        assert result["total_cost_basis"] == Decimal("1000.00")
        # Proceeds: 250.00 * 5 = 1250, gain = 1250 - 1000 = 250
        assert result["realized_gain_loss"] == Decimal("250.00")


@pytest.mark.unit
class TestRecordSaleInsufficientQuantity:
    """Tests for record_sale when insufficient shares are available."""

    @pytest.mark.asyncio
    async def test_raises_value_error(self):
        """Should raise ValueError when requested quantity exceeds available shares."""
        service = TaxLotService()

        lot = _make_mock_lot(date(2024, 1, 1), 5, "100.00")
        db = _build_db_mock([lot])

        with pytest.raises(ValueError, match="Insufficient shares"):
            await service.record_sale(
                db=db,
                org_id=uuid4(),
                holding_id=uuid4(),
                account_id=uuid4(),
                quantity=Decimal("10"),
                sale_price_per_share=Decimal("200.00"),
                sale_date=date(2025, 6, 1),
                method=CostBasisMethod.FIFO,
            )

    @pytest.mark.asyncio
    async def test_raises_when_no_lots_exist(self):
        """Should raise ValueError when no open lots exist."""
        service = TaxLotService()
        db = _build_db_mock([])

        with pytest.raises(ValueError, match="Insufficient shares"):
            await service.record_sale(
                db=db,
                org_id=uuid4(),
                holding_id=uuid4(),
                account_id=uuid4(),
                quantity=Decimal("1"),
                sale_price_per_share=Decimal("100.00"),
                sale_date=date(2025, 6, 1),
                method=CostBasisMethod.FIFO,
            )


@pytest.mark.unit
class TestRealizedGainLossCalculation:
    """Tests for realized gain/loss math in record_sale."""

    @pytest.mark.asyncio
    async def test_gain_calculation(self):
        """Should calculate positive gain when sale price exceeds cost basis."""
        service = TaxLotService()

        lot = _make_mock_lot(date(2023, 1, 1), 10, "100.00")
        db = _build_db_mock([lot])

        result = await service.record_sale(
            db=db,
            org_id=uuid4(),
            holding_id=uuid4(),
            account_id=uuid4(),
            quantity=Decimal("10"),
            sale_price_per_share=Decimal("150.00"),
            sale_date=date(2025, 6, 1),
            method=CostBasisMethod.FIFO,
        )

        # Proceeds: 10 * 150 = 1500, Cost: 10 * 100 = 1000, Gain = 500
        assert result["total_proceeds"] == Decimal("1500.00")
        assert result["total_cost_basis"] == Decimal("1000.00")
        assert result["realized_gain_loss"] == Decimal("500.00")

    @pytest.mark.asyncio
    async def test_loss_calculation(self):
        """Should calculate negative loss when sale price is below cost basis."""
        service = TaxLotService()

        lot = _make_mock_lot(date(2024, 1, 1), 10, "200.00")
        db = _build_db_mock([lot])

        result = await service.record_sale(
            db=db,
            org_id=uuid4(),
            holding_id=uuid4(),
            account_id=uuid4(),
            quantity=Decimal("10"),
            sale_price_per_share=Decimal("150.00"),
            sale_date=date(2025, 6, 1),
            method=CostBasisMethod.FIFO,
        )

        # Proceeds: 10 * 150 = 1500, Cost: 10 * 200 = 2000, Loss = -500
        assert result["total_proceeds"] == Decimal("1500.00")
        assert result["total_cost_basis"] == Decimal("2000.00")
        assert result["realized_gain_loss"] == Decimal("-500.00")

    @pytest.mark.asyncio
    async def test_short_term_vs_long_term_split(self):
        """Should split gains into short-term and long-term buckets."""
        service = TaxLotService()

        # Short-term lot (acquired recently)
        short_lot = _make_mock_lot(date(2025, 3, 1), 5, "100.00")
        # Long-term lot (acquired > 366 days ago)
        long_lot = _make_mock_lot(date(2023, 1, 1), 5, "80.00")
        db = _build_db_mock([short_lot, long_lot])

        sale_date = date(2025, 6, 1)
        result = await service.record_sale(
            db=db,
            org_id=uuid4(),
            holding_id=uuid4(),
            account_id=uuid4(),
            quantity=Decimal("10"),
            sale_price_per_share=Decimal("150.00"),
            sale_date=sale_date,
            method=CostBasisMethod.FIFO,
        )

        # Short-term lot: proceeds 5*150=750, cost 5*100=500, gain=250
        # Long-term lot: proceeds 5*150=750, cost 5*80=400, gain=350
        assert result["short_term_gain_loss"] == Decimal("250.00")
        assert result["long_term_gain_loss"] == Decimal("350.00")
        assert result["realized_gain_loss"] == Decimal("600.00")

    @pytest.mark.asyncio
    async def test_lot_fields_updated_after_full_sale(self):
        """Should update lot fields correctly when fully sold."""
        service = TaxLotService()

        lot = _make_mock_lot(date(2023, 1, 1), 10, "100.00")
        db = _build_db_mock([lot])

        await service.record_sale(
            db=db,
            org_id=uuid4(),
            holding_id=uuid4(),
            account_id=uuid4(),
            quantity=Decimal("10"),
            sale_price_per_share=Decimal("150.00"),
            sale_date=date(2025, 6, 1),
            method=CostBasisMethod.FIFO,
        )

        assert lot.remaining_quantity == Decimal("0")
        assert lot.is_closed is True
        assert lot.closed_at is not None
        assert lot.sale_proceeds == Decimal("1500.00")
        assert lot.realized_gain_loss == Decimal("500.00")
        assert lot.holding_period == "LONG_TERM"
