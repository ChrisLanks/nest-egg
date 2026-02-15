"""add_notifications_table

Revision ID: 6983b851f847
Revises: a1b2c3d4e5f6
Create Date: 2026-02-15 02:20:14.372031

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6983b851f847'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('type', sa.Enum('SYNC_FAILED', 'REAUTH_REQUIRED', 'SYNC_STALE', 'ACCOUNT_ERROR', 'BUDGET_ALERT', 'TRANSACTION_DUPLICATE', 'LARGE_TRANSACTION', name='notificationtype'), nullable=False),
        sa.Column('priority', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'URGENT', name='notificationpriority'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('related_entity_type', sa.String(50), nullable=True),
        sa.Column('related_entity_id', sa.UUID(), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_dismissed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.Column('dismissed_at', sa.DateTime(), nullable=True),
        sa.Column('action_url', sa.String(500), nullable=True),
        sa.Column('action_label', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('ix_notifications_organization_id', 'notifications', ['organization_id'])
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])
    op.create_index('ix_notifications_type', 'notifications', ['type'])
    op.create_index('ix_notifications_is_read', 'notifications', ['is_read'])
    op.create_index('ix_notifications_created_at', 'notifications', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_notifications_created_at', table_name='notifications')
    op.drop_index('ix_notifications_is_read', table_name='notifications')
    op.drop_index('ix_notifications_type', table_name='notifications')
    op.drop_index('ix_notifications_user_id', table_name='notifications')
    op.drop_index('ix_notifications_organization_id', table_name='notifications')
    op.drop_table('notifications')
    op.execute('DROP TYPE notificationpriority')
    op.execute('DROP TYPE notificationtype')
