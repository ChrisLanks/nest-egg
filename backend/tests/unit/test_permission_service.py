"""Unit tests for PermissionService."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4
from datetime import timedelta

from fastapi import HTTPException

from app.services.permission_service import PermissionService, permission_service
from app.models.permission import PermissionGrant, PermissionGrantAudit
from app.models.user import User
from app.utils.datetime_utils import utc_now


def _make_user(*, is_org_admin=False, org_id=None):
    u = Mock(spec=User)
    u.id = uuid4()
    u.organization_id = org_id or uuid4()
    u.is_org_admin = is_org_admin
    return u


def _make_grant(*, grantor_id, grantee_id, resource_type="account", actions=None,
                resource_id=None, is_active=True, expires_at=None, org_id=None):
    g = Mock(spec=PermissionGrant)
    g.id = uuid4()
    g.grantor_id = grantor_id
    g.grantee_id = grantee_id
    g.organization_id = org_id or uuid4()
    g.resource_type = resource_type
    g.resource_id = resource_id
    g.actions = actions or ["read"]
    g.is_active = is_active
    g.expires_at = expires_at
    g.granted_at = utc_now()
    return g


@pytest.mark.unit
class TestPermissionServiceCheck:
    """Tests for PermissionService.check()."""

    @pytest.fixture
    def db(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_org_admin_always_allowed(self, db):
        """Org admin bypasses all grant checks."""
        actor = _make_user(is_org_admin=True)
        svc = PermissionService()
        result = await svc.check(db, actor, "delete", "account", owner_id=uuid4())
        assert result is True
        db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_owner_always_allowed(self, db):
        """Resource owner is always allowed."""
        actor = _make_user()
        svc = PermissionService()
        result = await svc.check(db, actor, "update", "account", owner_id=actor.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_no_owner_id_denies(self, db):
        """No owner_id → can't look up grant → deny."""
        actor = _make_user()
        svc = PermissionService()
        result = await svc.check(db, actor, "read", "account")
        assert result is False

    @pytest.mark.asyncio
    async def test_grant_with_action_allows(self, db):
        """Active grant that includes the requested action → allow."""
        actor = _make_user()
        owner = _make_user()
        grant = _make_grant(grantor_id=owner.id, grantee_id=actor.id, actions=["read", "update"])

        with patch(
            "app.services.permission_service.permission_grant_crud.find_active",
            new=AsyncMock(return_value=grant),
        ):
            svc = PermissionService()
            result = await svc.check(db, actor, "read", "account", owner_id=owner.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_grant_without_action_denies(self, db):
        """Active grant that does NOT include the requested action → deny."""
        actor = _make_user()
        owner = _make_user()
        grant = _make_grant(grantor_id=owner.id, grantee_id=actor.id, actions=["read"])

        with patch(
            "app.services.permission_service.permission_grant_crud.find_active",
            new=AsyncMock(return_value=grant),
        ):
            svc = PermissionService()
            result = await svc.check(db, actor, "delete", "account", owner_id=owner.id)
        assert result is False

    @pytest.mark.asyncio
    async def test_no_grant_denies(self, db):
        """No grant in DB → deny."""
        actor = _make_user()
        owner = _make_user()

        with patch(
            "app.services.permission_service.permission_grant_crud.find_active",
            new=AsyncMock(return_value=None),
        ):
            svc = PermissionService()
            result = await svc.check(db, actor, "read", "account", owner_id=owner.id)
        assert result is False

    @pytest.mark.asyncio
    async def test_expired_grant_denies(self, db):
        """Expired grant → deny, even if actions match."""
        actor = _make_user()
        owner = _make_user()
        past = utc_now() - timedelta(days=1)
        grant = _make_grant(
            grantor_id=owner.id, grantee_id=actor.id,
            actions=["read"], expires_at=past,
        )

        with patch(
            "app.services.permission_service.permission_grant_crud.find_active",
            new=AsyncMock(return_value=grant),
        ):
            svc = PermissionService()
            result = await svc.check(db, actor, "read", "account", owner_id=owner.id)
        assert result is False


@pytest.mark.unit
class TestPermissionServiceRequire:
    """Tests for PermissionService.require()."""

    @pytest.fixture
    def db(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_allowed_does_not_raise(self, db):
        """Should not raise when actor has permission."""
        actor = _make_user()
        svc = PermissionService()
        # Owner of own resource — should not raise
        await svc.require(db, actor, "read", "account", owner_id=actor.id)

    @pytest.mark.asyncio
    async def test_denied_raises_403(self, db):
        """Should raise HTTP 403 when actor lacks permission."""
        actor = _make_user()
        owner = _make_user()

        with patch(
            "app.services.permission_service.permission_grant_crud.find_active",
            new=AsyncMock(return_value=None),
        ):
            svc = PermissionService()
            with pytest.raises(HTTPException) as exc_info:
                await svc.require(db, actor, "read", "account", owner_id=owner.id)
            assert exc_info.value.status_code == 403


@pytest.mark.unit
class TestPermissionServiceGrant:
    """Tests for PermissionService.grant()."""

    @pytest.fixture
    def db(self):
        db = AsyncMock()
        db.flush = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.add = Mock()
        return db

    @pytest.mark.asyncio
    async def test_creates_new_grant(self, db):
        """Should create a new PermissionGrant row when none exists."""
        grantor = _make_user()
        grantee_id = uuid4()

        with patch(
            "app.services.permission_service.permission_grant_crud.find_exact",
            new=AsyncMock(return_value=None),
        ):
            svc = PermissionService()
            await svc.grant(db, grantor, grantee_id, "account", ["read"])

        # db.add should have been called (grant + audit)
        assert db.add.call_count == 2
        added = [call.args[0] for call in db.add.call_args_list]
        assert any(isinstance(o, PermissionGrant) for o in added)
        assert any(isinstance(o, PermissionGrantAudit) for o in added)

    @pytest.mark.asyncio
    async def test_updates_existing_grant(self, db):
        """Should update existing grant when one already exists."""
        grantor = _make_user()
        grantee_id = uuid4()
        existing = _make_grant(grantor_id=grantor.id, grantee_id=grantee_id, actions=["read"])

        with patch(
            "app.services.permission_service.permission_grant_crud.find_exact",
            new=AsyncMock(return_value=existing),
        ):
            svc = PermissionService()
            await svc.grant(db, grantor, grantee_id, "account", ["read", "update"])

        assert existing.actions == ["read", "update"]
        # Only audit row is added (not a new grant)
        added = [call.args[0] for call in db.add.call_args_list]
        assert all(isinstance(o, PermissionGrantAudit) for o in added)
        audit = added[0]
        assert audit.action == "updated"

    @pytest.mark.asyncio
    async def test_invalid_resource_type_raises_400(self, db):
        """Should raise HTTP 400 for an invalid resource_type."""
        grantor = _make_user()
        svc = PermissionService()
        with pytest.raises(HTTPException) as exc_info:
            await svc.grant(db, grantor, uuid4(), "permission", ["read"])
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_empty_actions_raises_400(self, db):
        """Should raise HTTP 400 for empty actions list."""
        grantor = _make_user()
        svc = PermissionService()
        with pytest.raises(HTTPException) as exc_info:
            await svc.grant(db, grantor, uuid4(), "account", [])
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_invalid_actions_raises_400(self, db):
        """Should raise HTTP 400 for invalid action names."""
        grantor = _make_user()
        svc = PermissionService()
        with pytest.raises(HTTPException) as exc_info:
            await svc.grant(db, grantor, uuid4(), "account", ["grant"])
        assert exc_info.value.status_code == 400


@pytest.mark.unit
class TestPermissionServiceRevoke:
    """Tests for PermissionService.revoke()."""

    @pytest.fixture
    def db(self):
        db = AsyncMock()
        db.flush = AsyncMock()
        db.commit = AsyncMock()
        db.add = Mock()
        return db

    @pytest.mark.asyncio
    async def test_grantor_can_revoke(self, db):
        """Grant owner can revoke their own grant."""
        grantor = _make_user()
        grant = _make_grant(grantor_id=grantor.id, grantee_id=uuid4(), org_id=grantor.organization_id)

        with patch(
            "app.services.permission_service.permission_grant_crud.get_by_id",
            new=AsyncMock(return_value=grant),
        ):
            svc = PermissionService()
            await svc.revoke(db, grantor, grant.id)

        assert grant.is_active is False
        added = [call.args[0] for call in db.add.call_args_list]
        assert any(isinstance(o, PermissionGrantAudit) for o in added)
        audit = next(o for o in added if isinstance(o, PermissionGrantAudit))
        assert audit.action == "revoked"

    @pytest.mark.asyncio
    async def test_org_admin_can_revoke(self, db):
        """Org admin can revoke any grant."""
        admin = _make_user(is_org_admin=True)
        other_user = _make_user(org_id=admin.organization_id)
        grant = _make_grant(grantor_id=other_user.id, grantee_id=uuid4(), org_id=admin.organization_id)

        with patch(
            "app.services.permission_service.permission_grant_crud.get_by_id",
            new=AsyncMock(return_value=grant),
        ):
            svc = PermissionService()
            await svc.revoke(db, admin, grant.id)

        assert grant.is_active is False

    @pytest.mark.asyncio
    async def test_non_owner_cannot_revoke(self, db):
        """Non-owner non-admin raises 403."""
        shared_org = uuid4()
        actor = _make_user(org_id=shared_org)
        owner = _make_user(org_id=shared_org)
        grant = _make_grant(grantor_id=owner.id, grantee_id=uuid4(), org_id=shared_org)

        with patch(
            "app.services.permission_service.permission_grant_crud.get_by_id",
            new=AsyncMock(return_value=grant),
        ):
            svc = PermissionService()
            with pytest.raises(HTTPException) as exc_info:
                await svc.revoke(db, actor, grant.id)
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_grant_not_found_raises_404(self, db):
        """Missing grant raises 404."""
        with patch(
            "app.services.permission_service.permission_grant_crud.get_by_id",
            new=AsyncMock(return_value=None),
        ):
            svc = PermissionService()
            with pytest.raises(HTTPException) as exc_info:
                await svc.revoke(db, _make_user(), uuid4())
            assert exc_info.value.status_code == 404
