"""Tests for GDPR export streaming (no truncation)."""

import io
import csv
import zipfile

import pytest


class TestExportStreaming:
    """Verify data export returns all data without truncation."""

    @pytest.mark.asyncio
    async def test_export_includes_all_transactions(
        self, authenticated_client, bulk_transactions
    ):
        """Insert 200 transactions → /settings/export ZIP contains all 200 in CSV."""
        await bulk_transactions(200)

        response = await authenticated_client.get("/api/v1/settings/export")
        assert response.status_code == 200

        # Parse ZIP
        zip_bytes = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_bytes) as zf:
            csv_files = [name for name in zf.namelist() if name.endswith(".csv")]
            assert any("transactions" in f for f in csv_files), f"Expected transactions CSV, got {csv_files}"

            txn_file = next(f for f in csv_files if "transactions" in f)
            with zf.open(txn_file) as f:
                reader = csv.reader(io.TextIOWrapper(f, encoding="utf-8"))
                rows = list(reader)
                # First row is header, rest are data
                data_rows = rows[1:]
                assert len(data_rows) == 200, f"Expected 200 transactions, got {len(data_rows)}"

    @pytest.mark.asyncio
    async def test_export_no_truncation_header(self, authenticated_client, bulk_transactions):
        """Export should not include X-Export-Truncated header."""
        await bulk_transactions(50)

        response = await authenticated_client.get("/api/v1/settings/export")
        assert response.status_code == 200
        assert "X-Export-Truncated" not in response.headers
