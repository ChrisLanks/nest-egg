"""Service for managing transaction file attachments (receipts, documents)."""

import uuid

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attachment import TransactionAttachment
from app.models.transaction import Transaction
from app.models.user import User
from app.services.storage_service import StorageService

# Validation constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_ATTACHMENTS_PER_TRANSACTION = 5
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "application/pdf",
}


async def _verify_transaction_access(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    user: User,
) -> Transaction:
    """Verify the user has access to the transaction via organization membership.

    Returns the transaction if access is granted.

    Raises:
        HTTPException: If the transaction is not found or user lacks access.
    """
    result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.organization_id == user.organization_id,
        )
    )
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )
    return txn


async def _verify_attachment_access(
    db: AsyncSession,
    attachment_id: uuid.UUID,
    user: User,
) -> TransactionAttachment:
    """Verify the user has access to the attachment via organization membership.

    Returns the attachment if access is granted.

    Raises:
        HTTPException: If the attachment is not found or user lacks access.
    """
    result = await db.execute(
        select(TransactionAttachment).where(
            TransactionAttachment.id == attachment_id,
            TransactionAttachment.organization_id == user.organization_id,
        )
    )
    attachment = result.scalar_one_or_none()
    if not attachment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found",
        )
    return attachment


async def upload_attachment(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    user: User,
    file: UploadFile,
    storage: StorageService,
) -> TransactionAttachment:
    """Upload a file attachment to a transaction.

    Validates file size, content type, and attachment count limits,
    then saves the file via StorageService and creates a DB record.

    Args:
        db: Database session.
        transaction_id: Target transaction UUID.
        user: Authenticated user.
        file: Uploaded file (multipart/form-data).
        storage: StorageService instance (local or S3).

    Returns:
        The created TransactionAttachment record.

    Raises:
        HTTPException: On validation failure or access denial.
    """
    txn = await _verify_transaction_access(db, transaction_id, user)

    # Validate content type
    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{content_type}' is not allowed. "
            f"Allowed types: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}",
        )

    # Read file data and validate size
    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds the {MAX_FILE_SIZE // (1024 * 1024)}MB limit.",
        )

    # Check attachment count limit
    count_result = await db.execute(
        select(func.count()).where(
            TransactionAttachment.transaction_id == transaction_id,
        )
    )
    current_count = count_result.scalar()
    if current_count >= MAX_ATTACHMENTS_PER_TRANSACTION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Maximum of {MAX_ATTACHMENTS_PER_TRANSACTION}"
                " attachments per transaction reached."
            ),
        )

    # Build storage key and save
    original_filename = file.filename or "unnamed"
    unique_filename = f"{uuid.uuid4()}_{original_filename}"
    storage_key = f"attachments/{txn.organization_id}/{transaction_id}/{unique_filename}"

    await storage.save(storage_key, data, content_type=content_type)

    # Create DB record
    attachment = TransactionAttachment(
        organization_id=txn.organization_id,
        transaction_id=transaction_id,
        user_id=user.id,
        filename=unique_filename,
        original_filename=original_filename,
        storage_key=storage_key,
        content_type=content_type,
        file_size=len(data),
    )
    db.add(attachment)
    await db.commit()
    await db.refresh(attachment)

    return attachment


async def list_attachments(
    db: AsyncSession,
    transaction_id: uuid.UUID,
    user: User,
) -> list[TransactionAttachment]:
    """List all attachments for a transaction.

    Args:
        db: Database session.
        transaction_id: Target transaction UUID.
        user: Authenticated user.

    Returns:
        List of TransactionAttachment records.
    """
    await _verify_transaction_access(db, transaction_id, user)

    result = await db.execute(
        select(TransactionAttachment)
        .where(TransactionAttachment.transaction_id == transaction_id)
        .order_by(TransactionAttachment.created_at.desc())
    )
    return list(result.scalars().all())


async def get_attachment(
    db: AsyncSession,
    attachment_id: uuid.UUID,
    user: User,
) -> TransactionAttachment:
    """Get a single attachment record.

    Args:
        db: Database session.
        attachment_id: Attachment UUID.
        user: Authenticated user.

    Returns:
        The TransactionAttachment record.
    """
    return await _verify_attachment_access(db, attachment_id, user)


async def get_download_url(
    db: AsyncSession,
    attachment_id: uuid.UUID,
    user: User,
    storage: StorageService,
) -> dict:
    """Get a download URL or path for an attachment.

    For S3 backend: returns a presigned URL.
    For local backend: returns the local file path (the API layer streams it).

    Args:
        db: Database session.
        attachment_id: Attachment UUID.
        user: Authenticated user.
        storage: StorageService instance.

    Returns:
        Dict with 'url' (presigned S3 URL) or 'path' (local file path) and 'content_type'.
    """
    attachment = await _verify_attachment_access(db, attachment_id, user)

    from app.config import settings

    if settings.STORAGE_BACKEND == "s3":
        # Generate presigned URL for S3
        import posixpath

        import boto3

        kwargs: dict = {"region_name": settings.AWS_REGION}
        if settings.AWS_ACCESS_KEY_ID:
            kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
            kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY

        s3_client = boto3.client("s3", **kwargs)
        full_key = (
            f"{settings.AWS_S3_PREFIX}{posixpath.normpath(attachment.storage_key).lstrip('/')}"
        )

        presigned_url = s3_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.AWS_S3_BUCKET,
                "Key": full_key,
                "ResponseContentDisposition": (
                    "attachment; filename=" f'"{attachment.original_filename}"'
                ),
            },
            ExpiresIn=3600,  # 1 hour
        )
        return {
            "url": presigned_url,
            "content_type": attachment.content_type,
            "filename": attachment.original_filename,
        }
    else:
        # Local storage — return storage key so the API can stream the file
        return {
            "storage_key": attachment.storage_key,
            "content_type": attachment.content_type,
            "filename": attachment.original_filename,
        }


async def delete_attachment(
    db: AsyncSession,
    attachment_id: uuid.UUID,
    user: User,
    storage: StorageService,
) -> None:
    """Delete an attachment from storage and the database.

    Args:
        db: Database session.
        attachment_id: Attachment UUID.
        user: Authenticated user.
        storage: StorageService instance.
    """
    attachment = await _verify_attachment_access(db, attachment_id, user)

    # Delete from storage (best-effort; DB record is authoritative)
    try:
        await storage.delete(attachment.storage_key)
    except Exception:
        pass  # Storage deletion failures should not block DB cleanup

    await db.delete(attachment)
    await db.commit()
