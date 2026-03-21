"""Tests for user management: household status toggle, dev hard-delete, dev random users."""

from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.user import User


@pytest.fixture
def admin_user():
    user = Mock(spec=User)
    user.id = uuid4()
    user.organization_id = uuid4()
    user.email = "admin@test.com"
    user.is_active = True
    user.is_org_admin = True
    user.is_primary_household_member = True
    return user


@pytest.fixture
def member_user(admin_user):
    user = Mock(spec=User)
    user.id = uuid4()
    user.organization_id = admin_user.organization_id
    user.email = "member@test.com"
    user.first_name = "Member"
    user.last_name = "User"
    user.is_active = True
    user.is_org_admin = False
    user.is_primary_household_member = False
    return user


@pytest.fixture
def mock_db():
    return AsyncMock()


# ---------------------------------------------------------------------------
# Household: PATCH /members/{user_id}/status
# ---------------------------------------------------------------------------


class TestUpdateMemberStatus:
    @pytest.mark.asyncio
    async def test_disable_member(self, admin_user, member_user, mock_db):
        from app.api.v1.household import UpdateMemberStatusRequest, update_member_status

        # Mock DB returning the member
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = member_user
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        body = UpdateMemberStatusRequest(is_active=False)
        await update_member_status(
            user_id=member_user.id, body=body, current_user=admin_user, db=mock_db
        )

        assert member_user.is_active is False

    @pytest.mark.asyncio
    async def test_reenable_member(self, admin_user, member_user, mock_db):
        from app.api.v1.household import UpdateMemberStatusRequest, update_member_status

        member_user.is_active = False

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = member_user
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        body = UpdateMemberStatusRequest(is_active=True)
        await update_member_status(
            user_id=member_user.id, body=body, current_user=admin_user, db=mock_db
        )

        assert member_user.is_active is True

    @pytest.mark.asyncio
    async def test_cannot_disable_self(self, admin_user, mock_db):
        from app.api.v1.household import UpdateMemberStatusRequest, update_member_status

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = admin_user
        mock_db.execute = AsyncMock(return_value=mock_result)

        body = UpdateMemberStatusRequest(is_active=False)
        with pytest.raises(HTTPException) as exc_info:
            await update_member_status(
                user_id=admin_user.id, body=body, current_user=admin_user, db=mock_db
            )
        assert exc_info.value.status_code == 400
        assert "your own" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_cannot_disable_primary_member(self, admin_user, mock_db):
        from app.api.v1.household import UpdateMemberStatusRequest, update_member_status

        primary = Mock(spec=User)
        primary.id = uuid4()
        primary.organization_id = admin_user.organization_id
        primary.is_primary_household_member = True
        primary.is_active = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = primary
        mock_db.execute = AsyncMock(return_value=mock_result)

        body = UpdateMemberStatusRequest(is_active=False)
        with pytest.raises(HTTPException) as exc_info:
            await update_member_status(
                user_id=primary.id, body=body, current_user=admin_user, db=mock_db
            )
        assert exc_info.value.status_code == 400
        assert "primary" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_user_not_found(self, admin_user, mock_db):
        from app.api.v1.household import UpdateMemberStatusRequest, update_member_status

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        body = UpdateMemberStatusRequest(is_active=False)
        with pytest.raises(HTTPException) as exc_info:
            await update_member_status(
                user_id=uuid4(), body=body, current_user=admin_user, db=mock_db
            )
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Dev: DELETE /dev/users/{user_id}
# ---------------------------------------------------------------------------


class TestDevHardDeleteUser:
    @pytest.mark.asyncio
    async def test_hard_delete_member(self, admin_user, member_user, mock_db):
        from app.api.v1.dev import hard_delete_user

        # First call: find user, second call: count remaining
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = member_user

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1  # 1 remaining after delete

        mock_db.execute = AsyncMock(side_effect=[mock_user_result, mock_count_result])
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()

        await hard_delete_user(user_id=member_user.id, current_user=admin_user, db=mock_db)

        mock_db.delete.assert_called_once_with(member_user)

    @pytest.mark.asyncio
    async def test_cannot_delete_self(self, admin_user, mock_db):
        from app.api.v1.dev import hard_delete_user

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = admin_user
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await hard_delete_user(user_id=admin_user.id, current_user=admin_user, db=mock_db)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_cannot_delete_primary_member(self, admin_user, mock_db):
        from app.api.v1.dev import hard_delete_user

        primary = Mock(spec=User)
        primary.id = uuid4()
        primary.organization_id = admin_user.organization_id
        primary.is_primary_household_member = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = primary
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await hard_delete_user(user_id=primary.id, current_user=admin_user, db=mock_db)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_user_not_found(self, admin_user, mock_db):
        from app.api.v1.dev import hard_delete_user

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await hard_delete_user(user_id=uuid4(), current_user=admin_user, db=mock_db)
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Dev: POST /dev/users/random
# ---------------------------------------------------------------------------


class TestDevCreateRandomUsers:
    @pytest.mark.asyncio
    async def test_create_random_users(self, admin_user, mock_db):
        from app.api.v1.dev import CreateRandomUsersRequest, create_random_users

        # Mock: no existing users found (uniqueness check)
        mock_no_user = MagicMock()
        mock_no_user.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_no_user)
        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.add = MagicMock()

        body = CreateRandomUsersRequest(count=3)
        result = await create_random_users(body=body, current_user=admin_user, db=mock_db)

        assert len(result["created"]) == 3
        assert mock_db.add.call_count == 3

    @pytest.mark.asyncio
    async def test_rejects_invalid_count(self, admin_user, mock_db):
        from app.api.v1.dev import CreateRandomUsersRequest, create_random_users

        body = CreateRandomUsersRequest(count=0)
        with pytest.raises(HTTPException) as exc_info:
            await create_random_users(body=body, current_user=admin_user, db=mock_db)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_rejects_too_many(self, admin_user, mock_db):
        from app.api.v1.dev import CreateRandomUsersRequest, create_random_users

        body = CreateRandomUsersRequest(count=51)
        with pytest.raises(HTTPException) as exc_info:
            await create_random_users(body=body, current_user=admin_user, db=mock_db)
        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# Dev: GET /dev/users
# ---------------------------------------------------------------------------


class TestDevListUsers:
    @pytest.mark.asyncio
    async def test_list_users(self, admin_user, mock_db):
        from app.api.v1.dev import list_all_users

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [admin_user]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await list_all_users(current_user=admin_user, db=mock_db)
        assert len(result) == 1
