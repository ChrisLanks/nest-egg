"""Label API endpoints."""

from typing import List
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
    label = Label(
        organization_id=current_user.organization_id,
        name=label_data.name,
        color=label_data.color,
        is_income=label_data.is_income,
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

    if label_data.name is not None:
        label.name = label_data.name
    if label_data.color is not None:
        label.color = label_data.color
    if label_data.is_income is not None:
        label.is_income = label_data.is_income

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
