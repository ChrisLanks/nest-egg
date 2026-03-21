"""Unit tests for the permissions API endpoints.

Covers:
  - _ip() helper: rightmost X-Forwarded-For extraction
  - list_audit(): pagination limit/offset parameters
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.permissions import _ip, list_audit
from app.models.permission import PermissionGrantAudit
from app.models.user import User
from app.utils.datetime_utils import utc_now

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(*, is_org_admin=False):
    u = Mock(spec=User)
    u.id = uuid4()
    u.organization_id = uuid4()
    u.is_org_admin = is_org_admin
    return u


def _make_audit_entry():
    e = Mock(spec=PermissionGrantAudit)
    e.id = uuid4()
    e.grant_id = uuid4()
    e.action = "created"
    e.actor_id = uuid4()
    e.grantor_id = uuid4()
    e.grantee_id = uuid4()
    e.resource_type = "transaction"
    e.resource_id = None
    e.actions_before = None
    e.actions_after = ["read"]
    e.ip_address = "10.0.0.1"
    e.occurred_at = utc_now()
    return e


def _make_request(*, forwarded: str | None = None, client_host: str = "127.0.0.1"):
    """Build a minimal mock Request."""
    req = Mock()
    req.headers = {}
    if forwarded is not None:
        req.headers["X-Forwarded-For"] = forwarded
    if client_host:
        req.client = Mock()
        req.client.host = client_host
    else:
        req.client = None
    return req


# ---------------------------------------------------------------------------
# _ip() helper
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIpHelper:
    """Tests for the _ip() helper that extracts client IP from the request."""

    def test_returns_client_host_when_no_forwarded_header(self):
        """Without X-Forwarded-For, returns request.client.host."""
        req = _make_request(client_host="1.2.3.4")
        assert _ip(req) == "1.2.3.4"

    def test_returns_none_when_no_client_and_no_forwarded(self):
        """No header and no client → None."""
        req = _make_request(client_host=None)
        req.client = None
        assert _ip(req) is None

    def test_single_ip_in_forwarded_header(self):
        """Single IP in X-Forwarded-For is returned directly."""
        req = _make_request(forwarded="203.0.113.5")
        assert _ip(req) == "203.0.113.5"

    def test_returns_rightmost_ip_from_forwarded_header(self):
        """With multiple IPs, the rightmost is the proxy-appended trusted one."""
        # Client-supplied (spoofable) → proxy-appended (trusted) order
        req = _make_request(forwarded="1.1.1.1, 2.2.2.2, 3.3.3.3")
        # Should return the last (rightmost) IP, not the first
        assert _ip(req) == "3.3.3.3"

    def test_strips_whitespace_from_rightmost_ip(self):
        """Trailing whitespace around the rightmost IP is stripped."""
        req = _make_request(forwarded="1.1.1.1,  192.168.0.1  ")
        assert _ip(req) == "192.168.0.1"

    def test_does_not_use_leftmost_ip_when_multiple_present(self):
        """The leftmost IP is client-supplied and must NOT be trusted."""
        req = _make_request(forwarded="evil-spoof, 10.0.0.1, 172.16.0.1")
        result = _ip(req)
        assert result == "172.16.0.1"
        assert result != "evil-spoof"

    def test_two_ips_returns_last(self):
        """With exactly two IPs, the second (proxy-appended) is returned."""
        req = _make_request(forwarded="5.5.5.5, 9.9.9.9")
        assert _ip(req) == "9.9.9.9"


# ---------------------------------------------------------------------------
# list_audit() pagination
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestListAuditPagination:
    """Tests for the list_audit endpoint pagination parameters."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        return _make_user()

    @pytest.mark.asyncio
    async def test_default_limit_and_offset_used(self, mock_db, mock_user):
        """Calling without params uses limit=50, offset=0."""
        with patch(
            "app.api.v1.permissions.permission_service.list_audit",
            new=AsyncMock(return_value=[]),
        ) as mock_list:
            await list_audit(
                current_user=mock_user,
                db=mock_db,
                limit=50,
                offset=0,
            )
        mock_list.assert_called_once_with(mock_db, grantor=mock_user, limit=50, offset=0)

    @pytest.mark.asyncio
    async def test_custom_limit_forwarded(self, mock_db, mock_user):
        """Custom limit is passed through to the service layer."""
        with patch(
            "app.api.v1.permissions.permission_service.list_audit",
            new=AsyncMock(return_value=[]),
        ) as mock_list:
            await list_audit(
                current_user=mock_user,
                db=mock_db,
                limit=10,
                offset=0,
            )
        mock_list.assert_called_once_with(mock_db, grantor=mock_user, limit=10, offset=0)

    @pytest.mark.asyncio
    async def test_custom_offset_forwarded(self, mock_db, mock_user):
        """Custom offset is passed through to the service layer."""
        with patch(
            "app.api.v1.permissions.permission_service.list_audit",
            new=AsyncMock(return_value=[]),
        ) as mock_list:
            await list_audit(
                current_user=mock_user,
                db=mock_db,
                limit=50,
                offset=100,
            )
        mock_list.assert_called_once_with(mock_db, grantor=mock_user, limit=50, offset=100)

    @pytest.mark.asyncio
    async def test_max_limit_forwarded(self, mock_db, mock_user):
        """Maximum allowed limit (200) is passed through correctly."""
        with patch(
            "app.api.v1.permissions.permission_service.list_audit",
            new=AsyncMock(return_value=[]),
        ) as mock_list:
            await list_audit(
                current_user=mock_user,
                db=mock_db,
                limit=200,
                offset=0,
            )
        mock_list.assert_called_once_with(mock_db, grantor=mock_user, limit=200, offset=0)

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_entries(self, mock_db, mock_user):
        """Returns empty list when service returns nothing."""
        with patch(
            "app.api.v1.permissions.permission_service.list_audit",
            new=AsyncMock(return_value=[]),
        ):
            result = await list_audit(
                current_user=mock_user,
                db=mock_db,
                limit=50,
                offset=0,
            )
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_validated_audit_responses(self, mock_db, mock_user):
        """Returns AuditResponse objects validated from service entries."""
        entry = _make_audit_entry()
        entry.grantor_id = mock_user.id

        with patch(
            "app.api.v1.permissions.permission_service.list_audit",
            new=AsyncMock(return_value=[entry]),
        ):
            result = await list_audit(
                current_user=mock_user,
                db=mock_db,
                limit=50,
                offset=0,
            )
        assert len(result) == 1
        assert result[0].action == "created"
        assert result[0].resource_type == "transaction"


