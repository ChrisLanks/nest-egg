"""Unit tests for CapitalGainsHarvestingService."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.capital_gains_harvesting_service import CapitalGainsHarvestingService


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def org_id():
    return uuid4()


# ── get_ltcg_bracket_fill ─────────────────────────────────────────────────


class TestLtcgBracketFill:
    @pytest.mark.asyncio
    async def test_ltcg_bracket_fill_single(self, mock_db, org_id):
        """Single filer with $30k income should have room up to the 0% LTCG ceiling."""
        from app.services.capital_gains_harvesting_service import _ltcg_0pct_ceiling
        ceiling = float(_ltcg_0pct_ceiling()["single"])
        expected_room = ceiling - 30000.0

        result = await CapitalGainsHarvestingService.get_ltcg_bracket_fill(
            db=mock_db,
            organization_id=org_id,
            current_taxable_income=Decimal("30000"),
            filing_status="single",
        )
        assert result["filing_status"] == "single"
        assert result["ltcg_0pct_ceiling"] == pytest.approx(ceiling)
        assert result["current_taxable_income"] == pytest.approx(30000.0)
        assert result["available_0pct_room"] == pytest.approx(expected_room)
        assert result["suggested_harvest_amount"] == pytest.approx(expected_room)

    @pytest.mark.asyncio
    async def test_ltcg_bracket_fill_married(self, mock_db, org_id):
        """Married filer with $60k income should have room up to the 0% LTCG ceiling."""
        from app.services.capital_gains_harvesting_service import _ltcg_0pct_ceiling
        ceiling = float(_ltcg_0pct_ceiling()["married_filing_jointly"])
        expected_room = ceiling - 60000.0

        result = await CapitalGainsHarvestingService.get_ltcg_bracket_fill(
            db=mock_db,
            organization_id=org_id,
            current_taxable_income=Decimal("60000"),
            filing_status="married_filing_jointly",
        )
        assert result["ltcg_0pct_ceiling"] == pytest.approx(ceiling)
        assert result["available_0pct_room"] == pytest.approx(expected_room)

    @pytest.mark.asyncio
    async def test_ltcg_bracket_fill_no_room(self, mock_db, org_id):
        """Income already at or above ceiling — should return 0 room."""
        result = await CapitalGainsHarvestingService.get_ltcg_bracket_fill(
            db=mock_db,
            organization_id=org_id,
            current_taxable_income=Decimal("60000"),
            filing_status="single",
        )
        assert result["available_0pct_room"] == pytest.approx(0.0)
        assert result["suggested_harvest_amount"] == pytest.approx(0.0)

    @pytest.mark.asyncio
    async def test_ltcg_bracket_fill_head_of_household(self, mock_db, org_id):
        """Head of household with $40k income → room up to HoH ceiling."""
        from app.services.capital_gains_harvesting_service import _ltcg_0pct_ceiling
        ceiling = float(_ltcg_0pct_ceiling()["head_of_household"])
        expected_room = ceiling - 40000.0

        result = await CapitalGainsHarvestingService.get_ltcg_bracket_fill(
            db=mock_db,
            organization_id=org_id,
            current_taxable_income=Decimal("40000"),
            filing_status="head_of_household",
        )
        assert result["ltcg_0pct_ceiling"] == pytest.approx(ceiling)
        assert result["available_0pct_room"] == pytest.approx(expected_room)

    @pytest.mark.asyncio
    async def test_suggestion_capped_at_50k(self, mock_db, org_id):
        """Suggestion should be capped at $50,000 even when room is larger."""
        from app.services.capital_gains_harvesting_service import _ltcg_0pct_ceiling
        ceiling = float(_ltcg_0pct_ceiling()["married_filing_jointly"])

        result = await CapitalGainsHarvestingService.get_ltcg_bracket_fill(
            db=mock_db,
            organization_id=org_id,
            current_taxable_income=Decimal("0"),
            filing_status="married_filing_jointly",
        )
        # Room equals the full ceiling, but suggestion should cap at $50,000
        assert result["available_0pct_room"] == pytest.approx(ceiling)
        assert result["suggested_harvest_amount"] == pytest.approx(50000.0)


# ── get_ytd_realized_gains ────────────────────────────────────────────────


def _make_closed_lot(acquisition_date, close_date, realized_gain_loss):
    """Helper to build a mock closed TaxLot."""
    lot = MagicMock()
    lot.organization_id = uuid4()
    lot.is_closed = True
    lot.acquisition_date = acquisition_date
    lot.closed_at = datetime.combine(close_date, datetime.min.time())
    lot.realized_gain_loss = Decimal(str(realized_gain_loss))
    return lot


class TestYtdRealizedGains:
    @pytest.mark.asyncio
    async def test_ytd_realized_gains_splits_stcg_ltcg(self, mock_db, org_id):
        """Short-term and long-term gains are correctly separated."""
        today = date.today()
        tax_year = today.year

        # Short-term lot: held 100 days
        stcg_lot = _make_closed_lot(
            acquisition_date=today - timedelta(days=100),
            close_date=today.replace(month=6, day=1) if today.month > 6 else today,
            realized_gain_loss=Decimal("1000"),
        )
        stcg_lot.closed_at = datetime(tax_year, 6, 1)

        # Long-term lot: held 400 days
        ltcg_lot = _make_closed_lot(
            acquisition_date=today - timedelta(days=400),
            close_date=today,
            realized_gain_loss=Decimal("2500"),
        )
        ltcg_lot.closed_at = datetime(tax_year, 8, 15)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [stcg_lot, ltcg_lot]
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await CapitalGainsHarvestingService.get_ytd_realized_gains(
            db=mock_db,
            organization_id=org_id,
            user_id=None,
            tax_year=tax_year,
        )

        assert result["tax_year"] == tax_year
        assert result["realized_stcg"] == pytest.approx(1000.0)
        assert result["realized_ltcg"] == pytest.approx(2500.0)
        assert result["total_realized"] == pytest.approx(3500.0)

    @pytest.mark.asyncio
    async def test_ytd_realized_gains_excludes_wrong_year(self, mock_db, org_id):
        """Lots closed in a different year are excluded."""
        # Lot closed in 2024 should not count for 2025
        lot = _make_closed_lot(
            acquisition_date=date(2023, 1, 1),
            close_date=date(2024, 6, 1),
            realized_gain_loss=Decimal("5000"),
        )
        lot.closed_at = datetime(2024, 6, 1)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [lot]
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await CapitalGainsHarvestingService.get_ytd_realized_gains(
            db=mock_db,
            organization_id=org_id,
            user_id=None,
            tax_year=2025,
        )

        assert result["realized_stcg"] == pytest.approx(0.0)
        assert result["realized_ltcg"] == pytest.approx(0.0)
        assert result["total_realized"] == pytest.approx(0.0)

    @pytest.mark.asyncio
    async def test_ytd_realized_gains_empty(self, mock_db, org_id):
        """No closed lots returns zeros."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await CapitalGainsHarvestingService.get_ytd_realized_gains(
            db=mock_db,
            organization_id=org_id,
            user_id=None,
            tax_year=2026,
        )

        assert result["realized_stcg"] == 0.0
        assert result["realized_ltcg"] == 0.0
        assert result["total_realized"] == 0.0
