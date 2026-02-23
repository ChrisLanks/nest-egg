"""Unit tests for dependencies module."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import (
    get_current_user,
    get_current_active_user,
    get_current_admin_user,
    get_verified_account,
    verify_household_member,
    get_user_accounts,
    get_all_household_accounts,
    verify_account_access,
)
from app.models.user import User, AccountShare, SharePermission
from app.models.account import Account
from app.services.identity.base import AuthenticatedIdentity


def _make_identity(user_id):
    return AuthenticatedIdentity(
        user_id=user_id,
        provider="builtin",
        subject=str(user_id),
        email="user@example.com",
        groups=[],
        raw_claims={},
    )


@pytest.mark.unit
class TestGetCurrentUser:
    """Test get_current_user dependency (delegates to IdentityProviderChain)."""

    @pytest.fixture
    def mock_credentials(self):
        creds = Mock(spec=HTTPAuthorizationCredentials)
        creds.credentials = "valid-token"
        return creds

    @pytest.fixture
    def mock_db(self):
        return AsyncMock(spec=AsyncSession)

    @pytest.mark.asyncio
    async def test_valid_token_returns_user(self, mock_credentials, mock_db):
        """Should return user when chain authenticates the token successfully."""
        user_id = uuid4()
        mock_user = Mock(spec=User)
        mock_user.id = user_id
        mock_user.is_active = True

        mock_chain = Mock()
        mock_chain.authenticate = AsyncMock(return_value=_make_identity(user_id))

        with patch("app.dependencies.get_chain", return_value=mock_chain):
            with patch("app.dependencies.user_crud.get_by_id", new=AsyncMock(return_value=mock_user)):
                result = await get_current_user(mock_credentials, mock_db)
                assert result == mock_user

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self, mock_credentials, mock_db):
        """Should propagate 401 when chain rejects the token."""
        mock_chain = Mock()
        mock_chain.authenticate = AsyncMock(
            side_effect=HTTPException(status_code=401, detail="Invalid or expired token")
        )

        with patch("app.dependencies.get_chain", return_value=mock_chain):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials, mock_db)

            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_user_not_found_raises_401(self, mock_credentials, mock_db):
        """Should raise 401 when identity resolves but DB has no matching user."""
        user_id = uuid4()
        mock_chain = Mock()
        mock_chain.authenticate = AsyncMock(return_value=_make_identity(user_id))

        with patch("app.dependencies.get_chain", return_value=mock_chain):
            with patch("app.dependencies.user_crud.get_by_id", new=AsyncMock(return_value=None)):
                with pytest.raises(HTTPException) as exc_info:
                    await get_current_user(mock_credentials, mock_db)

                assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_inactive_user_raises_403(self, mock_credentials, mock_db):
        """Should raise 403 for inactive user."""
        user_id = uuid4()
        mock_user = Mock(spec=User)
        mock_user.id = user_id
        mock_user.is_active = False

        mock_chain = Mock()
        mock_chain.authenticate = AsyncMock(return_value=_make_identity(user_id))

        with patch("app.dependencies.get_chain", return_value=mock_chain):
            with patch("app.dependencies.user_crud.get_by_id", new=AsyncMock(return_value=mock_user)):
                with pytest.raises(HTTPException) as exc_info:
                    await get_current_user(mock_credentials, mock_db)

                assert exc_info.value.status_code == 403
                assert "inactive" in exc_info.value.detail.lower()


@pytest.mark.unit
class TestGetCurrentActiveUser:
    """Test get_current_active_user dependency."""

    @pytest.mark.asyncio
    async def test_active_user_returns_user(self):
        """Should return active user."""
        mock_user = Mock(spec=User)
        mock_user.is_active = True

        result = await get_current_active_user(mock_user)

        assert result == mock_user

    @pytest.mark.asyncio
    async def test_inactive_user_raises_error(self):
        """Should raise 403 for inactive user."""
        mock_user = Mock(spec=User)
        mock_user.is_active = False

        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_user(mock_user)

        assert exc_info.value.status_code == 403


@pytest.mark.unit
class TestGetCurrentAdminUser:
    """Test get_current_admin_user dependency."""

    @pytest.mark.asyncio
    async def test_admin_user_returns_user(self):
        """Should return admin user."""
        mock_user = Mock(spec=User)
        mock_user.is_org_admin = True

        result = await get_current_admin_user(mock_user)

        assert result == mock_user

    @pytest.mark.asyncio
    async def test_non_admin_user_raises_error(self):
        """Should raise 403 for non-admin user."""
        mock_user = Mock(spec=User)
        mock_user.is_org_admin = False

        with pytest.raises(HTTPException) as exc_info:
            await get_current_admin_user(mock_user)

        assert exc_info.value.status_code == 403
        assert "admin" in exc_info.value.detail.lower()


@pytest.mark.unit
class TestGetVerifiedAccount:
    """Test get_verified_account dependency."""

    @pytest.fixture
    def mock_user(self):
        """Create mock user."""
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        return user

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.mark.asyncio
    async def test_valid_account_returns_account(self, mock_user, mock_db):
        """Should return account when it belongs to user's organization."""
        account_id = uuid4()
        mock_account = Mock(spec=Account)
        mock_account.id = account_id
        mock_account.organization_id = mock_user.organization_id

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_account)
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await get_verified_account(account_id, mock_user, mock_db)

        assert result == mock_account

    @pytest.mark.asyncio
    async def test_account_not_found_raises_error(self, mock_user, mock_db):
        """Should raise 404 when account not found."""
        account_id = uuid4()

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await get_verified_account(account_id, mock_user, mock_db)

        assert exc_info.value.status_code == 404


