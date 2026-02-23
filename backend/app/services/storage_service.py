"""
Storage service abstraction for file uploads.

Supports two backends, selected by STORAGE_BACKEND env var:
  - "local" (default): stores files in LOCAL_UPLOAD_DIR — for dev and single-instance deployments
  - "s3": stores files in AWS S3 — uses IAM instance role when no explicit credentials are set

Usage (in FastAPI endpoints)::

    from app.services.storage_service import get_storage_service, StorageService

    @router.post("/upload")
    async def upload(
        file: UploadFile = File(...),
        storage: StorageService = Depends(get_storage_service),
    ):
        key = f"uploads/{uuid4()}/{file.filename}"
        data = await file.read()
        url = await storage.save(key, data, content_type=file.content_type or "text/csv")
        ...

Dev (default)::

    STORAGE_BACKEND=local
    LOCAL_UPLOAD_DIR=/tmp/nestegg-uploads

Prod (S3 with IAM role — no hardcoded credentials)::

    STORAGE_BACKEND=s3
    AWS_S3_BUCKET=my-nestegg-uploads
    AWS_REGION=us-east-1
    AWS_S3_PREFIX=csv-uploads/
    # Leave AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY unset to use the instance IAM role

Prod (S3 with explicit credentials)::

    STORAGE_BACKEND=s3
    AWS_S3_BUCKET=my-nestegg-uploads
    AWS_ACCESS_KEY_ID=AKIA...
    AWS_SECRET_ACCESS_KEY=...
"""

import os
from typing import Protocol, runtime_checkable

from app.config import settings


@runtime_checkable
class StorageService(Protocol):
    """Protocol for file storage backends."""

    async def save(self, key: str, data: bytes, content_type: str = "text/csv") -> str:
        """
        Store ``data`` under ``key``.

        Returns:
            A reference string (local path or S3 URI) for logging/auditing.
        """
        ...

    async def load(self, key: str) -> bytes:
        """Load and return the raw bytes stored at ``key``."""
        ...

    async def delete(self, key: str) -> None:
        """Delete the object stored at ``key``."""
        ...


class LocalStorageService:
    """
    Stores files on the local filesystem under ``LOCAL_UPLOAD_DIR``.

    Suitable for development and single-instance deployments.
    """

    def __init__(self, base_dir: str = settings.LOCAL_UPLOAD_DIR):
        self._base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    def _full_path(self, key: str) -> str:
        # Prevent path traversal
        safe_key = os.path.normpath(key).lstrip("/")
        return os.path.join(self._base_dir, safe_key)

    async def save(self, key: str, data: bytes, content_type: str = "text/csv") -> str:
        path = self._full_path(key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        return path

    async def load(self, key: str) -> bytes:
        path = self._full_path(key)
        with open(path, "rb") as f:
            return f.read()

    async def delete(self, key: str) -> None:
        path = self._full_path(key)
        if os.path.exists(path):
            os.remove(path)


class S3StorageService:
    """
    Stores files in AWS S3.

    Uses the IAM instance role automatically when ``AWS_ACCESS_KEY_ID`` is not set,
    which is the recommended approach for EC2/ECS/Lambda deployments.
    """

    def __init__(self):
        import boto3  # lazy import — not installed in dev by default unless needed

        kwargs: dict = {"region_name": settings.AWS_REGION}
        if settings.AWS_ACCESS_KEY_ID:
            kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
            kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY

        self._s3 = boto3.client("s3", **kwargs)
        self._bucket = settings.AWS_S3_BUCKET
        self._prefix = settings.AWS_S3_PREFIX

    def _full_key(self, key: str) -> str:
        return f"{self._prefix}{key}"

    async def save(self, key: str, data: bytes, content_type: str = "text/csv") -> str:
        full_key = self._full_key(key)
        self._s3.put_object(
            Bucket=self._bucket,
            Key=full_key,
            Body=data,
            ContentType=content_type,
        )
        return f"s3://{self._bucket}/{full_key}"

    async def load(self, key: str) -> bytes:
        full_key = self._full_key(key)
        response = self._s3.get_object(Bucket=self._bucket, Key=full_key)
        return response["Body"].read()

    async def delete(self, key: str) -> None:
        full_key = self._full_key(key)
        self._s3.delete_object(Bucket=self._bucket, Key=full_key)


def get_storage_service() -> StorageService:
    """
    FastAPI dependency that returns the configured storage backend.

    Example::

        storage: StorageService = Depends(get_storage_service)
    """
    if settings.STORAGE_BACKEND == "s3":
        if not settings.AWS_S3_BUCKET:
            raise RuntimeError(
                "STORAGE_BACKEND=s3 requires AWS_S3_BUCKET to be set in environment"
            )
        return S3StorageService()
    return LocalStorageService()
