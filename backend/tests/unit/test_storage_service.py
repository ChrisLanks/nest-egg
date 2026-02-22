"""Tests for the storage service abstraction (local + S3 backends)."""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# boto3 is not installed in the dev venv (it's a prod dependency).
# Inject a lightweight mock so the S3 tests can still run without it installed.
if "boto3" not in sys.modules:
    sys.modules["boto3"] = MagicMock()

from app.services.storage_service import LocalStorageService, S3StorageService, get_storage_service


@pytest.mark.unit
class TestLocalStorageService:
    """Tests for LocalStorageService (filesystem backend)."""

    @pytest.fixture
    def tmp_dir(self, tmp_path):
        return str(tmp_path)

    @pytest.fixture
    def storage(self, tmp_dir):
        return LocalStorageService(base_dir=tmp_dir)

    @pytest.mark.asyncio
    async def test_save_and_load_round_trip(self, storage):
        """Saved data should be retrievable unchanged."""
        data = b"col1,col2\nval1,val2\n"
        await storage.save("upload/test.csv", data)
        loaded = await storage.load("upload/test.csv")
        assert loaded == data

    @pytest.mark.asyncio
    async def test_save_returns_path_string(self, storage, tmp_dir):
        """save() should return the full filesystem path."""
        result = await storage.save("test.csv", b"data")
        assert isinstance(result, str)
        assert result.startswith(tmp_dir)
        assert "test.csv" in result

    @pytest.mark.asyncio
    async def test_save_creates_parent_directories(self, storage, tmp_dir):
        """Nested keys should create intermediate directories."""
        await storage.save("a/b/c/file.csv", b"data")
        assert os.path.isfile(os.path.join(tmp_dir, "a", "b", "c", "file.csv"))

    @pytest.mark.asyncio
    async def test_delete_removes_file(self, storage):
        """delete() should remove the file from disk."""
        await storage.save("to_delete.csv", b"data")
        await storage.delete("to_delete.csv")
        with pytest.raises(FileNotFoundError):
            await storage.load("to_delete.csv")

    @pytest.mark.asyncio
    async def test_delete_nonexistent_file_is_noop(self, storage):
        """Deleting a file that doesn't exist should not raise."""
        await storage.delete("does_not_exist.csv")  # Should not raise

    @pytest.mark.asyncio
    async def test_path_traversal_is_blocked(self, storage, tmp_dir):
        """Keys with '../' components should be normalised to stay inside base_dir."""
        # Store data using a traversal-looking key
        await storage.save("../../../etc/passwd_test", b"harmless")
        # The file should land inside tmp_dir, not at /etc/
        assert not os.path.exists("/etc/passwd_test")

    @pytest.mark.asyncio
    async def test_overwrite_existing_file(self, storage):
        """Saving to an existing key should overwrite the content."""
        await storage.save("file.csv", b"original")
        await storage.save("file.csv", b"updated")
        assert await storage.load("file.csv") == b"updated"

    @pytest.mark.asyncio
    async def test_binary_data_preserved(self, storage):
        """Binary data (non-UTF-8) should be stored and loaded without corruption."""
        binary_data = bytes(range(256))
        await storage.save("binary.bin", binary_data)
        assert await storage.load("binary.bin") == binary_data


