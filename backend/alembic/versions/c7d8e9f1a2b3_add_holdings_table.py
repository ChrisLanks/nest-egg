"""add_holdings_table

Revision ID: c7d8e9f1a2b3
Revises: bd8a5247f8d8
Create Date: 2026-02-13 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c7d8e9f1a2b3'
down_revision: Union[str, None] = 'bd8a5247f8d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create holdings table
    op.create_table(
        'holdings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ticker', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('shares', sa.Numeric(precision=15, scale=6), nullable=False),
        sa.Column('cost_basis_per_share', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('total_cost_basis', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('current_price_per_share', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('current_total_value', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('price_as_of', sa.DateTime(), nullable=True),
        sa.Column('asset_type', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('ix_holdings_account_id', 'holdings', ['account_id'])
    op.create_index('ix_holdings_organization_id', 'holdings', ['organization_id'])
    op.create_index('ix_holdings_ticker', 'holdings', ['ticker'])


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('ix_holdings_ticker', table_name='holdings')
    op.drop_index('ix_holdings_organization_id', table_name='holdings')
    op.drop_index('ix_holdings_account_id', table_name='holdings')

    # Drop table
    op.drop_table('holdings')
