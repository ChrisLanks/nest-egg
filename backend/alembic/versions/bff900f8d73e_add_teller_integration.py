"""add_teller_integration

Revision ID: bff900f8d73e
Revises: 9ab98de679dc
Create Date: 2026-02-17 13:37:33.962157

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bff900f8d73e'
down_revision: Union[str, None] = '9ab98de679dc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create teller_enrollments table
    op.create_table(
        'teller_enrollments',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('enrollment_id', sa.String(255), nullable=False),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('institution_name', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.Column('last_error_code', sa.String(100), nullable=True),
        sa.Column('last_error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_teller_enrollments_enrollment_id', 'teller_enrollments', ['enrollment_id'], unique=True)
    op.create_index('ix_teller_enrollments_organization_id', 'teller_enrollments', ['organization_id'])
    op.create_index('ix_teller_enrollments_user_id', 'teller_enrollments', ['user_id'])

    # Add teller_enrollment_id to accounts table
    op.add_column('accounts', sa.Column('teller_enrollment_id', sa.UUID(), nullable=True))
    op.create_index('ix_accounts_teller_enrollment_id', 'accounts', ['teller_enrollment_id'])
    op.create_foreign_key(
        'fk_accounts_teller_enrollment_id',
        'accounts',
        'teller_enrollments',
        ['teller_enrollment_id'],
        ['id'],
        ondelete='CASCADE'
    )

    # Add 'teller' to account_source enum
    # Note: This uses raw SQL for PostgreSQL enum modification
    op.execute("ALTER TYPE accountsource ADD VALUE IF NOT EXISTS 'teller' AFTER 'plaid'")


def downgrade() -> None:
    # Remove teller from account_source enum (cannot easily remove enum values in PostgreSQL)
    # Drop foreign key and column from accounts
    op.drop_constraint('fk_accounts_teller_enrollment_id', 'accounts', type_='foreignkey')
    op.drop_index('ix_accounts_teller_enrollment_id', 'accounts')
    op.drop_column('accounts', 'teller_enrollment_id')

    # Drop teller_enrollments table
    op.drop_index('ix_teller_enrollments_user_id', 'teller_enrollments')
    op.drop_index('ix_teller_enrollments_organization_id', 'teller_enrollments')
    op.drop_index('ix_teller_enrollments_enrollment_id', 'teller_enrollments')
    op.drop_table('teller_enrollments')
