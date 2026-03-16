"""Functional tests for guest access API endpoints."""

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.user import (
    GuestInvitationStatus,
    GuestRole,
    HouseholdGuest,
    HouseholdGuestInvitation,
)
from app.utils.datetime_utils import utc_now


def _make_user(org_id=None, is_admin=False, email="admin@example.com"):
    """Create a mock user without spec= so private attrs can be set."""
    user = Mock()
    user.id = uuid4()
    org = org_id or uuid4()
    user.organization_id = org
    user.is_active = True
    user.is_org_admin = is_admin
    user.email = email
    user.email_verified = True
    user.display_name = "Test Admin"
    user._is_guest = False
    user._home_org_id = user.organization_id
    user._guest_role = None
    return user


def _make_request(client_ip="127.0.0.1"):
    request = Mock()
    request.client = Mock()
    request.client.host = client_ip
    return request


class TestInviteGuest:
    """Test POST /guest-access/invite."""

    @pytest.mark.asyncio
    @patch("app.api.v1.guest_access.rate_limit_service")
    @patch("app.api.v1.guest_access.email_service")
    async def test_invite_guest_success(self, mock_email, mock_rate):
        from app.api.v1.guest_access import InviteGuestRequest, invite_guest

        mock_rate.check_rate_limit = AsyncMock(return_value=True)
        mock_email.send_invitation_email = AsyncMock()

        admin = _make_user(is_admin=True)
        request = _make_request()
        db = AsyncMock()

        # No existing guest
        mock_result1 = Mock()
        mock_result1.scalar_one_or_none.return_value = None
        # No pending invitation
        mock_result2 = Mock()
        mock_result2.scalar_one_or_none.return_value = None
        # Org name for email
        mock_result3 = Mock()
        mock_result3.scalar_one.return_value = "Smith Family"

        db.execute.side_effect = [mock_result1, mock_result2, mock_result3]
        db.commit = AsyncMock()

        # Simulate DB refresh setting the primary key
        async def fake_refresh(obj):
            if not obj.id:
                obj.id = uuid4()

        db.refresh = AsyncMock(side_effect=fake_refresh)

        body = InviteGuestRequest(email="guest@example.com", role=GuestRole.VIEWER)
        result = await invite_guest(body, request, admin, db)

        assert result.email == "guest@example.com"
        assert result.role == GuestRole.VIEWER
        assert db.add.called

    @pytest.mark.asyncio
    @patch("app.api.v1.guest_access.rate_limit_service")
    async def test_cannot_invite_self(self, mock_rate):
        from app.api.v1.guest_access import InviteGuestRequest, invite_guest

        mock_rate.check_rate_limit = AsyncMock(return_value=True)

        admin = _make_user(is_admin=True, email="admin@example.com")
        request = _make_request()
        db = AsyncMock()

        body = InviteGuestRequest(email="admin@example.com")

        with pytest.raises(HTTPException) as exc_info:
            await invite_guest(body, request, admin, db)
        assert exc_info.value.status_code == 400
        assert "yourself" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("app.api.v1.guest_access.rate_limit_service")
    async def test_rate_limited(self, mock_rate):
        from app.api.v1.guest_access import InviteGuestRequest, invite_guest

        mock_rate.check_rate_limit = AsyncMock(return_value=False)

        admin = _make_user(is_admin=True)
        request = _make_request()
        db = AsyncMock()
        body = InviteGuestRequest(email="guest@example.com")

        with pytest.raises(HTTPException) as exc_info:
            await invite_guest(body, request, admin, db)
        assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    @patch("app.api.v1.guest_access.rate_limit_service")
    async def test_duplicate_active_guest(self, mock_rate):
        from app.api.v1.guest_access import InviteGuestRequest, invite_guest

        mock_rate.check_rate_limit = AsyncMock(return_value=True)

        admin = _make_user(is_admin=True)
        request = _make_request()
        db = AsyncMock()

        # Existing active guest found
        existing = Mock(spec=HouseholdGuest)
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = existing
        db.execute.return_value = mock_result

        body = InviteGuestRequest(email="guest@example.com")

        with pytest.raises(HTTPException) as exc_info:
            await invite_guest(body, request, admin, db)
        assert exc_info.value.status_code == 409