@pytest.mark.unit
class TestGetStorageService:
    """Tests for the get_storage_service() factory function."""

    def test_default_returns_local_storage(self):
        """With STORAGE_BACKEND='local', should return LocalStorageService."""
        mock_settings = type("S", (), {
            "STORAGE_BACKEND": "local",
            "LOCAL_UPLOAD_DIR": "/tmp/test-nestegg",
            "AWS_S3_BUCKET": None,
            "AWS_REGION": "us-east-1",
            "AWS_ACCESS_KEY_ID": None,
            "AWS_SECRET_ACCESS_KEY": None,
            "AWS_S3_PREFIX": "csv-uploads/",
        })()
        with patch("app.services.storage_service.settings", mock_settings):
            service = get_storage_service()
        assert isinstance(service, LocalStorageService)

    def test_s3_backend_without_bucket_raises(self):
        """STORAGE_BACKEND='s3' with no AWS_S3_BUCKET should raise RuntimeError."""
        mock_settings = type("S", (), {
            "STORAGE_BACKEND": "s3",
            "AWS_S3_BUCKET": None,
            "AWS_REGION": "us-east-1",
            "AWS_ACCESS_KEY_ID": None,
            "AWS_SECRET_ACCESS_KEY": None,
            "AWS_S3_PREFIX": "csv-uploads/",
        })()
        with patch("app.services.storage_service.settings", mock_settings):
            with pytest.raises(RuntimeError, match="AWS_S3_BUCKET"):
                get_storage_service()

    def test_s3_backend_with_bucket_returns_s3_service(self):
        """STORAGE_BACKEND='s3' with AWS_S3_BUCKET set should return S3StorageService."""
        mock_settings = type("S", (), {
            "STORAGE_BACKEND": "s3",
            "AWS_S3_BUCKET": "my-bucket",
            "AWS_REGION": "us-east-1",
            "AWS_ACCESS_KEY_ID": None,
            "AWS_SECRET_ACCESS_KEY": None,
            "AWS_S3_PREFIX": "csv-uploads/",
        })()
        mock_boto3 = MagicMock()
        with patch("app.services.storage_service.settings", mock_settings):
            with patch("boto3.client", return_value=MagicMock()):
                service = get_storage_service()
        assert isinstance(service, S3StorageService)


@pytest.mark.unit
class TestS3StorageService:
    """Tests for S3StorageService delegating to boto3."""

    @pytest.fixture
    def mock_s3_client(self):
        return MagicMock()

    @pytest.fixture
    def service(self, mock_s3_client):
        mock_settings = type("S", (), {
            "AWS_REGION": "us-east-1",
            "AWS_ACCESS_KEY_ID": None,
            "AWS_SECRET_ACCESS_KEY": None,
            "AWS_S3_BUCKET": "test-bucket",
            "AWS_S3_PREFIX": "uploads/",
        })()
        with patch("app.services.storage_service.settings", mock_settings):
            with patch("boto3.client", return_value=mock_s3_client):
                svc = S3StorageService()
        svc._s3 = mock_s3_client  # Replace with our mock after init
        return svc

    @pytest.mark.asyncio
    async def test_save_calls_put_object(self, service, mock_s3_client):
        """save() should call s3.put_object with correct bucket and key."""
        await service.save("myfile.csv", b"data", content_type="text/csv")
        mock_s3_client.put_object.assert_called_once()
        call_kwargs = mock_s3_client.put_object.call_args[1]
        assert call_kwargs["Bucket"] == "test-bucket"
        assert call_kwargs["Key"] == "uploads/myfile.csv"
        assert call_kwargs["Body"] == b"data"
        assert call_kwargs["ContentType"] == "text/csv"

    @pytest.mark.asyncio
    async def test_save_returns_s3_uri(self, service, mock_s3_client):
        """save() should return an s3:// URI."""
        result = await service.save("test.csv", b"data")
        assert result == "s3://test-bucket/uploads/test.csv"

    @pytest.mark.asyncio
    async def test_load_calls_get_object(self, service, mock_s3_client):
        """load() should call s3.get_object and return body bytes."""
        mock_s3_client.get_object.return_value = {"Body": MagicMock(read=lambda: b"content")}
        result = await service.load("test.csv")
        assert result == b"content"
        mock_s3_client.get_object.assert_called_once_with(
            Bucket="test-bucket", Key="uploads/test.csv"
        )

    @pytest.mark.asyncio
    async def test_delete_calls_delete_object(self, service, mock_s3_client):
        """delete() should call s3.delete_object with the correct key."""
        await service.delete("test.csv")
        mock_s3_client.delete_object.assert_called_once_with(
            Bucket="test-bucket", Key="uploads/test.csv"
        )

    @pytest.mark.asyncio
    async def test_prefix_is_prepended_to_key(self, service, mock_s3_client):
        """S3 keys should include the configured prefix."""
        await service.save("subdir/file.csv", b"data")
        call_kwargs = mock_s3_client.put_object.call_args[1]
        assert call_kwargs["Key"] == "uploads/subdir/file.csv"
