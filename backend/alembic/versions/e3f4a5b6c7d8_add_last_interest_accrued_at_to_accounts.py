"""add_last_interest_accrued_at_to_accounts

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-02-20 12:02:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3f4a5b6c7d8'
down_revision: Union[str, None] = 'd2e3f4a5b6c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Track when interest was last auto-accrued to prevent double-accrual
    op.add_column(
        'accounts',
        sa.Column('last_interest_accrued_at', sa.Date(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('accounts', 'last_interest_accrued_at')
