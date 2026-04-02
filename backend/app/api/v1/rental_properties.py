"""Rental Properties P&L API endpoints."""

from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user, verify_household_member
from app.models.user import User
from app.services.input_sanitization_service import input_sanitization_service
from app.services.rental_property_service import RentalPropertyService

router = APIRouter()


class RentalFieldsUpdate(BaseModel):
    """Request body for updating rental-specific fields."""

    is_rental_property: Optional[bool] = None
    rental_monthly_income: Optional[Decimal] = None
    rental_address: Optional[str] = None
    rental_type: Optional[str] = None  # "buy_and_hold", "long_term_rental", "short_term_rental"


@router.get("")
async def list_rental_properties(
    user_id: Optional[UUID] = Query(None, description="Filter by user"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all accounts flagged as rental properties.

    Returns property details including name, address, value, and monthly rent.
    """
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)

    service = RentalPropertyService(db)
    return await service.get_rental_properties(current_user.organization_id, user_id)


@router.get("/summary")
async def get_properties_summary(
    year: int = Query(default=None, description="Year for P&L (defaults to current)"),
    user_id: Optional[UUID] = Query(None, description="Filter by user"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Summary P&L across all rental properties for a given year.

    Returns total rental income, expenses, net income, average cap rate,
    and per-property breakdown.
    """
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)

    if year is None:
        year = date.today().year

    service = RentalPropertyService(db)
    return await service.get_all_properties_summary(current_user.organization_id, year, user_id)


@router.get("/{account_id}/pnl")
async def get_property_pnl(
    account_id: UUID,
    year: int = Query(default=None, description="Year for P&L (defaults to current)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed P&L for a single rental property.

    Returns Schedule E-style breakdown with:
    - Gross income, total expenses, net income
    - Cap rate
    - Expense breakdown by category
    - Monthly income/expense chart data
    """
    if year is None:
        year = date.today().year

    service = RentalPropertyService(db)
    result = await service.get_property_pnl(
        current_user.organization_id, account_id, year, user_id=current_user.id
    )

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.patch("/{account_id}")
async def update_rental_fields(
    account_id: UUID,
    body: RentalFieldsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update rental-specific fields on an account.

    Allows setting/unsetting an account as a rental property and
    updating monthly income and address.
    """
    # Sanitize user text input
    sanitized_address = (
        input_sanitization_service.sanitize_html(body.rental_address)
        if body.rental_address
        else body.rental_address
    )

    service = RentalPropertyService(db)
    result = await service.update_rental_fields(
        organization_id=current_user.organization_id,
        account_id=account_id,
        is_rental_property=body.is_rental_property,
        rental_monthly_income=body.rental_monthly_income,
        rental_address=sanitized_address,
        rental_type=body.rental_type,
        user_id=current_user.id,
    )

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result
