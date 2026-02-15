"""add_new_account_types_and_property_type

Revision ID: e1f2g3h4i5j6
Revises: 9c709d400b8b
Create Date: 2026-02-15 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1f2g3h4i5j6'
down_revision: Union[str, None] = '9c709d400b8b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create PropertyType enum (only if it doesn't exist)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE propertytype AS ENUM ('personal_residence', 'investment', 'vacation_home');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Add property_type column to accounts table (only if it doesn't exist)
    op.execute("""
        DO $$ BEGIN
            ALTER TABLE accounts ADD COLUMN property_type propertytype;
        EXCEPTION
            WHEN duplicate_column THEN null;
        END $$;
    """)

    # Add new account type values to accounttype enum
    # Cash & Checking (money_market and cd are new)
    op.execute("ALTER TYPE accounttype ADD VALUE IF NOT EXISTS 'money_market'")
    op.execute("ALTER TYPE accounttype ADD VALUE IF NOT EXISTS 'cd'")

    # Debt (student_loan is new)
    op.execute("ALTER TYPE accounttype ADD VALUE IF NOT EXISTS 'student_loan'")

    # Investment Accounts (pension is new)
    op.execute("ALTER TYPE accounttype ADD VALUE IF NOT EXISTS 'pension'")

    # Alternative Investments (collectibles and precious_metals are new)
    op.execute("ALTER TYPE accounttype ADD VALUE IF NOT EXISTS 'collectibles'")
    op.execute("ALTER TYPE accounttype ADD VALUE IF NOT EXISTS 'precious_metals'")

    # Insurance & Annuities (both are new)
    op.execute("ALTER TYPE accounttype ADD VALUE IF NOT EXISTS 'life_insurance_cash_value'")
    op.execute("ALTER TYPE accounttype ADD VALUE IF NOT EXISTS 'annuity'")

    # Securities (bond and stock_options are new)
    op.execute("ALTER TYPE accounttype ADD VALUE IF NOT EXISTS 'bond'")
    op.execute("ALTER TYPE accounttype ADD VALUE IF NOT EXISTS 'stock_options'")

    # Business (business_equity is new)
    op.execute("ALTER TYPE accounttype ADD VALUE IF NOT EXISTS 'business_equity'")


def downgrade() -> None:
    # Remove property_type column
    op.drop_column('accounts', 'property_type')

    # Drop propertytype enum
    op.execute("DROP TYPE IF EXISTS propertytype")

    # Note: PostgreSQL does not support removing enum values directly
    # For now, we'll leave the new account type values in the database
    pass