class TestListGuests:
    """Test GET /guest-access/guests."""

    @pytest.mark.asyncio
    async def test_list_guests_returns_active(self):
        from app.api.v1.guest_access import list_guests

        admin = _make_user(is_admin=True)
        db = AsyncMock()

        guest_user_email = "guest@example.com"
        guest = Mock(spec=HouseholdGuest)
        guest.id = uuid4()
        guest.user_id = uuid4()
        guest.organization_id = admin.organization_id
        guest.role = GuestRole.VIEWER
        guest.label = "Mom & Dad"
        guest.is_active = True
        guest.created_at = utc_now()
        guest.revoked_at = None

        mock_result = Mock()
        mock_result.all.return_value = [(guest, guest_user_email)]
        db.execute.return_value = mock_result

        result = await list_guests(admin, db)
        assert len(result) == 1
        assert result[0].user_email == "guest@example.com"
        assert result[0].label == "Mom & Dad"

    @pytest.mark.asyncio
    async def test_list_guests_empty(self):
        from app.api.v1.guest_access import list_guests

        admin = _make_user(is_admin=True)
        db = AsyncMock()

        mock_result = Mock()
        mock_result.all.return_value = []
        db.execute.return_value = mock_result

        result = await list_guests(admin, db)
        assert len(result) == 0


class TestRevokeGuest:
    """Test DELETE /guest-access/guests/{id}."""

    @pytest.mark.asyncio
    async def test_revoke_success(self):
        from app.api.v1.guest_access import revoke_guest

        admin = _make_user(is_admin=True)
        db = AsyncMock()

        guest = Mock(spec=HouseholdGuest)
        guest.id = uuid4()
        guest.organization_id = admin.organization_id
        guest.is_active = True

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = guest
        db.execute.return_value = mock_result
        db.commit = AsyncMock()

        await revoke_guest(guest.id, admin, db)

        assert guest.is_active is False
        assert guest.revoked_at is not None
        assert guest.revoked_by_id == admin.id

    @pytest.mark.asyncio
    async def test_revoke_not_found(self):
        from app.api.v1.guest_access import revoke_guest

        admin = _make_user(is_admin=True)
        db = AsyncMock()

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await revoke_guest(uuid4(), admin, db)
        assert exc_info.value.status_code == 404


class TestAcceptInvitation:
    """Test POST /guest-access/accept/{code}."""

    @pytest.mark.asyncio
    async def test_accept_creates_guest_record(self):
        from app.api.v1.guest_access import accept_guest_invitation

        user = _make_user(email="alice@example.com")
        db = AsyncMock()

        target_org = uuid4()
        invitation = Mock(spec=HouseholdGuestInvitation)
        invitation.email = "alice@example.com"
        invitation.status = GuestInvitationStatus.PENDING
        invitation.is_expired = False
        invitation.organization_id = target_org
        invitation.invited_by_id = uuid4()
        invitation.role = GuestRole.VIEWER
        invitation.label = "My Daughter"

        # First execute: find invitation
        mock_result1 = Mock()
        mock_result1.scalar_one_or_none.return_value = invitation
        # Second execute: check existing guest
        mock_result2 = Mock()
        mock_result2.scalar_one_or_none.return_value = None

        db.execute.side_effect = [mock_result1, mock_result2]
        db.commit = AsyncMock()

        result = await accept_guest_invitation("valid-code", user, db)
        assert result["detail"] == "Guest access granted successfully"
        assert db.add.called
        assert invitation.status == GuestInvitationStatus.ACCEPTED

    @pytest.mark.asyncio
    async def test_accept_reactivates_revoked_guest(self):
        from app.api.v1.guest_access import accept_guest_invitation

        user = _make_user(email="alice@example.com")
        db = AsyncMock()

        target_org = uuid4()
        invitation = Mock(spec=HouseholdGuestInvitation)
        invitation.email = "alice@example.com"
        invitation.status = GuestInvitationStatus.PENDING
        invitation.is_expired = False
        invitation.organization_id = target_org
        invitation.invited_by_id = uuid4()
        invitation.role = GuestRole.ADVISOR
        invitation.label = "Financial Advisor"

        # Existing revoked guest
        existing_guest = Mock(spec=HouseholdGuest)
        existing_guest.is_active = False
        existing_guest.revoked_at = utc_now()

        mock_result1 = Mock()
        mock_result1.scalar_one_or_none.return_value = invitation
        mock_result2 = Mock()
        mock_result2.scalar_one_or_none.return_value = existing_guest

        db.execute.side_effect = [mock_result1, mock_result2]
        db.commit = AsyncMock()

        await accept_guest_invitation("valid-code", user, db)
        assert existing_guest.is_active is True
        assert existing_guest.role == GuestRole.ADVISOR
        assert existing_guest.revoked_at is None


