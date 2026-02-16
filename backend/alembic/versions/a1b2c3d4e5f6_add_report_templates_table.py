"""add_report_templates_table

Revision ID: a1b2c3d4e5f6
Revises: 6ad249139327
Create Date: 2026-02-15 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '6ad249139327'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create report_templates table
    op.create_table(
        'report_templates',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('report_type', sa.String(50), nullable=False),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_shared', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_by_user_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(
            ['organization_id'],
            ['organizations.id'],
            name='report_templates_organization_id_fkey',
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['created_by_user_id'],
            ['users.id'],
            name='report_templates_created_by_user_id_fkey',
            ondelete='CASCADE'
        ),
    )

    # Create indexes
    op.create_index(
        'ix_report_templates_organization_id',
        'report_templates',
        ['organization_id']
    )
    op.create_index(
        'ix_report_templates_created_by_user_id',
        'report_templates',
        ['created_by_user_id']
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_report_templates_created_by_user_id', 'report_templates')
    op.drop_index('ix_report_templates_organization_id', 'report_templates')

    # Drop table
    op.drop_table('report_templates')
