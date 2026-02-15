"""add_bill_reminder_fields_to_recurring_transactions

Revision ID: 6ad249139327
Revises: e0dadb17e879
Create Date: 2026-02-15 17:05:29.900844

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6ad249139327'
down_revision: Union[str, None] = 'e0dadb17e879'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add bill reminder fields to recurring_transactions table
    op.add_column('recurring_transactions', sa.Column('is_bill', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('recurring_transactions', sa.Column('reminder_days_before', sa.Integer(), nullable=False, server_default='3'))

    # Remove server defaults after adding columns (they're only needed for existing rows)
    op.alter_column('recurring_transactions', 'is_bill', server_default=None)
    op.alter_column('recurring_transactions', 'reminder_days_before', server_default=None)


def downgrade() -> None:
    # Remove bill reminder fields
    op.drop_column('recurring_transactions', 'reminder_days_before')
    op.drop_column('recurring_transactions', 'is_bill')
