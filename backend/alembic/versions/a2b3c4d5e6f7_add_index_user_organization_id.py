"""add_index_user_organization_id

Adds a database index on users.organization_id, which is used as the
primary tenant-isolation filter in nearly every query. Without this index
every multi-tenant lookup performs a full table scan.

Revision ID: a2b3c4d5e6f7
Revises: e92a1c3f8b04
Create Date: 2026-02-20 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, None] = 'e92a1c3f8b04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        'ix_users_organization_id',
        'users',
        ['organization_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_users_organization_id', table_name='users')
