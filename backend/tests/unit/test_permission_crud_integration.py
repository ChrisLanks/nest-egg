"""Integration tests for permission CRUD and service with a real (SQLite) DB.

These tests use the real SQLite in-memory database (via the db_session fixture)
to verify that:
  1. find_active returns wildcard grants when queried with a specific resource_id
  2. list_grants_for_grantee fetches all grants for a grantee + resource_type
  3. filter_allowed_resources (bulk check) resolves grants in a single DB query
  4. PermissionService.check returns correct results for various grant scenarios
"""

import uuid
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from datetime import timedelta

from app.crud.permission import permission_grant_crud
from app.models.permission import PermissionGrant
from app.models.user import Organization, User
from app.services.permission_service import PermissionService
from app.utils.datetime_utils import utc_now


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _org(name: str = "Test Org") -> Organization:
    return Organization(id=uuid.uuid4(), name=name)


def _user(org_id: uuid.UUID, *, is_org_admin: bool = False) -> User:
    return User(
        id=uuid.uuid4(),
        organization_id=org_id,
        email=f"{uuid.uuid4()}@test.com",
        password_hash="hashed",
        is_active=True,
        is_org_admin=is_org_admin,
        is_primary_household_member=False,
        email_verified=True,
        failed_login_attempts=0,
    )


def _grant(
    org_id: uuid.UUID,
    grantor_id: uuid.UUID,
    grantee_id: uuid.UUID,
    *,
    resource_type: str = "account",
    resource_id=None,
    actions=None,
    is_active: bool = True,
) -> PermissionGrant:
    return PermissionGrant(
        id=uuid.uuid4(),
        organization_id=org_id,
        grantor_id=grantor_id,
        grantee_id=grantee_id,
        resource_type=resource_type,
        resource_id=resource_id,
        actions=actions or ["read", "update"],
        granted_at=utc_now(),
        is_active=is_active,
        granted_by=grantor_id,
    )


# ---------------------------------------------------------------------------
# Tests for PermissionGrantCRUD.find_active
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_find_active_returns_wildcard_grant_when_queried_with_specific_resource(
    db_session: AsyncSession,
):
    """
    THE CRITICAL SCENARIO:
    A wildcard grant (resource_id=NULL) must be found when find_active is
    called with a specific resource_id UUID.

    This is the core SQL that enables 'bulk-visibility' permission checking.
    """
    org = _org()
    grantor = _user(org.id)
    grantee = _user(org.id)
    db_session.add_all([org, grantor, grantee])
    await db_session.flush()

    # Create wildcard grant — resource_id is NULL (covers all accounts)
    wildcard_grant = _grant(org.id, grantor.id, grantee.id, resource_id=None)
    db_session.add(wildcard_grant)
    await db_session.commit()

    # Query with a specific account UUID — should still find the wildcard grant
    specific_resource_id = uuid.uuid4()
    result = await permission_grant_crud.find_active(
        db_session,
        grantor_id=grantor.id,
        grantee_id=grantee.id,
        resource_type="account",
        resource_id=specific_resource_id,
    )

    assert result is not None, (
        "find_active should return the wildcard (resource_id=NULL) grant "
        "when queried with a specific resource_id"
    )
    assert result.id == wildcard_grant.id
    assert result.resource_id is None  # Still the wildcard
    assert "update" in result.actions


@pytest.mark.asyncio
async def test_find_active_returns_exact_grant_when_resource_id_matches(
    db_session: AsyncSession,
):
    """Exact-match grant (resource_id = specific UUID) is returned correctly."""
    org = _org()
    grantor = _user(org.id)
    grantee = _user(org.id)
    db_session.add_all([org, grantor, grantee])
    await db_session.flush()

    specific_id = uuid.uuid4()
    exact_grant = _grant(org.id, grantor.id, grantee.id, resource_id=specific_id)
    db_session.add(exact_grant)
    await db_session.commit()

    result = await permission_grant_crud.find_active(
        db_session,
        grantor_id=grantor.id,
        grantee_id=grantee.id,
        resource_type="account",
        resource_id=specific_id,
    )

    assert result is not None
    assert result.id == exact_grant.id
    assert result.resource_id == specific_id


