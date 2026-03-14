"""Add index on user organization_id for query performance.

Revision ID: 539b8bbbf1c7
Revises: z8a9b0c1d2e3
Create Date: 2026-03-13

The users.organization_id column is used in nearly every tenant-scoped query.
Adding a B-tree index dramatically improves lookup and join performance.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "539b8bbbf1c7"
down_revision: Union[str, None] = "z8a9b0c1d2e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_users_organization_id", "users", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_users_organization_id", table_name="users")