@pytest.mark.unit
class TestVerifyHouseholdMember:
    """Test verify_household_member function."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.mark.asyncio
    async def test_valid_household_member_returns_user(self, mock_db):
        """Should return user when they are in household."""
        user_id = uuid4()
        org_id = uuid4()

        mock_user = Mock(spec=User)
        mock_user.id = user_id
        mock_user.organization_id = org_id
        mock_user.is_active = True

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_user)
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await verify_household_member(mock_db, user_id, org_id)

        assert result == mock_user

    @pytest.mark.asyncio
    async def test_user_not_in_household_raises_error(self, mock_db):
        """Should raise 404 when user not in household."""
        user_id = uuid4()
        org_id = uuid4()

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await verify_household_member(mock_db, user_id, org_id)

        assert exc_info.value.status_code == 404
        assert "household" in exc_info.value.detail.lower()


@pytest.mark.unit
class TestGetUserAccounts:
    """Test get_user_accounts function."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.mark.asyncio
    async def test_returns_owned_accounts(self, mock_db):
        """Should return accounts owned by user."""
        user_id = uuid4()
        org_id = uuid4()

        mock_account = Mock(spec=Account)
        mock_account.id = uuid4()
        mock_account.user_id = user_id

        mock_scalars = Mock()
        mock_scalars.all = Mock(return_value=[mock_account])
        mock_unique = Mock()
        mock_unique.scalars = Mock(return_value=mock_scalars)
        mock_result = Mock()
        mock_result.unique = Mock(return_value=mock_unique)

        mock_shared_scalars = Mock()
        mock_shared_scalars.all = Mock(return_value=[])
        mock_shared_unique = Mock()
        mock_shared_unique.scalars = Mock(return_value=mock_shared_scalars)
        mock_shared_result = Mock()
        mock_shared_result.unique = Mock(return_value=mock_shared_unique)

        mock_db.execute = AsyncMock(side_effect=[mock_result, mock_shared_result])

        result = await get_user_accounts(mock_db, user_id, org_id)

        assert len(result) == 1
        assert result[0] == mock_account

    @pytest.mark.asyncio
    async def test_returns_shared_accounts(self, mock_db):
        """Should return accounts shared with user."""
        user_id = uuid4()
        org_id = uuid4()

        mock_shared_account = Mock(spec=Account)
        mock_shared_account.id = uuid4()

        mock_owned_scalars = Mock()
        mock_owned_scalars.all = Mock(return_value=[])
        mock_owned_unique = Mock()
        mock_owned_unique.scalars = Mock(return_value=mock_owned_scalars)
        mock_owned_result = Mock()
        mock_owned_result.unique = Mock(return_value=mock_owned_unique)

        mock_shared_scalars = Mock()
        mock_shared_scalars.all = Mock(return_value=[mock_shared_account])
        mock_shared_unique = Mock()
        mock_shared_unique.scalars = Mock(return_value=mock_shared_scalars)
        mock_shared_result = Mock()
        mock_shared_result.unique = Mock(return_value=mock_shared_unique)

        mock_db.execute = AsyncMock(side_effect=[mock_owned_result, mock_shared_result])

        result = await get_user_accounts(mock_db, user_id, org_id)

        assert len(result) == 1
        assert result[0] == mock_shared_account

    @pytest.mark.asyncio
    async def test_deduplicates_accounts(self, mock_db):
        """Should deduplicate when account is both owned and shared."""
        user_id = uuid4()
        org_id = uuid4()

        account_id = uuid4()
        mock_account1 = Mock(spec=Account)
        mock_account1.id = account_id

        mock_account2 = Mock(spec=Account)
        mock_account2.id = account_id

        mock_owned_scalars = Mock()
        mock_owned_scalars.all = Mock(return_value=[mock_account1])
        mock_owned_unique = Mock()
        mock_owned_unique.scalars = Mock(return_value=mock_owned_scalars)
        mock_owned_result = Mock()
        mock_owned_result.unique = Mock(return_value=mock_owned_unique)

        mock_shared_scalars = Mock()
        mock_shared_scalars.all = Mock(return_value=[mock_account2])
        mock_shared_unique = Mock()
        mock_shared_unique.scalars = Mock(return_value=mock_shared_scalars)
        mock_shared_result = Mock()
        mock_shared_result.unique = Mock(return_value=mock_shared_unique)

        mock_db.execute = AsyncMock(side_effect=[mock_owned_result, mock_shared_result])

        result = await get_user_accounts(mock_db, user_id, org_id)

        assert len(result) == 1
        assert result[0].id == account_id


