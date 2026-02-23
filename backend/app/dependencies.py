"""FastAPI dependencies for authentication and authorization."""

from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Path, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.crud.user import user_crud
from app.models.user import User, AccountShare, SharePermission
from app.models.account import Account
from app.services.identity.chain import get_chain
from sqlalchemy.orm import joinedload

# HTTP Bearer token scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get current authenticated user from JWT token.

    Delegates to the IdentityProviderChain which supports the built-in HS256
    JWT as well as external OIDC providers (Cognito, Keycloak, Okta, Google).

    Args:
        credentials: HTTP Bearer credentials
        db: Database session

    Returns:
        Current user

    Raises:
        HTTPException: If token is invalid or user not found
    """
    chain = get_chain()
    # chain.authenticate raises HTTPException(401) on failure
    identity = await chain.authenticate(credentials.credentials, db)

    if identity.user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not resolve user from token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await user_crud.get_by_id(db, identity.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current active user.

    Args:
        current_user: Current user from token

    Returns:
        Current active user

    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current user if they are an organization admin.

    Args:
        current_user: Current user from token

    Returns:
        Current user if admin

    Raises:
        HTTPException: If user is not an org admin
    """
    if not current_user.is_org_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User must be an organization admin",
        )
    return current_user


async def get_verified_account(
    account_id: UUID = Path(..., description="Account ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Account:
    """
    Get and verify account belongs to user's organization.

    This dependency eliminates code duplication for account verification
    across multiple endpoints.

    Args:
        account_id: Account UUID from path parameter
        current_user: Current authenticated user
        db: Database session

    Returns:
        Verified account

    Raises:
        HTTPException: If account not found or doesn't belong to user's organization
    """
    result = await db.execute(
        select(Account).where(
            Account.id == account_id,
            Account.organization_id == current_user.organization_id,
        )
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    return account


# Household multi-user support functions


async def verify_household_member(
    db: AsyncSession,
    user_id: UUID,
    organization_id: UUID,
) -> User:
    """Verify that a user is a member of the specified household.

    Args:
        db: Database session
        user_id: User ID to verify
        organization_id: Organization ID (household) to check membership

    Returns:
        User object if verified

    Raises:
        HTTPException: If user not found or not in household
    """
    result = await db.execute(
        select(User).where(
            User.id == user_id, User.organization_id == organization_id, User.is_active.is_(True)
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found or not in household"
        )

    return user


async def get_user_accounts(
    db: AsyncSession,
    user_id: UUID,
    organization_id: UUID,
) -> list[Account]:
    """Get all accounts owned by or shared with a specific user.

    Args:
        db: Database session
        user_id: User ID to get accounts for
        organization_id: Organization ID to filter by

    Returns:
        List of accounts (owned + shared)
    """
    # Get accounts owned by user (load all provider relationships)
    result = await db.execute(
        select(Account)
        .options(joinedload(Account.plaid_item), joinedload(Account.teller_enrollment))
        .where(
            Account.user_id == user_id,
            Account.organization_id == organization_id,
            Account.is_active.is_(True),
        )
    )
    owned_accounts = result.unique().scalars().all()

    # Get accounts shared with user (load all provider relationships)
    result = await db.execute(
        select(Account)
        .options(joinedload(Account.plaid_item), joinedload(Account.teller_enrollment))
        .join(AccountShare, AccountShare.account_id == Account.id)
        .where(
            AccountShare.shared_with_user_id == user_id,
            Account.organization_id == organization_id,
            Account.is_active.is_(True),
        )
    )
    shared_accounts = result.unique().scalars().all()

    # Combine and deduplicate (in case an account is both owned and shared)
    account_ids = set()
    all_accounts = []

    for account in owned_accounts + shared_accounts:
        if account.id not in account_ids:
            all_accounts.append(account)
            account_ids.add(account.id)

    return all_accounts


async def get_all_household_accounts(
    db: AsyncSession,
    organization_id: UUID,
) -> list[Account]:
    """Get all active accounts in a household.

    Args:
        db: Database session
        organization_id: Organization ID (household)

    Returns:
        List of all active accounts in household
    """
    result = await db.execute(
        select(Account)
        .options(joinedload(Account.plaid_item), joinedload(Account.teller_enrollment))
        .where(Account.organization_id == organization_id, Account.is_active.is_(True))
    )
    return result.unique().scalars().all()


async def verify_account_access(
    account_id: UUID, current_user: User, db: AsyncSession, require_edit: bool = False
) -> Account:
    """Verify user has access to account (owned or shared).

    Args:
        account_id: Account ID to check
        current_user: Current authenticated user
        db: Database session
        require_edit: If True, require edit permission (not just view)

    Returns:
        Account if user has access

    Raises:
        HTTPException: If user doesn't have access
    """
    # Get account
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    # Check household membership
    if account.organization_id != current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Owner has full access
    if account.user_id == current_user.id:
        return account

    # Check shared access
    result = await db.execute(
        select(AccountShare).where(
            AccountShare.account_id == account_id,
            AccountShare.shared_with_user_id == current_user.id,
        )
    )
    share = result.scalar_one_or_none()

    if not share:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You don't have access to this account"
        )

    # If edit permission required, check it
    if require_edit and share.permission != SharePermission.EDIT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have edit permission for this account",
        )

    return account
