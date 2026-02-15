"""add_budgets

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f7
Create Date: 2026-02-15 16:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, None] = 'a1b2c3d4e5f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create BudgetPeriod enum
    op.execute("""
        CREATE TYPE budgetperiod AS ENUM ('monthly', 'quarterly', 'yearly')
    """)

    # Create budgets table
    op.create_table(
        'budgets',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('period', sa.Enum('MONTHLY', 'QUARTERLY', 'YEARLY', name='budgetperiod'), nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('rollover_unused', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('alert_threshold', sa.Numeric(5, 2), nullable=False, server_default='0.80'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('ix_budgets_organization_id', 'budgets', ['organization_id'])
    op.create_index('ix_budgets_category_id', 'budgets', ['category_id'])
    op.create_index('ix_budgets_org_active', 'budgets', ['organization_id', 'is_active'])
    op.create_index('ix_budgets_org_dates', 'budgets', ['organization_id', 'start_date', 'end_date'])


def downgrade() -> None:
    op.drop_index('ix_budgets_org_dates', table_name='budgets')
    op.drop_index('ix_budgets_org_active', table_name='budgets')
    op.drop_index('ix_budgets_category_id', table_name='budgets')
    op.drop_index('ix_budgets_organization_id', table_name='budgets')
    op.drop_table('budgets')
    op.execute('DROP TYPE budgetperiod')
