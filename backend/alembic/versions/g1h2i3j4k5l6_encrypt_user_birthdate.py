"""Encrypt user birthdate field (GDPR Art. 32)

Converts the ``users.birthdate`` column from a plain DATE type to TEXT so
the EncryptedDate TypeDecorator can store versioned Fernet-encrypted ISO
date strings instead of plaintext dates.

Existing NULL values stay NULL.  Any non-NULL plaintext DATE values are
handled gracefully: EncryptedDate.process_result_value falls back to ISO
date parsing when decryption fails (the value looks like "YYYY-MM-DD"),
so data is not lost and users don't need to re-enter their birthday — it
will be transparently re-encrypted the next time the row is saved.

Revision ID: g1h2i3j4k5l6
Revises: fecf4db781a3
Create Date: 2026-02-23 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "g1h2i3j4k5l6"
down_revision: Union[str, None] = "fecf4db781a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Cast DATE → TEXT so EncryptedDate can store versioned ciphertext.
    # PostgreSQL supports USING clause for explicit cast; SQLite handles it
    # transparently via batch mode.
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "birthdate",
            existing_type=sa.Date(),
            type_=sa.Text(),
            existing_nullable=True,
            postgresql_using="birthdate::text",
        )


def downgrade() -> None:
    # Reverse: TEXT → DATE.  Any encrypted rows will become NULL on cast
    # failure in PostgreSQL (USING clause drops unreadable values).
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "birthdate",
            existing_type=sa.Text(),
            type_=sa.Date(),
            existing_nullable=True,
            postgresql_using="birthdate::date",
        )
