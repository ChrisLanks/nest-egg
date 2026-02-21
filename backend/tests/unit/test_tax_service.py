"""Unit tests for TaxService business logic.

Covers:
  - Duplicate label names are merged into a single summary
  - transaction_count reflects the deduplicated transaction list, not the raw DB aggregate
  - _get_transactions_for_label accepts a list of label IDs (merged duplicates)
  - is_transfer transactions are NOT filtered out (explicit tax label wins)
"""

import pytest
from decimal import Decimal
from datetime import date
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from app.services.tax_service import TaxService


# ── helpers ───────────────────────────────────────────────────────────────────

def _summary_row(label_id, label_name, total_amount, transaction_count, color="#9F7AEA"):
    """Return a mock DB aggregate row matching the summary SELECT columns."""
    row = Mock()
    row.label_id = label_id
    row.label_name = label_name
    row.label_color = color
    row.total_amount = Decimal(str(total_amount))
    row.transaction_count = transaction_count
    return row


def _txn(txn_id=None):
    """Return a minimal transaction dict as returned by _get_transactions_for_label."""
    return {
        "id": str(txn_id or uuid4()),
        "date": "2026-02-11",
        "merchant_name": "Whole Foods Market",
        "description": "",
        "amount": 45.32,
        "category": "Food and Drink",
        "account_name": "Chase Checking",
    }


# ── merge duplicate label names ───────────────────────────────────────────────

@pytest.mark.unit
class TestGetTaxDeductibleSummaryMerge:
    """Duplicate label names (same name, different IDs) are merged into one summary."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_two_rows_with_same_name_produce_one_summary(self, mock_db):
        """Two 'Business Expenses' rows should produce exactly one summary entry."""
        org_id = uuid4()
        id1, id2 = uuid4(), uuid4()

        summary_result = Mock()
        summary_result.all.return_value = [
            _summary_row(id1, "Business Expenses", "45.32", 1),
            _summary_row(id2, "Business Expenses", "0.00", 0),
        ]
        mock_db.execute.return_value = summary_result

        with patch.object(
            TaxService,
            "_get_transactions_for_label",
            new_callable=AsyncMock,
            return_value=[_txn()],
        ):
            summaries = await TaxService.get_tax_deductible_summary(
                mock_db, org_id, date(2026, 1, 1), date(2026, 12, 31)
            )

        assert len(summaries) == 1
        assert summaries[0].label_name == "Business Expenses"

    @pytest.mark.asyncio
    async def test_merged_row_passes_both_label_ids_to_detail_query(self, mock_db):
        """The merged entry should pass ALL label IDs to _get_transactions_for_label."""
        org_id = uuid4()
        id1, id2 = uuid4(), uuid4()

        summary_result = Mock()
        summary_result.all.return_value = [
            _summary_row(id1, "Business Expenses", "45.32", 1),
            _summary_row(id2, "Business Expenses", "0.00", 0),
        ]
        mock_db.execute.return_value = summary_result

        with patch.object(
            TaxService,
            "_get_transactions_for_label",
            new_callable=AsyncMock,
            return_value=[_txn()],
        ) as mock_detail:
            await TaxService.get_tax_deductible_summary(
                mock_db, org_id, date(2026, 1, 1), date(2026, 12, 31)
            )

        called_label_ids = mock_detail.call_args[0][4]  # positional: (db, org, start, end, label_ids)
        assert id1 in called_label_ids
        assert id2 in called_label_ids

    @pytest.mark.asyncio
    async def test_different_label_names_stay_separate(self, mock_db):
        """Rows with different label names should NOT be merged."""
        org_id = uuid4()

        summary_result = Mock()
        summary_result.all.return_value = [
            _summary_row(uuid4(), "Business Expenses", "45.32", 1),
            _summary_row(uuid4(), "Medical & Dental", "200.00", 2),
        ]
        mock_db.execute.return_value = summary_result

        with patch.object(
            TaxService,
            "_get_transactions_for_label",
            new_callable=AsyncMock,
            return_value=[_txn()],
        ):
            summaries = await TaxService.get_tax_deductible_summary(
                mock_db, org_id, date(2026, 1, 1), date(2026, 12, 31)
            )

        assert len(summaries) == 2
        names = {s.label_name for s in summaries}
        assert names == {"Business Expenses", "Medical & Dental"}

    @pytest.mark.asyncio
    async def test_empty_result_returns_empty_list(self, mock_db):
        """No matching transactions returns an empty list, not an error."""
        org_id = uuid4()

        summary_result = Mock()
        summary_result.all.return_value = []
        mock_db.execute.return_value = summary_result

        summaries = await TaxService.get_tax_deductible_summary(
            mock_db, org_id, date(2026, 1, 1), date(2026, 12, 31)
        )

        assert summaries == []


# ── transaction_count uses len(transactions) ─────────────────────────────────

@pytest.mark.unit
class TestTransactionCountDedup:
    """transaction_count must reflect the deduplicated list, not the raw DB aggregate."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_count_matches_deduplicated_list_length(self, mock_db):
        """If DB returns count=2 but dedup yields 1, summary.transaction_count == 1."""
        org_id = uuid4()

        summary_result = Mock()
        # DB aggregate says 2 (possibly inflated by duplicate transaction_labels rows)
        summary_result.all.return_value = [
            _summary_row(uuid4(), "Medical & Dental", "90.64", 2)
        ]
        mock_db.execute.return_value = summary_result

        # But the deduplicated detail query only returns 1 transaction
        with patch.object(
            TaxService,
            "_get_transactions_for_label",
            new_callable=AsyncMock,
            return_value=[_txn()],  # only 1
        ):
            summaries = await TaxService.get_tax_deductible_summary(
                mock_db, org_id, date(2026, 1, 1), date(2026, 12, 31)
            )

        assert summaries[0].transaction_count == 1  # len(transactions), not 2


