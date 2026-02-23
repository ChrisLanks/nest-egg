"""CSV import API endpoints."""

import logging
from typing import Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.csv_import import (
    CSVPreviewResponse,
    CSVImportResponse,
)
from app.services.csv_import_service import csv_import_service
from app.services.input_sanitization_service import input_sanitization_service
from app.services.rate_limit_service import rate_limit_service

logger = logging.getLogger(__name__)

router = APIRouter()


def validate_csv_file(file: UploadFile) -> None:
    """
    Validate CSV file upload for security.

    Args:
        file: Uploaded file

    Raises:
        HTTPException: If file validation fails
    """
    # Check file extension
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    filename_lower = file.filename.lower()
    if not filename_lower.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed (.csv extension)")

    # Sanitize filename to prevent path traversal
    sanitized_name = input_sanitization_service.sanitize_filename(file.filename)
    if sanitized_name != file.filename:
        raise HTTPException(
            status_code=400, detail="Invalid filename. Filename contains unsafe characters"
        )

    # Check content type (allow both text/csv and application/vnd.ms-excel)
    allowed_types = ["text/csv", "application/vnd.ms-excel", "application/csv"]
    if file.content_type:
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid content type: {file.content_type}. Expected CSV file",
            )

    # File size check is handled by RequestSizeLimitMiddleware (10MB limit)


@router.post("/validate")
async def validate_csv(
    http_request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Validate CSV file format and security.
    Rate limited to 20 requests per minute.
    """
    # Rate limit: 20 validation requests per minute per IP
    await rate_limit_service.check_rate_limit(
        request=http_request,
        max_requests=20,
        window_seconds=60,
    )

    # Validate file upload security
    validate_csv_file(file)

    try:
        content = await file.read()
        csv_content = content.decode("utf-8")
    except Exception as e:
        logger.error("Failed to read CSV file: %s", e, exc_info=True)
        raise HTTPException(status_code=400, detail="Failed to read file")

    validation = csv_import_service.validate_csv_format(csv_content)

    if not validation["is_valid"]:
        raise HTTPException(status_code=400, detail={"errors": validation["errors"]})

    return {"message": "CSV file is valid"}


@router.post("/preview", response_model=CSVPreviewResponse)
async def preview_csv_import(
    http_request: Request,
    file: UploadFile = File(...),
    column_mapping: Dict[str, str] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Preview CSV file before import with security validation.
    Rate limited to 15 requests per minute.

    Returns detected columns, sample rows, and row count.
    """
    # Rate limit: 15 preview requests per minute per IP
    await rate_limit_service.check_rate_limit(
        request=http_request,
        max_requests=15,
        window_seconds=60,
    )

    # Validate file upload security
    validate_csv_file(file)

    try:
        content = await file.read()
        csv_content = content.decode("utf-8")
    except Exception as e:
        logger.error("Failed to read CSV file: %s", e, exc_info=True)
        raise HTTPException(status_code=400, detail="Failed to read file")

    preview = await csv_import_service.preview_csv(
        csv_content=csv_content,
        column_mapping=column_mapping,
    )

    return preview


@router.post("/import", response_model=CSVImportResponse)
async def import_csv(
    account_id: UUID,
    http_request: Request,
    file: UploadFile = File(...),
    column_mapping: Dict[str, str] = None,
    skip_duplicates: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Import transactions from CSV file with security validation.
    Rate limited to 10 imports per hour to prevent abuse.

    Args:
        account_id: Account to import transactions into
        file: CSV file to import
        column_mapping: Manual column mapping (date, amount, description, merchant)
        skip_duplicates: Skip duplicate transactions

    Returns:
        Import statistics (imported, skipped, errors)
    """
    # Rate limit: 10 import requests per hour per IP (stricter limit for resource-intensive operation)
    await rate_limit_service.check_rate_limit(
        request=http_request,
        max_requests=10,
        window_seconds=3600,  # 1 hour
    )

    # Validate file upload security
    validate_csv_file(file)

    # Read file
    try:
        content = await file.read()
        csv_content = content.decode("utf-8")
    except Exception as e:
        logger.error("Failed to read CSV file: %s", e, exc_info=True)
        raise HTTPException(status_code=400, detail="Failed to read file")

    # Validate CSV
    validation = csv_import_service.validate_csv_format(csv_content)
    if not validation["is_valid"]:
        raise HTTPException(
            status_code=400,
            detail={"message": "Invalid CSV format", "errors": validation["errors"]},
        )

    # Auto-detect column mapping if not provided
    if not column_mapping:
        preview = await csv_import_service.preview_csv(csv_content)
        column_mapping = preview["detected_mapping"]

        # Ensure required columns are detected
        if not column_mapping.get("date") or not column_mapping.get("amount"):
            raise HTTPException(
                status_code=400,
                detail="Could not auto-detect required columns. Please specify column_mapping.",
            )

    # Import transactions
    try:
        result = await csv_import_service.import_csv(
            db=db,
            user=current_user,
            account_id=account_id,
            csv_content=csv_content,
            column_mapping=column_mapping,
            skip_duplicates=skip_duplicates,
        )
        return result
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid CSV data or account configuration")
