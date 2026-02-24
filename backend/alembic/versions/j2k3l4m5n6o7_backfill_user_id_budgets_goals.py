"""Backfill user_id on existing budgets and savings_goals.

For each organization, assigns all unowned budgets/goals to the org admin
(or first user if no admin flag). New budgets/goals already set user_id on
create, so this only affects pre-existing records.

Revision ID: j2k3l4m5n6o7
Revises: i1j2k3l4m5n6
Create Date: 2026-02-24 16:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "j2k3l4m5n6o7"
down_revision: Union[str, None] = "i1j2k3l4m5n6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # For each org, pick the admin user (is_org_admin=true, earliest created).
    # Fall back to the first user in the org if no admin exists.
    rows = conn.execute(
        sa.text("""
            SELECT DISTINCT u.organization_id, u.id AS user_id
            FROM users u
            WHERE u.is_active = true
              AND u.id = (
                  SELECT u2.id FROM users u2
                  WHERE u2.organization_id = u.organization_id
                    AND u2.is_active = true
                  ORDER BY u2.is_org_admin DESC, u2.created_at ASC
                  LIMIT 1
              )
        """)
    ).fetchall()

    for org_id, user_id in rows:
        # Backfill budgets
        conn.execute(
            sa.text(
                "UPDATE budgets SET user_id = :uid WHERE organization_id = :oid AND user_id IS NULL"
            ),
            {"uid": user_id, "oid": org_id},
        )
        # Backfill savings_goals
        conn.execute(
            sa.text(
                "UPDATE savings_goals SET user_id = :uid WHERE organization_id = :oid AND user_id IS NULL"
            ),
            {"uid": user_id, "oid": org_id},
        )


def downgrade() -> None:
    # Clear backfilled user_id values (set back to NULL)
    op.execute("UPDATE budgets SET user_id = NULL")
    op.execute("UPDATE savings_goals SET user_id = NULL")
