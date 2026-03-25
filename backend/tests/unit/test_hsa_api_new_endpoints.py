"""Unit tests for new HSA API endpoints: ytd_summary, upload/download attachment."""

from datetime import date, datetime, timezone
from decimal import Decimal
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import UploadFile

from app.api.v1.hsa import (
    download_receipt_attachment,
    get_ytd_summary,
    upload_receipt_attachment,
)
from app.models.user import User


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_user(org_id=None, user_id=None):
    u = Mock(spec=User)
    u.id = user_id or uuid4()
    u.organization_id = org_id or uuid4()
    return u


def _make_receipt(**overrides):
    defaults = {
        "id": uuid4(),
        "organization_id": uuid4(),
        "user_id": uuid4(),
        "expense_date": date(2026, 1, 15),
        "amount": Decimal("250.00"),
        "description": "Dental cleaning",
        "category": "dental",
        "is_reimbursed": False,
        "reimbursed_at": None,
        "tax_year": 2026,
        "notes": None,
        "file_key": None,
        "file_name": None,
        "file_content_type": None,
        "created_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    obj = Mock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


# ── YTD Summary ───────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestGetYtdSummary:
    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        return _make_user()

    async def test_returns_zeros_when_no_hsa_accounts(self, mock_db, mock_user):
        # No HSA accounts found
        mock_db.execute.return_value.fetchall.return_value = []

        result = await get_ytd_summary(
            year=2026,
            current_user=mock_user,
            db=mock_db,
        )

        assert result["ytd_contributions"] == 0.0
        assert result["ytd_medical_expenses"] == 0.0
        assert result["hsa_accounts_found"] == 0

    async def test_sums_positive_transactions_as_contributions(self, mock_db, mock_user):
        acct_id = uuid4()
        # First execute: HSA account IDs
        acct_result = Mock()
        acct_result.fetchall.return_value = [(acct_id,)]
        # Second execute: transactions
        txn_result = Mock()
        txn_result.fetchall.return_value = [
            (Decimal("1500.00"),),
            (Decimal("800.00"),),
            (Decimal("-200.00"),),  # medical withdrawal
        ]
        mock_db.execute.side_effect = [acct_result, txn_result]

        result = await get_ytd_summary(
            year=2026,
            current_user=mock_user,
            db=mock_db,
        )

        assert result["ytd_contributions"] == pytest.approx(2300.0)
        assert result["ytd_medical_expenses"] == pytest.approx(200.0)
        assert result["hsa_accounts_found"] == 1

    async def test_defaults_to_current_year_when_no_year_param(self, mock_db, mock_user):
        from datetime import datetime as dt

        acct_result = Mock()
        acct_result.fetchall.return_value = []
        mock_db.execute.return_value.fetchall.return_value = []

        result = await get_ytd_summary(
            year=None,
            current_user=mock_user,
            db=mock_db,
        )

        assert result["year"] == dt.utcnow().year

    async def test_medical_expenses_are_absolute_value(self, mock_db, mock_user):
        acct_id = uuid4()
        acct_result = Mock()
        acct_result.fetchall.return_value = [(acct_id,)]
        txn_result = Mock()
        txn_result.fetchall.return_value = [
            (Decimal("-300.00"),),
            (Decimal("-150.00"),),
        ]
        mock_db.execute.side_effect = [acct_result, txn_result]

        result = await get_ytd_summary(
            year=2026,
            current_user=mock_user,
            db=mock_db,
        )

        assert result["ytd_contributions"] == 0.0
        assert result["ytd_medical_expenses"] == pytest.approx(450.0)


# ── Upload Attachment ─────────────────────────────────────────────────────────


@pytest.mark.unit
class TestUploadReceiptAttachment:
    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        return _make_user()

    @pytest.fixture
    def mock_storage(self):
        s = AsyncMock()
        s.save = AsyncMock(return_value="local/path/to/file.jpg")
        return s

    def _make_upload_file(self, content_type: str = "image/jpeg", filename: str = "receipt.jpg", data: bytes = b"fake-image"):
        f = Mock(spec=UploadFile)
        f.content_type = content_type
        f.filename = filename
        f.read = AsyncMock(return_value=data)
        return f

    async def test_upload_jpeg_succeeds(self, mock_db, mock_user, mock_storage):
        receipt_id = uuid4()
        receipt = _make_receipt(id=receipt_id, organization_id=mock_user.organization_id, user_id=mock_user.id)
        scalar_result = Mock()
        scalar_result.scalar_one_or_none.return_value = receipt
        mock_db.execute.return_value = scalar_result

        upload = self._make_upload_file("image/jpeg", "bill.jpg")

        result = await upload_receipt_attachment(
            receipt_id=receipt_id,
            file=upload,
            current_user=mock_user,
            db=mock_db,
            storage=mock_storage,
        )

        mock_storage.save.assert_awaited_once()
        assert result["file_name"] == "bill.jpg"
        assert result["file_content_type"] == "image/jpeg"

    async def test_upload_pdf_succeeds(self, mock_db, mock_user, mock_storage):
        receipt_id = uuid4()
        receipt = _make_receipt(id=receipt_id, organization_id=mock_user.organization_id, user_id=mock_user.id)
        scalar_result = Mock()
        scalar_result.scalar_one_or_none.return_value = receipt
        mock_db.execute.return_value = scalar_result

        upload = self._make_upload_file("application/pdf", "claim.pdf")

        result = await upload_receipt_attachment(
            receipt_id=receipt_id,
            file=upload,
            current_user=mock_user,
            db=mock_db,
            storage=mock_storage,
        )

        assert result["file_content_type"] == "application/pdf"

    async def test_upload_unsupported_mime_returns_415(self, mock_db, mock_user, mock_storage):
        from fastapi import HTTPException

        upload = self._make_upload_file("text/plain", "notes.txt")

        with pytest.raises(HTTPException) as exc:
            await upload_receipt_attachment(
                receipt_id=uuid4(),
                file=upload,
                current_user=mock_user,
                db=mock_db,
                storage=mock_storage,
            )

        assert exc.value.status_code == 415

    async def test_upload_receipt_not_found_returns_404(self, mock_db, mock_user, mock_storage):
        from fastapi import HTTPException

        scalar_result = Mock()
        scalar_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = scalar_result

        upload = self._make_upload_file("image/jpeg")

        with pytest.raises(HTTPException) as exc:
            await upload_receipt_attachment(
                receipt_id=uuid4(),
                file=upload,
                current_user=mock_user,
                db=mock_db,
                storage=mock_storage,
            )

        assert exc.value.status_code == 404

    async def test_upload_file_too_large_returns_413(self, mock_db, mock_user, mock_storage):
        from fastapi import HTTPException

        receipt_id = uuid4()
        receipt = _make_receipt(id=receipt_id)
        scalar_result = Mock()
        scalar_result.scalar_one_or_none.return_value = receipt
        mock_db.execute.return_value = scalar_result

        # 21 MB file exceeds 20 MB cap
        oversized = self._make_upload_file("image/jpeg", "huge.jpg", b"x" * (21 * 1024 * 1024))

        with pytest.raises(HTTPException) as exc:
            await upload_receipt_attachment(
                receipt_id=receipt_id,
                file=oversized,
                current_user=mock_user,
                db=mock_db,
                storage=mock_storage,
            )

        assert exc.value.status_code == 413


# ── Download Attachment ───────────────────────────────────────────────────────


@pytest.mark.unit
class TestDownloadReceiptAttachment:
    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        return _make_user()

    @pytest.fixture
    def mock_storage(self):
        s = AsyncMock()
        s.load = AsyncMock(return_value=b"image-bytes")
        return s

    async def test_download_returns_streaming_response(self, mock_db, mock_user, mock_storage):
        from fastapi.responses import StreamingResponse

        receipt_id = uuid4()
        receipt = _make_receipt(
            id=receipt_id,
            organization_id=mock_user.organization_id,
            user_id=mock_user.id,
            file_key="hsa-receipts/org/receipt/uuid.jpg",
            file_name="bill.jpg",
            file_content_type="image/jpeg",
        )
        scalar_result = Mock()
        scalar_result.scalar_one_or_none.return_value = receipt
        mock_db.execute.return_value = scalar_result

        response = await download_receipt_attachment(
            receipt_id=receipt_id,
            current_user=mock_user,
            db=mock_db,
            storage=mock_storage,
        )

        assert isinstance(response, StreamingResponse)
        assert response.media_type == "image/jpeg"

    async def test_download_receipt_without_attachment_returns_404(self, mock_db, mock_user, mock_storage):
        from fastapi import HTTPException

        receipt_id = uuid4()
        receipt = _make_receipt(id=receipt_id, file_key=None)
        scalar_result = Mock()
        scalar_result.scalar_one_or_none.return_value = receipt
        mock_db.execute.return_value = scalar_result

        with pytest.raises(HTTPException) as exc:
            await download_receipt_attachment(
                receipt_id=receipt_id,
                current_user=mock_user,
                db=mock_db,
                storage=mock_storage,
            )

        assert exc.value.status_code == 404

    async def test_download_receipt_not_found_returns_404(self, mock_db, mock_user, mock_storage):
        from fastapi import HTTPException

        scalar_result = Mock()
        scalar_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = scalar_result

        with pytest.raises(HTTPException) as exc:
            await download_receipt_attachment(
                receipt_id=uuid4(),
                current_user=mock_user,
                db=mock_db,
                storage=mock_storage,
            )

        assert exc.value.status_code == 404

    async def test_download_storage_file_not_found_returns_404(self, mock_db, mock_user, mock_storage):
        from fastapi import HTTPException

        receipt_id = uuid4()
        receipt = _make_receipt(
            id=receipt_id,
            file_key="hsa-receipts/missing.jpg",
            file_name="missing.jpg",
            file_content_type="image/jpeg",
        )
        scalar_result = Mock()
        scalar_result.scalar_one_or_none.return_value = receipt
        mock_db.execute.return_value = scalar_result
        mock_storage.load = AsyncMock(side_effect=FileNotFoundError)

        with pytest.raises(HTTPException) as exc:
            await download_receipt_attachment(
                receipt_id=receipt_id,
                current_user=mock_user,
                db=mock_db,
                storage=mock_storage,
            )

        assert exc.value.status_code == 404
