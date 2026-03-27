"""Add cash/espp account types, dependents, insurance policies, TLH records, SS benefit estimates

Revision ID: r62a1b2c3d4e5
Revises: 37e1d1767687
Create Date: 2026-03-27

Adds:
- 'cash' and 'espp' to accounttype enum
- 'policytype' and 'harveststatus' enums
- insurance_policies table
- dependents table
- tax_loss_harvest_records table
- ss_benefit_estimates table
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "r62a1b2c3d4e5"
down_revision: Union[str, None] = "37e1d1767687"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- Enum additions (cannot be inside explicit transaction for asyncpg) --
    op.execute("ALTER TYPE accounttype ADD VALUE IF NOT EXISTS 'cash'")
    op.execute("ALTER TYPE accounttype ADD VALUE IF NOT EXISTS 'espp'")

    # -- PolicyType enum --
    policytype = postgresql.ENUM(
        'term_life', 'whole_life', 'universal_life',
        'disability_short_term', 'disability_long_term',
        'umbrella', 'homeowners', 'renters', 'auto',
        'health', 'dental', 'vision', 'long_term_care', 'other',
        name='policytype',
        create_type=False,
    )
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE policytype AS ENUM ("
        "'term_life','whole_life','universal_life',"
        "'disability_short_term','disability_long_term',"
        "'umbrella','homeowners','renters','auto',"
        "'health','dental','vision','long_term_care','other'"
        "); EXCEPTION WHEN duplicate_object THEN null; END $$;"
    )

    # -- HarvestStatus enum --
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE harveststatus AS ENUM ("
        "'active_window','window_closed','wash_sale_triggered'"
        "); EXCEPTION WHEN duplicate_object THEN null; END $$;"
    )

    # -- insurance_policies table --
    op.create_table(
        'insurance_policies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('household_id', postgresql.UUID(as_uuid=True),
                   sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                   sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('policy_type', sa.Enum('term_life', 'whole_life', 'universal_life',
                   'disability_short_term', 'disability_long_term',
                   'umbrella', 'homeowners', 'renters', 'auto',
                   'health', 'dental', 'vision', 'long_term_care', 'other',
                   name='policytype', create_type=False), nullable=False),
        sa.Column('provider', sa.String(200), nullable=True),
        sa.Column('policy_number', sa.String(100), nullable=True),
        sa.Column('coverage_amount', sa.Numeric(15, 2), nullable=True),
        sa.Column('annual_premium', sa.Numeric(10, 2), nullable=True),
        sa.Column('monthly_premium', sa.Numeric(10, 2), nullable=True),
        sa.Column('deductible', sa.Numeric(10, 2), nullable=True),
        sa.Column('effective_date', sa.Date, nullable=True),
        sa.Column('expiration_date', sa.Date, nullable=True),
        sa.Column('beneficiary_name', sa.String(200), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('is_active', sa.Boolean, default=True, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )

    # -- dependents table --
    op.create_table(
        'dependents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('household_id', postgresql.UUID(as_uuid=True),
                   sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('date_of_birth', sa.Date, nullable=False),
        sa.Column('relationship', sa.String(50), nullable=False),
        sa.Column('expected_college_start_year', sa.Integer, nullable=True),
        sa.Column('expected_college_cost_annual', sa.Numeric(10, 2), nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )

    # -- tax_loss_harvest_records table --
    op.create_table(
        'tax_loss_harvest_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True),
                   sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                   sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('date_harvested', sa.Date, nullable=False),
        sa.Column('ticker_sold', sa.String(20), nullable=False),
        sa.Column('lot_acquisition_date', sa.Date, nullable=True),
        sa.Column('loss_amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('replacement_ticker', sa.String(20), nullable=True),
        sa.Column('wash_sale_window_end', sa.Date, nullable=False),
        sa.Column('status', sa.Enum('active_window', 'window_closed', 'wash_sale_triggered',
                   name='harveststatus', create_type=False), nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )

    # -- ss_benefit_estimates table --
    op.create_table(
        'ss_benefit_estimates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                   sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True, index=True),
        sa.Column('age_62_benefit', sa.Numeric(10, 2), nullable=True),
        sa.Column('age_67_benefit', sa.Numeric(10, 2), nullable=True),
        sa.Column('age_70_benefit', sa.Numeric(10, 2), nullable=True),
        sa.Column('as_of_year', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )


def downgrade() -> None:
    op.drop_table('ss_benefit_estimates')
    op.drop_table('tax_loss_harvest_records')
    op.drop_table('dependents')
    op.drop_table('insurance_policies')
    op.execute("DROP TYPE IF EXISTS harveststatus")
    op.execute("DROP TYPE IF EXISTS policytype")
    # Cannot remove enum values from accounttype in PostgreSQL
