"""Tests for notification composite indexes.

Verifies that the four composite indexes added in migration
8023eee2c8e5 are present in the live database.
Uses SQLite PRAGMA to stay compatible with the test DB (same pattern as
test_login_count_and_welcome.py::TestMigrationApplied).
"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def _get_notification_indexes(db_session: AsyncSession) -> set[str]:
    """Return index names on the notifications table via SQLite PRAGMA."""
    result = await db_session.execute(text("PRAGMA index_list(notifications)"))
    # PRAGMA index_list returns: (seq, name, unique, origin, partial)
    return {row[1] for row in result.fetchall()}


@pytest.mark.asyncio
class TestNotificationCompositeIndexes:
    """Verify composite indexes exist on the notifications table (catches missing migrations)."""

    async def test_user_created_at_index_exists(self, db_session: AsyncSession):
        """(user_id, created_at) index — speeds up per-user notification feeds."""
        indexes = await _get_notification_indexes(db_session)
        assert "ix_notifications_user_created" in indexes, (
            "Missing ix_notifications_user_created — run: alembic upgrade head"
        )

    async def test_org_created_at_index_exists(self, db_session: AsyncSession):
        """(organization_id, created_at) index — speeds up org-wide notification queries."""
        indexes = await _get_notification_indexes(db_session)
        assert "ix_notifications_org_created" in indexes, (
            "Missing ix_notifications_org_created — run: alembic upgrade head"
        )

    async def test_user_is_read_index_exists(self, db_session: AsyncSession):
        """(user_id, is_read) index — speeds up unread-count queries."""
        indexes = await _get_notification_indexes(db_session)
        assert "ix_notifications_user_is_read" in indexes, (
            "Missing ix_notifications_user_is_read — run: alembic upgrade head"
        )

    async def test_org_is_dismissed_index_exists(self, db_session: AsyncSession):
        """(organization_id, is_dismissed) index — speeds up digest/active notification queries."""
        indexes = await _get_notification_indexes(db_session)
        assert "ix_notifications_org_dismissed" in indexes, (
            "Missing ix_notifications_org_dismissed — run: alembic upgrade head"
        )
