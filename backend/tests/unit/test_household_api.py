"""Unit tests for household API endpoints."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4
from datetime import datetime, timedelta

from fastapi import HTTPException

from app.api.v1.household import (
    list_household_members,
    invite_member,
    list_invitations,
    remove_member,
    cancel_invitation,
    get_invitation_details,
    accept_invitation,
    InviteMemberRequest,
    MAX_HOUSEHOLD_MEMBERS,
    router,
)
from app.models.user import User, HouseholdInvitation, InvitationStatus


@pytest.mark.unit
class TestListHouseholdMembers:
    """Test list_household_members endpoint."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        return user

    @pytest.mark.asyncio
    async def test_lists_active_household_members(self, mock_db, mock_user):
        """Should list all active members in household."""
        member1 = Mock(spec=User)
        member1.id = uuid4()
        member1.email = "member1@example.com"

        member2 = Mock(spec=User)
        member2.id = uuid4()
        member2.email = "member2@example.com"

        result = Mock()
        result.scalars.return_value.all.return_value = [member1, member2]
        mock_db.execute.return_value = result

        members = await list_household_members(
            current_user=mock_user,
            db=mock_db,
        )

        assert len(members) == 2
        assert members[0].email == "member1@example.com"
        assert members[1].email == "member2@example.com"


@pytest.mark.unit
class TestInviteMember:
    """Test invite_member endpoint."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        user.email = "admin@example.com"
        user.is_org_admin = True
        return user

    @pytest.fixture
    def mock_request(self):
        request = Mock()
        request.client = Mock()
        request.client.host = "127.0.0.1"
        return request

    @pytest.mark.asyncio
    async def test_creates_invitation_successfully(
        self, mock_db, mock_user, mock_request
    ):
        """Should create household invitation."""
        request_data = InviteMemberRequest(email="newmember@example.com")

        # Mock household size check (under limit)
        member_result = Mock()
        member_result.scalars.return_value.all.return_value = [Mock(), Mock()]  # 2 members

        # Mock existing user check (not found)
        existing_user_result = Mock()
        existing_user_result.scalar_one_or_none.return_value = None

        # Mock pending invitation check (not found)
        invitation_result = Mock()
        invitation_result.scalar_one_or_none.return_value = None

        mock_db.execute.side_effect = [
            member_result,
            existing_user_result,
            invitation_result,
        ]

        with patch(
            "app.api.v1.household.rate_limit_service.check_rate_limit",
            return_value=None,
        ):
            with patch("app.api.v1.household.secrets.token_urlsafe", return_value="test-token"):
                result = await invite_member(
                    request_data=request_data,
                    http_request=mock_request,
                    current_user=mock_user,
                    db=mock_db,
                )

                assert result["email"] == "newmember@example.com"
                assert result["invitation_code"] == "test-token"
                assert result["invited_by_email"] == "admin@example.com"
                assert mock_db.add.called
                assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_rejects_when_household_full(
        self, mock_db, mock_user, mock_request
    ):
        """Should reject invitation when household is at max capacity."""
        request_data = InviteMemberRequest(email="newmember@example.com")

        # Mock household size check (at limit)
        members = [Mock() for _ in range(MAX_HOUSEHOLD_MEMBERS)]
        member_result = Mock()
        member_result.scalars.return_value.all.return_value = members
        mock_db.execute.return_value = member_result

        with patch(
            "app.api.v1.household.rate_limit_service.check_rate_limit",
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await invite_member(
                    request_data=request_data,
                    http_request=mock_request,
                    current_user=mock_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 400
            assert "cannot exceed" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_rejects_already_member(
        self, mock_db, mock_user, mock_request
    ):
        """Should reject invitation for existing member."""
        request_data = InviteMemberRequest(email="existing@example.com")

        # Mock household size check
        member_result = Mock()
        member_result.scalars.return_value.all.return_value = [Mock()]

        # Mock existing user check (found)
        existing_user = Mock(spec=User)
        existing_user_result = Mock()
        existing_user_result.scalar_one_or_none.return_value = existing_user

        mock_db.execute.side_effect = [member_result, existing_user_result]

        with patch(
            "app.api.v1.household.rate_limit_service.check_rate_limit",
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await invite_member(
                    request_data=request_data,
                    http_request=mock_request,
                    current_user=mock_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 400
            assert "already a member" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_rejects_pending_invitation(
        self, mock_db, mock_user, mock_request
    ):
        """Should reject when invitation already pending."""
        request_data = InviteMemberRequest(email="pending@example.com")

        # Mock household size check
        member_result = Mock()
        member_result.scalars.return_value.all.return_value = [Mock()]

        # Mock existing user check (not found)
        existing_user_result = Mock()
        existing_user_result.scalar_one_or_none.return_value = None

        # Mock pending invitation check (found)
        invitation = Mock(spec=HouseholdInvitation)
        invitation_result = Mock()
        invitation_result.scalar_one_or_none.return_value = invitation

        mock_db.execute.side_effect = [
            member_result,
            existing_user_result,
            invitation_result,
        ]

        with patch(
            "app.api.v1.household.rate_limit_service.check_rate_limit",
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await invite_member(
                    request_data=request_data,
                    http_request=mock_request,
                    current_user=mock_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 400
            assert "already pending" in exc_info.value.detail


@pytest.mark.unit
class TestListInvitations:
    """Test list_invitations endpoint."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        return user

    @pytest.mark.asyncio
    async def test_lists_pending_invitations(self, mock_db, mock_user):
        """Should list all pending invitations for household."""
        invitation1 = Mock(spec=HouseholdInvitation)
        invitation1.id = uuid4()
        invitation1.email = "invite1@example.com"
        invitation1.invited_by_user_id = uuid4()
        invitation1.invitation_code = "code1"
        invitation1.status = InvitationStatus.PENDING
        invitation1.expires_at = datetime.utcnow() + timedelta(days=7)
        invitation1.created_at = datetime.utcnow()

        # Mock invited_by user
        invited_by = Mock(spec=User)
        invited_by.email = "admin@example.com"

        # Mock invitation query
        invitation_result = Mock()
        invitation_result.scalars.return_value.all.return_value = [invitation1]

        # Mock user query
        user_result = Mock()
        user_result.scalar_one.return_value = invited_by

        mock_db.execute.side_effect = [invitation_result, user_result]

        result = await list_invitations(
            current_user=mock_user,
            db=mock_db,
        )

        assert len(result) == 1
        assert result[0]["email"] == "invite1@example.com"
        assert result[0]["invited_by_email"] == "admin@example.com"


