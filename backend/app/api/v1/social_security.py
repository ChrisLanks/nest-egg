"""Social Security manual benefit import endpoint."""

from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.ss_benefit_estimate import SSBenefitEstimate
from app.models.user import User

router = APIRouter()


class SSBenefitInput(BaseModel):
    age_62_benefit: Optional[Decimal] = None
    age_67_benefit: Optional[Decimal] = None
    age_70_benefit: Optional[Decimal] = None
    as_of_year: Optional[int] = None


class SSBenefitResponse(BaseModel):
    id: UUID
    user_id: UUID
    age_62_benefit: Optional[float] = None
    age_67_benefit: Optional[float] = None
    age_70_benefit: Optional[float] = None
    as_of_year: Optional[int] = None


@router.post("/manual-benefit", response_model=SSBenefitResponse)
async def save_ss_benefit_estimate(
    body: SSBenefitInput,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save or update a user's manually-entered Social Security benefit estimate from SSA.gov."""
    result = await db.execute(
        select(SSBenefitEstimate).where(SSBenefitEstimate.user_id == current_user.id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        if body.age_62_benefit is not None:
            existing.age_62_benefit = body.age_62_benefit
        if body.age_67_benefit is not None:
            existing.age_67_benefit = body.age_67_benefit
        if body.age_70_benefit is not None:
            existing.age_70_benefit = body.age_70_benefit
        if body.as_of_year is not None:
            existing.as_of_year = body.as_of_year
        await db.commit()
        await db.refresh(existing)
        record = existing
    else:
        record = SSBenefitEstimate(
            user_id=current_user.id,
            age_62_benefit=body.age_62_benefit,
            age_67_benefit=body.age_67_benefit,
            age_70_benefit=body.age_70_benefit,
            as_of_year=body.as_of_year,
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)

    return SSBenefitResponse(
        id=record.id,
        user_id=record.user_id,
        age_62_benefit=float(record.age_62_benefit) if record.age_62_benefit else None,
        age_67_benefit=float(record.age_67_benefit) if record.age_67_benefit else None,
        age_70_benefit=float(record.age_70_benefit) if record.age_70_benefit else None,
        as_of_year=record.as_of_year,
    )


@router.get("/manual-benefit", response_model=Optional[SSBenefitResponse])
async def get_ss_benefit_estimate(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the user's stored SS benefit estimate."""
    result = await db.execute(
        select(SSBenefitEstimate).where(SSBenefitEstimate.user_id == current_user.id)
    )
    record = result.scalar_one_or_none()
    if not record:
        return None

    return SSBenefitResponse(
        id=record.id,
        user_id=record.user_id,
        age_62_benefit=float(record.age_62_benefit) if record.age_62_benefit else None,
        age_67_benefit=float(record.age_67_benefit) if record.age_67_benefit else None,
        age_70_benefit=float(record.age_70_benefit) if record.age_70_benefit else None,
        as_of_year=record.as_of_year,
    )
