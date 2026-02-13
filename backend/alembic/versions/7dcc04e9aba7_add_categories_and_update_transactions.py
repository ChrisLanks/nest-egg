"""add_categories_and_update_transactions

Revision ID: 7dcc04e9aba7
Revises: 0ec592f33321
Create Date: 2026-02-13 01:55:29.914560

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7dcc04e9aba7'
down_revision: Union[str, None] = '0ec592f33321'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create categories table
    op.create_table(
        'categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('color', sa.String(7), nullable=True),
        sa.Column('parent_category_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_category_id'], ['categories.id'], ondelete='CASCADE'),
    )

    # Create indexes for categories
    op.create_index('ix_categories_organization_id', 'categories', ['organization_id'])
    op.create_index('ix_categories_org_name', 'categories', ['organization_id', 'name'], unique=True)

    # Add category_id column to transactions table
    op.add_column('transactions', sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_transactions_category_id', 'transactions', 'categories', ['category_id'], ['id'], ondelete='SET NULL')
    op.create_index('ix_transactions_category_id', 'transactions', ['category_id'])


def downgrade() -> None:
    # Remove category_id from transactions
    op.drop_index('ix_transactions_category_id', 'transactions')
    op.drop_constraint('fk_transactions_category_id', 'transactions', type_='foreignkey')
    op.drop_column('transactions', 'category_id')

    # Drop categories table
    op.drop_index('ix_categories_org_name', 'categories')
    op.drop_index('ix_categories_organization_id', 'categories')
    op.drop_table('categories')
