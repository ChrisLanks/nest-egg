"""add_fk_indexes_refresh_token_invitations_account_shares

Revision ID: 5b92773f35b5
Revises: 978c23c8472f
Create Date: 2026-03-22 09:41:25.656599

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '5b92773f35b5'
down_revision: Union[str, None] = '978c23c8472f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index('ix_refresh_tokens_user_id', 'refresh_tokens', ['user_id'], unique=False)
    op.create_index('ix_household_invitations_organization_id', 'household_invitations', ['organization_id'], unique=False)
    op.create_index('ix_household_invitations_invited_by_user_id', 'household_invitations', ['invited_by_user_id'], unique=False)
    op.create_index('ix_account_shares_account_id', 'account_shares', ['account_id'], unique=False)
    op.create_index('ix_account_shares_shared_with_user_id', 'account_shares', ['shared_with_user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_account_shares_shared_with_user_id', table_name='account_shares')
    op.drop_index('ix_account_shares_account_id', table_name='account_shares')
    op.drop_index('ix_household_invitations_invited_by_user_id', table_name='household_invitations')
    op.drop_index('ix_household_invitations_organization_id', table_name='household_invitations')
    op.drop_index('ix_refresh_tokens_user_id', table_name='refresh_tokens')
