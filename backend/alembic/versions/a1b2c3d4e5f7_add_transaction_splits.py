"""add_transaction_splits

Revision ID: a1b2c3d4e5f7
Revises: e1f2g3h4i5j6
Create Date: 2026-02-15 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f7'
down_revision: Union[str, None] = 'e1f2g3h4i5j6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add is_split column to transactions table
    op.add_column('transactions', sa.Column('is_split', sa.Boolean(), nullable=False, server_default='false'))

    # Create transaction_splits table
    op.create_table(
        'transaction_splits',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('parent_transaction_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['parent_transaction_id'], ['transactions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('ix_transaction_splits_parent_transaction_id', 'transaction_splits', ['parent_transaction_id'])
    op.create_index('ix_transaction_splits_organization_id', 'transaction_splits', ['organization_id'])


def downgrade() -> None:
    op.drop_index('ix_transaction_splits_organization_id', table_name='transaction_splits')
    op.drop_index('ix_transaction_splits_parent_transaction_id', table_name='transaction_splits')
    op.drop_table('transaction_splits')
    op.drop_column('transactions', 'is_split')
