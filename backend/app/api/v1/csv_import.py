"""CSV import API endpoints."""

from typing import Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.csv_import import (
    CSVPreviewRequest,
    CSVPreviewResponse,
    CSVImportRequest,
    CSVImportResponse,
)
from app.services.csv_import_service import csv_import_service

router = APIRouter()


@router.post("/validate")
async def validate_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Validate CSV file format. Requires authentication."""
    try:
        content = await file.read()
        csv_content = content.decode("utf-8")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")

    validation = csv_import_service.validate_csv_format(csv_content)

    if not validation["is_valid"]:
        raise HTTPException(status_code=400, detail={"errors": validation["errors"]})

    return {"message": "CSV file is valid"}


@router.post("/preview", response_model=CSVPreviewResponse)
async def preview_csv_import(
    file: UploadFile = File(...),
    column_mapping: Dict[str, str] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Preview CSV file before import. Requires authentication.

    Returns detected columns, sample rows, and row count.
    """
    try:
        content = await file.read()
        csv_content = content.decode("utf-8")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")

    preview = await csv_import_service.preview_csv(
        csv_content=csv_content,
        column_mapping=column_mapping,
    )

    return preview


@router.post("/import", response_model=CSVImportResponse)
async def import_csv(
    account_id: UUID,
    file: UploadFile = File(...),
    column_mapping: Dict[str, str] = None,
    skip_duplicates: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Import transactions from CSV file.

    Args:
        account_id: Account to import transactions into
        file: CSV file to import
        column_mapping: Manual column mapping (date, amount, description, merchant)
        skip_duplicates: Skip duplicate transactions

    Returns:
        Import statistics (imported, skipped, errors)
    """
    # Read file
    try:
        content = await file.read()
        csv_content = content.decode("utf-8")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")

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
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
