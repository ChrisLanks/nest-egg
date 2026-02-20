"""Add priority, auto_sync, is_funded, funded_at to savings_goals

Revision ID: a1b2c3d4e5f6
Revises: fecf4db781a3
Create Date: 2026-02-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'fecf4db781a3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('savings_goals', sa.Column('auto_sync', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('savings_goals', sa.Column('priority', sa.Integer(), nullable=True))
    op.add_column('savings_goals', sa.Column('is_funded', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('savings_goals', sa.Column('funded_at', sa.DateTime(), nullable=True))
    op.create_index('ix_savings_goals_priority', 'savings_goals', ['organization_id', 'priority'])


def downgrade() -> None:
    op.drop_index('ix_savings_goals_priority', table_name='savings_goals')
    op.drop_column('savings_goals', 'funded_at')
    op.drop_column('savings_goals', 'is_funded')
    op.drop_column('savings_goals', 'priority')
    op.drop_column('savings_goals', 'auto_sync')
