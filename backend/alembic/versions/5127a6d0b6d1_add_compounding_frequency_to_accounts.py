"""add_compounding_frequency_to_accounts

Revision ID: 5127a6d0b6d1
Revises: 982f64048c14
Create Date: 2026-02-18 23:34:37.338993

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5127a6d0b6d1'
down_revision: Union[str, None] = '982f64048c14'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create compounding frequency enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE compoundingfrequency AS ENUM ('daily', 'monthly', 'quarterly', 'at_maturity');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Add compounding_frequency column for CD accounts
    op.add_column('accounts', sa.Column('compounding_frequency', sa.Enum('daily', 'monthly', 'quarterly', 'at_maturity', name='compoundingfrequency'), nullable=True))


def downgrade() -> None:
    # Remove compounding_frequency column
    op.drop_column('accounts', 'compounding_frequency')

    # Drop compounding frequency enum
    op.execute("DROP TYPE IF EXISTS compoundingfrequency")