@pytest.mark.asyncio
async def test_find_active_returns_none_when_no_grant_exists(
    db_session: AsyncSession,
):
    """No matching grant → None returned."""
    org = _org()
    grantor = _user(org.id)
    grantee = _user(org.id)
    db_session.add_all([org, grantor, grantee])
    await db_session.flush()
    await db_session.commit()

    result = await permission_grant_crud.find_active(
        db_session,
        grantor_id=grantor.id,
        grantee_id=grantee.id,
        resource_type="account",
        resource_id=uuid.uuid4(),
    )

    assert result is None


@pytest.mark.asyncio
async def test_find_active_returns_none_when_grant_is_inactive(
    db_session: AsyncSession,
):
    """Inactive wildcard grant is ignored."""
    org = _org()
    grantor = _user(org.id)
    grantee = _user(org.id)
    db_session.add_all([org, grantor, grantee])
    await db_session.flush()

    inactive_grant = _grant(org.id, grantor.id, grantee.id, resource_id=None, is_active=False)
    db_session.add(inactive_grant)
    await db_session.commit()

    result = await permission_grant_crud.find_active(
        db_session,
        grantor_id=grantor.id,
        grantee_id=grantee.id,
        resource_type="account",
        resource_id=uuid.uuid4(),
    )

    assert result is None


@pytest.mark.asyncio
async def test_find_active_wildcard_does_not_cross_grantee(
    db_session: AsyncSession,
):
    """A wildcard grant for grantee_A is NOT returned when querying for grantee_B."""
    org = _org()
    grantor = _user(org.id)
    grantee_a = _user(org.id)
    grantee_b = _user(org.id)
    db_session.add_all([org, grantor, grantee_a, grantee_b])
    await db_session.flush()

    # Grant only for grantee_a
    wildcard = _grant(org.id, grantor.id, grantee_a.id, resource_id=None)
    db_session.add(wildcard)
    await db_session.commit()

    # Query for grantee_b — should find nothing
    result = await permission_grant_crud.find_active(
        db_session,
        grantor_id=grantor.id,
        grantee_id=grantee_b.id,
        resource_type="account",
        resource_id=uuid.uuid4(),
    )

    assert result is None


@pytest.mark.asyncio
async def test_find_active_wildcard_does_not_cross_resource_type(
    db_session: AsyncSession,
):
    """A wildcard grant for 'account' is NOT returned when querying for 'transaction'."""
    org = _org()
    grantor = _user(org.id)
    grantee = _user(org.id)
    db_session.add_all([org, grantor, grantee])
    await db_session.flush()

    # Grant only for 'account'
    wildcard = _grant(org.id, grantor.id, grantee.id, resource_type="account", resource_id=None)
    db_session.add(wildcard)
    await db_session.commit()

    # Query for 'transaction' — should find nothing
    result = await permission_grant_crud.find_active(
        db_session,
        grantor_id=grantor.id,
        grantee_id=grantee.id,
        resource_type="transaction",
        resource_id=uuid.uuid4(),
    )

    assert result is None


# ---------------------------------------------------------------------------
# Tests for PermissionService.check with real DB
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_permission_service_check_allows_grantee_with_wildcard_grant(
    db_session: AsyncSession,
):
    """
    PermissionService.check must return True for a grantee whose wildcard grant
    includes the requested action — even when queried with a specific resource_id.
    """
    org = _org()
    grantor_user = _user(org.id)
    grantee_user = _user(org.id, is_org_admin=False)
    db_session.add_all([org, grantor_user, grantee_user])
    await db_session.flush()

    wildcard = _grant(
        org.id, grantor_user.id, grantee_user.id,
        resource_id=None, actions=["read", "update"]
    )
    db_session.add(wildcard)
    await db_session.commit()

    svc = PermissionService()
    specific_account_id = uuid.uuid4()  # Some account the grantor owns

    # 'update' should be allowed
    result = await svc.check(
        db_session,
        actor=grantee_user,
        action="update",
        resource_type="account",
        resource_id=specific_account_id,
        owner_id=grantor_user.id,
    )

    assert result is True, (
        "PermissionService.check should return True when a wildcard grant covers "
        "the requested action, even when called with a specific resource_id"
    )


