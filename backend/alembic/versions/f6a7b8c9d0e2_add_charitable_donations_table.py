"""add charitable donations table

Revision ID: f6a7b8c9d0e2
Revises: e5f6a8b9c0d1
Create Date: 2026-03-24 00:00:00.000000

Creates charitable_donations table for tracking donations and optimizing
QCD, bunching, and appreciated security donation strategies.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f6a7b8c9d0e2'
down_revision: Union[str, None] = 'e5f6a8b9c0d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'charitable_donations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('donation_date', sa.Date(), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('organization_name', sa.String(255), nullable=False),
        sa.Column('donation_type', sa.String(50), nullable=False),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('accounts.id'), nullable=True),
        sa.Column('security_symbol', sa.String(20), nullable=True),
        sa.Column('cost_basis', sa.Numeric(12, 2), nullable=True),
        sa.Column('is_bunched', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('tax_year', sa.Integer(), nullable=False, index=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('charitable_donations')
