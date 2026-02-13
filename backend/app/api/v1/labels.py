"""Label API endpoints."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.transaction import Label
from app.schemas.transaction import LabelCreate, LabelUpdate, LabelResponse

router = APIRouter()


async def get_label_depth(label_id: UUID, db: AsyncSession) -> int:
    """Get the depth of a label in the hierarchy (0 = root, 1 = child, 2 = grandchild)."""
    depth = 0
    current_id = label_id

    while current_id and depth < 3:  # Safety limit
        result = await db.execute(
            select(Label.parent_label_id).where(Label.id == current_id)
        )
        parent_id = result.scalar_one_or_none()

        if parent_id:
            depth += 1
            current_id = parent_id
        else:
            break

    return depth


async def validate_parent_label(
    parent_label_id: Optional[UUID],
    organization_id: UUID,
    db: AsyncSession,
) -> Optional[Label]:
    """Validate parent label exists and is at correct depth (max 1 level deep)."""
    if not parent_label_id:
        return None

    # Check parent exists and belongs to organization
    result = await db.execute(
        select(Label).where(
            Label.id == parent_label_id,
            Label.organization_id == organization_id,
        )
    )
    parent = result.scalar_one_or_none()

    if not parent:
        raise HTTPException(status_code=404, detail="Parent label not found")

    # Check parent depth (parent cannot have a parent - max 2 levels)
    if parent.parent_label_id is not None:
        raise HTTPException(
            status_code=400,
            detail="Cannot create label: parent already has a parent. Maximum 2 levels allowed (parent and child)."
        )

    return parent


@router.get("/", response_model=List[LabelResponse])
async def list_labels(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all labels for the current user's organization."""
    result = await db.execute(
        select(Label)
        .where(Label.organization_id == current_user.organization_id)
        .order_by(Label.name)
    )
    labels = result.scalars().all()
    return labels


@router.post("/", response_model=LabelResponse, status_code=201)
async def create_label(
    label_data: LabelCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new label."""
    # Validate parent if provided
    await validate_parent_label(
        label_data.parent_label_id,
        current_user.organization_id,
        db
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

    # Validate parent if changing it
    if label_data.parent_label_id is not None:
        # Prevent setting self as parent
        if label_data.parent_label_id == label_id:
            raise HTTPException(
                status_code=400,
                detail="Cannot set label as its own parent"
            )

        # Check if this label has children - if so, can't make it a child
        children_result = await db.execute(
            select(Label.id).where(Label.parent_label_id == label_id).limit(1)
        )
        has_children = children_result.scalar_one_or_none() is not None

        if has_children and label_data.parent_label_id:
            raise HTTPException(
                status_code=400,
                detail="Cannot assign a parent to this label because it already has children. Maximum 2 levels allowed."
            )

        # Validate the new parent
        await validate_parent_label(
            label_data.parent_label_id,
            current_user.organization_id,
            db
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

    await db.delete(label)
    await db.commit()
