"""CRUD operations for insurance policies."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.insurance_policy import InsurancePolicy


class InsurancePolicyCRUD:
    """CRUD operations for InsurancePolicy model."""

    @staticmethod
    async def get_by_id(db: AsyncSession, policy_id: UUID) -> Optional[InsurancePolicy]:
        result = await db.execute(select(InsurancePolicy).where(InsurancePolicy.id == policy_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def list_for_household(
        db: AsyncSession,
        household_id: UUID,
        active_only: bool = True,
    ) -> List[InsurancePolicy]:
        conditions = [InsurancePolicy.household_id == household_id]
        if active_only:
            conditions.append(InsurancePolicy.is_active.is_(True))  # noqa: E712
        result = await db.execute(
            select(InsurancePolicy)
            .where(and_(*conditions))
            .order_by(InsurancePolicy.policy_type, InsurancePolicy.provider)
        )
        return list(result.scalars().all())

    @staticmethod
    async def create(db: AsyncSession, **kwargs) -> InsurancePolicy:
        policy = InsurancePolicy(**kwargs)
        db.add(policy)
        await db.commit()
        await db.refresh(policy)
        return policy

    @staticmethod
    async def update(db: AsyncSession, policy: InsurancePolicy, **kwargs) -> InsurancePolicy:
        for key, value in kwargs.items():
            if hasattr(policy, key):
                setattr(policy, key, value)
        await db.commit()
        await db.refresh(policy)
        return policy

    @staticmethod
    async def delete(db: AsyncSession, policy: InsurancePolicy) -> None:
        await db.delete(policy)
        await db.commit()


insurance_policy_crud = InsurancePolicyCRUD()