# ---------------------------------------------------------------------------
# _display_name() helper
# ---------------------------------------------------------------------------

from app.api.v1.permissions import _display_name


@pytest.mark.unit
class TestDisplayNameHelper:
    """Tests for _display_name helper."""

    def test_display_name_set(self):
        u = Mock(spec=User)
        u.display_name = "Custom Name"
        u.first_name = "First"
        u.last_name = "Last"
        u.email = "user@example.com"
        assert _display_name(u) == "Custom Name"

    def test_first_and_last_name(self):
        u = Mock(spec=User)
        u.display_name = None
        u.first_name = "John"
        u.last_name = "Doe"
        u.email = "john@example.com"
        assert _display_name(u) == "John Doe"

    def test_only_first_name(self):
        u = Mock(spec=User)
        u.display_name = None
        u.first_name = "Jane"
        u.last_name = None
        u.email = "jane@example.com"
        assert _display_name(u) == "Jane"

    def test_no_name_falls_back_to_email(self):
        u = Mock(spec=User)
        u.display_name = None
        u.first_name = None
        u.last_name = None
        u.email = "user@example.com"
        assert _display_name(u) == "user@example.com"

    def test_empty_strings_fall_back_to_email(self):
        u = Mock(spec=User)
        u.display_name = None
        u.first_name = ""
        u.last_name = ""
        u.email = "user@example.com"
        assert _display_name(u) == "user@example.com"


# ---------------------------------------------------------------------------
# list_given / list_received
# ---------------------------------------------------------------------------

from app.api.v1.permissions import list_given, list_received


@pytest.mark.unit
class TestListGiven:
    """Tests for GET /permissions/given."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_returns_enriched_grants(self, mock_db):
        user = _make_user()
        grant = Mock()
        grant.grantor_id = user.id
        grant.grantee_id = uuid4()
        grant.id = uuid4()
        grant.resource_type = "transaction"
        grant.resource_id = None
        grant.actions = ["read"]
        grant.is_active = True
        grant.organization_id = user.organization_id
        grant.expires_at = None
        grant.created_at = utc_now()
        grant.updated_at = utc_now()

        with (
            patch(
                "app.api.v1.permissions.permission_service.list_given",
                new=AsyncMock(return_value=[grant]),
            ),
            patch(
                "app.api.v1.permissions._enrich_grants",
                new=AsyncMock(return_value=[Mock()]),
            ),
        ):
            result = await list_given(current_user=user, db=mock_db)
            assert len(result) == 1


@pytest.mark.unit
class TestListReceived:
    """Tests for GET /permissions/received."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_returns_enriched_grants(self, mock_db):
        user = _make_user()
        grant = Mock()
        grant.grantor_id = uuid4()
        grant.grantee_id = user.id

        with (
            patch(
                "app.api.v1.permissions.permission_service.list_received",
                new=AsyncMock(return_value=[grant]),
            ),
            patch(
                "app.api.v1.permissions._enrich_grants",
                new=AsyncMock(return_value=[Mock()]),
            ),
        ):
            result = await list_received(current_user=user, db=mock_db)
            assert len(result) == 1


