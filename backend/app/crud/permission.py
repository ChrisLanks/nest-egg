"""CRUD operations for permission grants."""

from typing import Optional
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permission import PermissionGrant, PermissionGrantAudit


class PermissionGrantCRUD:
    """CRUD helpers for PermissionGrant and PermissionGrantAudit."""

    @staticmethod
    async def get_by_id(db: AsyncSession, grant_id: UUID) -> Optional[PermissionGrant]:
        result = await db.execute(
            select(PermissionGrant).where(PermissionGrant.id == grant_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def find_active(
        db: AsyncSession,
        grantor_id: UUID,
        grantee_id: UUID,
        resource_type: str,
        resource_id: Optional[UUID] = None,
    ) -> Optional[PermissionGrant]:
        """Return the most permissive active grant that covers this resource.

        Checks two conditions (OR):
          1. Exact match: same resource_id
          2. Wildcard grant: resource_id IS NULL (covers all resources of this type)
        """
        result = await db.execute(
            select(PermissionGrant).where(
                PermissionGrant.grantor_id == grantor_id,
                PermissionGrant.grantee_id == grantee_id,
                PermissionGrant.resource_type == resource_type,
                PermissionGrant.is_active.is_(True),
                or_(
                    PermissionGrant.resource_id == resource_id,
                    PermissionGrant.resource_id.is_(None),
                ),
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def find_exact(
        db: AsyncSession,
        grantor_id: UUID,
        grantee_id: UUID,
        resource_type: str,
        resource_id: Optional[UUID],
    ) -> Optional[PermissionGrant]:
        """Return the grant that exactly matches all four key fields (including NULL)."""
        condition = and_(
            PermissionGrant.grantor_id == grantor_id,
            PermissionGrant.grantee_id == grantee_id,
            PermissionGrant.resource_type == resource_type,
        )
        if resource_id is None:
            condition = and_(condition, PermissionGrant.resource_id.is_(None))
        else:
            condition = and_(condition, PermissionGrant.resource_id == resource_id)

        result = await db.execute(select(PermissionGrant).where(condition))
        return result.scalar_one_or_none()

    @staticmethod
    async def list_given(
        db: AsyncSession, grantor_id: UUID, org_id: UUID
    ) -> list[PermissionGrant]:
        result = await db.execute(
            select(PermissionGrant)
            .where(
                PermissionGrant.organization_id == org_id,
                PermissionGrant.grantor_id == grantor_id,
                PermissionGrant.is_active.is_(True),
            )
            .order_by(PermissionGrant.granted_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def list_received(
        db: AsyncSession, grantee_id: UUID, org_id: UUID
    ) -> list[PermissionGrant]:
        result = await db.execute(
            select(PermissionGrant)
            .where(
                PermissionGrant.organization_id == org_id,
                PermissionGrant.grantee_id == grantee_id,
                PermissionGrant.is_active.is_(True),
            )
            .order_by(PermissionGrant.granted_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def list_audit(
        db: AsyncSession, grantor_id: UUID, limit: int = 50, offset: int = 0
    ) -> list[PermissionGrantAudit]:
        result = await db.execute(
            select(PermissionGrantAudit)
            .where(PermissionGrantAudit.grantor_id == grantor_id)
            .order_by(PermissionGrantAudit.occurred_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())


permission_grant_crud = PermissionGrantCRUD()
