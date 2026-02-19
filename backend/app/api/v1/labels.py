"""Label API endpoints."""

from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.transaction import Label
from app.schemas.transaction import LabelCreate, LabelUpdate, LabelResponse
from app.services.tax_service import TaxService
from app.services.hierarchy_validation_service import hierarchy_validation_service

router = APIRouter()


async def get_label_depth(label_id: UUID, db: AsyncSession) -> int:
    """Get the depth of a label in the hierarchy (0 = root, 1 = child, 2 = grandchild)."""
    depth = 0
    current_id = label_id

    while current_id and depth < 3:  # Safety limit
        result = await db.execute(select(Label.parent_label_id).where(Label.id == current_id))
        parent_id = result.scalar_one_or_none()

        if parent_id:
            depth += 1
            current_id = parent_id
        else:
            break

    return depth


@router.get("/", response_model=List[LabelResponse])
async def list_labels(
    is_income: Optional[bool] = Query(None, description="Filter by income/expense type"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all labels for the current user's organization."""
    query = (
        select(Label)
        .where(Label.organization_id == current_user.organization_id)
        .order_by(Label.name)
    )
    if is_income is not None:
        query = query.where(Label.is_income == is_income)
    result = await db.execute(query)
    labels = result.scalars().all()
    return labels


@router.get("/{label_id}", response_model=LabelResponse)
async def get_label(
    label_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific label by ID."""
    result = await db.execute(
        select(Label).where(
            Label.id == label_id,
            Label.organization_id == current_user.organization_id,
        )
    )
    label = result.scalar_one_or_none()

    if not label:
        raise HTTPException(status_code=404, detail="Label not found")

    return label


@router.post("/", response_model=LabelResponse, status_code=201)
async def create_label(
    label_data: LabelCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new label."""
    # Prevent creating "Transfer" label (reserved for system)
    if label_data.name.lower() == "transfer":
        raise HTTPException(
            status_code=400,
            detail="Cannot create label named 'Transfer' - this is a reserved system label",
        )

    # Validate parent if provided
    if label_data.parent_label_id is not None:
        await hierarchy_validation_service.validate_parent(
            label_data.parent_label_id,
            current_user.organization_id,
            db,
            Label,
            parent_field_name="parent_label_id",
            entity_name="label",
        )

    label = Label(
        organization_id=current_user.organization_id,
        name=label_data.name,
        color=label_data.color,
        is_income=label_data.is_income,
        parent_label_id=label_data.parent_label_id,
    )
    db.add(label)
    await db.commit()
    await db.refresh(label)
    return label


@router.patch("/{label_id}", response_model=LabelResponse)
async def update_label(
    label_id: UUID,
    label_data: LabelUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a label."""
    result = await db.execute(
        select(Label).where(
            Label.id == label_id,
            Label.organization_id == current_user.organization_id,
        )
    )
    label = result.scalar_one_or_none()

    if not label:
        raise HTTPException(status_code=404, detail="Label not found")

    # Prevent renaming to "Transfer" (reserved for system)
    if label_data.name is not None and label_data.name.lower() == "transfer":
        raise HTTPException(
            status_code=400,
            detail="Cannot rename label to 'Transfer' - this is a reserved system label",
        )

    # Validate parent if changing it
    if label_data.parent_label_id is not None:
        # Prevent setting self as parent
        if label_data.parent_label_id == label_id:
            raise HTTPException(status_code=400, detail="Cannot set label as its own parent")

        # Check if this label has children - if so, can't make it a child
        children_result = await db.execute(
            select(Label.id).where(Label.parent_label_id == label_id).limit(1)
        )
        has_children = children_result.scalar_one_or_none() is not None

        if has_children and label_data.parent_label_id:
            raise HTTPException(
                status_code=400,
                detail="Cannot assign a parent to this label because it already has children. Maximum 2 levels allowed.",
            )

        # Validate the new parent
        await hierarchy_validation_service.validate_parent(
            label_data.parent_label_id,
            current_user.organization_id,
            db,
            Label,
            parent_field_name="parent_label_id",
            entity_name="label",
        )

    if label_data.name is not None:
        label.name = label_data.name
    if label_data.color is not None:
        label.color = label_data.color
    if label_data.is_income is not None:
        label.is_income = label_data.is_income
    if label_data.parent_label_id is not None:
        label.parent_label_id = label_data.parent_label_id

    await db.commit()
    await db.refresh(label)
    return label


@router.delete("/{label_id}", status_code=204)
async def delete_label(
    label_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a label."""
    result = await db.execute(
        select(Label).where(
            Label.id == label_id,
            Label.organization_id == current_user.organization_id,
        )
    )
    label = result.scalar_one_or_none()

    if not label:
        raise HTTPException(status_code=404, detail="Label not found")

    # Prevent deleting system labels
    if label.is_system:
        raise HTTPException(status_code=400, detail="Cannot delete system label")

    await db.delete(label)
    await db.commit()


# Tax-Deductible Endpoints


@router.post("/tax-deductible/initialize", response_model=List[LabelResponse], status_code=201)
async def initialize_tax_labels(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Initialize default tax-deductible labels for the organization.

    Creates standard IRS-aligned tax labels:
    - Medical & Dental
    - Charitable Donations
    - Business Expenses
    - Education
    - Home Office

    Idempotent operation - only creates labels that don't exist.
    """
    labels = await TaxService.initialize_tax_labels(db, current_user.organization_id)
    return labels


@router.get("/tax-deductible")
async def get_tax_deductible_transactions(
    start_date: date = Query(..., description="Start date for tax period (e.g., 2024-01-01)"),
    end_date: date = Query(..., description="End date for tax period (e.g., 2024-12-31)"),
    label_ids: Optional[List[UUID]] = Query(None, description="Filter by specific tax label IDs"),
    user_id: Optional[UUID] = Query(None, description="Filter by user"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get tax-deductible transactions grouped by label.

    Returns summary with:
    - Total amount per tax category
    - Transaction count per category
    - Detailed transaction list per category

    Useful for tax preparation and reporting.
    """
    summaries = await TaxService.get_tax_deductible_summary(
        db,
        current_user.organization_id,
        start_date,
        end_date,
        label_ids,
        user_id,
    )

    # Convert to dict format for JSON response
    return [
        {
            "label_id": str(summary.label_id),
            "label_name": summary.label_name,
            "label_color": summary.label_color,
            "total_amount": float(summary.total_amount),
            "transaction_count": summary.transaction_count,
            "transactions": summary.transactions,
        }
        for summary in summaries
    ]


@router.get("/tax-deductible/export")
async def export_tax_deductible_csv(
    start_date: date = Query(..., description="Start date for tax period"),
    end_date: date = Query(..., description="End date for tax period"),
    label_ids: Optional[List[UUID]] = Query(None, description="Filter by specific tax label IDs"),
    user_id: Optional[UUID] = Query(None, description="Filter by user"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Export tax-deductible transactions as CSV.

    Format optimized for tax software import:
    - Date, Merchant, Description, Category, Tax Label, Amount, Account, Notes

    Returns CSV file with name: tax_deductible_transactions_{start_date}_{end_date}.csv
    """
    csv_data = await TaxService.generate_tax_export_csv(
        db,
        current_user.organization_id,
        start_date,
        end_date,
        label_ids,
        user_id,
    )

    # Generate filename
    filename = f"tax_deductible_transactions_{start_date}_{end_date}.csv"

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
