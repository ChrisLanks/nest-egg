"""Category API endpoints."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import (
    get_current_user,
    get_user_accounts,
    verify_household_member,
)
from app.models.transaction import Category, Transaction
from app.models.user import User
from app.schemas.transaction import CategoryCreate, CategoryResponse, CategoryUpdate
from app.services.hierarchy_validation_service import hierarchy_validation_service
from app.services.input_sanitization_service import input_sanitization_service

router = APIRouter()


@router.get("/", response_model=List[CategoryResponse])
async def list_categories(
    user_id: Optional[UUID] = Query(
        None, description="Filter by user. None = combined household view"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all categories for the current user's organization.

    Returns both custom categories (from categories table) and provider categories
    (from transactions.category_primary). Provider categories come from connected
    accounts (Plaid, Teller, MX, etc.) and have is_custom=False.

    When user_id is provided, transaction counts reflect only that user's accounts.
    """
    # Get account IDs for filtering (if user_id specified)
    account_ids = None
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)
        accounts = await get_user_accounts(db, user_id, current_user.organization_id)
        account_ids = [acc.id for acc in accounts]

    # Get custom categories from categories table
    custom_query = (
        select(Category, func.count(Transaction.id).label("transaction_count"))
        .outerjoin(Transaction, Transaction.category_id == Category.id)
        .where(Category.organization_id == current_user.organization_id)
    )
    if account_ids is not None:
        custom_query = custom_query.where(
            (Transaction.account_id.in_(account_ids)) | (Transaction.id.is_(None))
        )
    custom_result = await db.execute(custom_query.group_by(Category.id).order_by(Category.name))
    custom_categories = custom_result.all()

    # Get provider categories from transactions (agnostic of provider source)
    # These are categories assigned by account providers like Plaid, Teller, MX
    provider_query = select(
        Transaction.category_primary, func.count(Transaction.id).label("transaction_count")
    ).where(
        Transaction.organization_id == current_user.organization_id,
        Transaction.category_primary.isnot(None),
        Transaction.category_primary != "",
    )
    if account_ids is not None:
        provider_query = provider_query.where(Transaction.account_id.in_(account_ids))
    provider_result = await db.execute(
        provider_query.group_by(Transaction.category_primary).order_by(Transaction.category_primary)
    )
    provider_categories = provider_result.all()

    # Build response combining both types
    response = []

    # Add custom categories
    for category, tx_count in custom_categories:
        response.append(
            CategoryResponse(
                id=category.id,
                organization_id=category.organization_id,
                name=category.name,
                color=category.color,
                parent_category_id=category.parent_category_id,
                # Legacy field, kept for compatibility
                plaid_category_name=category.plaid_category_name,
                is_custom=True,
                transaction_count=tx_count,
                created_at=category.created_at,
                updated_at=category.updated_at,
            )
        )

    # Add provider categories that aren't already custom categories
    custom_category_names = {cat.name.lower() for cat, _ in custom_categories}
    for provider_name, tx_count in provider_categories:
        if provider_name.lower() not in custom_category_names:
            response.append(
                CategoryResponse(
                    id=None,
                    organization_id=current_user.organization_id,
                    name=provider_name,
                    color=None,
                    parent_category_id=None,
                    plaid_category_name=None,  # Not a mapped category
                    is_custom=False,
                    transaction_count=tx_count,
                    created_at=None,
                    updated_at=None,
                )
            )

    # Sort by name
    response.sort(key=lambda x: x.name.lower())

    return response


@router.post("/", response_model=CategoryResponse, status_code=201)
async def create_category(
    category_data: CategoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new category."""
    # Validate parent if provided
    await hierarchy_validation_service.validate_parent(
        category_data.parent_category_id,
        current_user.organization_id,
        db,
        Category,
        parent_field_name="parent_category_id",
        entity_name="category",
    )

    # Sanitize user text input
    sanitized_name = input_sanitization_service.sanitize_html(category_data.name)

    category = Category(
        organization_id=current_user.organization_id,
        name=sanitized_name,
        color=category_data.color,
        parent_category_id=category_data.parent_category_id,
        plaid_category_name=category_data.plaid_category_name,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


@router.patch("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: UUID,
    category_data: CategoryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a category."""
    result = await db.execute(
        select(Category).where(
            Category.id == category_id,
            Category.organization_id == current_user.organization_id,
        )
    )
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Validate parent if changing it
    if category_data.parent_category_id is not None:
        # Prevent setting self as parent
        if category_data.parent_category_id == category_id:
            raise HTTPException(status_code=400, detail="Cannot set category as its own parent")

        # Check if this category has children - if so, can't make it a child
        children_result = await db.execute(
            select(Category.id).where(Category.parent_category_id == category_id).limit(1)
        )
        has_children = children_result.scalar_one_or_none() is not None

        if has_children and category_data.parent_category_id:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Cannot assign a parent to this category"
                    " because it already has children."
                    " Maximum 2 levels allowed."
                ),
            )

        # Validate the new parent
        await hierarchy_validation_service.validate_parent(
            category_data.parent_category_id,
            current_user.organization_id,
            db,
            Category,
            parent_field_name="parent_category_id",
            entity_name="category",
        )

    if category_data.name is not None:
        category.name = input_sanitization_service.sanitize_html(category_data.name)
    if category_data.color is not None:
        category.color = category_data.color
    if category_data.parent_category_id is not None:
        category.parent_category_id = category_data.parent_category_id
    if category_data.plaid_category_name is not None:
        category.plaid_category_name = category_data.plaid_category_name

    await db.commit()
    await db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=204)
async def delete_category(
    category_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a category."""
    result = await db.execute(
        select(Category).where(
            Category.id == category_id,
            Category.organization_id == current_user.organization_id,
        )
    )
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    await db.delete(category)
    await db.commit()
