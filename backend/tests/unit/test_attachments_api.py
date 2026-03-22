"""Unit tests for attachments API endpoints."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import UploadFile
from fastapi.responses import RedirectResponse, StreamingResponse

from app.api.v1.attachments import (
    delete_attachment,
    download_attachment,
    get_attachment,
    list_attachments,
    upload_attachment,
)
from app.models.user import User


def _make_attachment(**overrides):
    """Create a mock attachment object with model_validate-compatible attrs."""
    defaults = {
        "id": uuid4(),
        "organization_id": uuid4(),
        "transaction_id": uuid4(),
        "user_id": uuid4(),
        "filename": "stored_abc123.jpg",
        "original_filename": "receipt.jpg",
        "content_type": "image/jpeg",
        "file_size": 204800,
        "created_at": datetime.now(timezone.utc),
        "ocr_status": None,
        "ocr_data": None,
    }
    defaults.update(overrides)
    obj = Mock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


@pytest.mark.unit
class TestUploadAttachment:
    """Tests for upload_attachment endpoint."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        return Mock(spec=User)

    @pytest.fixture
    def mock_storage(self):
        return AsyncMock()

    @pytest.mark.asyncio
    @patch("app.api.v1.attachments.attachment_service.upload_attachment")
    async def test_upload_success(self, mock_upload, mock_db, mock_user, mock_storage):
        """Should upload file and return attachment response."""
        transaction_id = uuid4()
        mock_attachment = _make_attachment(transaction_id=transaction_id)
        mock_upload.return_value = mock_attachment

        mock_file = Mock(spec=UploadFile)
        mock_file.filename = "receipt.jpg"
        mock_file.content_type = "image/jpeg"

        result = await upload_attachment(
            transaction_id=transaction_id,
            file=mock_file,
            current_user=mock_user,
            db=mock_db,
            storage=mock_storage,
        )

        mock_upload.assert_awaited_once_with(
            db=mock_db,
            transaction_id=transaction_id,
            user=mock_user,
            file=mock_file,
            storage=mock_storage,
        )
        assert result.id == mock_attachment.id
        assert result.transaction_id == transaction_id
        assert result.original_filename == mock_attachment.original_filename


@pytest.mark.unit
class TestListAttachments:
    """Tests for list_attachments endpoint."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        return Mock(spec=User)

    @pytest.mark.asyncio
    @patch("app.api.v1.attachments.attachment_service.list_attachments")
    async def test_returns_attachments(self, mock_list, mock_db, mock_user):
        """Should return list of attachments for a transaction."""
        transaction_id = uuid4()
        attachments = [
            _make_attachment(transaction_id=transaction_id),
            _make_attachment(transaction_id=transaction_id),
        ]
        mock_list.return_value = attachments

        result = await list_attachments(
            transaction_id=transaction_id,
            current_user=mock_user,
            db=mock_db,
        )

        mock_list.assert_awaited_once_with(
            db=mock_db,
            transaction_id=transaction_id,
            user=mock_user,
        )
        assert len(result.attachments) == 2
        assert result.attachments[0].id == attachments[0].id
        assert result.attachments[1].id == attachments[1].id

    @pytest.mark.asyncio
    @patch("app.api.v1.attachments.attachment_service.list_attachments")
    async def test_returns_empty_list(self, mock_list, mock_db, mock_user):
        """Should return empty list when no attachments exist."""
        mock_list.return_value = []

        result = await list_attachments(
            transaction_id=uuid4(),
            current_user=mock_user,
            db=mock_db,
        )

        assert result.attachments == []


@pytest.mark.unit
class TestGetAttachment:
    """Tests for get_attachment endpoint."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        return Mock(spec=User)

    @pytest.mark.asyncio
    @patch("app.api.v1.attachments.attachment_service.get_attachment")
    async def test_returns_attachment_metadata(self, mock_get, mock_db, mock_user):
        """Should return metadata for a single attachment."""
        attachment_id = uuid4()
        mock_attachment = _make_attachment(id=attachment_id)
        mock_get.return_value = mock_attachment

        result = await get_attachment(
            attachment_id=attachment_id,
            current_user=mock_user,
            db=mock_db,
        )

        mock_get.assert_awaited_once_with(
            db=mock_db,
            attachment_id=attachment_id,
            user=mock_user,
        )
        assert result.id == attachment_id
        assert result.filename == mock_attachment.filename
        assert result.file_size == mock_attachment.file_size


@pytest.mark.unit
class TestDownloadAttachment:
    """Tests for download_attachment endpoint."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        return Mock(spec=User)

    @pytest.fixture
    def mock_storage(self):
        return AsyncMock()

    @pytest.mark.asyncio
    @patch("app.api.v1.attachments.attachment_service.get_download_url")
    async def test_s3_returns_redirect(self, mock_download, mock_db, mock_user, mock_storage):
        """Should return a redirect response for S3-backed storage."""
        attachment_id = uuid4()
        presigned_url = "https://s3.amazonaws.com/bucket/key?signature=abc"
        mock_download.return_value = {"url": presigned_url}

        result = await download_attachment(
            attachment_id=attachment_id,
            current_user=mock_user,
            db=mock_db,
            storage=mock_storage,
        )

        mock_download.assert_awaited_once_with(
            db=mock_db,
            attachment_id=attachment_id,
            user=mock_user,
            storage=mock_storage,
        )
        assert isinstance(result, RedirectResponse)
        assert result.status_code == 302
        assert result.headers["location"] == presigned_url

    @pytest.mark.asyncio
    @patch("app.api.v1.attachments.attachment_service.get_download_url")
    async def test_local_returns_streaming_response(
        self, mock_download, mock_db, mock_user, mock_storage
    ):
        """Should return a streaming response for local storage."""
        attachment_id = uuid4()
        file_bytes = b"fake-image-data"
        mock_download.return_value = {
            "storage_key": "attachments/abc123.jpg",
            "content_type": "image/jpeg",
            "filename": "test.jpg",
        }
        mock_storage.load.return_value = file_bytes

        result = await download_attachment(
            attachment_id=attachment_id,
            current_user=mock_user,
            db=mock_db,
            storage=mock_storage,
        )

        mock_storage.load.assert_awaited_once_with("attachments/abc123.jpg")
        assert isinstance(result, StreamingResponse)
        assert result.media_type == "image/jpeg"
        assert result.headers["content-disposition"] == 'attachment; filename="test.jpg"'
        assert result.headers["content-length"] == str(len(file_bytes))


@pytest.mark.unit
class TestDeleteAttachment:
    """Tests for delete_attachment endpoint."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        return Mock(spec=User)

    @pytest.fixture
    def mock_storage(self):
        return AsyncMock()

    @pytest.mark.asyncio
    @patch("app.api.v1.attachments.attachment_service.delete_attachment")
    async def test_delete_calls_service(self, mock_delete, mock_db, mock_user, mock_storage):
        """Should call delete service with correct arguments."""
        attachment_id = uuid4()

        result = await delete_attachment(
            attachment_id=attachment_id,
            current_user=mock_user,
            db=mock_db,
            storage=mock_storage,
        )

        mock_delete.assert_awaited_once_with(
            db=mock_db,
            attachment_id=attachment_id,
            user=mock_user,
            storage=mock_storage,
        )
        assert result is None