# ── is_transfer transactions are included ────────────────────────────────────

@pytest.mark.unit
class TestIsTransferNotFiltered:
    """
    Transactions flagged is_transfer=True must appear if the user applied a
    tax label to them.  The service no longer filters on is_transfer.
    """

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_detail_query_called_without_is_transfer_filter(self, mock_db):
        """_get_transactions_for_label should not have an is_transfer condition."""
        import inspect
        import ast

        # Read the source of _get_transactions_for_label and assert it doesn't
        # reference is_transfer anywhere.
        source = inspect.getsource(TaxService._get_transactions_for_label)
        assert "is_transfer" not in source, (
            "_get_transactions_for_label must not filter on is_transfer; "
            "tax labels trump transfer classification"
        )

    @pytest.mark.asyncio
    async def test_summary_query_has_no_is_transfer_filter(self):
        """get_tax_deductible_summary SQL must not filter on is_transfer."""
        import inspect
        source = inspect.getsource(TaxService.get_tax_deductible_summary)
        # The source code of this method (pre-_get_transactions_for_label call)
        # must not reference is_transfer in the WHERE clause construction.
        assert "is_transfer" not in source, (
            "get_tax_deductible_summary must not filter on is_transfer"
        )


# ── only official tax labels surfaced ────────────────────────────────────────

@pytest.mark.unit
class TestTaxLabelNameFilter:
    """The summary query must restrict results to the 5 official tax label names."""

    def test_default_tax_labels_contains_expected_names(self):
        """DEFAULT_TAX_LABELS must contain the 5 standard IRS-aligned categories."""
        names = {l["name"] for l in TaxService.DEFAULT_TAX_LABELS}
        assert names == {
            "Medical & Dental",
            "Charitable Donations",
            "Business Expenses",
            "Education",
            "Home Office",
        }

    def test_summary_query_filters_by_tax_label_names(self):
        """The summary query source must reference the name filter."""
        import inspect
        source = inspect.getsource(TaxService.get_tax_deductible_summary)
        assert "tax_label_names" in source, (
            "get_tax_deductible_summary must filter labels by tax_label_names"
        )
        assert "Label.name.in_" in source, (
            "get_tax_deductible_summary must use Label.name.in_() to restrict labels"
        )
