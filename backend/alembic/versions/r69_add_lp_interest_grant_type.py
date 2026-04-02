"""Add lp_interest to granttype enum.

Revision ID: r69_add_lp_interest
Revises: r68_add_rental_type
Create Date: 2026-04-02

Adds LP Interest grant type for Limited Partnership tracking
(PE funds, real estate LPs, hedge funds).
"""

from typing import Sequence, Union
from alembic import op

revision: str = "r69_add_lp_interest"
down_revision: Union[str, None] = "r68_add_rental_type"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE granttype ADD VALUE IF NOT EXISTS 'lp_interest'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values
    pass
