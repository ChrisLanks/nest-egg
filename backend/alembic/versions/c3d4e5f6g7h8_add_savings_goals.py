"""add_savings_goals

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2026-02-15 16:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6g7h8'
down_revision: Union[str, None] = 'b2c3d4e5f6g7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create savings_goals table
    op.create_table(
        'savings_goals',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('target_amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('current_amount', sa.Numeric(15, 2), nullable=False, server_default='0.00'),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('target_date', sa.Date(), nullable=True),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_completed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('ix_savings_goals_organization_id', 'savings_goals', ['organization_id'])
    op.create_index('ix_savings_goals_account_id', 'savings_goals', ['account_id'])
    op.create_index('ix_savings_goals_org_active', 'savings_goals', ['organization_id', 'is_completed'])


def downgrade() -> None:
    op.drop_index('ix_savings_goals_org_active', table_name='savings_goals')
    op.drop_index('ix_savings_goals_account_id', table_name='savings_goals')
    op.drop_index('ix_savings_goals_organization_id', table_name='savings_goals')
    op.drop_table('savings_goals')
