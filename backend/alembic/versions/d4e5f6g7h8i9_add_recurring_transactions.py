"""add_recurring_transactions

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2026-02-15 16:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd4e5f6g7h8i9'
down_revision: Union[str, None] = 'c3d4e5f6g7h8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create RecurringFrequency enum
    op.execute("""
        CREATE TYPE recurringfrequency AS ENUM ('weekly', 'biweekly', 'monthly', 'quarterly', 'yearly')
    """)

    # Create recurring_transactions table
    op.create_table(
        'recurring_transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('merchant_name', sa.String(255), nullable=False),
        sa.Column('description_pattern', sa.String(500), nullable=True),
        sa.Column('frequency', sa.Enum('WEEKLY', 'BIWEEKLY', 'MONTHLY', 'QUARTERLY', 'YEARLY', name='recurringfrequency'), nullable=False),
        sa.Column('average_amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('amount_variance', sa.Numeric(15, 2), nullable=False, server_default='5.00'),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_user_created', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('confidence_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('first_occurrence', sa.Date(), nullable=False),
        sa.Column('last_occurrence', sa.Date(), nullable=True),
        sa.Column('next_expected_date', sa.Date(), nullable=True),
        sa.Column('occurrence_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('ix_recurring_transactions_organization_id', 'recurring_transactions', ['organization_id'])
    op.create_index('ix_recurring_transactions_account_id', 'recurring_transactions', ['account_id'])
    op.create_index('ix_recurring_transactions_merchant_name', 'recurring_transactions', ['merchant_name'])
    op.create_index('ix_recurring_org_merchant', 'recurring_transactions', ['organization_id', 'merchant_name'])
    op.create_index('ix_recurring_org_active', 'recurring_transactions', ['organization_id', 'is_active'])


def downgrade() -> None:
    op.drop_index('ix_recurring_org_active', table_name='recurring_transactions')
    op.drop_index('ix_recurring_org_merchant', table_name='recurring_transactions')
    op.drop_index('ix_recurring_transactions_merchant_name', table_name='recurring_transactions')
    op.drop_index('ix_recurring_transactions_account_id', table_name='recurring_transactions')
    op.drop_index('ix_recurring_transactions_organization_id', table_name='recurring_transactions')
    op.drop_table('recurring_transactions')
    op.execute('DROP TYPE recurringfrequency')
