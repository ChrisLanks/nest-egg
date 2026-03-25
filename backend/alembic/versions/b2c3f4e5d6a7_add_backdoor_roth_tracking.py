"""add backdoor Roth tracking

Revision ID: b2c3f4e5d6a7
Revises: a1b2e3f4c5d6
Create Date: 2026-03-24 00:00:00.000000

Adds form_8606_basis, after_tax_401k_balance, and mega_backdoor_eligible
to accounts for backdoor and mega-backdoor Roth planning.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3f4e5d6a7'
down_revision: Union[str, None] = 'a1b2e3f4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('accounts', sa.Column('form_8606_basis', sa.Numeric(15, 2), nullable=True))
    op.add_column('accounts', sa.Column('after_tax_401k_balance', sa.Numeric(15, 2), nullable=True))
    op.add_column('accounts', sa.Column('mega_backdoor_eligible', sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column('accounts', 'mega_backdoor_eligible')
    op.drop_column('accounts', 'after_tax_401k_balance')
    op.drop_column('accounts', 'form_8606_basis')
