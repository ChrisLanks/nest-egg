"""Unit tests for CSV import API endpoints."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.csv_import import (
    check_csv_row_limit,
    import_csv,
    preview_csv_import,
    validate_csv,
    validate_csv_file,
)
from app.models.user import User


@pytest.fixture
def mock_user():
    user = Mock(spec=User)
    user.id = uuid4()
    user.organization_id = uuid4()
    return user


@pytest.fixture
def mock_db():
    db = AsyncMock()
    return db


@pytest.fixture
def mock_http_request():
    req = MagicMock()
    req.client = MagicMock()
    req.client.host = "127.0.0.1"
    req.headers = {}
    return req


def _make_upload_file(
    filename="data.csv", content_type="text/csv", content=b"date,amount\n2024-01-01,50"
):
    f = MagicMock()
    f.filename = filename
    f.content_type = content_type
    f.read = AsyncMock(return_value=content)
    f.seek = AsyncMock(return_value=None)
    return f


class TestCheckCsvRowLimit:
    """Tests for check_csv_row_limit helper."""

    def test_passes_when_under_limit(self):
        csv_content = "date,amount\n" + "2024-01-01,50\n" * 100
        check_csv_row_limit(csv_content)  # Should not raise

    def test_passes_for_exactly_max_rows(self):
        from app.api.v1.csv_import import MAX_CSV_ROWS
        csv_content = "date,amount\n" + "2024-01-01,50\n" * MAX_CSV_ROWS
        check_csv_row_limit(csv_content)  # Should not raise

    def test_raises_400_when_exceeds_limit(self):
        from app.api.v1.csv_import import MAX_CSV_ROWS
        csv_content = "date,amount\n" + "2024-01-01,50\n" * (MAX_CSV_ROWS + 1)
        with pytest.raises(HTTPException) as exc_info:
            check_csv_row_limit(csv_content)
        assert exc_info.value.status_code == 400
        assert "too large" in exc_info.value.detail.lower()

    def test_blank_lines_are_not_counted(self):
        # Only 2 real data rows; extra blank lines should not count
        csv_content = "date,amount\n2024-01-01,50\n\n2024-01-02,60\n\n"
        check_csv_row_limit(csv_content)  # Should not raise

    def test_empty_csv_passes(self):
        check_csv_row_limit("")  # Should not raise


class TestValidateCsvFile:
    """Tests for validate_csv_file helper."""

    def test_no_filename_raises(self):
        f = _make_upload_file(filename=None)
        f.filename = None
        with pytest.raises(HTTPException) as exc_info:
            validate_csv_file(f)
        assert exc_info.value.status_code == 400
        assert "Filename" in exc_info.value.detail

    def test_non_csv_extension_raises(self):
        f = _make_upload_file(filename="data.xlsx")
        with pytest.raises(HTTPException) as exc_info:
            validate_csv_file(f)
        assert exc_info.value.status_code == 400
        assert "CSV" in exc_info.value.detail

    @patch("app.api.v1.csv_import.input_sanitization_service")
    def test_unsafe_filename_raises(self, mock_sanitize):
        mock_sanitize.sanitize_filename.return_value = "safe.csv"  # differs from original
        f = _make_upload_file(filename="../etc/passwd.csv")
        with pytest.raises(HTTPException) as exc_info:
            validate_csv_file(f)
        assert exc_info.value.status_code == 400
        assert "unsafe" in exc_info.value.detail.lower()

    @patch("app.api.v1.csv_import.input_sanitization_service")
    def test_invalid_content_type_raises(self, mock_sanitize):
        mock_sanitize.sanitize_filename.return_value = "data.csv"
        f = _make_upload_file(content_type="application/json")
        with pytest.raises(HTTPException) as exc_info:
            validate_csv_file(f)
        assert exc_info.value.status_code == 400
        assert "content type" in exc_info.value.detail.lower()

    @patch("app.api.v1.csv_import.input_sanitization_service")
    def test_valid_csv_passes(self, mock_sanitize):
        mock_sanitize.sanitize_filename.return_value = "data.csv"
        f = _make_upload_file()
        validate_csv_file(f)  # Should not raise

    @patch("app.api.v1.csv_import.input_sanitization_service")
    def test_valid_content_type_text_plain(self, mock_sanitize):
        mock_sanitize.sanitize_filename.return_value = "data.csv"
        f = _make_upload_file(content_type="text/plain")
        validate_csv_file(f)

    @patch("app.api.v1.csv_import.input_sanitization_service")
    def test_no_content_type_passes(self, mock_sanitize):
        mock_sanitize.sanitize_filename.return_value = "data.csv"
        f = _make_upload_file(content_type=None)
        f.content_type = None
        validate_csv_file(f)


class TestValidateCsvEndpoint:
    """Tests for POST /csv-import/validate."""

    @pytest.mark.asyncio
    @patch("app.api.v1.csv_import.rate_limit_service")
    @patch("app.api.v1.csv_import.validate_csv_file")
    @patch("app.api.v1.csv_import.csv_import_service")
    async def test_valid_csv_returns_message(
        self, mock_csv_svc, mock_validate, mock_rate_limit, mock_user, mock_http_request
    ):
        mock_rate_limit.check_rate_limit = AsyncMock()
        mock_csv_svc.validate_csv_format.return_value = {"is_valid": True, "errors": []}

        file = _make_upload_file()
        result = await validate_csv(mock_http_request, file, mock_user)
        assert result["message"] == "CSV file is valid"

    @pytest.mark.asyncio
    @patch("app.api.v1.csv_import.rate_limit_service")
    @patch("app.api.v1.csv_import.validate_csv_file")
    @patch("app.api.v1.csv_import.csv_import_service")
    async def test_invalid_csv_raises_400(
        self, mock_csv_svc, mock_validate, mock_rate_limit, mock_user, mock_http_request
    ):
        mock_rate_limit.check_rate_limit = AsyncMock()
        mock_csv_svc.validate_csv_format.return_value = {
            "is_valid": False,
            "errors": ["Missing date column"],
        }

        file = _make_upload_file()
        with pytest.raises(HTTPException) as exc_info:
            await validate_csv(mock_http_request, file, mock_user)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    @patch("app.api.v1.csv_import.rate_limit_service")
    @patch("app.api.v1.csv_import.validate_csv_file")
    async def test_read_error_raises_400(
        self, mock_validate, mock_rate_limit, mock_user, mock_http_request
    ):
        mock_rate_limit.check_rate_limit = AsyncMock()
        file = _make_upload_file()
        # First read (in validate_csv_content) returns valid bytes; second read raises
        file.read = AsyncMock(side_effect=[b"date,amount\n2024-01-01,50", Exception("read error")])

        with pytest.raises(HTTPException) as exc_info:
            await validate_csv(mock_http_request, file, mock_user)
        assert exc_info.value.status_code == 400


class TestPreviewCsvEndpoint:
    """Tests for POST /csv-import/preview."""

    @pytest.mark.asyncio
    @patch("app.api.v1.csv_import.rate_limit_service")
    @patch("app.api.v1.csv_import.validate_csv_file")
    @patch("app.api.v1.csv_import.csv_import_service")
    async def test_preview_returns_data(
        self, mock_csv_svc, mock_validate, mock_rate_limit, mock_user, mock_http_request
    ):
        mock_rate_limit.check_rate_limit = AsyncMock()
        mock_csv_svc.preview_csv = AsyncMock(
            return_value={
                "columns": ["date", "amount"],
                "sample_rows": [],
                "row_count": 5,
                "detected_mapping": {"date": "date", "amount": "amount"},
            }
        )

        file = _make_upload_file()
        result = await preview_csv_import(mock_http_request, file, None, mock_user)
        assert result["row_count"] == 5


class TestImportCsvEndpoint:
    """Tests for POST /csv-import/import."""

    @pytest.mark.asyncio
    @patch("app.api.v1.csv_import.rate_limit_service")
    @patch("app.api.v1.csv_import.validate_csv_file")
    @patch("app.api.v1.csv_import.csv_import_service")
    async def test_account_not_found_raises_404(
        self, mock_csv_svc, mock_validate, mock_rate_limit, mock_user, mock_db, mock_http_request
    ):
        mock_rate_limit.check_rate_limit = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        file = _make_upload_file()
        with pytest.raises(HTTPException) as exc_info:
            await import_csv(uuid4(), mock_http_request, file, None, True, mock_user, mock_db)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @patch("app.api.v1.csv_import.rate_limit_service")
    @patch("app.api.v1.csv_import.validate_csv_file")
    @patch("app.api.v1.csv_import.csv_import_service")
    async def test_invalid_csv_format_raises_400(
        self, mock_csv_svc, mock_validate, mock_rate_limit, mock_user, mock_db, mock_http_request
    ):
        mock_rate_limit.check_rate_limit = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = uuid4()  # account found
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_csv_svc.validate_csv_format.return_value = {
            "is_valid": False,
            "errors": ["Bad format"],
        }

        file = _make_upload_file()
        with pytest.raises(HTTPException) as exc_info:
            await import_csv(
                uuid4(),
                mock_http_request,
                file,
                {"date": "date", "amount": "amount"},
                True,
                mock_user,
                mock_db,
            )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    @patch("app.api.v1.csv_import.rate_limit_service")
    @patch("app.api.v1.csv_import.validate_csv_file")
    @patch("app.api.v1.csv_import.csv_import_service")
    async def test_successful_import(
        self, mock_csv_svc, mock_validate, mock_rate_limit, mock_user, mock_db, mock_http_request
    ):
        mock_rate_limit.check_rate_limit = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = uuid4()
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_csv_svc.validate_csv_format.return_value = {"is_valid": True, "errors": []}
        mock_csv_svc.import_csv = AsyncMock(
            return_value={
                "imported": 10,
                "skipped": 2,
                "errors": 0,
            }
        )

        file = _make_upload_file()
        result = await import_csv(
            uuid4(),
            mock_http_request,
            file,
            {"date": "date", "amount": "amount"},
            True,
            mock_user,
            mock_db,
        )
        assert result["imported"] == 10

    @pytest.mark.asyncio
    @patch("app.api.v1.csv_import.rate_limit_service")
    @patch("app.api.v1.csv_import.validate_csv_file")
    @patch("app.api.v1.csv_import.csv_import_service")
    async def test_auto_detect_mapping_when_not_provided(
        self, mock_csv_svc, mock_validate, mock_rate_limit, mock_user, mock_db, mock_http_request
    ):
        mock_rate_limit.check_rate_limit = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = uuid4()
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_csv_svc.validate_csv_format.return_value = {"is_valid": True, "errors": []}
        mock_csv_svc.preview_csv = AsyncMock(
            return_value={
                "detected_mapping": {"date": "Date", "amount": "Amount"},
            }
        )
        mock_csv_svc.import_csv = AsyncMock(return_value={"imported": 5, "skipped": 0, "errors": 0})

        file = _make_upload_file()
        result = await import_csv(uuid4(), mock_http_request, file, None, True, mock_user, mock_db)
        assert result["imported"] == 5

    @pytest.mark.asyncio
    @patch("app.api.v1.csv_import.rate_limit_service")
    @patch("app.api.v1.csv_import.validate_csv_file")
    @patch("app.api.v1.csv_import.csv_import_service")
    async def test_auto_detect_missing_required_columns_raises_400(
        self, mock_csv_svc, mock_validate, mock_rate_limit, mock_user, mock_db, mock_http_request
    ):
        mock_rate_limit.check_rate_limit = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = uuid4()
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_csv_svc.validate_csv_format.return_value = {"is_valid": True, "errors": []}
        mock_csv_svc.preview_csv = AsyncMock(
            return_value={
                "detected_mapping": {},  # nothing detected
            }
        )

        file = _make_upload_file()
        with pytest.raises(HTTPException) as exc_info:
            await import_csv(uuid4(), mock_http_request, file, None, True, mock_user, mock_db)
        assert exc_info.value.status_code == 400
        assert "auto-detect" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    @patch("app.api.v1.csv_import.rate_limit_service")
    @patch("app.api.v1.csv_import.validate_csv_file")
    @patch("app.api.v1.csv_import.csv_import_service")
    async def test_import_value_error_raises_400(
        self, mock_csv_svc, mock_validate, mock_rate_limit, mock_user, mock_db, mock_http_request
    ):
        mock_rate_limit.check_rate_limit = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = uuid4()
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_csv_svc.validate_csv_format.return_value = {"is_valid": True, "errors": []}
        mock_csv_svc.import_csv = AsyncMock(side_effect=ValueError("Bad data"))

        file = _make_upload_file()
        with pytest.raises(HTTPException) as exc_info:
            await import_csv(
                uuid4(),
                mock_http_request,
                file,
                {"date": "date", "amount": "amount"},
                True,
                mock_user,
                mock_db,
            )
        assert exc_info.value.status_code == 400
