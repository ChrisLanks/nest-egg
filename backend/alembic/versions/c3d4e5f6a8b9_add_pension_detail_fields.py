"""add pension detail fields

Revision ID: c3d4e5f6a8b9
Revises: b2c3f4e5d6a7
Create Date: 2026-03-24 00:00:00.000000

Adds extended pension planning fields to accounts: COLA rate, survivor
percentage, lump sum value, pension type, employer name, years of service,
and formula percentage per year.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a8b9'
down_revision: Union[str, None] = 'b2c3f4e5d6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('accounts', sa.Column('pension_cola_rate', sa.Numeric(5, 3), nullable=True))
    op.add_column('accounts', sa.Column('pension_survivor_pct', sa.Numeric(5, 2), nullable=True))
    op.add_column('accounts', sa.Column('pension_lump_sum_value', sa.Numeric(15, 2), nullable=True))
    op.add_column('accounts', sa.Column('pension_type', sa.String(50), nullable=True))
    op.add_column('accounts', sa.Column('pension_employer_name', sa.String(255), nullable=True))
    op.add_column('accounts', sa.Column('pension_years_of_service', sa.Numeric(5, 1), nullable=True))
    op.add_column('accounts', sa.Column('pension_formula_pct_per_year', sa.Numeric(5, 3), nullable=True))


def downgrade() -> None:
    op.drop_column('accounts', 'pension_formula_pct_per_year')
    op.drop_column('accounts', 'pension_years_of_service')
    op.drop_column('accounts', 'pension_employer_name')
    op.drop_column('accounts', 'pension_type')
    op.drop_column('accounts', 'pension_lump_sum_value')
    op.drop_column('accounts', 'pension_survivor_pct')
    op.drop_column('accounts', 'pension_cola_rate')
