"""add_transaction_merges

Revision ID: e5f6g7h8i9j0
Revises: d4e5f6g7h8i9
Create Date: 2026-02-15 16:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e5f6g7h8i9j0'
down_revision: Union[str, None] = 'd4e5f6g7h8i9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create transaction_merges table
    op.create_table(
        'transaction_merges',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('primary_transaction_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('duplicate_transaction_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('merge_reason', sa.Text(), nullable=True),
        sa.Column('is_auto_merged', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('merged_at', sa.DateTime(), nullable=False),
        sa.Column('merged_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['primary_transaction_id'], ['transactions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['merged_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('ix_transaction_merges_organization_id', 'transaction_merges', ['organization_id'])
    op.create_index('ix_transaction_merges_primary', 'transaction_merges', ['primary_transaction_id'])
    op.create_index('ix_transaction_merges_duplicate', 'transaction_merges', ['duplicate_transaction_id'])
    op.create_index('ix_transaction_merges_org_date', 'transaction_merges', ['organization_id', 'merged_at'])


def downgrade() -> None:
    op.drop_index('ix_transaction_merges_org_date', table_name='transaction_merges')
    op.drop_index('ix_transaction_merges_duplicate', table_name='transaction_merges')
    op.drop_index('ix_transaction_merges_primary', table_name='transaction_merges')
    op.drop_index('ix_transaction_merges_organization_id', table_name='transaction_merges')
    op.drop_table('transaction_merges')
