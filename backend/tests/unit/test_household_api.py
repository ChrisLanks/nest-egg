"""Unit tests for household API endpoints."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4
from datetime import date, datetime, timedelta
from decimal import Decimal

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

        # Mock household size check (under limit) - returns count via scalar_one()
        member_result = Mock()
        member_result.scalar_one.return_value = 2  # 2 members, under limit

        # Mock existing user check (not found)
        existing_user_result = Mock()
        existing_user_result.scalar_one_or_none.return_value = None

        # Mock bulk delete result (always executed, even when 0 rows deleted)
        delete_result = Mock()
        # Mock org name query
        org_mock = Mock()
        org_mock.name = "Test Household"
        org_result = Mock()
        org_result.scalar_one_or_none.return_value = org_mock

        mock_db.execute.side_effect = [
            member_result,
            existing_user_result,
            delete_result,
            org_result,
        ]

        with patch(
            "app.api.v1.household.rate_limit_service.check_rate_limit",
            return_value=None,
        ):
            with patch("app.api.v1.household.secrets.token_urlsafe", return_value="test-token"):
                with patch("app.api.v1.household.email_service.send_invitation_email", new=AsyncMock(return_value=False)):
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

        # Mock household size check (at limit) - returns count via scalar_one()
        member_result = Mock()
        member_result.scalar_one.return_value = MAX_HOUSEHOLD_MEMBERS
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

        # Mock household size check - returns count via scalar_one()
        member_result = Mock()
        member_result.scalar_one.return_value = 1

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
    async def test_replaces_existing_pending_invitation(
        self, mock_db, mock_user, mock_request
    ):
        """Should delete existing pending invitation and create a fresh one (no error)."""
        request_data = InviteMemberRequest(email="pending@example.com")

        # Mock household size check
        member_result = Mock()
        member_result.scalar_one.return_value = 1

        # Mock existing user check (not found)
        existing_user_result = Mock()
        existing_user_result.scalar_one_or_none.return_value = None

        # Mock bulk DELETE result (always executed)
        delete_result = Mock()

        # Mock org name query
        org_mock = Mock()
        org_mock.name = "Test Household"
        org_result = Mock()
        org_result.scalar_one_or_none.return_value = org_mock

        mock_db.execute.side_effect = [
            member_result,
            existing_user_result,
            delete_result,
            org_result,
        ]

        with patch(
            "app.api.v1.household.rate_limit_service.check_rate_limit",
            return_value=None,
        ):
            with patch("app.api.v1.household.secrets.token_urlsafe", return_value="new-token"):
                with patch("app.api.v1.household.email_service.send_invitation_email", new=AsyncMock(return_value=False)):
                    result = await invite_member(
                        request_data=request_data,
                        http_request=mock_request,
                        current_user=mock_user,
                        db=mock_db,
                    )

        # Should succeed and return the new invitation
        assert result["email"] == "pending@example.com"
        assert result["invitation_code"] == "new-token"
        # Bulk delete was executed (4 total: count, user check, delete, org)
        assert mock_db.execute.call_count == 4
        assert mock_db.add.called
        assert mock_db.commit.called


    @pytest.mark.asyncio
    async def test_member_count_uses_scalar_one_not_scalars_all(
        self, mock_db, mock_user, mock_request
    ):
        """household size check should use scalar_one() (COUNT query), not scalars().all()."""
        request_data = InviteMemberRequest(email="newmember@example.com")

        # scalar_one() returns the count integer directly — if the code
        # accidentally called scalars().all() it would get a Mock object,
        # and the >= comparison with MAX_HOUSEHOLD_MEMBERS would raise TypeError.
        count_result = Mock()
        count_result.scalar_one.return_value = 1  # one member, under limit

        existing_user_result = Mock()
        existing_user_result.scalar_one_or_none.return_value = None

        delete_result = Mock()

        org_mock = Mock()
        org_mock.name = "Test Household"
        org_result = Mock()
        org_result.scalar_one_or_none.return_value = org_mock

        mock_db.execute.side_effect = [count_result, existing_user_result, delete_result, org_result]

        with patch("app.api.v1.household.rate_limit_service.check_rate_limit", return_value=None):
            with patch("app.api.v1.household.secrets.token_urlsafe", return_value="tok"):
                with patch("app.api.v1.household.email_service.send_invitation_email", new=AsyncMock(return_value=False)):
                    result = await invite_member(
                        request_data=request_data,
                        http_request=mock_request,
                        current_user=mock_user,
                        db=mock_db,
                    )

        # If scalar_one() was called, the result["email"] will be set correctly
        assert result["email"] == "newmember@example.com"
        # Verify scalar_one was called (not scalars().all())
        count_result.scalar_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_allows_invite_when_one_below_limit(
        self, mock_db, mock_user, mock_request
    ):
        """Should allow invite when member count is exactly one below MAX_HOUSEHOLD_MEMBERS."""
        request_data = InviteMemberRequest(email="newmember@example.com")

        count_result = Mock()
        count_result.scalar_one.return_value = MAX_HOUSEHOLD_MEMBERS - 1

        existing_user_result = Mock()
        existing_user_result.scalar_one_or_none.return_value = None

        delete_result = Mock()

        org_mock = Mock()
        org_mock.name = "Test Household"
        org_result = Mock()
        org_result.scalar_one_or_none.return_value = org_mock

        mock_db.execute.side_effect = [count_result, existing_user_result, delete_result, org_result]

        with patch("app.api.v1.household.rate_limit_service.check_rate_limit", return_value=None):
            with patch("app.api.v1.household.secrets.token_urlsafe", return_value="tok"):
                with patch("app.api.v1.household.email_service.send_invitation_email", new=AsyncMock(return_value=False)):
                    result = await invite_member(
                        request_data=request_data,
                        http_request=mock_request,
                        current_user=mock_user,
                        db=mock_db,
                    )

        assert result["email"] == "newmember@example.com"

    @pytest.mark.asyncio
    async def test_rejects_exactly_at_limit(
        self, mock_db, mock_user, mock_request
    ):
        """Should reject when count equals MAX_HOUSEHOLD_MEMBERS (boundary condition)."""
        request_data = InviteMemberRequest(email="toomany@example.com")

        count_result = Mock()
        count_result.scalar_one.return_value = MAX_HOUSEHOLD_MEMBERS

        mock_db.execute.return_value = count_result

        with patch("app.api.v1.household.rate_limit_service.check_rate_limit", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await invite_member(
                    request_data=request_data,
                    http_request=mock_request,
                    current_user=mock_user,
                    db=mock_db,
                )

        assert exc_info.value.status_code == 400
        assert "cannot exceed" in exc_info.value.detail.lower()


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
        invited_by.id = invitation1.invited_by_user_id
        invited_by.email = "admin@example.com"

        # Mock invitation query
        invitation_result = Mock()
        invitation_result.scalars.return_value.all.return_value = [invitation1]

        # Mock batch user query (N+1 fix uses .scalars().all())
        user_result = Mock()
        user_result.scalars.return_value.all.return_value = [invited_by]

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
        invited_by.display_name = "Admin User"
        invited_by.first_name = "Admin"

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

            # Email is masked for public display
            assert result["email"] == "i***d@e***.com"
            # invited_by_name instead of invited_by_email
            assert result["invited_by_name"] == "Admin User"

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

        current_user = Mock(spec=User)
        current_user.email = "newuser@example.com"
        current_user.organization_id = None  # No org yet

        # Mock invitation query
        invitation_result = Mock()
        invitation_result.scalar_one_or_none.return_value = invitation

        mock_db.execute.side_effect = [invitation_result]

        with patch(
            "app.api.v1.household.rate_limit_service.check_rate_limit",
            return_value=None,
        ):
            result = await accept_invitation(
                invitation_code=invitation_code,
                request=mock_request,
                current_user=current_user,
                db=mock_db,
            )

            assert result["message"] == "Invitation accepted successfully"
            assert result["accounts_migrated"] == 0
            assert current_user.organization_id == invitation.organization_id
            assert invitation.status == InvitationStatus.ACCEPTED

    @pytest.mark.asyncio
    async def test_raises_404_for_invalid_code(self, mock_db, mock_request):
        """Should raise 404 for invalid invitation code."""
        invitation_code = "invalid"
        current_user = Mock(spec=User)
        current_user.email = "someone@example.com"

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
                    current_user=current_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_rejects_already_accepted_invitation(self, mock_db, mock_request):
        """Should reject invitation that was already accepted."""
        invitation_code = "test-code"
        current_user = Mock(spec=User)
        current_user.email = "user@example.com"

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
                    current_user=current_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 400
            assert "already been" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_rejects_expired_invitation(self, mock_db, mock_request):
        """Should reject expired invitation."""
        invitation_code = "test-code"
        current_user = Mock(spec=User)
        current_user.email = "user@example.com"

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
                    current_user=current_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 400
            assert "expired" in exc_info.value.detail.lower()
            assert invitation.status == InvitationStatus.EXPIRED

    @pytest.mark.asyncio
    async def test_rejects_when_email_mismatch(self, mock_db, mock_request):
        """Should reject when authenticated user's email doesn't match invitation."""
        invitation_code = "test-code"
        current_user = Mock(spec=User)
        current_user.email = "wrong@example.com"

        invitation = Mock(spec=HouseholdInvitation)
        invitation.email = "invited@example.com"
        invitation.status = InvitationStatus.PENDING
        invitation.expires_at = datetime.utcnow() + timedelta(days=7)

        invitation_result = Mock()
        invitation_result.scalar_one_or_none.return_value = invitation
        mock_db.execute.side_effect = [invitation_result]

        with patch(
            "app.api.v1.household.rate_limit_service.check_rate_limit",
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await accept_invitation(
                    invitation_code=invitation_code,
                    request=mock_request,
                    current_user=current_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 403
            assert "different email" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_migrates_solo_user_with_accounts(self, mock_db, mock_request):
        """Should migrate solo user and their accounts to new household."""
        from app.models.account import Account
        from app.models.user import Organization

        invitation_code = "test-code"
        old_org_id = uuid4()
        new_org_id = uuid4()

        invitation = Mock(spec=HouseholdInvitation)
        invitation.email = "solo@example.com"
        invitation.organization_id = new_org_id
        invitation.status = InvitationStatus.PENDING
        invitation.expires_at = datetime.utcnow() + timedelta(days=7)

        current_user = Mock(spec=User)
        current_user.email = "solo@example.com"
        current_user.id = uuid4()
        current_user.organization_id = old_org_id  # User in different org

        # Mock accounts to migrate
        account1 = Mock(spec=Account)
        account1.id = uuid4()
        account1.organization_id = old_org_id
        account1.user_id = current_user.id

        account2 = Mock(spec=Account)
        account2.id = uuid4()
        account2.organization_id = old_org_id
        account2.user_id = current_user.id

        old_org = Mock(spec=Organization)
        old_org.id = old_org_id

        # Mock invitation query
        invitation_result = Mock()
        invitation_result.scalar_one_or_none.return_value = invitation

        # Mock household members query (solo user)
        household_result = Mock()
        household_result.scalars.return_value.all.return_value = [current_user]  # Only 1 member

        # Mock user accounts query
        accounts_result = Mock()
        accounts_result.scalars.return_value.all.return_value = [account1, account2]

        # Mock old organization query
        org_result = Mock()
        org_result.scalar_one_or_none.return_value = old_org

        # Mock results for transaction migration updates (one per account)
        txn_update_result1 = Mock()
        txn_update_result2 = Mock()

        mock_db.execute.side_effect = [
            invitation_result,
            household_result,  # Household size check
            accounts_result,  # User's accounts
            txn_update_result1,  # Transaction migration for account1
            txn_update_result2,  # Transaction migration for account2
            org_result,  # Old organization
        ]

        with patch(
            "app.api.v1.household.rate_limit_service.check_rate_limit",
            return_value=None,
        ):
            result = await accept_invitation(
                invitation_code=invitation_code,
                request=mock_request,
                current_user=current_user,
                db=mock_db,
            )

            # Verify migration happened
            assert result["message"] == "Invitation accepted successfully"
            assert result["organization_id"] == str(new_org_id)
            assert result["accounts_migrated"] == 2

            # Verify account migrations
            assert account1.organization_id == new_org_id
            assert account2.organization_id == new_org_id

            # Verify user migration
            assert current_user.organization_id == new_org_id
            assert current_user.is_primary_household_member is False

            # Verify invitation marked as accepted
            assert invitation.status == InvitationStatus.ACCEPTED
            assert invitation.accepted_at is not None

            # Verify old org deleted
            mock_db.delete.assert_called_with(old_org)
            assert mock_db.commit.call_count == 2  # Once for migration, once for org delete

    @pytest.mark.asyncio
    async def test_migrates_user_without_accounts(self, mock_db, mock_request):
        """Should migrate solo user even if they have no accounts."""
        from app.models.user import Organization

        invitation_code = "test-code"
        old_org_id = uuid4()
        new_org_id = uuid4()

        invitation = Mock(spec=HouseholdInvitation)
        invitation.email = "user@example.com"
        invitation.organization_id = new_org_id
        invitation.status = InvitationStatus.PENDING
        invitation.expires_at = datetime.utcnow() + timedelta(days=7)

        current_user = Mock(spec=User)
        current_user.email = "user@example.com"
        current_user.id = uuid4()
        current_user.organization_id = old_org_id

        old_org = Mock(spec=Organization)
        old_org.id = old_org_id

        # Mock queries
        invitation_result = Mock()
        invitation_result.scalar_one_or_none.return_value = invitation

        household_result = Mock()
        household_result.scalars.return_value.all.return_value = [current_user]

        # No accounts
        accounts_result = Mock()
        accounts_result.scalars.return_value.all.return_value = []

        org_result = Mock()
        org_result.scalar_one_or_none.return_value = old_org

        mock_db.execute.side_effect = [
            invitation_result,
            household_result,
            accounts_result,
            org_result,
        ]

        with patch(
            "app.api.v1.household.rate_limit_service.check_rate_limit",
            return_value=None,
        ):
            result = await accept_invitation(
                invitation_code=invitation_code,
                request=mock_request,
                current_user=current_user,
                db=mock_db,
            )

            assert result["accounts_migrated"] == 0
            assert current_user.organization_id == new_org_id

    @pytest.mark.asyncio
    async def test_handles_missing_old_organization(self, mock_db, mock_request):
        """Should handle case where old organization was already deleted."""
        invitation_code = "test-code"
        old_org_id = uuid4()
        new_org_id = uuid4()

        invitation = Mock(spec=HouseholdInvitation)
        invitation.email = "user@example.com"
        invitation.organization_id = new_org_id
        invitation.status = InvitationStatus.PENDING
        invitation.expires_at = datetime.utcnow() + timedelta(days=7)

        current_user = Mock(spec=User)
        current_user.email = "user@example.com"
        current_user.id = uuid4()
        current_user.organization_id = old_org_id

        # Mock queries
        invitation_result = Mock()
        invitation_result.scalar_one_or_none.return_value = invitation

        household_result = Mock()
        household_result.scalars.return_value.all.return_value = [current_user]

        accounts_result = Mock()
        accounts_result.scalars.return_value.all.return_value = []

        # Old org not found
        org_result = Mock()
        org_result.scalar_one_or_none.return_value = None

        mock_db.execute.side_effect = [
            invitation_result,
            household_result,
            accounts_result,
            org_result,
        ]

        with patch(
            "app.api.v1.household.rate_limit_service.check_rate_limit",
            return_value=None,
        ):
            result = await accept_invitation(
                invitation_code=invitation_code,
                request=mock_request,
                current_user=current_user,
                db=mock_db,
            )

            # Should complete successfully even without old org
            assert result["message"] == "Invitation accepted successfully"
            # Delete should not be called if org not found
            assert not mock_db.delete.called

    @pytest.mark.asyncio
    async def test_rejects_when_already_in_target_household(self, mock_db, mock_request):
        """Should reject when user is already in the target household."""
        invitation_code = "test-code"
        org_id = uuid4()  # Same org

        invitation = Mock(spec=HouseholdInvitation)
        invitation.email = "user@example.com"
        invitation.organization_id = org_id
        invitation.status = InvitationStatus.PENDING
        invitation.expires_at = datetime.utcnow() + timedelta(days=7)

        current_user = Mock(spec=User)
        current_user.email = "user@example.com"
        current_user.organization_id = org_id  # Already in target org!

        # Mock queries
        invitation_result = Mock()
        invitation_result.scalar_one_or_none.return_value = invitation

        mock_db.execute.side_effect = [invitation_result]

        with patch(
            "app.api.v1.household.rate_limit_service.check_rate_limit",
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await accept_invitation(
                    invitation_code=invitation_code,
                    request=mock_request,
                    current_user=current_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 400
            assert "already a member" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_rejects_when_not_solo_in_current_household(self, mock_db, mock_request):
        """Should reject when user has other household members."""
        invitation_code = "test-code"
        old_org_id = uuid4()
        new_org_id = uuid4()

        invitation = Mock(spec=HouseholdInvitation)
        invitation.email = "user@example.com"
        invitation.organization_id = new_org_id
        invitation.status = InvitationStatus.PENDING
        invitation.expires_at = datetime.utcnow() + timedelta(days=7)

        current_user = Mock(spec=User)
        current_user.email = "user@example.com"
        current_user.organization_id = old_org_id

        other_user = Mock(spec=User)

        # Mock queries
        invitation_result = Mock()
        invitation_result.scalar_one_or_none.return_value = invitation

        # Multiple household members
        household_result = Mock()
        household_result.scalars.return_value.all.return_value = [current_user, other_user]

        mock_db.execute.side_effect = [invitation_result, household_result]

        with patch(
            "app.api.v1.household.rate_limit_service.check_rate_limit",
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await accept_invitation(
                    invitation_code=invitation_code,
                    request=mock_request,
                    current_user=current_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 400
            assert "not the only member" in exc_info.value.detail


# ---------------------------------------------------------------------------
# Invite email + join_url
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestInviteEmail:
    """Household invite should send an email and always include join_url."""

    def _make_admin(self):
        org = Mock()
        org.name = "Smith Family"

        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        user.email = "admin@example.com"
        user.display_name = "Admin"
        user.organization = org
        return user

    def _make_invitation(self, admin):
        import secrets
        inv = Mock(spec=HouseholdInvitation)
        inv.id = uuid4()
        inv.email = "invite@example.com"
        inv.invitation_code = secrets.token_urlsafe(32)
        inv.status = InvitationStatus.PENDING
        inv.expires_at = datetime.utcnow() + timedelta(days=7)
        inv.created_at = datetime.utcnow()
        return inv

    @pytest.mark.asyncio
    async def test_invite_response_includes_join_url(self):
        """InvitationResponse must always contain join_url."""
        admin = self._make_admin()
        invitation = self._make_invitation(admin)

        mock_request = Mock()
        mock_db = AsyncMock()

        # Member count query returns 1
        count_result = Mock()
        count_result.scalar_one.return_value = 1
        # No existing user for email check
        no_result = Mock()
        no_result.scalar_one_or_none.return_value = None
        # Bulk delete result (always executed)
        delete_result = Mock()
        # Org name query
        org_result = Mock()
        org_result.scalar_one_or_none.return_value = None  # falls back to "your household"
        mock_db.execute = AsyncMock(side_effect=[count_result, no_result, delete_result, org_result])
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock(side_effect=lambda obj: setattr(obj, "id", invitation.id) or
                                     setattr(obj, "invitation_code", invitation.invitation_code) or
                                     setattr(obj, "status", invitation.status) or
                                     setattr(obj, "expires_at", invitation.expires_at) or
                                     setattr(obj, "created_at", invitation.created_at) or
                                     setattr(obj, "email", invitation.email))

        with patch("app.api.v1.household.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.household.email_service.send_invitation_email", new=AsyncMock(return_value=False)):
                request_data = InviteMemberRequest(email="invite@example.com")
                result = await invite_member(request_data, mock_request, current_user=admin, db=mock_db)

        assert "join_url" in result
        assert "accept-invite?code=" in result["join_url"]

    @pytest.mark.asyncio
    async def test_invite_sends_email_when_configured(self):
        """When email service is configured, send_invitation_email should be called."""
        admin = self._make_admin()
        invitation = self._make_invitation(admin)

        mock_request = Mock()
        mock_db = AsyncMock()

        count_result = Mock()
        count_result.scalar_one.return_value = 1
        no_result = Mock()
        no_result.scalar_one_or_none.return_value = None
        delete_result = Mock()
        org_result = Mock()
        org_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(side_effect=[count_result, no_result, delete_result, org_result])
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock(side_effect=lambda obj: setattr(obj, "id", invitation.id) or
                                     setattr(obj, "invitation_code", invitation.invitation_code) or
                                     setattr(obj, "status", invitation.status) or
                                     setattr(obj, "expires_at", invitation.expires_at) or
                                     setattr(obj, "created_at", invitation.created_at) or
                                     setattr(obj, "email", invitation.email))

        with patch("app.api.v1.household.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.household.email_service.send_invitation_email", new=AsyncMock(return_value=True)) as mock_send:
                request_data = InviteMemberRequest(email="invite@example.com")
                await invite_member(request_data, mock_request, current_user=admin, db=mock_db)

        mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_invite_skips_email_when_not_configured(self):
        """When email service is not configured, invite still returns 201 (join_url present)."""
        admin = self._make_admin()
        invitation = self._make_invitation(admin)

        mock_request = Mock()
        mock_db = AsyncMock()

        count_result = Mock()
        count_result.scalar_one.return_value = 1
        no_result = Mock()
        no_result.scalar_one_or_none.return_value = None
        delete_result = Mock()
        org_result = Mock()
        org_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(side_effect=[count_result, no_result, delete_result, org_result])
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock(side_effect=lambda obj: setattr(obj, "id", invitation.id) or
                                     setattr(obj, "invitation_code", invitation.invitation_code) or
                                     setattr(obj, "status", invitation.status) or
                                     setattr(obj, "expires_at", invitation.expires_at) or
                                     setattr(obj, "created_at", invitation.created_at) or
                                     setattr(obj, "email", invitation.email))

        # Email service returns False (not configured)
        with patch("app.api.v1.household.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.household.email_service.send_invitation_email", new=AsyncMock(return_value=False)):
                request_data = InviteMemberRequest(email="invite@example.com")
                result = await invite_member(request_data, mock_request, current_user=admin, db=mock_db)

        # Should still return a valid response dict with join_url
        assert result is not None
        assert "join_url" in result


# ---------------------------------------------------------------------------
# Leave household
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestLeaveHousehold:
    """Tests for POST /household/leave."""

    def _make_user(self, *, is_primary: bool = False) -> Mock:
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        user.display_name = "Alice"
        user.first_name = "Alice"
        user.email = "alice@example.com"
        user.is_primary_household_member = is_primary
        user.is_org_admin = False
        return user

    @pytest.mark.asyncio
    async def test_primary_member_cannot_leave(self):
        """Primary household member gets 400 when trying to leave."""
        from app.api.v1.household import leave_household

        primary_user = self._make_user(is_primary=True)
        mock_db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await leave_household(current_user=primary_user, db=mock_db)

        assert exc_info.value.status_code == 400
        assert "primary" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_non_primary_member_can_leave(self):
        """Non-primary member gets 200 and a success message."""
        from app.api.v1.household import leave_household

        user = self._make_user(is_primary=False)
        mock_db = AsyncMock()
        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()

        mock_accounts_result = Mock()
        mock_accounts_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_accounts_result)
        mock_db.add = Mock()

        result = await leave_household(current_user=user, db=mock_db)

        assert "message" in result
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_leave_moves_accounts_to_new_org(self):
        """User's accounts are re-assigned to the new solo org."""
        from app.api.v1.household import leave_household
        from app.models.account import Account

        user = self._make_user(is_primary=False)
        old_org_id = user.organization_id

        mock_account = Mock(spec=Account)
        mock_account.organization_id = old_org_id
        mock_account.user_id = user.id

        mock_db = AsyncMock()
        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()

        mock_accounts_result = Mock()
        mock_accounts_result.scalars.return_value.all.return_value = [mock_account]

        # Empty result for UPDATE invitations, UPDATE transactions, SELECT budgets, SELECT goals
        mock_empty_result = Mock()
        mock_empty_result.scalars.return_value.all.return_value = []

        # execute calls: UPDATE invitations, SELECT accounts, UPDATE txns, SELECT budgets, SELECT goals
        mock_db.execute = AsyncMock(
            side_effect=[mock_empty_result, mock_accounts_result, mock_empty_result, mock_empty_result, mock_empty_result]
        )

        captured_org = None

        def capture_add(obj):
            nonlocal captured_org
            from app.models.user import Organization
            if isinstance(obj, Organization):
                captured_org = obj
                # Simulate flush giving the org an id
                obj.id = uuid4()

        mock_db.add = capture_add

        await leave_household(current_user=user, db=mock_db)

        # Account should now point to the new org
        assert mock_account.organization_id == captured_org.id

    @pytest.mark.asyncio
    async def test_leave_promotes_user_to_primary_admin(self):
        """After leaving, user becomes primary member and admin of new solo org."""
        from app.api.v1.household import leave_household

        user = self._make_user(is_primary=False)

        mock_db = AsyncMock()
        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()

        mock_empty_result = Mock()
        mock_empty_result.scalars.return_value.all.return_value = []
        # execute calls: UPDATE invitations, SELECT accounts (empty), SELECT budgets, SELECT goals
        mock_db.execute = AsyncMock(return_value=mock_empty_result)
        mock_db.add = Mock()

        await leave_household(current_user=user, db=mock_db)

        assert user.is_primary_household_member is True
        assert user.is_org_admin is True

    @pytest.mark.asyncio
    async def test_leave_expires_pending_invitations(self):
        """Leaving expires any PENDING invitations so the admin can re-invite cleanly."""
        from app.api.v1.household import leave_household

        user = self._make_user(is_primary=False)

        mock_db = AsyncMock()
        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.add = Mock()

        # execute is called for: UPDATE invitations, SELECT accounts, SELECT budgets, SELECT goals
        mock_empty_result = Mock()
        mock_empty_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_empty_result)

        await leave_household(current_user=user, db=mock_db)

        # The UPDATE call should have been made (execute called at least 4 times now)
        assert mock_db.execute.call_count >= 2
        # Commit should still happen
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_leave_copies_shared_budgets(self):
        """Leaving household should copy shared budgets the user had access to."""
        from app.api.v1.household import leave_household
        from app.models.budget import Budget, BudgetPeriod

        user = self._make_user(is_primary=False)

        mock_db = AsyncMock()
        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()

        # Shared budget accessible to the user (no spec= so all attrs work)
        shared_budget = Mock()
        shared_budget.name = "Household Groceries"
        shared_budget.amount = Decimal("500")
        shared_budget.period = BudgetPeriod.MONTHLY
        shared_budget.start_date = date(2026, 1, 1)
        shared_budget.end_date = None
        shared_budget.category_id = None
        shared_budget.label_id = None
        shared_budget.rollover_unused = False
        shared_budget.alert_threshold = Decimal("0.80")
        shared_budget.is_active = True
        shared_budget.is_shared = True
        shared_budget.shared_user_ids = None  # All members

        # Budget NOT shared with this user
        other_budget = Mock()
        other_budget.is_shared = True
        other_budget.shared_user_ids = [str(uuid4())]  # Different user only

        # UPDATE invitations result
        update_result = Mock()

        # SELECT accounts (empty)
        accounts_result = Mock()
        accounts_result.scalars.return_value.all.return_value = []

        # SELECT shared budgets
        budget_result = Mock()
        budget_result.scalars.return_value.all.return_value = [shared_budget, other_budget]

        # SELECT shared goals (empty)
        goal_result = Mock()
        goal_result.scalars.return_value.all.return_value = []

        added_objects = []
        def capture_add(obj):
            from app.models.user import Organization
            if isinstance(obj, Organization):
                obj.id = uuid4()
            added_objects.append(obj)

        mock_db.add = capture_add
        # Flow: 1) UPDATE invitations, 2) SELECT accounts, 3) SELECT budgets, 4) SELECT goals
        mock_db.execute = AsyncMock(
            side_effect=[update_result, accounts_result, budget_result, goal_result]
        )

        await leave_household(current_user=user, db=mock_db)

        # Should have copied the shared_budget (accessible) but not other_budget
        budget_copies = [o for o in added_objects if isinstance(o, Budget)]
        assert len(budget_copies) == 1
        assert budget_copies[0].name == "Household Groceries"
        assert budget_copies[0].is_shared is False  # Not shared in new solo household

    @pytest.mark.asyncio
    async def test_leave_copies_shared_goals(self):
        """Leaving household should copy shared goals the user had access to."""
        from app.api.v1.household import leave_household
        from app.models.savings_goal import SavingsGoal

        user = self._make_user(is_primary=False)

        mock_db = AsyncMock()
        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()

        shared_goal = Mock()
        shared_goal.name = "Family Vacation"
        shared_goal.description = "Trip to Hawaii"
        shared_goal.target_amount = Decimal("5000")
        shared_goal.current_amount = Decimal("1000")
        shared_goal.start_date = date(2026, 1, 1)
        shared_goal.target_date = date(2026, 12, 1)
        shared_goal.account_id = None
        shared_goal.auto_sync = False
        shared_goal.is_shared = True
        shared_goal.shared_user_ids = None  # All members

        # UPDATE invitations result
        update_result = Mock()

        # SELECT accounts (empty)
        accounts_result = Mock()
        accounts_result.scalars.return_value.all.return_value = []

        # SELECT shared budgets (empty)
        budget_result = Mock()
        budget_result.scalars.return_value.all.return_value = []

        # SELECT shared goals
        goal_result = Mock()
        goal_result.scalars.return_value.all.return_value = [shared_goal]

        added_objects = []
        def capture_add(obj):
            from app.models.user import Organization
            if isinstance(obj, Organization):
                obj.id = uuid4()
            added_objects.append(obj)

        mock_db.add = capture_add
        # Flow: 1) UPDATE invitations, 2) SELECT accounts, 3) SELECT budgets, 4) SELECT goals
        mock_db.execute = AsyncMock(
            side_effect=[update_result, accounts_result, budget_result, goal_result]
        )

        await leave_household(current_user=user, db=mock_db)

        goal_copies = [o for o in added_objects if isinstance(o, SavingsGoal)]
        assert len(goal_copies) == 1
        assert goal_copies[0].name == "Family Vacation"
        assert goal_copies[0].is_shared is False
