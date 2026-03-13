"""Transaction attachment API endpoints."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import RedirectResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services import attachment_service
from app.services.storage_service import StorageService, get_storage_service

router = APIRouter()


# ---------- Response schemas ----------


class AttachmentResponse(BaseModel):
    """Response schema for a single attachment."""

    id: UUID
    organization_id: UUID
    transaction_id: UUID
    user_id: UUID
    filename: str
    original_filename: str
    content_type: str
    file_size: int
    created_at: datetime

    model_config = {"from_attributes": True}


class AttachmentListResponse(BaseModel):
    """Response schema for listing attachments."""

    attachments: list[AttachmentResponse]


# ---------- Transaction-scoped endpoints ----------


@router.post(
    "/transactions/{transaction_id}/attachments",
    response_model=AttachmentResponse,
    status_code=201,
)
async def upload_attachment(
    transaction_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
):
    """Upload a file attachment (receipt/document) to a transaction.

    Accepts multipart/form-data. Max file size 10 MB.
    Allowed types: JPEG, PNG, GIF, WebP, PDF.
    Maximum 5 attachments per transaction.
    """
    attachment = await attachment_service.upload_attachment(
        db=db,
        transaction_id=transaction_id,
        user=current_user,
        file=file,
        storage=storage,
    )
    return AttachmentResponse.model_validate(attachment)


@router.get(
    "/transactions/{transaction_id}/attachments",
    response_model=AttachmentListResponse,
)
async def list_attachments(
    transaction_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all attachments for a transaction."""
    attachments = await attachment_service.list_attachments(
        db=db,
        transaction_id=transaction_id,
        user=current_user,
    )
    return AttachmentListResponse(
        attachments=[AttachmentResponse.model_validate(a) for a in attachments],
    )


# ---------- Attachment-scoped endpoints ----------


@router.get(
    "/attachments/{attachment_id}",
    response_model=AttachmentResponse,
)
async def get_attachment(
    attachment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get metadata for a single attachment."""
    attachment = await attachment_service.get_attachment(
        db=db,
        attachment_id=attachment_id,
        user=current_user,
    )
    return AttachmentResponse.model_validate(attachment)


@router.get(
    "/attachments/{attachment_id}/download",
)
async def download_attachment(
    attachment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
):
    """Download an attachment file.

    For S3 backend: redirects to a presigned URL (302).
    For local backend: streams the file content directly.
    """
    info = await attachment_service.get_download_url(
        db=db,
        attachment_id=attachment_id,
        user=current_user,
        storage=storage,
    )

    if "url" in info:
        # S3: redirect to presigned URL
        return RedirectResponse(url=info["url"], status_code=302)

    # Local storage: stream the file bytes
    data = await storage.load(info["storage_key"])
    filename = info["filename"]

    return StreamingResponse(
        iter([data]),
        media_type=info["content_type"],
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(data)),
        },
    )


@router.delete(
    "/attachments/{attachment_id}",
    status_code=204,
)
async def delete_attachment(
    attachment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
):
    """Delete an attachment (removes file from storage and DB record)."""
    await attachment_service.delete_attachment(
        db=db,
        attachment_id=attachment_id,
        user=current_user,
        storage=storage,
    )
