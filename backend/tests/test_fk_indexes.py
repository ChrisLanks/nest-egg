"""Tests for FK indexes added in migration 978c23c8472f.

Verifies that ix_bulk_operation_logs_user_id and ix_categories_parent_category_id
are present in the live database (SQLite PRAGMA, same pattern as
test_notification_indexes.py).
"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def _get_indexes(db_session: AsyncSession, table_name: str) -> set[str]:
    """Return index names on *table_name* via SQLite PRAGMA index_list."""
    result = await db_session.execute(text(f"PRAGMA index_list({table_name})"))
    return {row[1] for row in result.fetchall()}


@pytest.mark.asyncio
class TestFKIndexes:
    """Verify FK indexes exist — catches missing migrations."""

    async def test_bulk_operation_logs_user_id_index_exists(self, db_session: AsyncSession):
        """ix_bulk_operation_logs_user_id — speeds up 'get all ops by user' queries."""
        indexes = await _get_indexes(db_session, "bulk_operation_logs")
        assert "ix_bulk_operation_logs_user_id" in indexes, (
            "Missing ix_bulk_operation_logs_user_id — run: alembic upgrade head"
        )

    async def test_categories_parent_category_id_index_exists(self, db_session: AsyncSession):
        """ix_categories_parent_category_id — speeds up category hierarchy lookups."""
        indexes = await _get_indexes(db_session, "categories")
        assert "ix_categories_parent_category_id" in indexes, (
            "Missing ix_categories_parent_category_id — run: alembic upgrade head"
        )

    async def test_refresh_tokens_user_id_index_exists(self, db_session: AsyncSession):
        """ix_refresh_tokens_user_id — speeds up token revocation by user."""
        indexes = await _get_indexes(db_session, "refresh_tokens")
        assert "ix_refresh_tokens_user_id" in indexes, (
            "Missing ix_refresh_tokens_user_id — run: alembic upgrade head"
        )

    async def test_household_invitations_organization_id_index_exists(self, db_session: AsyncSession):
        """ix_household_invitations_organization_id — speeds up listing pending invites per org."""
        indexes = await _get_indexes(db_session, "household_invitations")
        assert "ix_household_invitations_organization_id" in indexes, (
            "Missing ix_household_invitations_organization_id — run: alembic upgrade head"
        )

    async def test_household_invitations_invited_by_user_id_index_exists(self, db_session: AsyncSession):
        """ix_household_invitations_invited_by_user_id — speeds up cascade deletes by inviter."""
        indexes = await _get_indexes(db_session, "household_invitations")
        assert "ix_household_invitations_invited_by_user_id" in indexes, (
            "Missing ix_household_invitations_invited_by_user_id — run: alembic upgrade head"
        )

    async def test_account_shares_account_id_index_exists(self, db_session: AsyncSession):
        """ix_account_shares_account_id — speeds up loading shares for an account."""
        indexes = await _get_indexes(db_session, "account_shares")
        assert "ix_account_shares_account_id" in indexes, (
            "Missing ix_account_shares_account_id — run: alembic upgrade head"
        )

    async def test_account_shares_shared_with_user_id_index_exists(self, db_session: AsyncSession):
        """ix_account_shares_shared_with_user_id — speeds up loading accounts shared with a user."""
        indexes = await _get_indexes(db_session, "account_shares")
        assert "ix_account_shares_shared_with_user_id" in indexes, (
            "Missing ix_account_shares_shared_with_user_id — run: alembic upgrade head"
        )
