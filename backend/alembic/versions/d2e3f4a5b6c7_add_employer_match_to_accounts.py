"""add_employer_match_to_accounts

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-02-20 12:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd2e3f4a5b6c7'
down_revision: Union[str, None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Employer match fields for retirement accounts (401k, 403b, etc.)
    op.add_column(
        'accounts',
        sa.Column('employer_match_percent', sa.Numeric(5, 2), nullable=True),
    )
    op.add_column(
        'accounts',
        sa.Column('employer_match_limit_percent', sa.Numeric(5, 2), nullable=True),
    )
    op.add_column(
        'accounts',
        sa.Column('annual_salary', sa.Numeric(15, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('accounts', 'annual_salary')
    op.drop_column('accounts', 'employer_match_limit_percent')
    op.drop_column('accounts', 'employer_match_percent')
