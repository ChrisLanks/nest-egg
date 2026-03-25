"""Add file attachment columns to hsa_receipts.

Revision ID: b8c9d0e1f2a3
Revises: p1q2r3s4t5u6
Create Date: 2026-03-25

Adds file_key, file_name, and file_content_type to support receipt image/PDF
uploads stored via the configured storage backend (local or S3).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, None] = "p1q2r3s4t5u6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("hsa_receipts", sa.Column("file_key", sa.String(1024), nullable=True))
    op.add_column("hsa_receipts", sa.Column("file_name", sa.String(255), nullable=True))
    op.add_column("hsa_receipts", sa.Column("file_content_type", sa.String(128), nullable=True))


def downgrade() -> None:
    op.drop_column("hsa_receipts", "file_content_type")
    op.drop_column("hsa_receipts", "file_name")
    op.drop_column("hsa_receipts", "file_key")
