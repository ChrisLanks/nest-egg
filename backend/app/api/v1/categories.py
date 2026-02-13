"""Category API endpoints."""

from typing import List, Dict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.transaction import Transaction

router = APIRouter()


class CategoryResponse(BaseModel):
    """Category with usage count."""
    name: str
    count: int


class CategoryRename(BaseModel):
    """Rename category request."""
    old_name: str
    new_name: str


@router.get("/", response_model=List[CategoryResponse])
async def list_categories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all unique categories with usage counts."""
    result = await db.execute(
        select(
            Transaction.category_primary,
            func.count(Transaction.id).label('count')
        )
        .where(
            Transaction.organization_id == current_user.organization_id,
            Transaction.category_primary.isnot(None)
        )
        .group_by(Transaction.category_primary)
        .order_by(Transaction.category_primary)
    )

    categories = []
    for row in result:
        categories.append(CategoryResponse(name=row[0], count=row[1]))

    return categories


@router.post("/rename")
async def rename_category(
    rename_data: CategoryRename,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rename a category across all transactions."""
    if not rename_data.old_name or not rename_data.new_name:
        raise HTTPException(status_code=400, detail="Both old_name and new_name are required")

    # Update all transactions with the old category name
    result = await db.execute(
        update(Transaction)
        .where(
            Transaction.organization_id == current_user.organization_id,
            Transaction.category_primary == rename_data.old_name
        )
        .values(category_primary=rename_data.new_name)
    )

    await db.commit()

    return {
        "message": f"Renamed '{rename_data.old_name}' to '{rename_data.new_name}'",
        "updated_count": result.rowcount
    }


@router.delete("/{category_name}")
async def delete_category(
    category_name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a category (sets it to null on all transactions)."""
    if not category_name:
        raise HTTPException(status_code=400, detail="Category name is required")

    # Set category to null for all transactions using this category
    result = await db.execute(
        update(Transaction)
        .where(
            Transaction.organization_id == current_user.organization_id,
            Transaction.category_primary == category_name
        )
        .values(category_primary=None)
    )

    await db.commit()

    return {
        "message": f"Deleted category '{category_name}'",
        "updated_count": result.rowcount
    }
