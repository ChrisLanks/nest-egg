"""CRUD operations for users."""

from datetime import datetime, date
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import Organization, RefreshToken, User
from app.utils.datetime_utils import utc_now


class UserCRUD:
    """CRUD operations for User model."""

    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> Optional[User]:
        """Get user by email."""
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        db: AsyncSession,
        email: str,
        password: str,
        organization_id: UUID,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        display_name: Optional[str] = None,
        birth_month: Optional[int] = None,
        birth_year: Optional[int] = None,
        is_org_admin: bool = False,
    ) -> User:
        """Create a new user."""
        if birth_year and birth_month:
            birthdate = date(birth_year, birth_month, 1)
        elif birth_year:
            birthdate = date(birth_year, 1, 1)
        else:
            birthdate = None
        user = User(
            email=email,
            password_hash=hash_password(password),
            organization_id=organization_id,
            first_name=first_name,
            last_name=last_name,
            display_name=display_name,
            birthdate=birthdate,
            is_org_admin=is_org_admin,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def update_last_login(db: AsyncSession, user_id: UUID) -> None:
        """Update user's last login timestamp."""
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.last_login_at = utc_now()
            await db.commit()


class OrganizationCRUD:
    """CRUD operations for Organization model."""

    @staticmethod
    async def create(
        db: AsyncSession,
        name: str,
        custom_month_end_day: int = 30,
        timezone: str = "UTC",
    ) -> Organization:
        """Create a new organization."""
        org = Organization(
            name=name,
            custom_month_end_day=custom_month_end_day,
            timezone=timezone,
        )
        db.add(org)
        await db.commit()
        await db.refresh(org)
        return org

    @staticmethod
    async def get_by_id(db: AsyncSession, org_id: UUID) -> Optional[Organization]:
        """Get organization by ID."""
        result = await db.execute(select(Organization).where(Organization.id == org_id))
        return result.scalar_one_or_none()


class RefreshTokenCRUD:
    """CRUD operations for RefreshToken model."""

    @staticmethod
    async def create(
        db: AsyncSession,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshToken:
        """Create a new refresh token."""
        token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db.add(token)
        await db.commit()
        await db.refresh(token)
        return token

    @staticmethod
    async def get_by_token_hash(db: AsyncSession, token_hash: str) -> Optional[RefreshToken]:
        """Get refresh token by hash."""
        result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
        return result.scalar_one_or_none()

    @staticmethod
    async def revoke(db: AsyncSession, token_hash: str) -> None:
        """Revoke a refresh token."""
        result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
        token = result.scalar_one_or_none()
        if token:
            token.revoked_at = utc_now()
            await db.commit()


# Create singleton instances
user_crud = UserCRUD()
organization_crud = OrganizationCRUD()
refresh_token_crud = RefreshTokenCRUD()
