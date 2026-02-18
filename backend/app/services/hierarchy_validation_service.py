"""Generic hierarchy validation service for categories, labels, etc."""

from typing import Optional, TypeVar, Type
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeMeta


T = TypeVar("T", bound=DeclarativeMeta)


class HierarchyValidationService:
    """Service for validating hierarchical relationships (categories, labels, etc.)."""

    @staticmethod
    async def validate_parent(
        parent_id: Optional[UUID],
        organization_id: UUID,
        db: AsyncSession,
        model_class: Type[T],
        parent_field_name: str = "parent_id",
        entity_name: str = "item",
    ) -> Optional[T]:
        """
        Validate parent entity exists and is at correct depth (max 1 level deep).

        Args:
            parent_id: UUID of the parent entity (None if no parent)
            organization_id: Organization ID to check ownership
            db: Database session
            model_class: SQLAlchemy model class (e.g., Category, Label)
            parent_field_name: Name of the parent ID field (e.g., "parent_category_id")
            entity_name: Human-readable name for error messages (e.g., "category", "label")

        Returns:
            Parent entity if valid, None if no parent specified

        Raises:
            HTTPException: If parent not found or hierarchy depth exceeded
        """
        if not parent_id:
            return None

        # Check parent exists and belongs to organization
        result = await db.execute(
            select(model_class).where(
                model_class.id == parent_id,
                model_class.organization_id == organization_id,
            )
        )
        parent = result.scalar_one_or_none()

        if not parent:
            raise HTTPException(status_code=404, detail=f"Parent {entity_name} not found")

        # Check parent depth (parent cannot have a parent - max 2 levels)
        parent_id_value = getattr(parent, parent_field_name, None)
        if parent_id_value is not None:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Cannot create {entity_name}: parent already has a parent. "
                    "Maximum 2 levels allowed (parent and child)."
                ),
            )

        return parent


# Create singleton instance
hierarchy_validation_service = HierarchyValidationService()
