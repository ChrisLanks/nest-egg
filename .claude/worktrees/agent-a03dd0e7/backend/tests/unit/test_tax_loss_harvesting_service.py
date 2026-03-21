"""Unit tests for TaxLossHarvestingService."""

from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.services.tax_loss_harvesting_service import (
    COMBINED_TAX_RATE,
    FEDERAL_TAX_RATE,
    STATE_TAX_RATE,
    TaxLossHarvestingService,
    TaxLossOpportunity,
)

# ── helpers ──────────────────────────────────────────────────────────────────


def _mock_holding(
    ticker="AAPL",
    name="Apple Inc",
    shares=Decimal("10"),
    cost_basis=Decimal("1500"),
    current_value=Decimal("1200"),
    sector="Technology",
    holding_id=None,
    account_id=None,
    organization_id=None,
):
    h = Mock()
    h.id = holding_id or uuid4()
    h.ticker = ticker
    h.name = name
    h.shares = shares
    h.total_cost_basis = cost_basis
    h.current_total_value = current_value
    h.sector = sector
    h.account_id = account_id or uuid4()
    h.organization_id = organization_id or uuid4()
    return h


def _mock_db_results(taxable_ids, fallback_ids, holdings):
    """Create a mock db that returns taxable account IDs and holdings."""
    db = AsyncMock()
    call_count = 0

    def mock_execute(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        result = Mock()
        if call_count == 1:
            # Taxable accounts query
            result.all.return_value = [(aid,) for aid in taxable_ids]
        elif call_count == 2:
            # Fallback accounts query
            result.all.return_value = [(aid,) for aid in fallback_ids]
        elif call_count == 3:
            # Holdings query
            scalars = Mock()
            scalars.all.return_value = holdings
            result.scalars.return_value = scalars
        return result

    db.execute.side_effect = mock_execute
    return db


# ── constants ────────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestTaxConstants:
    """Verify tax rate constants."""

    def test_federal_rate(self):
        assert FEDERAL_TAX_RATE == Decimal("0.22")

    def test_state_rate(self):
        assert STATE_TAX_RATE == Decimal("0.05")

    def test_combined_rate(self):
        assert COMBINED_TAX_RATE == Decimal("0.27")


# ── TaxLossOpportunity ──────────────────────────────────────────────────────


@pytest.mark.unit
class TestTaxLossOpportunity:
    """Test the data class construction."""

    def test_all_fields(self):
        hid = uuid4()
        opp = TaxLossOpportunity(
            holding_id=hid,
            ticker="AAPL",
            name="Apple Inc",
            shares=Decimal("10"),
            cost_basis=Decimal("1500"),
            current_value=Decimal("1200"),
            unrealized_loss=Decimal("300"),
            loss_percentage=Decimal("20.00"),
            estimated_tax_savings=Decimal("81.00"),
            wash_sale_risk=False,
            wash_sale_reason=None,
            sector="Technology",
            suggested_replacements=["MSFT", "GOOG"],
        )
        assert opp.holding_id == hid
        assert opp.ticker == "AAPL"
        assert opp.unrealized_loss == Decimal("300")
        assert opp.estimated_tax_savings == Decimal("81.00")
        assert opp.wash_sale_risk is False
        assert len(opp.suggested_replacements) == 2


# ── get_opportunities ────────────────────────────────────────────────────────


@pytest.mark.unit
class TestGetOpportunities:
    """Test tax loss harvesting opportunity detection."""

    @pytest.mark.asyncio
    async def test_no_taxable_accounts_returns_empty(self):
        """If no taxable accounts exist, return empty list."""
        db = _mock_db_results(taxable_ids=[], fallback_ids=[], holdings=[])

        svc = TaxLossHarvestingService()
        result = await svc.get_opportunities(db, uuid4())

        assert result == []

    @pytest.mark.asyncio
    async def test_holding_with_loss_creates_opportunity(self):
        """A holding with unrealized loss generates a harvesting opportunity."""
        acct_id = uuid4()
        org_id = uuid4()
        h = _mock_holding(
            ticker="AAPL",
            cost_basis=Decimal("1500"),
            current_value=Decimal("1200"),
            sector="Technology",
            account_id=acct_id,
            organization_id=org_id,
        )
        db = _mock_db_results(
            taxable_ids=[acct_id],
            fallback_ids=[],
            holdings=[h],
        )

        svc = TaxLossHarvestingService()
        result = await svc.get_opportunities(db, org_id)

        assert len(result) == 1
        opp = result[0]
        assert opp.ticker == "AAPL"
        assert opp.unrealized_loss == Decimal("300")
        # Tax savings: 300 * 0.27 = 81.00
        expected_savings = (Decimal("300") * COMBINED_TAX_RATE).quantize(Decimal("0.01"))
        assert opp.estimated_tax_savings == expected_savings

    @pytest.mark.asyncio
    async def test_holding_with_gain_excluded(self):
        """Holdings with no loss are excluded."""
        acct_id = uuid4()
        h = _mock_holding(
            cost_basis=Decimal("1000"),
            current_value=Decimal("1500"),
            account_id=acct_id,
        )
        db = _mock_db_results(
            taxable_ids=[acct_id],
            fallback_ids=[],
            holdings=[h],
        )

        svc = TaxLossHarvestingService()
        result = await svc.get_opportunities(db, uuid4())

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_holding_with_zero_gain_excluded(self):
        """Break-even holdings are excluded."""
        acct_id = uuid4()
        h = _mock_holding(
            cost_basis=Decimal("1000"),
            current_value=Decimal("1000"),
            account_id=acct_id,
        )
        db = _mock_db_results(
            taxable_ids=[acct_id],
            fallback_ids=[],
            holdings=[h],
        )

        svc = TaxLossHarvestingService()
        result = await svc.get_opportunities(db, uuid4())

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_none_cost_basis_skipped(self):
        """Holdings with None cost_basis are skipped."""
        acct_id = uuid4()
        h = _mock_holding(
            cost_basis=Decimal("1000"), current_value=Decimal("800"), account_id=acct_id
        )
        h.total_cost_basis = None
        db = _mock_db_results(
            taxable_ids=[acct_id],
            fallback_ids=[],
            holdings=[h],
        )

        svc = TaxLossHarvestingService()
        result = await svc.get_opportunities(db, uuid4())

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_none_current_value_skipped(self):
        """Holdings with None current_total_value are skipped."""
        acct_id = uuid4()
        h = _mock_holding(
            cost_basis=Decimal("1000"), current_value=Decimal("800"), account_id=acct_id
        )
        h.current_total_value = None
        db = _mock_db_results(
            taxable_ids=[acct_id],
            fallback_ids=[],
            holdings=[h],
        )

        svc = TaxLossHarvestingService()
        result = await svc.get_opportunities(db, uuid4())

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_same_sector_replacements(self):
        """Holdings in the same sector are suggested as replacements."""
        acct_id = uuid4()
        h1 = _mock_holding(
            ticker="AAPL",
            cost_basis=Decimal("1500"),
            current_value=Decimal("1200"),
            sector="Technology",
            account_id=acct_id,
        )
        h2 = _mock_holding(
            ticker="MSFT",
            cost_basis=Decimal("1000"),
            current_value=Decimal("1200"),
            sector="Technology",
            account_id=acct_id,
        )
        h3 = _mock_holding(
            ticker="GOOG",
            cost_basis=Decimal("2000"),
            current_value=Decimal("1500"),
            sector="Technology",
            account_id=acct_id,
        )
        db = _mock_db_results(
            taxable_ids=[acct_id],
            fallback_ids=[],
            holdings=[h1, h2, h3],
        )

        svc = TaxLossHarvestingService()
        result = await svc.get_opportunities(db, uuid4())

        # h1 (AAPL) has loss, should suggest MSFT and GOOG
        aapl_opp = next(o for o in result if o.ticker == "AAPL")
        assert "MSFT" in aapl_opp.suggested_replacements
        assert "GOOG" in aapl_opp.suggested_replacements
        assert "AAPL" not in aapl_opp.suggested_replacements

    @pytest.mark.asyncio
    async def test_no_sector_no_replacements(self):
        """Holdings with no sector get no replacement suggestions."""
        acct_id = uuid4()
        h = _mock_holding(
            ticker="XYZ",
            cost_basis=Decimal("1000"),
            current_value=Decimal("800"),
            sector=None,
            account_id=acct_id,
        )
        db = _mock_db_results(
            taxable_ids=[acct_id],
            fallback_ids=[],
            holdings=[h],
        )

        svc = TaxLossHarvestingService()
        result = await svc.get_opportunities(db, uuid4())

        assert len(result) == 1
        assert result[0].suggested_replacements == []

    @pytest.mark.asyncio
    async def test_sorted_by_largest_tax_savings(self):
        """Opportunities are sorted by estimated_tax_savings descending."""
        acct_id = uuid4()
        h1 = _mock_holding(
            ticker="SMALL",
            cost_basis=Decimal("500"),
            current_value=Decimal("400"),
            sector="Tech",
            account_id=acct_id,
        )
        h2 = _mock_holding(
            ticker="BIG",
            cost_basis=Decimal("5000"),
            current_value=Decimal("3000"),
            sector="Finance",
            account_id=acct_id,
        )
        db = _mock_db_results(
            taxable_ids=[acct_id],
            fallback_ids=[],
            holdings=[h1, h2],
        )

        svc = TaxLossHarvestingService()
        result = await svc.get_opportunities(db, uuid4())

        assert len(result) == 2
        assert result[0].ticker == "BIG"  # Larger loss comes first

    @pytest.mark.asyncio
    async def test_fallback_accounts_included(self):
        """Accounts with NULL tax_treatment but brokerage type are included."""
        taxable_id = uuid4()
        fallback_id = uuid4()
        h = _mock_holding(
            cost_basis=Decimal("1000"),
            current_value=Decimal("800"),
            account_id=fallback_id,
        )
        db = _mock_db_results(
            taxable_ids=[taxable_id],
            fallback_ids=[fallback_id],
            holdings=[h],
        )

        svc = TaxLossHarvestingService()
        result = await svc.get_opportunities(db, uuid4())

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_zero_cost_basis_loss_percentage_is_zero(self):
        """When cost basis is 0, loss percentage should be 0."""
        acct_id = uuid4()
        h = _mock_holding(
            cost_basis=Decimal("0"),
            current_value=Decimal("-100"),
            account_id=acct_id,
        )
        db = _mock_db_results(
            taxable_ids=[acct_id],
            fallback_ids=[],
            holdings=[h],
        )

        svc = TaxLossHarvestingService()
        result = await svc.get_opportunities(db, uuid4())

        assert len(result) == 1
        assert result[0].loss_percentage == Decimal("0")

    @pytest.mark.asyncio
    async def test_max_three_replacements(self):
        """At most 3 replacement suggestions per opportunity."""
        acct_id = uuid4()
        holdings = [
            _mock_holding(
                ticker=f"T{i}",
                cost_basis=Decimal("1000"),
                current_value=Decimal("800"),
                sector="Tech",
                account_id=acct_id,
            )
            for i in range(6)
        ]
        db = _mock_db_results(
            taxable_ids=[acct_id],
            fallback_ids=[],
            holdings=holdings,
        )

        svc = TaxLossHarvestingService()
        result = await svc.get_opportunities(db, uuid4())

        for opp in result:
            assert len(opp.suggested_replacements) <= 3
