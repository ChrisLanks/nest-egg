"""Onboarding wizard API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter()

VALID_STEPS = {"profile", "accounts", "budget", "goals"}


# --- Schemas ---


class OnboardingStatusResponse(BaseModel):
    """Response schema for onboarding status."""

    onboarding_completed: bool
    onboarding_step: str | None

    model_config = {"from_attributes": True}


class OnboardingStepUpdate(BaseModel):
    """Request schema for updating the current onboarding step."""

    step: str = Field(..., description="Current onboarding step: profile, accounts, budget, goals")


# --- Endpoints ---


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    current_user: User = Depends(get_current_user),
):
    """Return the current onboarding state for the authenticated user."""
    return OnboardingStatusResponse(
        onboarding_completed=current_user.onboarding_completed,
        onboarding_step=current_user.onboarding_step,
    )


@router.put("/step", response_model=OnboardingStatusResponse)
async def update_onboarding_step(
    body: OnboardingStepUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the current onboarding step."""
    if body.step not in VALID_STEPS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid step. Must be one of: {', '.join(sorted(VALID_STEPS))}",
        )

    if current_user.onboarding_completed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Onboarding has already been completed",
        )

    current_user.onboarding_step = body.step
    await db.commit()
    await db.refresh(current_user)

    return OnboardingStatusResponse(
        onboarding_completed=current_user.onboarding_completed,
        onboarding_step=current_user.onboarding_step,
    )


@router.post("/complete", response_model=OnboardingStatusResponse)
async def complete_onboarding(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark onboarding as complete for the authenticated user."""
    if current_user.onboarding_completed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Onboarding has already been completed",
        )

    current_user.onboarding_completed = True
    current_user.onboarding_step = None
    await db.commit()
    await db.refresh(current_user)

    return OnboardingStatusResponse(
        onboarding_completed=current_user.onboarding_completed,
        onboarding_step=current_user.onboarding_step,
    )
