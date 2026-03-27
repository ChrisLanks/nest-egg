"""Insurance policies CRUD API endpoints."""

from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.crud.insurance_policy import insurance_policy_crud
from app.dependencies import get_current_user
from app.models.insurance_policy import PolicyType
from app.models.user import User

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class InsurancePolicyCreate(BaseModel):
    policy_type: PolicyType
    provider: Optional[str] = None
    policy_number: Optional[str] = None
    coverage_amount: Optional[Decimal] = None
    annual_premium: Optional[Decimal] = None
    monthly_premium: Optional[Decimal] = None
    deductible: Optional[Decimal] = None
    effective_date: Optional[date] = None
    expiration_date: Optional[date] = None
    beneficiary_name: Optional[str] = None
    notes: Optional[str] = None
    user_id: Optional[UUID] = None


class InsurancePolicyUpdate(BaseModel):
    policy_type: Optional[PolicyType] = None
    provider: Optional[str] = None
    policy_number: Optional[str] = None
    coverage_amount: Optional[Decimal] = None
    annual_premium: Optional[Decimal] = None
    monthly_premium: Optional[Decimal] = None
    deductible: Optional[Decimal] = None
    effective_date: Optional[date] = None
    expiration_date: Optional[date] = None
    beneficiary_name: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class InsurancePolicyResponse(BaseModel):
    id: UUID
    household_id: UUID
    user_id: Optional[UUID] = None
    policy_type: str
    provider: Optional[str] = None
    policy_number: Optional[str] = None
    coverage_amount: Optional[float] = None
    annual_premium: Optional[float] = None
    monthly_premium: Optional[float] = None
    deductible: Optional[float] = None
    effective_date: Optional[date] = None
    expiration_date: Optional[date] = None
    beneficiary_name: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


class CoverageSummaryResponse(BaseModel):
    total_life_coverage: float
    has_disability: bool
    has_umbrella: bool
    has_health: bool
    has_ltc: bool
    total_annual_premiums: float
    policy_count: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=List[InsurancePolicyResponse])
async def list_insurance_policies(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all insurance policies for the household."""
    policies = await insurance_policy_crud.list_for_household(
        db, current_user.organization_id
    )
    return [
        InsurancePolicyResponse(
            id=p.id,
            household_id=p.household_id,
            user_id=p.user_id,
            policy_type=p.policy_type.value,
            provider=p.provider,
            policy_number=p.policy_number,
            coverage_amount=float(p.coverage_amount) if p.coverage_amount else None,
            annual_premium=float(p.annual_premium) if p.annual_premium else None,
            monthly_premium=float(p.monthly_premium) if p.monthly_premium else None,
            deductible=float(p.deductible) if p.deductible else None,
            effective_date=p.effective_date,
            expiration_date=p.expiration_date,
            beneficiary_name=p.beneficiary_name,
            notes=p.notes,
            is_active=p.is_active,
        )
        for p in policies
    ]


@router.post("", response_model=InsurancePolicyResponse, status_code=201)
async def create_insurance_policy(
    body: InsurancePolicyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new insurance policy."""
    policy = await insurance_policy_crud.create(
        db,
        household_id=current_user.organization_id,
        **body.model_dump(exclude_none=True),
    )
    return InsurancePolicyResponse(
        id=policy.id,
        household_id=policy.household_id,
        user_id=policy.user_id,
        policy_type=policy.policy_type.value,
        provider=policy.provider,
        policy_number=policy.policy_number,
        coverage_amount=float(policy.coverage_amount) if policy.coverage_amount else None,
        annual_premium=float(policy.annual_premium) if policy.annual_premium else None,
        monthly_premium=float(policy.monthly_premium) if policy.monthly_premium else None,
        deductible=float(policy.deductible) if policy.deductible else None,
        effective_date=policy.effective_date,
        expiration_date=policy.expiration_date,
        beneficiary_name=policy.beneficiary_name,
        notes=policy.notes,
        is_active=policy.is_active,
    )


@router.put("/{policy_id}", response_model=InsurancePolicyResponse)
async def update_insurance_policy(
    policy_id: UUID,
    body: InsurancePolicyUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an insurance policy."""
    policy = await insurance_policy_crud.get_by_id(db, policy_id)
    if not policy or policy.household_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Policy not found")
    policy = await insurance_policy_crud.update(
        db, policy, **body.model_dump(exclude_none=True)
    )
    return InsurancePolicyResponse(
        id=policy.id,
        household_id=policy.household_id,
        user_id=policy.user_id,
        policy_type=policy.policy_type.value,
        provider=policy.provider,
        policy_number=policy.policy_number,
        coverage_amount=float(policy.coverage_amount) if policy.coverage_amount else None,
        annual_premium=float(policy.annual_premium) if policy.annual_premium else None,
        monthly_premium=float(policy.monthly_premium) if policy.monthly_premium else None,
        deductible=float(policy.deductible) if policy.deductible else None,
        effective_date=policy.effective_date,
        expiration_date=policy.expiration_date,
        beneficiary_name=policy.beneficiary_name,
        notes=policy.notes,
        is_active=policy.is_active,
    )


@router.delete("/{policy_id}", status_code=204)
async def delete_insurance_policy(
    policy_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an insurance policy."""
    policy = await insurance_policy_crud.get_by_id(db, policy_id)
    if not policy or policy.household_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Policy not found")
    await insurance_policy_crud.delete(db, policy)


@router.get("/summary", response_model=CoverageSummaryResponse)
async def get_coverage_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a summary of insurance coverage for the household."""
    policies = await insurance_policy_crud.list_for_household(
        db, current_user.organization_id
    )

    life_types = {"term_life", "whole_life", "universal_life"}
    disability_types = {"disability_short_term", "disability_long_term"}

    total_life = sum(
        float(p.coverage_amount or 0)
        for p in policies
        if p.policy_type.value in life_types
    )
    has_disability = any(p.policy_type.value in disability_types for p in policies)
    has_umbrella = any(p.policy_type.value == "umbrella" for p in policies)
    has_health = any(p.policy_type.value == "health" for p in policies)
    has_ltc = any(p.policy_type.value == "long_term_care" for p in policies)
    total_annual = sum(float(p.annual_premium or 0) for p in policies)

    return CoverageSummaryResponse(
        total_life_coverage=total_life,
        has_disability=has_disability,
        has_umbrella=has_umbrella,
        has_health=has_health,
        has_ltc=has_ltc,
        total_annual_premiums=total_annual,
        policy_count=len(policies),
    )
