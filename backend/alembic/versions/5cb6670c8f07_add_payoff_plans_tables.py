"""add_payoff_plans_tables

Revision ID: 5cb6670c8f07
Revises: 2714b0f122bf
Create Date: 2026-02-16 00:16:51.490890

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5cb6670c8f07'
down_revision: Union[str, None] = '2714b0f122bf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create payoff_plans table
    op.create_table(
        'payoff_plans',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('strategy', sa.String(20), nullable=False),
        sa.Column('extra_monthly_payment', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(
            ['organization_id'],
            ['organizations.id'],
            name='payoff_plans_organization_id_fkey',
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['users.id'],
            name='payoff_plans_user_id_fkey',
            ondelete='CASCADE'
        ),
    )

    # Create indexes
    op.create_index(
        'ix_payoff_plans_organization_id',
        'payoff_plans',
        ['organization_id']
    )
    op.create_index(
        'ix_payoff_plans_user_id',
        'payoff_plans',
        ['user_id']
    )

    # Create payoff_plan_accounts table
    op.create_table(
        'payoff_plan_accounts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('payoff_plan_id', sa.UUID(), nullable=False),
        sa.Column('account_id', sa.UUID(), nullable=False),
        sa.Column('custom_priority', sa.Integer(), nullable=True),
        sa.Column('extra_payment_amount', sa.Numeric(10, 2), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(
            ['payoff_plan_id'],
            ['payoff_plans.id'],
            name='payoff_plan_accounts_payoff_plan_id_fkey',
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['account_id'],
            ['accounts.id'],
            name='payoff_plan_accounts_account_id_fkey',
            ondelete='CASCADE'
        ),
        sa.UniqueConstraint('payoff_plan_id', 'account_id', name='uq_payoff_plan_account')
    )

    # Create indexes
    op.create_index(
        'ix_payoff_plan_accounts_payoff_plan_id',
        'payoff_plan_accounts',
        ['payoff_plan_id']
    )
    op.create_index(
        'ix_payoff_plan_accounts_account_id',
        'payoff_plan_accounts',
        ['account_id']
    )


def downgrade() -> None:
    # Drop payoff_plan_accounts table
    op.drop_index('ix_payoff_plan_accounts_account_id', 'payoff_plan_accounts')
    op.drop_index('ix_payoff_plan_accounts_payoff_plan_id', 'payoff_plan_accounts')
    op.drop_table('payoff_plan_accounts')

    # Drop payoff_plans table
    op.drop_index('ix_payoff_plans_user_id', 'payoff_plans')
    op.drop_index('ix_payoff_plans_organization_id', 'payoff_plans')
    op.drop_table('payoff_plans')
