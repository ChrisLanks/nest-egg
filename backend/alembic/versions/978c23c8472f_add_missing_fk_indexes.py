"""add_missing_fk_indexes

Revision ID: 978c23c8472f
Revises: 8023eee2c8e5
Create Date: 2026-03-21 23:03:05.217620

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '978c23c8472f'
down_revision: Union[str, None] = '8023eee2c8e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(op.f('ix_bulk_operation_logs_user_id'), 'bulk_operation_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_categories_parent_category_id'), 'categories', ['parent_category_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_categories_parent_category_id'), table_name='categories')
    op.drop_index(op.f('ix_bulk_operation_logs_user_id'), table_name='bulk_operation_logs')
