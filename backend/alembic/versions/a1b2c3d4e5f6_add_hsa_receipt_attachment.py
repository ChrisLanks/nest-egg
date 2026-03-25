"""Add file attachment columns to hsa_receipts.

Revision ID: a1b2c3d4e5f6
Revises: z8a9b0c1d2e3
Create Date: 2026-03-25

Adds file_key, file_name, and file_content_type to support receipt image/PDF
uploads stored via the configured storage backend (local or S3).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "z8a9b0c1d2e3"
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
