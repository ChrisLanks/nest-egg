"""Expanded unit tests for TaxService — covers initialize_tax_labels,
_get_transactions_for_label, generate_tax_export_csv, and filter branches.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from app.services.tax_service import TaxDeductibleSummary, TaxService

# ── helpers ──────────────────────────────────────────────────────────────────


def _summary_row(label_id, label_name, total_amount, transaction_count, color="#9F7AEA"):
    row = Mock()
    row.label_id = label_id
    row.label_name = label_name
    row.label_color = color
    row.total_amount = Decimal(str(total_amount))
    row.transaction_count = transaction_count
    return row


def _txn(
    txn_id=None,
    merchant="Whole Foods",
    amount=45.32,
    category="Food and Drink",
    description="",
    account_name="Chase Checking",
):
    return {
        "id": str(txn_id or uuid4()),
        "date": "2026-02-11",
        "merchant_name": merchant,
        "description": description,
        "amount": amount,
        "category": category,
        "account_name": account_name,
    }


def _txn_row(
    txn_id=None,
    txn_date=None,
    merchant="Whole Foods",
    description="",
    amount=Decimal("-45.32"),
    category="Food",
    account_name="Chase",
):
    row = Mock()
    row.id = txn_id or uuid4()
    row.date = txn_date or date(2026, 2, 11)
    row.merchant_name = merchant
    row.description = description
    row.amount = amount
    row.category_primary = category
    row.account_name = account_name
    return row


# ── TaxDeductibleSummary dataclass ──────────────────────────────────────────


@pytest.mark.unit
class TestTaxDeductibleSummary:
    """Test TaxDeductibleSummary construction."""

    def test_summary_fields(self):
        lid = uuid4()
        s = TaxDeductibleSummary(
            label_id=lid,
            label_name="Medical & Dental",
            label_color="#48BB78",
            total_amount=Decimal("100.00"),
            transaction_count=3,
            transactions=[_txn()],
        )
        assert s.label_id == lid
        assert s.label_name == "Medical & Dental"
        assert s.label_color == "#48BB78"
        assert s.total_amount == Decimal("100.00")
        assert s.transaction_count == 3
        assert len(s.transactions) == 1


# ── initialize_tax_labels ────────────────────────────────────────────────────


@pytest.mark.unit
class TestInitializeTaxLabels:
    """Test idempotent creation of default tax labels."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_creates_all_labels_when_none_exist(self, mock_db):
        """All 5 labels created when none exist."""
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock

        labels = await TaxService.initialize_tax_labels(mock_db, uuid4())

        assert len(labels) == 5
        mock_db.commit.assert_awaited_once()
        # db.add should have been called 5 times (once per new label)
        assert mock_db.add.call_count == 5

    @pytest.mark.asyncio
    async def test_skips_existing_labels(self, mock_db):
        """Existing labels are returned without creating duplicates."""
        existing_label = Mock()
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = existing_label
        mock_db.execute.return_value = result_mock

        labels = await TaxService.initialize_tax_labels(mock_db, uuid4())

        assert len(labels) == 5
        # No db.add calls because all labels already exist
        mock_db.add.assert_not_called()
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_mixed_existing_and_new(self, mock_db):
        """Some existing, some new — only new ones are created."""
        call_count = 0

        def alternate_existing(*args, **kwargs):
            nonlocal call_count
            result_mock = Mock()
            call_count += 1
            # First 2 exist, rest don't
            result_mock.scalar_one_or_none.return_value = Mock() if call_count <= 2 else None
            return result_mock

        mock_db.execute.side_effect = alternate_existing

        labels = await TaxService.initialize_tax_labels(mock_db, uuid4())
        assert len(labels) == 5
        assert mock_db.add.call_count == 3  # 5 total - 2 existing = 3 new

    @pytest.mark.asyncio
    async def test_refreshes_all_labels_after_commit(self, mock_db):
        """All labels are refreshed after commit."""
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock

        await TaxService.initialize_tax_labels(mock_db, uuid4())

        assert mock_db.refresh.await_count == 5


# ── _get_transactions_for_label ──────────────────────────────────────────────


