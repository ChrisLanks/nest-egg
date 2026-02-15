"""CSV import schemas."""

from typing import Dict, List, Any, Optional
from uuid import UUID

from pydantic import BaseModel


class CSVPreviewRequest(BaseModel):
    """Request schema for CSV preview."""

    column_mapping: Optional[Dict[str, str]] = None


class CSVPreviewResponse(BaseModel):
    """Response schema for CSV preview."""

    headers: List[str]
    detected_mapping: Dict[str, Optional[str]]
    preview_rows: List[Dict[str, Any]]
    total_rows: int


class CSVImportRequest(BaseModel):
    """Request schema for CSV import."""

    account_id: UUID
    column_mapping: Dict[str, str]
    skip_duplicates: bool = True


class CSVImportResponse(BaseModel):
    """Response schema for CSV import."""

    imported: int
    skipped: int
    errors: List[str]
    total_processed: int
