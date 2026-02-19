"""add_parent_label_id_to_labels

Revision ID: b243c5a21d21
Revises: 9956d569c01d
Create Date: 2026-02-19 17:08:45.551454

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b243c5a21d21'
down_revision: Union[str, None] = '9956d569c01d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('labels', sa.Column(
        'parent_label_id',
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey('labels.id', ondelete='SET NULL'),
        nullable=True,
    ))
    op.create_index('ix_labels_parent_label_id', 'labels', ['parent_label_id'])


def downgrade() -> None:
    op.drop_index('ix_labels_parent_label_id', table_name='labels')
    op.drop_column('labels', 'parent_label_id')
