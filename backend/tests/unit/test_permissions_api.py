"""Unit tests for the permissions API endpoints.

Covers:
  - _ip() helper: rightmost X-Forwarded-For extraction
  - list_audit(): pagination limit/offset parameters
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from fastapi import HTTPException

from app.api.v1.permissions import _ip, list_audit
from app.models.user import User
from app.models.permission import PermissionGrantAudit
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
        mock_list.assert_called_once_with(
            mock_db, grantor=mock_user, limit=50, offset=0
        )

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
        mock_list.assert_called_once_with(
            mock_db, grantor=mock_user, limit=10, offset=0
        )

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
        mock_list.assert_called_once_with(
            mock_db, grantor=mock_user, limit=50, offset=100
        )

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
        mock_list.assert_called_once_with(
            mock_db, grantor=mock_user, limit=200, offset=0
        )

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
