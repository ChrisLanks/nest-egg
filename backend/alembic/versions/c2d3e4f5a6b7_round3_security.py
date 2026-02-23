"""round3_security

Security audit fixes:
- Add user_consents table (GDPR consent tracking)
- Change accounts.annual_salary from Numeric(15,2) to Text (for EncryptedString)

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-02-22 00:01:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, None] = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create user_consents table for GDPR consent tracking
    op.create_table(
        "user_consents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("consent_type", sa.String(50), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("consented_at", sa.DateTime(), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_user_consents_user_id", "user_consents", ["user_id"])

    # 2. Change annual_salary from Numeric(15,2) to Text (EncryptedString stores as text)
    #    Existing plaintext numeric values are preserved as their string representation;
    #    they will be re-read as strings and should be re-saved with encryption via the app.
    op.alter_column(
        "accounts",
        "annual_salary",
        existing_type=sa.Numeric(15, 2),
        type_=sa.Text(),
        existing_nullable=True,
        postgresql_using="annual_salary::text",
    )


def downgrade() -> None:
    # Reverse annual_salary back to Numeric
    op.alter_column(
        "accounts",
        "annual_salary",
        existing_type=sa.Text(),
        type_=sa.Numeric(15, 2),
        existing_nullable=True,
        postgresql_using="annual_salary::numeric",
    )

    # Drop user_consents table
    op.drop_index("ix_user_consents_user_id", table_name="user_consents")
    op.drop_table("user_consents")