@pytest.mark.unit
class TestGetTransactionsForLabel:
    """Test the detail transaction query helper."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_returns_formatted_transactions(self, mock_db):
        """Transactions are properly formatted."""
        row = _txn_row()
        result_mock = Mock()
        result_mock.all.return_value = [row]
        mock_db.execute.return_value = result_mock

        txns = await TaxService._get_transactions_for_label(
            mock_db, uuid4(), date(2026, 1, 1), date(2026, 12, 31), [uuid4()]
        )

        assert len(txns) == 1
        assert txns[0]["merchant_name"] == "Whole Foods"
        assert txns[0]["amount"] == float(abs(row.amount))
        assert txns[0]["date"] == "2026-02-11"

    @pytest.mark.asyncio
    async def test_none_description_becomes_empty_string(self, mock_db):
        """None description is converted to empty string."""
        row = _txn_row(description=None)
        result_mock = Mock()
        result_mock.all.return_value = [row]
        mock_db.execute.return_value = result_mock

        txns = await TaxService._get_transactions_for_label(
            mock_db, uuid4(), date(2026, 1, 1), date(2026, 12, 31), [uuid4()]
        )

        assert txns[0]["description"] == ""

    @pytest.mark.asyncio
    async def test_none_category_becomes_uncategorized(self, mock_db):
        """None category_primary is converted to 'Uncategorized'."""
        row = _txn_row(category=None)
        result_mock = Mock()
        result_mock.all.return_value = [row]
        mock_db.execute.return_value = result_mock

        txns = await TaxService._get_transactions_for_label(
            mock_db, uuid4(), date(2026, 1, 1), date(2026, 12, 31), [uuid4()]
        )

        assert txns[0]["category"] == "Uncategorized"

    @pytest.mark.asyncio
    async def test_with_user_id_filter(self, mock_db):
        """User ID filter is applied when provided."""
        result_mock = Mock()
        result_mock.all.return_value = []
        mock_db.execute.return_value = result_mock

        await TaxService._get_transactions_for_label(
            mock_db, uuid4(), date(2026, 1, 1), date(2026, 12, 31), [uuid4()], user_id=uuid4()
        )

        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_empty_result(self, mock_db):
        """No matching transactions returns empty list."""
        result_mock = Mock()
        result_mock.all.return_value = []
        mock_db.execute.return_value = result_mock

        txns = await TaxService._get_transactions_for_label(
            mock_db, uuid4(), date(2026, 1, 1), date(2026, 12, 31), [uuid4()]
        )

        assert txns == []


# ── get_tax_deductible_summary with label_ids and user_id filters ───────────


@pytest.mark.unit
class TestGetTaxDeductibleSummaryFilters:
    """Test optional filters on summary query."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_with_label_ids_filter(self, mock_db):
        """label_ids filter is applied when provided."""
        summary_result = Mock()
        summary_result.all.return_value = []
        mock_db.execute.return_value = summary_result

        result = await TaxService.get_tax_deductible_summary(
            mock_db, uuid4(), date(2026, 1, 1), date(2026, 12, 31), label_ids=[uuid4()]
        )

        assert result == []
        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_with_user_id_filter(self, mock_db):
        """user_id filter is applied when provided."""
        summary_result = Mock()
        summary_result.all.return_value = []
        mock_db.execute.return_value = summary_result

        result = await TaxService.get_tax_deductible_summary(
            mock_db, uuid4(), date(2026, 1, 1), date(2026, 12, 31), user_id=uuid4()
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_merged_amounts_are_summed(self, mock_db):
        """Duplicate label names have their amounts summed."""
        org_id = uuid4()
        id1, id2 = uuid4(), uuid4()

        summary_result = Mock()
        summary_result.all.return_value = [
            _summary_row(id1, "Business Expenses", "100.00", 2),
            _summary_row(id2, "Business Expenses", "50.00", 1),
        ]
        mock_db.execute.return_value = summary_result

        with patch.object(
            TaxService,
            "_get_transactions_for_label",
            new_callable=AsyncMock,
            return_value=[_txn(), _txn(), _txn()],
        ):
            summaries = await TaxService.get_tax_deductible_summary(
                mock_db, org_id, date(2026, 1, 1), date(2026, 12, 31)
            )

        assert len(summaries) == 1
        assert summaries[0].total_amount == Decimal("150.00")


# ── generate_tax_export_csv ──────────────────────────────────────────────────


@pytest.mark.unit
class TestGenerateTaxExportCSV:
    """Test CSV export generation."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_csv_header_row(self, mock_db):
        """CSV output contains the expected header row."""
        with patch.object(
            TaxService,
            "get_tax_deductible_summary",
            new_callable=AsyncMock,
            return_value=[],
        ):
            csv_str = await TaxService.generate_tax_export_csv(
                mock_db, uuid4(), date(2026, 1, 1), date(2026, 12, 31)
            )

        assert "Date,Merchant,Description,Category,Tax Label,Amount,Account,Notes" in csv_str

    @pytest.mark.asyncio
    async def test_csv_data_rows(self, mock_db):
        """CSV output contains transaction data rows."""
        summary = TaxDeductibleSummary(
            label_id=uuid4(),
            label_name="Business Expenses",
            label_color="#9F7AEA",
            total_amount=Decimal("100.00"),
            transaction_count=1,
            transactions=[_txn(merchant="Office Depot", amount=100.0, category="Office Supplies")],
        )

        with patch.object(
            TaxService,
            "get_tax_deductible_summary",
            new_callable=AsyncMock,
            return_value=[summary],
        ):
            csv_str = await TaxService.generate_tax_export_csv(
                mock_db, uuid4(), date(2026, 1, 1), date(2026, 12, 31)
            )

        assert "Office Depot" in csv_str
        assert "Business Expenses" in csv_str
        assert "$100.00" in csv_str

    @pytest.mark.asyncio
    async def test_csv_with_label_ids_and_user_id(self, mock_db):
        """CSV export passes label_ids and user_id to summary."""
        label_ids = [uuid4()]
        user_id = uuid4()

        with patch.object(
            TaxService,
            "get_tax_deductible_summary",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_summary:
            await TaxService.generate_tax_export_csv(
                mock_db,
                uuid4(),
                date(2026, 1, 1),
                date(2026, 12, 31),
                label_ids=label_ids,
                user_id=user_id,
            )

        call_kwargs = mock_summary.call_args
        assert call_kwargs[1].get("label_ids") == label_ids or call_kwargs[0][4] == label_ids

    @pytest.mark.asyncio
    async def test_csv_empty_summaries(self, mock_db):
        """Empty summaries produce header-only CSV."""
        with patch.object(
            TaxService,
            "get_tax_deductible_summary",
            new_callable=AsyncMock,
            return_value=[],
        ):
            csv_str = await TaxService.generate_tax_export_csv(
                mock_db, uuid4(), date(2026, 1, 1), date(2026, 12, 31)
            )

        lines = csv_str.strip().split("\n")
        assert len(lines) == 1  # Only header

    @pytest.mark.asyncio
    async def test_csv_multiple_summaries_multiple_transactions(self, mock_db):
        """Multiple summaries with multiple transactions produce correct rows."""
        s1 = TaxDeductibleSummary(
            label_id=uuid4(),
            label_name="Medical & Dental",
            label_color="#48BB78",
            total_amount=Decimal("200.00"),
            transaction_count=2,
            transactions=[_txn(amount=100.0), _txn(amount=100.0)],
        )
        s2 = TaxDeductibleSummary(
            label_id=uuid4(),
            label_name="Education",
            label_color="#ED8936",
            total_amount=Decimal("50.00"),
            transaction_count=1,
            transactions=[_txn(amount=50.0)],
        )

        with patch.object(
            TaxService,
            "get_tax_deductible_summary",
            new_callable=AsyncMock,
            return_value=[s1, s2],
        ):
            csv_str = await TaxService.generate_tax_export_csv(
                mock_db, uuid4(), date(2026, 1, 1), date(2026, 12, 31)
            )

        lines = csv_str.strip().split("\n")
        assert len(lines) == 4  # 1 header + 3 data rows
