"""CRUD operations for dependents."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dependent import Dependent


class DependentCRUD:
    """CRUD operations for Dependent model."""

    @staticmethod
    async def get_by_id(db: AsyncSession, dependent_id: UUID) -> Optional[Dependent]:
        result = await db.execute(select(Dependent).where(Dependent.id == dependent_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def list_for_household(db: AsyncSession, household_id: UUID) -> List[Dependent]:
        result = await db.execute(
            select(Dependent)
            .where(Dependent.household_id == household_id)
            .order_by(Dependent.date_of_birth)
        )
        return list(result.scalars().all())

    @staticmethod
    async def create(db: AsyncSession, **kwargs) -> Dependent:
        dependent = Dependent(**kwargs)
        db.add(dependent)
        await db.commit()
        await db.refresh(dependent)
        return dependent

    @staticmethod
    async def update(db: AsyncSession, dependent: Dependent, **kwargs) -> Dependent:
        for key, value in kwargs.items():
            if hasattr(dependent, key):
                setattr(dependent, key, value)
        await db.commit()
        await db.refresh(dependent)
        return dependent

    @staticmethod
    async def delete(db: AsyncSession, dependent: Dependent) -> None:
        await db.delete(dependent)
        await db.commit()


dependent_crud = DependentCRUD()