@pytest.mark.asyncio
async def test_permission_service_check_denies_action_not_in_grant(
    db_session: AsyncSession,
):
    """Action not listed in the wildcard grant → False."""
    org = _org()
    grantor_user = _user(org.id)
    grantee_user = _user(org.id)
    db_session.add_all([org, grantor_user, grantee_user])
    await db_session.flush()

    # Grant only read
    wildcard = _grant(
        org.id, grantor_user.id, grantee_user.id,
        resource_id=None, actions=["read"]
    )
    db_session.add(wildcard)
    await db_session.commit()

    svc = PermissionService()
    result = await svc.check(
        db_session,
        actor=grantee_user,
        action="delete",  # not in grant
        resource_type="account",
        resource_id=uuid.uuid4(),
        owner_id=grantor_user.id,
    )

    assert result is False


@pytest.mark.asyncio
async def test_permission_service_check_denies_when_no_grant(
    db_session: AsyncSession,
):
    """No grant at all → False."""
    org = _org()
    grantor_user = _user(org.id)
    grantee_user = _user(org.id)
    db_session.add_all([org, grantor_user, grantee_user])
    await db_session.commit()

    svc = PermissionService()
    result = await svc.check(
        db_session,
        actor=grantee_user,
        action="read",
        resource_type="account",
        resource_id=uuid.uuid4(),
        owner_id=grantor_user.id,
    )

    assert result is False


@pytest.mark.asyncio
async def test_permission_service_check_owner_always_allowed(
    db_session: AsyncSession,
):
    """Owner accessing their own resource → True (no grant lookup needed)."""
    org = _org()
    user = _user(org.id)
    db_session.add_all([org, user])
    await db_session.commit()

    svc = PermissionService()
    result = await svc.check(
        db_session,
        actor=user,
        action="delete",
        resource_type="account",
        resource_id=uuid.uuid4(),
        owner_id=user.id,  # Same as actor
    )

    assert result is True


@pytest.mark.asyncio
async def test_permission_service_check_org_admin_always_allowed(
    db_session: AsyncSession,
):
    """Org admin → True regardless of grants."""
    org = _org()
    admin = _user(org.id, is_org_admin=True)
    other = _user(org.id)
    db_session.add_all([org, admin, other])
    await db_session.commit()

    svc = PermissionService()
    result = await svc.check(
        db_session,
        actor=admin,
        action="delete",
        resource_type="account",
        resource_id=uuid.uuid4(),
        owner_id=other.id,
    )

    assert result is True


# ---------------------------------------------------------------------------
# Tests for PermissionGrantCRUD.list_grants_for_grantee
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_grants_for_grantee_returns_all_active_grants(
    db_session: AsyncSession,
):
    """Returns all active grants for a grantee + resource_type, ignoring grantor."""
    org = _org()
    grantor_a = _user(org.id)
    grantor_b = _user(org.id)
    grantee = _user(org.id)
    db_session.add_all([org, grantor_a, grantor_b, grantee])
    await db_session.flush()

    g1 = _grant(org.id, grantor_a.id, grantee.id, resource_id=None, actions=["read", "update"])
    g2 = _grant(org.id, grantor_b.id, grantee.id, resource_id=None, actions=["read"])
    db_session.add_all([g1, g2])
    await db_session.commit()

    results = await permission_grant_crud.list_grants_for_grantee(
        db_session, grantee_id=grantee.id, resource_type="account",
    )

    assert len(results) == 2
    ids = {r.id for r in results}
    assert g1.id in ids
    assert g2.id in ids


