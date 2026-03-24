"""CSV import API endpoints."""

import logging
from typing import Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.account import Account
from app.models.user import User
from app.schemas.csv_import import (
    CSVImportResponse,
    CSVPreviewResponse,
)
from app.services.csv_import_service import csv_import_service
from app.services.input_sanitization_service import input_sanitization_service
from app.services.rate_limit_service import rate_limit_service

logger = logging.getLogger(__name__)

router = APIRouter()

# Safety cap: a single CSV must not exceed this many data rows.
# Prevents memory exhaustion from maliciously crafted files (many tiny rows).
MAX_CSV_ROWS = 10_000


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
    allowed_types = ["text/csv", "application/vnd.ms-excel", "application/csv", "text/plain"]
    if file.content_type:
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid content type: {file.content_type}. Expected CSV file",
            )

    # File size check is handled by RequestSizeLimitMiddleware (10MB limit)


def check_csv_row_limit(csv_content: str) -> None:
    """Raise 400 if the CSV exceeds MAX_CSV_ROWS data rows.

    Counts non-blank lines excluding the header so the limit applies to
    actual data, not the column names row.

    Raises:
        HTTPException: 400 if row count exceeds MAX_CSV_ROWS.
    """
    lines = [ln for ln in csv_content.splitlines() if ln.strip()]
    data_rows = max(0, len(lines) - 1)  # subtract header row
    if data_rows > MAX_CSV_ROWS:
        raise HTTPException(
            status_code=400,
            detail=f"CSV file too large: {data_rows:,} rows exceeds the {MAX_CSV_ROWS:,}-row limit.",
        )


async def validate_csv_content(file: UploadFile) -> None:
    """
    Validate that uploaded file is actually a text CSV, not a binary file.

    Reads the first chunk of the file and checks for binary content
    and valid UTF-8 encoding, then resets the file position.

    Args:
        file: Uploaded file

    Raises:
        HTTPException: If file content is binary or not valid UTF-8
    """
    # Read first chunk to verify it's actually a text file
    first_chunk = await file.read(8192)
    await file.seek(0)  # Reset file position

    # Check for binary content (null bytes indicate binary file)
    if b"\x00" in first_chunk:
        raise HTTPException(
            status_code=400, detail="File appears to be binary, not a valid CSV text file"
        )

    # Verify UTF-8 encoding
    try:
        first_chunk.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File is not valid UTF-8 encoded text")


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
    # Rate limit: 20 validation requests per minute per user
    await rate_limit_service.check_rate_limit(
        request=http_request,
        max_requests=20,
        window_seconds=60,
        identifier=str(current_user.id),
    )

    # Validate file upload security
    validate_csv_file(file)
    await validate_csv_content(file)

    try:
        content = await file.read()
        csv_content = content.decode("utf-8")
    except Exception as e:
        logger.error("Failed to read CSV file: %s", e, exc_info=True)
        raise HTTPException(status_code=400, detail="Failed to read file")

    check_csv_row_limit(csv_content)

    validation = csv_import_service.validate_csv_format(csv_content)

    if not validation["is_valid"]:
        raise HTTPException(status_code=400, detail={"errors": validation["errors"]})

    return {"message": "CSV file is valid"}


@router.post("/preview", response_model=CSVPreviewResponse)
async def preview_csv_import(
    http_request: Request,
    file: UploadFile = File(...),
    column_mapping: Optional[Dict[str, str]] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Preview CSV file before import with security validation.
    Rate limited to 15 requests per minute.

    Returns detected columns, sample rows, and row count.
    """
    # Rate limit: 15 preview requests per minute per user
    await rate_limit_service.check_rate_limit(
        request=http_request,
        max_requests=15,
        window_seconds=60,
        identifier=str(current_user.id),
    )

    # Validate file upload security
    validate_csv_file(file)
    await validate_csv_content(file)

    try:
        content = await file.read()
        csv_content = content.decode("utf-8")
    except Exception as e:
        logger.error("Failed to read CSV file: %s", e, exc_info=True)
        raise HTTPException(status_code=400, detail="Failed to read file")

    check_csv_row_limit(csv_content)

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
    column_mapping: Optional[Dict[str, str]] = None,
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
    # Rate limit: 10 imports/hour per user (resource-intensive)
    await rate_limit_service.check_rate_limit(
        request=http_request,
        max_requests=10,
        window_seconds=3600,  # 1 hour
        identifier=str(current_user.id),
    )

    # Verify account belongs to current user's organization (IDOR prevention)
    account_result = await db.execute(
        select(Account.id).where(
            Account.id == account_id,
            Account.organization_id == current_user.organization_id,
        )
    )
    if not account_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Account not found")

    # Validate file upload security
    validate_csv_file(file)
    await validate_csv_content(file)

    # Read file
    try:
        content = await file.read()
        csv_content = content.decode("utf-8")
    except Exception as e:
        logger.error("Failed to read CSV file: %s", e, exc_info=True)
        raise HTTPException(status_code=400, detail="Failed to read file")

    check_csv_row_limit(csv_content)

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
