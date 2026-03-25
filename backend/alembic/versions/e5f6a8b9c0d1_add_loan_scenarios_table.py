"""add loan scenarios table

Revision ID: e5f6a8b9c0d1
Revises: d4e5f6a8b9c0
Create Date: 2026-03-24 00:00:00.000000

Creates loan_scenarios table for storing loan origination and comparison
scenarios per user/organization.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e5f6a8b9c0d1'
down_revision: Union[str, None] = 'd4e5f6a8b9c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'loan_scenarios',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('scenario_name', sa.String(255), nullable=False),
        sa.Column('loan_type', sa.String(50), nullable=False),
        sa.Column('loan_amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('interest_rate', sa.Numeric(5, 3), nullable=False),
        sa.Column('term_months', sa.Integer(), nullable=False),
        sa.Column('monthly_payment', sa.Numeric(10, 2), nullable=True),
        sa.Column('dti_impact_pct', sa.Numeric(5, 2), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('loan_scenarios')
