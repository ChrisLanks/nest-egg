"""Security tests for household guest access.

These tests verify the defense-in-depth layers that prevent unauthorized
cross-household data access.
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.dependencies import get_organization_scoped_user
from app.models.user import (
    GuestInvitationStatus,
    HouseholdGuest,
    HouseholdGuestInvitation,
)
from app.utils.datetime_utils import utc_now


def _make_user(org_id=None, is_admin=False, email="user@example.com"):
    """Create a mock user without spec= so private attrs (_is_guest etc.) can be set."""
    user = Mock()
    user.id = uuid4()
    org = org_id or uuid4()
    user.organization_id = org
    user.is_active = True
    user.is_org_admin = is_admin
    user.email = email
    user.email_verified = True
    user.display_name = None
    user.__dict__["organization_id"] = org
    return user


def _make_guest(user_id, org_id, role="viewer", is_active=True):
    guest = Mock(spec=HouseholdGuest)
    guest.id = uuid4()
    guest.user_id = user_id
    guest.organization_id = org_id
    guest.role = role
    guest.is_active = is_active
    guest.label = None
    guest.created_at = utc_now()
    guest.revoked_at = None
    return guest


def _make_request(method="GET", household_id=None):
    headers_dict = {}
    if household_id:
        headers_dict["X-Household-Id"] = str(household_id)

    request = Mock()
    request.method = method
    request.headers = Mock()
    request.headers.get = lambda key, default=None: headers_dict.get(key, default)
    return request


class TestGuestContextResolution:
    """Test the get_organization_scoped_user dependency."""

    @pytest.mark.asyncio
    async def test_no_header_returns_home_context(self):
        """Without X-Household-Id, user stays in home org."""
        user = _make_user()
        home_org = user.organization_id
        request = _make_request()
        db = AsyncMock()

        with patch(
            "app.dependencies.get_current_user",
            new_callable=AsyncMock,
            return_value=user,
        ):
            result = await get_organization_scoped_user(request, Mock(), db)

        assert result.organization_id == home_org
        assert result._is_guest is False

    @pytest.mark.asyncio
    async def test_same_org_header_returns_home_context(self):
        """X-Household-Id matching home org is a no-op."""
        user = _make_user()
        request = _make_request(household_id=user.organization_id)
        db = AsyncMock()

        with patch(
            "app.dependencies.get_current_user",
            new_callable=AsyncMock,
            return_value=user,
        ):
            result = await get_organization_scoped_user(request, Mock(), db)

        assert result.organization_id == user.organization_id
        assert result._is_guest is False

    @pytest.mark.asyncio
    async def test_invalid_uuid_header_returns_400(self):
        """Malformed X-Household-Id returns 400."""
        user = _make_user()
        request = _make_request()
        request.headers.get = lambda key, default=None: (
            "not-a-uuid" if key == "X-Household-Id" else default
        )
        db = AsyncMock()

        with patch(
            "app.dependencies.get_current_user",
            new_callable=AsyncMock,
            return_value=user,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_organization_scoped_user(request, Mock(), db)
            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_no_guest_record_returns_403(self):
        """Valid UUID but no guest record returns 403."""
        user = _make_user()
        target_org = uuid4()
        request = _make_request(household_id=target_org)
        db = AsyncMock()

        # No guest record found
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        with patch(
            "app.dependencies.get_current_user",
            new_callable=AsyncMock,
            return_value=user,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_organization_scoped_user(request, Mock(), db)
            assert exc_info.value.status_code == 403
            assert "No active guest access" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_revoked_guest_returns_403(self):
        """Revoked guest record (is_active=False) returns 403."""
        user = _make_user()
        target_org = uuid4()
        request = _make_request(household_id=target_org)
        db = AsyncMock()

        # Guest record exists but is_active=False — query returns None due to filter
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        with patch(
            "app.dependencies.get_current_user",
            new_callable=AsyncMock,
            return_value=user,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_organization_scoped_user(request, Mock(), db)
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_viewer_blocked_on_post(self):
        """Viewer guest is blocked on POST requests."""
        user = _make_user()
        target_org = uuid4()
        guest = _make_guest(user.id, target_org, role="viewer")

        for method in ["POST", "PUT", "PATCH", "DELETE"]:
            request = _make_request(method=method, household_id=target_org)
            db = AsyncMock()
            mock_result = Mock()
            mock_result.scalar_one_or_none.return_value = guest
            db.execute.return_value = mock_result

            with patch(
                "app.dependencies.get_current_user",
                new_callable=AsyncMock,
                return_value=user,
            ):
                with pytest.raises(HTTPException) as exc_info:
                    await get_organization_scoped_user(request, Mock(), db)
                assert exc_info.value.status_code == 403
                assert "read-only" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_viewer_allowed_on_get(self):
        """Viewer guest is allowed on GET requests."""
        user = _make_user()
        target_org = uuid4()
        guest = _make_guest(user.id, target_org, role="viewer")
        request = _make_request(method="GET", household_id=target_org)
        db = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = guest
        db.execute.return_value = mock_result

        with patch(
            "app.dependencies.get_current_user",
            new_callable=AsyncMock,
            return_value=user,
        ):
            result = await get_organization_scoped_user(request, Mock(), db)

        assert result._is_guest is True
        assert result._guest_role == "viewer"
        assert result.__dict__["organization_id"] == target_org

    @pytest.mark.asyncio
    async def test_advisor_allowed_on_post(self):
        """Advisor guest is allowed on write requests."""
        user = _make_user()
        target_org = uuid4()
        guest = _make_guest(user.id, target_org, role="advisor")
        request = _make_request(method="POST", household_id=target_org)
        db = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = guest
        db.execute.return_value = mock_result

        with patch(
            "app.dependencies.get_current_user",
            new_callable=AsyncMock,
            return_value=user,
        ):
            result = await get_organization_scoped_user(request, Mock(), db)

        assert result._is_guest is True
        assert result._guest_role == "advisor"

    @pytest.mark.asyncio
    async def test_org_id_overridden_in_guest_context(self):
        """Guest context overrides organization_id in __dict__."""
        user = _make_user()
        home_org = user.organization_id
        target_org = uuid4()
        guest = _make_guest(user.id, target_org, role="viewer")
        request = _make_request(method="GET", household_id=target_org)
        db = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = guest
        db.execute.return_value = mock_result

        with patch(
            "app.dependencies.get_current_user",
            new_callable=AsyncMock,
            return_value=user,
        ):
            result = await get_organization_scoped_user(request, Mock(), db)

        # Organization ID is overridden
        assert result.__dict__["organization_id"] == target_org
        # Home org is preserved
        assert result._home_org_id == home_org

    @pytest.mark.asyncio
    async def test_guest_cannot_be_admin(self):
        """Guest users are blocked by get_current_admin_user even if admin at home."""
        from app.dependencies import get_current_admin_user

        user = _make_user(is_admin=True)
        user._is_guest = True

        with pytest.raises(HTTPException) as exc_info:
            await get_current_admin_user(user)
        assert exc_info.value.status_code == 403
        assert "Guests cannot perform admin" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_non_guest_admin_still_works(self):
        """Non-guest admin users still pass get_current_admin_user."""
        from app.dependencies import get_current_admin_user

        user = _make_user(is_admin=True)
        user._is_guest = False

        result = await get_current_admin_user(user)
        assert result == user

    @pytest.mark.asyncio
    async def test_guest_from_org_a_cannot_access_org_b(self):
        """A guest of org A cannot spoof header to access org B."""
        user = _make_user()
        org_a = uuid4()
        org_b = uuid4()

        # User has guest access to org_a but NOT org_b
        _make_guest(user.id, org_a, role="viewer")

        # Request targets org_b
        request = _make_request(method="GET", household_id=org_b)
        db = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None  # No guest record for org_b
        db.execute.return_value = mock_result

        with patch(
            "app.dependencies.get_current_user",
            new_callable=AsyncMock,
            return_value=user,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_organization_scoped_user(request, Mock(), db)
            assert exc_info.value.status_code == 403


class TestGuestInvitationSecurity:
    """Test invitation acceptance security."""

    @pytest.fixture(autouse=True)
    def mock_rate_limit(self):
        with patch("app.services.rate_limit_service.rate_limit_service.check_rate_limit", new_callable=AsyncMock):
            yield

    @pytest.mark.asyncio
    async def test_wrong_email_cannot_accept_invitation(self):
        """User cannot accept an invitation sent to a different email."""
        from app.api.v1.guest_access import accept_guest_invitation

        user = _make_user(email="alice@example.com")
        user._is_guest = False
        user._home_org_id = user.organization_id
        user._guest_role = None

        invitation = Mock(spec=HouseholdGuestInvitation)
        invitation.email = "bob@example.com"
        invitation.status = GuestInvitationStatus.PENDING
        invitation.is_expired = False
        invitation.organization_id = uuid4()

        db = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = invitation
        db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await accept_guest_invitation("some-code", MagicMock(), user, db)
        assert exc_info.value.status_code == 403
        assert "different email" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_cannot_accept_expired_invitation(self):
        """Expired invitations cannot be accepted."""
        from app.api.v1.guest_access import accept_guest_invitation

        user = _make_user(email="alice@example.com")
        user._is_guest = False
        user._home_org_id = user.organization_id
        user._guest_role = None

        invitation = Mock(spec=HouseholdGuestInvitation)
        invitation.email = "alice@example.com"
        invitation.status = GuestInvitationStatus.PENDING
        invitation.is_expired = True
        invitation.organization_id = uuid4()

        db = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = invitation
        db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await accept_guest_invitation("some-code", MagicMock(), user, db)
        assert exc_info.value.status_code == 400
        assert "expired" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_cannot_accept_already_accepted_invitation(self):
        """Already-accepted invitations cannot be accepted again."""
        from app.api.v1.guest_access import accept_guest_invitation

        user = _make_user(email="alice@example.com")
        user._is_guest = False
        user._home_org_id = user.organization_id
        user._guest_role = None

        invitation = Mock(spec=HouseholdGuestInvitation)
        invitation.email = "alice@example.com"
        invitation.status = GuestInvitationStatus.ACCEPTED
        invitation.organization_id = uuid4()

        db = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = invitation
        db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await accept_guest_invitation("some-code", MagicMock(), user, db)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_cannot_guest_your_own_household(self):
        """Cannot accept guest invitation to your own household."""
        from app.api.v1.guest_access import accept_guest_invitation

        user = _make_user(email="alice@example.com")
        user._is_guest = False
        user._home_org_id = user.organization_id
        user._guest_role = None

        invitation = Mock(spec=HouseholdGuestInvitation)
        invitation.email = "alice@example.com"
        invitation.status = GuestInvitationStatus.PENDING
        invitation.is_expired = False
        invitation.organization_id = user.organization_id  # Same org!

        db = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = invitation
        db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await accept_guest_invitation("some-code", MagicMock(), user, db)
        assert exc_info.value.status_code == 400
        assert "already a member" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invitation_not_found(self):
        """Non-existent invitation code returns 404."""
        from app.api.v1.guest_access import accept_guest_invitation

        user = _make_user()
        user._is_guest = False
        user._home_org_id = user.organization_id
        user._guest_role = None

        db = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await accept_guest_invitation("bad-code", MagicMock(), user, db)
        assert exc_info.value.status_code == 404


class TestGuestAdminEndpointBlocking:
    """Verify that guests cannot call admin-only endpoints."""

    @pytest.mark.asyncio
    async def test_guest_cannot_invite_guests(self):
        """Guest cannot invite other guests (requires admin)."""
        from app.dependencies import get_current_admin_user

        user = _make_user(is_admin=True)
        user._is_guest = True

        with pytest.raises(HTTPException) as exc_info:
            await get_current_admin_user(user)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_guest_cannot_list_guests(self):
        """Guest cannot list household guests (requires admin)."""
        from app.dependencies import get_current_admin_user

        user = _make_user(is_admin=False)
        user._is_guest = True

        with pytest.raises(HTTPException) as exc_info:
            await get_current_admin_user(user)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_guest_cannot_revoke_guests(self):
        """Guest cannot revoke other guests (requires admin)."""
        from app.dependencies import get_current_admin_user

        user = _make_user(is_admin=True)
        user._is_guest = True

        with pytest.raises(HTTPException) as exc_info:
            await get_current_admin_user(user)
        assert exc_info.value.status_code == 403
        assert "Guests cannot" in exc_info.value.detail