@pytest.mark.asyncio
async def test_list_grants_for_grantee_ignores_inactive(
    db_session: AsyncSession,
):
    """Inactive grants are excluded."""
    org = _org()
    grantor = _user(org.id)
    grantee = _user(org.id)
    db_session.add_all([org, grantor, grantee])
    await db_session.flush()

    active = _grant(org.id, grantor.id, grantee.id, resource_id=None, is_active=True)
    inactive = _grant(org.id, grantor.id, grantee.id, resource_type="transaction",
                      resource_id=None, is_active=False)
    db_session.add_all([active, inactive])
    await db_session.commit()

    results = await permission_grant_crud.list_grants_for_grantee(
        db_session, grantee_id=grantee.id, resource_type="account",
    )

    assert len(results) == 1
    assert results[0].id == active.id


# ---------------------------------------------------------------------------
# Tests for PermissionService.filter_allowed_resources
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_filter_allowed_resources_wildcard_grant(
    db_session: AsyncSession,
):
    """
    THE KEY SCENARIO: A wildcard grant must allow all resources from the grantor
    when checked via the bulk filter_allowed_resources method.
    """
    org = _org()
    grantor = _user(org.id)
    grantee = _user(org.id, is_org_admin=False)
    db_session.add_all([org, grantor, grantee])
    await db_session.flush()

    wildcard = _grant(org.id, grantor.id, grantee.id, resource_id=None, actions=["read", "update"])
    db_session.add(wildcard)
    await db_session.commit()

    svc = PermissionService()
    acc_ids = [uuid.uuid4() for _ in range(5)]
    pairs = [(acc_id, grantor.id) for acc_id in acc_ids]

    allowed = await svc.filter_allowed_resources(
        db_session, grantee, "update", "account", pairs,
    )

    assert set(allowed) == set(acc_ids), (
        "All accounts from the grantor should be allowed via wildcard grant"
    )


@pytest.mark.asyncio
async def test_filter_allowed_resources_owner_always_allowed(
    db_session: AsyncSession,
):
    """Owner's own accounts are always in the allowed set, no grant needed."""
    org = _org()
    user = _user(org.id)
    db_session.add_all([org, user])
    await db_session.commit()

    svc = PermissionService()
    acc_ids = [uuid.uuid4() for _ in range(3)]
    pairs = [(acc_id, user.id) for acc_id in acc_ids]

    allowed = await svc.filter_allowed_resources(
        db_session, user, "update", "account", pairs,
    )

    assert set(allowed) == set(acc_ids)


@pytest.mark.asyncio
async def test_filter_allowed_resources_org_admin_always_allowed(
    db_session: AsyncSession,
):
    """Org admin can access all resources regardless of grants."""
    org = _org()
    admin = _user(org.id, is_org_admin=True)
    other = _user(org.id)
    db_session.add_all([org, admin, other])
    await db_session.commit()

    svc = PermissionService()
    acc_ids = [uuid.uuid4() for _ in range(3)]
    pairs = [(acc_id, other.id) for acc_id in acc_ids]

    allowed = await svc.filter_allowed_resources(
        db_session, admin, "delete", "account", pairs,
    )

    assert set(allowed) == set(acc_ids)


@pytest.mark.asyncio
async def test_filter_allowed_resources_denies_without_grant(
    db_session: AsyncSession,
):
    """Without a grant, non-owned resources are excluded."""
    org = _org()
    owner = _user(org.id)
    actor = _user(org.id, is_org_admin=False)
    db_session.add_all([org, owner, actor])
    await db_session.commit()

    svc = PermissionService()
    pairs = [(uuid.uuid4(), owner.id) for _ in range(3)]

    allowed = await svc.filter_allowed_resources(
        db_session, actor, "update", "account", pairs,
    )

    assert allowed == []


