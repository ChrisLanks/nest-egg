"""create_portfolio_snapshots_table

Revision ID: 9c709d400b8b
Revises: 00cdb0f2deaf
Create Date: 2026-02-14 18:08:24.936677

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '9c709d400b8b'
down_revision: Union[str, None] = '00cdb0f2deaf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create portfolio_snapshots table
    op.create_table(
        'portfolio_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('snapshot_date', sa.Date(), nullable=False),

        # Portfolio totals
        sa.Column('total_value', sa.Numeric(15, 2), nullable=False),
        sa.Column('total_cost_basis', sa.Numeric(15, 2), nullable=True),
        sa.Column('total_gain_loss', sa.Numeric(15, 2), nullable=True),
        sa.Column('total_gain_loss_percent', sa.Numeric(10, 4), nullable=True),

        # Asset allocation
        sa.Column('stocks_value', sa.Numeric(15, 2), server_default='0'),
        sa.Column('bonds_value', sa.Numeric(15, 2), server_default='0'),
        sa.Column('etf_value', sa.Numeric(15, 2), server_default='0'),
        sa.Column('mutual_funds_value', sa.Numeric(15, 2), server_default='0'),
        sa.Column('cash_value', sa.Numeric(15, 2), server_default='0'),
        sa.Column('other_value', sa.Numeric(15, 2), server_default='0'),

        # Category breakdown
        sa.Column('retirement_value', sa.Numeric(15, 2), server_default='0'),
        sa.Column('taxable_value', sa.Numeric(15, 2), server_default='0'),

        # Geographic breakdown
        sa.Column('domestic_value', sa.Numeric(15, 2), server_default='0'),
        sa.Column('international_value', sa.Numeric(15, 2), server_default='0'),

        # Full snapshot data (JSONB)
        sa.Column('snapshot_data', postgresql.JSON(), nullable=True),

        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),

        # Unique constraint: one snapshot per organization per day
        sa.UniqueConstraint('organization_id', 'snapshot_date', name='uq_org_snapshot_date'),
    )

    # Create index for efficient queries
    op.create_index('ix_portfolio_snapshots_org_date', 'portfolio_snapshots', ['organization_id', 'snapshot_date'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_portfolio_snapshots_org_date', table_name='portfolio_snapshots')

    # Drop table
    op.drop_table('portfolio_snapshots')