class TestDeclineInvitation:
    """Test POST /guest-access/decline/{code}."""

    @pytest.mark.asyncio
    async def test_decline_success(self):
        from app.api.v1.guest_access import decline_guest_invitation

        user = _make_user(email="alice@example.com")
        db = AsyncMock()

        invitation = Mock(spec=HouseholdGuestInvitation)
        invitation.email = "alice@example.com"
        invitation.status = GuestInvitationStatus.PENDING

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = invitation
        db.execute.return_value = mock_result
        db.commit = AsyncMock()

        await decline_guest_invitation("some-code", user, db)
        assert invitation.status == GuestInvitationStatus.DECLINED


class TestMyHouseholds:
    """Test GET /guest-access/my-households."""

    @pytest.mark.asyncio
    async def test_returns_guest_households(self):
        from app.api.v1.guest_access import my_guest_households

        user = _make_user()
        db = AsyncMock()

        org_id = uuid4()
        guest = Mock(spec=HouseholdGuest)
        guest.organization_id = org_id
        guest.role = GuestRole.VIEWER
        guest.label = "Parents"
        guest.is_active = True

        mock_result = Mock()
        mock_result.all.return_value = [(guest, "Smith Family")]
        db.execute.return_value = mock_result

        result = await my_guest_households(user, db)
        assert len(result) == 1
        assert result[0].organization_name == "Smith Family"
        assert result[0].role == GuestRole.VIEWER

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_guest_access(self):
        from app.api.v1.guest_access import my_guest_households

        user = _make_user()
        db = AsyncMock()

        mock_result = Mock()
        mock_result.all.return_value = []
        db.execute.return_value = mock_result

        result = await my_guest_households(user, db)
        assert len(result) == 0


class TestLeaveGuestHousehold:
    """Test DELETE /guest-access/leave/{org_id}."""

    @pytest.mark.asyncio
    async def test_leave_success(self):
        from app.api.v1.guest_access import leave_guest_household

        user = _make_user()
        db = AsyncMock()
        org_id = uuid4()

        guest = Mock(spec=HouseholdGuest)
        guest.is_active = True

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = guest
        db.execute.return_value = mock_result
        db.commit = AsyncMock()

        await leave_guest_household(org_id, user, db)
        assert guest.is_active is False
        assert guest.revoked_by_id == user.id

    @pytest.mark.asyncio
    async def test_leave_not_found(self):
        from app.api.v1.guest_access import leave_guest_household

        user = _make_user()
        db = AsyncMock()

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await leave_guest_household(uuid4(), user, db)
        assert exc_info.value.status_code == 404


class TestUpdateGuest:
    """Test PATCH /guest-access/guests/{id}."""

    @pytest.mark.asyncio
    async def test_update_role(self):
        from app.api.v1.guest_access import UpdateGuestRequest, update_guest

        admin = _make_user(is_admin=True)
        db = AsyncMock()

        guest = Mock(spec=HouseholdGuest)
        guest.id = uuid4()
        guest.user_id = uuid4()
        guest.organization_id = admin.organization_id
        guest.role = GuestRole.VIEWER
        guest.label = "Old Label"
        guest.is_active = True
        guest.created_at = utc_now()
        guest.revoked_at = None

        # First query: find guest
        mock_result1 = Mock()
        mock_result1.scalar_one_or_none.return_value = guest
        # Second query: get email (after refresh)
        mock_result2 = Mock()
        mock_result2.scalar_one.return_value = "guest@example.com"

        db.execute.side_effect = [mock_result1, mock_result2]
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        body = UpdateGuestRequest(role=GuestRole.ADVISOR, label="Financial Advisor")
        await update_guest(guest.id, body, admin, db)

        assert guest.role == GuestRole.ADVISOR
        assert guest.label == "Financial Advisor"
