"""add household multi-user support

Revision ID: d345678901cd
Revises: c234567890bc
Create Date: 2026-02-15 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd345678901cd'
down_revision = 'c234567890bc'
branch_labels = None
depends_on = None


def upgrade():
    # Create household_invitations table
    op.create_table(
        'household_invitations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('invited_by_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('invitation_code', sa.String(64), nullable=False, unique=True),
        sa.Column('status', sa.Enum('pending', 'accepted', 'declined', 'expired', name='invitation_status'), nullable=False, server_default='pending'),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('accepted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invited_by_user_id'], ['users.id'], ondelete='CASCADE'),
    )

    # Create indexes for household_invitations
    op.create_index('idx_invitation_code', 'household_invitations', ['invitation_code'], unique=True)
    op.create_index('idx_household_inv_org_status', 'household_invitations', ['organization_id', 'status'])

    # Create account_shares table
    op.create_table(
        'account_shares',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('shared_with_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('permission', sa.Enum('view', 'edit', name='share_permission'), nullable=False, server_default='view'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['shared_with_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('account_id', 'shared_with_user_id', name='uq_account_user_share'),
    )

    # Create index for account_shares
    op.create_index('idx_shared_with_user', 'account_shares', ['shared_with_user_id'])

    # Add plaid_item_hash column to accounts
    op.add_column('accounts', sa.Column('plaid_item_hash', sa.String(64), nullable=True))
    op.create_index('idx_plaid_item_hash', 'accounts', ['organization_id', 'plaid_item_hash'])

    # Add is_primary_household_member column to users
    op.add_column('users', sa.Column('is_primary_household_member', sa.Boolean(), server_default='false', nullable=False))


def downgrade():
    # Remove is_primary_household_member column from users
    op.drop_column('users', 'is_primary_household_member')

    # Remove plaid_item_hash and index from accounts
    op.drop_index('idx_plaid_item_hash', table_name='accounts')
    op.drop_column('accounts', 'plaid_item_hash')

    # Drop account_shares table and index
    op.drop_index('idx_shared_with_user', table_name='account_shares')
    op.drop_table('account_shares')

    # Drop account_shares permission enum
    op.execute("DROP TYPE IF EXISTS share_permission")

    # Drop household_invitations table and indexes
    op.drop_index('idx_household_inv_org_status', table_name='household_invitations')
    op.drop_index('idx_invitation_code', table_name='household_invitations')
    op.drop_table('household_invitations')

    # Drop invitation_status enum
    op.execute("DROP TYPE IF EXISTS invitation_status")
