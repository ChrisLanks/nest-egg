"""add_label_id_to_budgets

Revision ID: f65f5ac15458
Revises: 8dc2b060f568
Create Date: 2026-02-20 00:49:49.931620

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f65f5ac15458'
down_revision: Union[str, None] = '8dc2b060f568'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'budgets',
        sa.Column('label_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        'fk_budgets_label_id',
        'budgets',
        'labels',
        ['label_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_index('ix_budgets_label_id', 'budgets', ['label_id'])


def downgrade() -> None:
    op.drop_index('ix_budgets_label_id', table_name='budgets')
    op.drop_constraint('fk_budgets_label_id', 'budgets', type_='foreignkey')
    op.drop_column('budgets', 'label_id')
