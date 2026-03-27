"""Dependents CRUD API endpoints."""

from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.crud.dependent import dependent_crud
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class DependentCreate(BaseModel):
    first_name: str
    date_of_birth: date
    relationship: str  # "child", "parent", "other"
    expected_college_start_year: Optional[int] = None
    expected_college_cost_annual: Optional[Decimal] = None
    notes: Optional[str] = None


class DependentUpdate(BaseModel):
    first_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    relationship: Optional[str] = None
    expected_college_start_year: Optional[int] = None
    expected_college_cost_annual: Optional[Decimal] = None
    notes: Optional[str] = None


class DependentResponse(BaseModel):
    id: UUID
    household_id: UUID
    first_name: str
    date_of_birth: date
    relationship: str
    expected_college_start_year: Optional[int] = None
    expected_college_cost_annual: Optional[float] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=List[DependentResponse])
async def list_dependents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all dependents for the household."""
    deps = await dependent_crud.list_for_household(db, current_user.organization_id)
    return [
        DependentResponse(
            id=d.id,
            household_id=d.household_id,
            first_name=d.first_name,
            date_of_birth=d.date_of_birth,
            relationship=d.relationship,
            expected_college_start_year=d.expected_college_start_year,
            expected_college_cost_annual=(
                float(d.expected_college_cost_annual) if d.expected_college_cost_annual else None
            ),
            notes=d.notes,
        )
        for d in deps
    ]


@router.post("", response_model=DependentResponse, status_code=201)
async def create_dependent(
    body: DependentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a dependent to the household."""
    dep = await dependent_crud.create(
        db,
        household_id=current_user.organization_id,
        **body.model_dump(exclude_none=True),
    )
    return DependentResponse(
        id=dep.id,
        household_id=dep.household_id,
        first_name=dep.first_name,
        date_of_birth=dep.date_of_birth,
        relationship=dep.relationship,
        expected_college_start_year=dep.expected_college_start_year,
        expected_college_cost_annual=(
            float(dep.expected_college_cost_annual) if dep.expected_college_cost_annual else None
        ),
        notes=dep.notes,
    )


@router.put("/{dependent_id}", response_model=DependentResponse)
async def update_dependent(
    dependent_id: UUID,
    body: DependentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a dependent."""
    dep = await dependent_crud.get_by_id(db, dependent_id)
    if not dep or dep.household_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Dependent not found")
    dep = await dependent_crud.update(db, dep, **body.model_dump(exclude_none=True))
    return DependentResponse(
        id=dep.id,
        household_id=dep.household_id,
        first_name=dep.first_name,
        date_of_birth=dep.date_of_birth,
        relationship=dep.relationship,
        expected_college_start_year=dep.expected_college_start_year,
        expected_college_cost_annual=(
            float(dep.expected_college_cost_annual) if dep.expected_college_cost_annual else None
        ),
        notes=dep.notes,
    )


@router.delete("/{dependent_id}", status_code=204)
async def delete_dependent(
    dependent_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a dependent."""
    dep = await dependent_crud.get_by_id(db, dependent_id)
    if not dep or dep.household_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Dependent not found")
    await dependent_crud.delete(db, dep)
