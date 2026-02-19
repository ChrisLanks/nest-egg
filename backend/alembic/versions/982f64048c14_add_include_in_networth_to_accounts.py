"""add_include_in_networth_to_accounts

Revision ID: 982f64048c14
Revises: 4c77d7675f31
Create Date: 2026-02-18 23:12:58.259356

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '982f64048c14'
down_revision: Union[str, None] = '4c77d7675f31'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add include_in_networth column
    # None = auto-determine based on company_status (public=true, private=false)
    op.add_column('accounts', sa.Column('include_in_networth', sa.Boolean(), nullable=True))


def downgrade() -> None:
    # Remove include_in_networth column
    op.drop_column('accounts', 'include_in_networth')
