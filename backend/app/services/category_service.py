"""Category service for mapping Plaid categories to custom categories."""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Category


async def get_category_id_for_plaid_category(
    db: AsyncSession,
    organization_id: UUID,
    plaid_category_name: Optional[str],
) -> Optional[UUID]:
    """
    Find a custom category that matches the given Plaid category name.

    This enables auto-mapping of transactions to custom categories when they're
    synced from Plaid/MX. If a custom category has a plaid_category_name that
    matches the transaction's category_primary, return its ID.

    Args:
        db: Database session
        organization_id: Organization ID to scope the search
        plaid_category_name: The Plaid category_primary from the transaction

    Returns:
        UUID of the matching custom category, or None if no match found
    """
    if not plaid_category_name:
        return None

    result = await db.execute(
        select(Category.id)
        .where(
            Category.organization_id == organization_id,
            Category.plaid_category_name == plaid_category_name,
        )
        .limit(1)
    )

    category_id = result.scalar_one_or_none()
    return category_id
