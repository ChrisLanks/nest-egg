"""create_account_contributions_table

Revision ID: a1b2c3d4e5f6
Revises: e1f2g3h4i5j6
Create Date: 2026-02-15 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'e1f2g3h4i5j6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create contribution type enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE contributiontype AS ENUM ('fixed_amount', 'shares', 'percentage_growth');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create contribution frequency enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE contributionfrequency AS ENUM ('weekly', 'biweekly', 'monthly', 'quarterly', 'annually');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create account_contributions table
    op.create_table(
        'account_contributions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('account_id', UUID(as_uuid=True), sa.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('contribution_type', sa.Enum('fixed_amount', 'shares', 'percentage_growth', name='contributiontype'), nullable=False),
        sa.Column('amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('frequency', sa.Enum('weekly', 'biweekly', 'monthly', 'quarterly', 'annually', name='contributionfrequency'), nullable=False),
        sa.Column('start_date', sa.Date, nullable=False),
        sa.Column('end_date', sa.Date, nullable=True),
        sa.Column('is_active', sa.Boolean, default=True, nullable=False),
        sa.Column('notes', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )


def downgrade() -> None:
    # Drop table
    op.drop_table('account_contributions')

    # Drop enums
    op.execute("DROP TYPE IF EXISTS contributiontype")
    op.execute("DROP TYPE IF EXISTS contributionfrequency")