# ---------------------------------------------------------------------------
# create_grant
# ---------------------------------------------------------------------------

from app.api.v1.permissions import create_grant
from app.schemas.permission import GrantCreate


@pytest.mark.unit
class TestCreateGrant:
    """Tests for POST /permissions/grants."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_permission_resource_type_rejected(self, mock_db):
        """Schema-level validation rejects 'permission' as resource_type.
        We also test the endpoint guard with a mocked body to ensure defense-in-depth."""
        user = _make_user()

        # Schema rejects 'permission' at Pydantic validation level
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            GrantCreate(
                grantee_id=uuid4(),
                resource_type="permission",
                actions=["read"],
            )

        # Also test endpoint-level guard by bypassing Pydantic
        body = Mock()
        body.resource_type = "permission"
        body.grantee_id = uuid4()
        body.actions = ["read"]
        body.resource_id = None
        body.expires_at = None
        request = _make_request()

        with pytest.raises(HTTPException) as exc_info:
            await create_grant(body, request, current_user=user, db=mock_db)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_grantee_not_in_org_raises_422(self, mock_db):
        user = _make_user()
        # Use a Mock to bypass Pydantic validation for endpoint-level testing
        body = Mock()
        body.resource_type = "transaction"
        body.grantee_id = uuid4()
        body.actions = ["read"]
        body.resource_id = None
        body.expires_at = None
        request = _make_request()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await create_grant(body, request, current_user=user, db=mock_db)
        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_cannot_grant_to_self(self, mock_db):
        user = _make_user()
        body = Mock()
        body.resource_type = "transaction"
        body.grantee_id = user.id
        body.actions = ["read"]
        body.resource_id = None
        body.expires_at = None
        request = _make_request()

        # Grantee found in same org
        mock_grantee = Mock(spec=User)
        mock_grantee.id = user.id
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_grantee
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await create_grant(body, request, current_user=user, db=mock_db)
        assert exc_info.value.status_code == 400
        assert "yourself" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# update_grant
# ---------------------------------------------------------------------------

from app.api.v1.permissions import update_grant
from app.schemas.permission import GrantUpdate


@pytest.mark.unit
class TestUpdateGrant:
    """Tests for PUT /permissions/grants/{grant_id}."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_grant_not_found_raises_404(self, mock_db):
        user = _make_user()
        body = GrantUpdate(actions=["read", "update"])
        request = _make_request()

        with patch(
            "app.api.v1.permissions.permission_grant_crud.get_by_id",
            new=AsyncMock(return_value=None),
        ):
            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc_info:
                await update_grant(uuid4(), body, request, current_user=user, db=mock_db)
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_non_grantor_non_admin_raises_403(self, mock_db):
        user = _make_user(is_org_admin=False)
        existing = Mock()
        existing.is_active = True
        existing.organization_id = user.organization_id
        existing.grantor_id = uuid4()  # different from user

        body = GrantUpdate(actions=["read"])
        request = _make_request()

        with patch(
            "app.api.v1.permissions.permission_grant_crud.get_by_id",
            new=AsyncMock(return_value=existing),
        ):
            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc_info:
                await update_grant(uuid4(), body, request, current_user=user, db=mock_db)
            assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# revoke_grant
# ---------------------------------------------------------------------------

from app.api.v1.permissions import revoke_grant


@pytest.mark.unit
class TestRevokeGrant:
    """Tests for DELETE /permissions/grants/{grant_id}."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_calls_permission_service_revoke(self, mock_db):
        user = _make_user()
        request = _make_request()

        with patch(
            "app.api.v1.permissions.permission_service.revoke",
            new=AsyncMock(),
        ) as mock_revoke:
            grant_id = uuid4()
            await revoke_grant(grant_id, request, current_user=user, db=mock_db)
            mock_revoke.assert_called_once()


# ---------------------------------------------------------------------------
# list_members / list_resource_types
# ---------------------------------------------------------------------------

from app.api.v1.permissions import list_members, list_resource_types


@pytest.mark.unit
class TestListMembers:
    """Tests for GET /permissions/members."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_returns_household_members(self, mock_db):
        user = _make_user()
        member = Mock(spec=User)
        member.id = uuid4()
        member.email = "other@example.com"
        member.first_name = "Other"
        member.last_name = "User"
        member.display_name = None
        member.is_active = True
        member.organization_id = user.organization_id

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [member]
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await list_members(current_user=user, db=mock_db)
        assert len(result) == 1


@pytest.mark.unit
class TestListResourceTypes:
    """Tests for GET /permissions/resource-types."""

    @pytest.mark.asyncio
    async def test_returns_resource_types(self):
        user = _make_user()
        result = await list_resource_types(current_user=user)
        assert isinstance(result, list)
        assert len(result) > 0
