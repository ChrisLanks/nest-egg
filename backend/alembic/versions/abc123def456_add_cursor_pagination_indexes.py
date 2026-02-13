"""add_cursor_pagination_indexes

Revision ID: abc123def456
Revises: 056d7f850487
Create Date: 2026-02-13 03:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'abc123def456'
down_revision: Union[str, None] = '056d7f850487'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add composite indexes for efficient cursor-based pagination
    # Index for organization-level transaction queries
    op.create_index(
        'ix_transactions_cursor_org',
        'transactions',
        ['organization_id', sa.text('date DESC'), sa.text('created_at DESC'), sa.text('id DESC')]
    )

    # Index for account-specific transaction queries
    op.create_index(
        'ix_transactions_cursor_account',
        'transactions',
        ['account_id', sa.text('date DESC'), sa.text('created_at DESC'), sa.text('id DESC')]
    )


def downgrade() -> None:
    # Remove cursor pagination indexes
    op.drop_index('ix_transactions_cursor_account', 'transactions')
    op.drop_index('ix_transactions_cursor_org', 'transactions')