@pytest.mark.asyncio
async def test_filter_allowed_resources_denies_wrong_action(
    db_session: AsyncSession,
):
    """Grant with 'read' only does not allow 'delete'."""
    org = _org()
    grantor = _user(org.id)
    grantee = _user(org.id, is_org_admin=False)
    db_session.add_all([org, grantor, grantee])
    await db_session.flush()

    wildcard = _grant(org.id, grantor.id, grantee.id, resource_id=None, actions=["read"])
    db_session.add(wildcard)
    await db_session.commit()

    svc = PermissionService()
    pairs = [(uuid.uuid4(), grantor.id)]

    allowed = await svc.filter_allowed_resources(
        db_session, grantee, "delete", "account", pairs,
    )

    assert allowed == []


@pytest.mark.asyncio
async def test_filter_allowed_resources_expired_grant_excluded(
    db_session: AsyncSession,
):
    """Expired wildcard grant does NOT allow access."""
    org = _org()
    grantor = _user(org.id)
    grantee = _user(org.id, is_org_admin=False)
    db_session.add_all([org, grantor, grantee])
    await db_session.flush()

    expired_grant = PermissionGrant(
        id=uuid.uuid4(),
        organization_id=org.id,
        grantor_id=grantor.id,
        grantee_id=grantee.id,
        resource_type="account",
        resource_id=None,
        actions=["read", "update"],
        granted_at=utc_now(),
        expires_at=utc_now() - timedelta(days=1),  # Expired
        is_active=True,
        granted_by=grantor.id,
    )
    db_session.add(expired_grant)
    await db_session.commit()

    svc = PermissionService()
    pairs = [(uuid.uuid4(), grantor.id)]

    allowed = await svc.filter_allowed_resources(
        db_session, grantee, "update", "account", pairs,
    )

    assert allowed == []


@pytest.mark.asyncio
async def test_filter_allowed_resources_mixed_owned_and_granted(
    db_session: AsyncSession,
):
    """Mix of owned accounts + granted accounts: all should be in the result."""
    org = _org()
    user_a = _user(org.id, is_org_admin=False)
    user_b = _user(org.id)
    db_session.add_all([org, user_a, user_b])
    await db_session.flush()

    # user_b grants user_a 'update' access to all accounts
    wildcard = _grant(org.id, user_b.id, user_a.id, resource_id=None, actions=["read", "update"])
    db_session.add(wildcard)
    await db_session.commit()

    svc = PermissionService()
    own_acc = uuid.uuid4()
    other_acc_1 = uuid.uuid4()
    other_acc_2 = uuid.uuid4()
    pairs = [
        (own_acc, user_a.id),        # owned by actor
        (other_acc_1, user_b.id),    # owned by user_b (granted)
        (other_acc_2, user_b.id),    # owned by user_b (granted)
    ]

    allowed = await svc.filter_allowed_resources(
        db_session, user_a, "update", "account", pairs,
    )

    assert set(allowed) == {own_acc, other_acc_1, other_acc_2}


@pytest.mark.asyncio
async def test_filter_allowed_resources_specific_resource_grant(
    db_session: AsyncSession,
):
    """A grant for a specific resource_id only allows that one resource."""
    org = _org()
    grantor = _user(org.id)
    grantee = _user(org.id, is_org_admin=False)
    db_session.add_all([org, grantor, grantee])
    await db_session.flush()

    target_resource = uuid.uuid4()
    specific_grant = _grant(
        org.id, grantor.id, grantee.id,
        resource_id=target_resource, actions=["read", "update"],
    )
    db_session.add(specific_grant)
    await db_session.commit()

    svc = PermissionService()
    other_resource = uuid.uuid4()
    pairs = [
        (target_resource, grantor.id),  # This one has a specific grant
        (other_resource, grantor.id),   # This one does NOT
    ]

    allowed = await svc.filter_allowed_resources(
        db_session, grantee, "update", "account", pairs,
    )

    assert allowed == [target_resource]
