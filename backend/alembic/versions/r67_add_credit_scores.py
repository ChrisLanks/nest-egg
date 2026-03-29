"""Add credit_scores table for manual credit score tracking.

Revision ID: r67_add_credit_scores
Revises: r66_merge_heads
Create Date: 2026-03-29

Stores user-entered credit score history (manual entry from Equifax, TransUnion,
Experian, FICO, or other bureaus). No third-party integration — user enters scores
they pull from their bank or bureau directly.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "r67_add_credit_scores"
down_revision: Union[str, None] = "r66_merge_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Table may already exist in dev environments — skip if so
    from sqlalchemy import inspect as sa_inspect
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    if "credit_scores" in inspector.get_table_names():
        return
    op.create_table(
        "credit_scores",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("score_date", sa.Date(), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),  # Equifax, TransUnion, Experian, FICO, Other
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_credit_scores_organization_id", "credit_scores", ["organization_id"])
    op.create_index("ix_credit_scores_user_id", "credit_scores", ["user_id"])
    op.create_index("ix_credit_scores_score_date", "credit_scores", ["score_date"])


def downgrade() -> None:
    op.drop_index("ix_credit_scores_score_date", table_name="credit_scores")
    op.drop_index("ix_credit_scores_user_id", table_name="credit_scores")
    op.drop_index("ix_credit_scores_organization_id", table_name="credit_scores")
    op.drop_table("credit_scores")