@pytest.mark.unit
class TestRemoveMember:
    """Test remove_member endpoint."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        user.is_org_admin = True
        return user

    @pytest.mark.asyncio
    async def test_removes_member_successfully(self, mock_db, mock_user):
        """Should soft delete member by marking inactive."""
        user_id = uuid4()
        user_to_remove = Mock(spec=User)
        user_to_remove.id = user_id
        user_to_remove.is_primary_household_member = False

        result = Mock()
        result.scalar_one_or_none.return_value = user_to_remove
        mock_db.execute.return_value = result

        await remove_member(
            user_id=user_id,
            current_user=mock_user,
            db=mock_db,
        )

        assert user_to_remove.is_active is False
        assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_raises_404_when_user_not_found(self, mock_db, mock_user):
        """Should raise 404 when user doesn't exist."""
        user_id = uuid4()

        result = Mock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result

        with pytest.raises(HTTPException) as exc_info:
            await remove_member(
                user_id=user_id,
                current_user=mock_user,
                db=mock_db,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_prevents_removing_self(self, mock_db, mock_user):
        """Should prevent admin from removing themselves."""
        user_to_remove = Mock(spec=User)
        user_to_remove.id = mock_user.id  # Same as current user

        result = Mock()
        result.scalar_one_or_none.return_value = user_to_remove
        mock_db.execute.return_value = result

        with pytest.raises(HTTPException) as exc_info:
            await remove_member(
                user_id=mock_user.id,
                current_user=mock_user,
                db=mock_db,
            )

        assert exc_info.value.status_code == 400
        assert "Cannot remove yourself" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_prevents_removing_primary_member(self, mock_db, mock_user):
        """Should prevent removing primary household member."""
        user_id = uuid4()
        user_to_remove = Mock(spec=User)
        user_to_remove.id = user_id
        user_to_remove.is_primary_household_member = True

        result = Mock()
        result.scalar_one_or_none.return_value = user_to_remove
        mock_db.execute.return_value = result

        with pytest.raises(HTTPException) as exc_info:
            await remove_member(
                user_id=user_id,
                current_user=mock_user,
                db=mock_db,
            )

        assert exc_info.value.status_code == 400
        assert "primary household member" in exc_info.value.detail


@pytest.mark.unit
class TestCancelInvitation:
    """Test cancel_invitation endpoint."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        user.is_org_admin = True
        return user

    @pytest.mark.asyncio
    async def test_cancels_invitation_successfully(self, mock_db, mock_user):
        """Should delete invitation."""
        invitation_id = uuid4()
        invitation = Mock(spec=HouseholdInvitation)
        invitation.id = invitation_id

        result = Mock()
        result.scalar_one_or_none.return_value = invitation
        mock_db.execute.return_value = result

        await cancel_invitation(
            invitation_id=invitation_id,
            current_user=mock_user,
            db=mock_db,
        )

        assert mock_db.delete.called
        assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_raises_404_when_invitation_not_found(self, mock_db, mock_user):
        """Should raise 404 when invitation doesn't exist."""
        invitation_id = uuid4()

        result = Mock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result

        with pytest.raises(HTTPException) as exc_info:
            await cancel_invitation(
                invitation_id=invitation_id,
                current_user=mock_user,
                db=mock_db,
            )

        assert exc_info.value.status_code == 404


@pytest.mark.unit
class TestGetInvitationDetails:
    """Test get_invitation_details endpoint."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_request(self):
        request = Mock()
        request.client = Mock()
        request.client.host = "127.0.0.1"
        return request

    @pytest.mark.asyncio
    async def test_returns_invitation_details(self, mock_db, mock_request):
        """Should return invitation details by code."""
        invitation_code = "test-code-123"

        invitation = Mock(spec=HouseholdInvitation)
        invitation.email = "invited@example.com"
        invitation.invited_by_user_id = uuid4()
        invitation.status = InvitationStatus.PENDING
        invitation.expires_at = datetime.utcnow() + timedelta(days=7)

        invited_by = Mock(spec=User)
        invited_by.email = "admin@example.com"

        # Mock invitation query
        invitation_result = Mock()
        invitation_result.scalar_one_or_none.return_value = invitation

        # Mock user query
        user_result = Mock()
        user_result.scalar_one.return_value = invited_by

        mock_db.execute.side_effect = [invitation_result, user_result]

        with patch(
            "app.api.v1.household.rate_limit_service.check_rate_limit",
            return_value=None,
        ):
            result = await get_invitation_details(
                invitation_code=invitation_code,
                request=mock_request,
                db=mock_db,
            )

            assert result["email"] == "invited@example.com"
            assert result["invited_by_email"] == "admin@example.com"

    @pytest.mark.asyncio
    async def test_raises_404_when_code_invalid(self, mock_db, mock_request):
        """Should raise 404 for invalid invitation code."""
        invitation_code = "invalid-code"

        result = Mock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result

        with patch(
            "app.api.v1.household.rate_limit_service.check_rate_limit",
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_invitation_details(
                    invitation_code=invitation_code,
                    request=mock_request,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404


@pytest.mark.unit
class TestAcceptInvitation:
    """Test accept_invitation endpoint."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_request(self):
        request = Mock()
        request.client = Mock()
        request.client.host = "127.0.0.1"
        return request

    @pytest.mark.asyncio
    async def test_accepts_invitation_for_new_user(self, mock_db, mock_request):
        """Should accept invitation for user without organization."""
        invitation_code = "test-code"

        invitation = Mock(spec=HouseholdInvitation)
        invitation.email = "newuser@example.com"
        invitation.organization_id = uuid4()
        invitation.status = InvitationStatus.PENDING
        invitation.expires_at = datetime.utcnow() + timedelta(days=7)

        existing_user = Mock(spec=User)
        existing_user.email = "newuser@example.com"
        existing_user.organization_id = None  # No org yet

        # Mock invitation query
        invitation_result = Mock()
        invitation_result.scalar_one_or_none.return_value = invitation

        # Mock user query
        user_result = Mock()
        user_result.scalar_one_or_none.return_value = existing_user

        mock_db.execute.side_effect = [invitation_result, user_result]

        with patch(
            "app.api.v1.household.rate_limit_service.check_rate_limit",
            return_value=None,
        ):
            result = await accept_invitation(
                invitation_code=invitation_code,
                request=mock_request,
                db=mock_db,
            )

            assert result["message"] == "Invitation accepted successfully"
            assert result["accounts_migrated"] == 0
            assert existing_user.organization_id == invitation.organization_id
            assert invitation.status == InvitationStatus.ACCEPTED

    @pytest.mark.asyncio
    async def test_raises_404_for_invalid_code(self, mock_db, mock_request):
        """Should raise 404 for invalid invitation code."""
        invitation_code = "invalid"

        result = Mock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result

        with patch(
            "app.api.v1.household.rate_limit_service.check_rate_limit",
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await accept_invitation(
                    invitation_code=invitation_code,
                    request=mock_request,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_rejects_already_accepted_invitation(self, mock_db, mock_request):
        """Should reject invitation that was already accepted."""
        invitation_code = "test-code"

        invitation = Mock(spec=HouseholdInvitation)
        invitation.status = InvitationStatus.ACCEPTED  # Already accepted
        invitation.expires_at = datetime.utcnow() + timedelta(days=7)

        result = Mock()
        result.scalar_one_or_none.return_value = invitation
        mock_db.execute.return_value = result

        with patch(
            "app.api.v1.household.rate_limit_service.check_rate_limit",
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await accept_invitation(
                    invitation_code=invitation_code,
                    request=mock_request,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 400
            assert "already been" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_rejects_expired_invitation(self, mock_db, mock_request):
        """Should reject expired invitation."""
        invitation_code = "test-code"

        invitation = Mock(spec=HouseholdInvitation)
        invitation.status = InvitationStatus.PENDING
        invitation.expires_at = datetime.utcnow() - timedelta(days=1)  # Expired

        result = Mock()
        result.scalar_one_or_none.return_value = invitation
        mock_db.execute.return_value = result

        with patch(
            "app.api.v1.household.rate_limit_service.check_rate_limit",
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await accept_invitation(
                    invitation_code=invitation_code,
                    request=mock_request,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 400
            assert "expired" in exc_info.value.detail.lower()
            assert invitation.status == InvitationStatus.EXPIRED

    @pytest.mark.asyncio
    async def test_rejects_when_user_not_registered(self, mock_db, mock_request):
        """Should reject when user hasn't registered yet."""
        invitation_code = "test-code"

        invitation = Mock(spec=HouseholdInvitation)
        invitation.email = "notregistered@example.com"
        invitation.status = InvitationStatus.PENDING
        invitation.expires_at = datetime.utcnow() + timedelta(days=7)

        # Mock invitation query
        invitation_result = Mock()
        invitation_result.scalar_one_or_none.return_value = invitation

        # Mock user query (not found)
        user_result = Mock()
        user_result.scalar_one_or_none.return_value = None

        mock_db.execute.side_effect = [invitation_result, user_result]

        with patch(
            "app.api.v1.household.rate_limit_service.check_rate_limit",
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await accept_invitation(
                    invitation_code=invitation_code,
                    request=mock_request,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 400
            assert "not found" in exc_info.value.detail
            assert "register first" in exc_info.value.detail.lower()