@pytest.mark.unit
class TestGetAllHouseholdAccounts:
    """Test get_all_household_accounts function."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.mark.asyncio
    async def test_returns_all_household_accounts(self, mock_db):
        """Should return all accounts in household."""
        org_id = uuid4()

        mock_account1 = Mock(spec=Account)
        mock_account1.id = uuid4()
        mock_account2 = Mock(spec=Account)
        mock_account2.id = uuid4()

        mock_scalars = Mock()
        mock_scalars.all = Mock(return_value=[mock_account1, mock_account2])
        mock_unique = Mock()
        mock_unique.scalars = Mock(return_value=mock_scalars)
        mock_result = Mock()
        mock_result.unique = Mock(return_value=mock_unique)

        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await get_all_household_accounts(mock_db, org_id)

        assert len(result) == 2
        assert mock_account1 in result
        assert mock_account2 in result


@pytest.mark.unit
class TestVerifyAccountAccess:
    """Test verify_account_access function."""

    @pytest.fixture
    def mock_user(self):
        """Create mock user."""
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        return user

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.mark.asyncio
    async def test_owner_has_access(self, mock_user, mock_db):
        """Should return account when user is owner."""
        account_id = uuid4()
        mock_account = Mock(spec=Account)
        mock_account.id = account_id
        mock_account.organization_id = mock_user.organization_id
        mock_account.user_id = mock_user.id

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_account)
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await verify_account_access(account_id, mock_user, mock_db)

        assert result == mock_account

    @pytest.mark.asyncio
    async def test_account_not_found_raises_error(self, mock_user, mock_db):
        """Should raise 404 when account doesn't exist."""
        account_id = uuid4()

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await verify_account_access(account_id, mock_user, mock_db)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_wrong_organization_raises_error(self, mock_user, mock_db):
        """Should raise 403 when account belongs to different organization."""
        account_id = uuid4()
        mock_account = Mock(spec=Account)
        mock_account.id = account_id
        mock_account.organization_id = uuid4()  # Different org
        mock_account.user_id = uuid4()

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_account)
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await verify_account_access(account_id, mock_user, mock_db)

        assert exc_info.value.status_code == 403
        assert "denied" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_shared_view_access_allowed(self, mock_user, mock_db):
        """Should allow access when account is shared with view permission."""
        account_id = uuid4()
        mock_account = Mock(spec=Account)
        mock_account.id = account_id
        mock_account.organization_id = mock_user.organization_id
        mock_account.user_id = uuid4()  # Different user

        mock_share = Mock(spec=AccountShare)
        mock_share.permission = SharePermission.VIEW

        mock_account_result = Mock()
        mock_account_result.scalar_one_or_none = Mock(return_value=mock_account)

        mock_share_result = Mock()
        mock_share_result.scalar_one_or_none = Mock(return_value=mock_share)

        mock_db.execute = AsyncMock(side_effect=[mock_account_result, mock_share_result])

        result = await verify_account_access(account_id, mock_user, mock_db, require_edit=False)

        assert result == mock_account

    @pytest.mark.asyncio
    async def test_shared_edit_access_allowed(self, mock_user, mock_db):
        """Should allow access when account is shared with edit permission."""
        account_id = uuid4()
        mock_account = Mock(spec=Account)
        mock_account.id = account_id
        mock_account.organization_id = mock_user.organization_id
        mock_account.user_id = uuid4()

        mock_share = Mock(spec=AccountShare)
        mock_share.permission = SharePermission.EDIT

        mock_account_result = Mock()
        mock_account_result.scalar_one_or_none = Mock(return_value=mock_account)

        mock_share_result = Mock()
        mock_share_result.scalar_one_or_none = Mock(return_value=mock_share)

        mock_db.execute = AsyncMock(side_effect=[mock_account_result, mock_share_result])

        result = await verify_account_access(account_id, mock_user, mock_db, require_edit=True)

        assert result == mock_account

    @pytest.mark.asyncio
    async def test_view_permission_denied_when_edit_required(self, mock_user, mock_db):
        """Should raise 403 when edit required but only has view permission."""
        account_id = uuid4()
        mock_account = Mock(spec=Account)
        mock_account.id = account_id
        mock_account.organization_id = mock_user.organization_id
        mock_account.user_id = uuid4()

        mock_share = Mock(spec=AccountShare)
        mock_share.permission = SharePermission.VIEW

        mock_account_result = Mock()
        mock_account_result.scalar_one_or_none = Mock(return_value=mock_account)

        mock_share_result = Mock()
        mock_share_result.scalar_one_or_none = Mock(return_value=mock_share)

        mock_db.execute = AsyncMock(side_effect=[mock_account_result, mock_share_result])

        with pytest.raises(HTTPException) as exc_info:
            await verify_account_access(account_id, mock_user, mock_db, require_edit=True)

        assert exc_info.value.status_code == 403
        assert "edit permission" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_no_shared_access_raises_error(self, mock_user, mock_db):
        """Should raise 403 when account not shared with user."""
        account_id = uuid4()
        mock_account = Mock(spec=Account)
        mock_account.id = account_id
        mock_account.organization_id = mock_user.organization_id
        mock_account.user_id = uuid4()

        mock_account_result = Mock()
        mock_account_result.scalar_one_or_none = Mock(return_value=mock_account)

        mock_share_result = Mock()
        mock_share_result.scalar_one_or_none = Mock(return_value=None)

        mock_db.execute = AsyncMock(side_effect=[mock_account_result, mock_share_result])

        with pytest.raises(HTTPException) as exc_info:
            await verify_account_access(account_id, mock_user, mock_db)

        assert exc_info.value.status_code == 403
        assert "don't have access" in exc_info.value.detail.lower()
