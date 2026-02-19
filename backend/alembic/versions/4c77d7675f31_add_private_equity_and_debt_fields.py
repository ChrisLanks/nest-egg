"""add_private_equity_and_debt_fields

Revision ID: 4c77d7675f31
Revises: bff900f8d73e
Create Date: 2026-02-18 22:59:57.314585

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4c77d7675f31'
down_revision: Union[str, None] = 'bff900f8d73e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new enum values to accounttype
    op.execute("ALTER TYPE accounttype ADD VALUE IF NOT EXISTS 'private_debt'")

    # Create new enum types
    op.execute("""
        CREATE TYPE granttype AS ENUM ('iso', 'nso', 'rsu', 'rsa')
    """)
    op.execute("""
        CREATE TYPE companystatus AS ENUM ('private', 'public')
    """)
    op.execute("""
        CREATE TYPE valuationmethod AS ENUM ('409a', 'preferred', 'custom')
    """)

    # Add Private Debt field
    op.add_column('accounts', sa.Column('principal_amount', sa.Numeric(precision=15, scale=2), nullable=True))

    # Add Private Equity fields
    op.add_column('accounts', sa.Column('grant_type', sa.Enum('iso', 'nso', 'rsu', 'rsa', name='granttype'), nullable=True))
    op.add_column('accounts', sa.Column('grant_date', sa.Date(), nullable=True))
    op.add_column('accounts', sa.Column('quantity', sa.Numeric(precision=15, scale=4), nullable=True))
    op.add_column('accounts', sa.Column('strike_price', sa.Numeric(precision=15, scale=4), nullable=True))
    op.add_column('accounts', sa.Column('vesting_schedule', sa.Text(), nullable=True))
    op.add_column('accounts', sa.Column('share_price', sa.Numeric(precision=15, scale=4), nullable=True))
    op.add_column('accounts', sa.Column('company_status', sa.Enum('private', 'public', name='companystatus'), nullable=True))
    op.add_column('accounts', sa.Column('valuation_method', sa.Enum('409a', 'preferred', 'custom', name='valuationmethod'), nullable=True))


def downgrade() -> None:
    # Remove Private Equity fields
    op.drop_column('accounts', 'valuation_method')
    op.drop_column('accounts', 'company_status')
    op.drop_column('accounts', 'share_price')
    op.drop_column('accounts', 'vesting_schedule')
    op.drop_column('accounts', 'strike_price')
    op.drop_column('accounts', 'quantity')
    op.drop_column('accounts', 'grant_date')
    op.drop_column('accounts', 'grant_type')

    # Remove Private Debt field
    op.drop_column('accounts', 'principal_amount')

    # Drop new enum types
    op.execute("DROP TYPE IF EXISTS valuationmethod")
    op.execute("DROP TYPE IF EXISTS companystatus")
    op.execute("DROP TYPE IF EXISTS granttype")

    # Note: Cannot remove enum value from accounttype in PostgreSQL
    # The 'private_debt' value will remain in the enum but unused
