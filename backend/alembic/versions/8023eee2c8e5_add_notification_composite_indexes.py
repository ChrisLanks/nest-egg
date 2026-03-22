"""add_notification_composite_indexes

Revision ID: 8023eee2c8e5
Revises: a1b2c3d4e5f8
Create Date: 2026-03-21 21:57:52.387879

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8023eee2c8e5'
down_revision: Union[str, None] = 'a1b2c3d4e5f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index('ix_notifications_org_created', 'notifications', ['organization_id', 'created_at'], unique=False)
    op.create_index('ix_notifications_org_dismissed', 'notifications', ['organization_id', 'is_dismissed'], unique=False)
    op.create_index('ix_notifications_user_created', 'notifications', ['user_id', 'created_at'], unique=False)
    op.create_index('ix_notifications_user_is_read', 'notifications', ['user_id', 'is_read'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_notifications_user_is_read', table_name='notifications')
    op.drop_index('ix_notifications_user_created', table_name='notifications')
    op.drop_index('ix_notifications_org_dismissed', table_name='notifications')
    op.drop_index('ix_notifications_org_created', table_name='notifications')


def _unused_downgrade_recreate_retired_tables() -> None:
    """Kept for reference only — these tables were dropped separately and are not restored here."""
    op.create_table('life_events',
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('scenario_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('name', sa.VARCHAR(length=200), autoincrement=False, nullable=False),
    sa.Column('category', postgresql.ENUM('CHILD', 'PET', 'HOME_PURCHASE', 'HOME_DOWNSIZE', 'CAREER_CHANGE', 'BONUS', 'HEALTHCARE', 'TRAVEL', 'VEHICLE', 'ELDER_CARE', 'WEDDING', 'DIVORCE', 'NEW_BABY', 'CUSTOM', name='lifeeventcategory'), autoincrement=False, nullable=False),
    sa.Column('start_age', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('end_age', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('annual_cost', sa.NUMERIC(precision=15, scale=2), autoincrement=False, nullable=True),
    sa.Column('one_time_cost', sa.NUMERIC(precision=15, scale=2), autoincrement=False, nullable=True),
    sa.Column('income_change', sa.NUMERIC(precision=15, scale=2), autoincrement=False, nullable=True),
    sa.Column('use_medical_inflation', sa.BOOLEAN(), autoincrement=False, nullable=False),
    sa.Column('custom_inflation_rate', sa.NUMERIC(precision=5, scale=2), autoincrement=False, nullable=True),
    sa.Column('is_preset', sa.BOOLEAN(), autoincrement=False, nullable=False),
    sa.Column('preset_key', sa.VARCHAR(length=100), autoincrement=False, nullable=True),
    sa.Column('sort_order', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['scenario_id'], ['retirement_scenarios.id'], name='life_events_scenario_id_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='life_events_pkey')
    )
    op.create_index('ix_life_events_scenario_id', 'life_events', ['scenario_id'], unique=False)
    op.create_table('retirement_scenarios',
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('organization_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('user_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('name', sa.VARCHAR(length=200), autoincrement=False, nullable=False),
    sa.Column('description', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('is_default', sa.BOOLEAN(), autoincrement=False, nullable=False),
    sa.Column('retirement_age', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('life_expectancy', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('current_annual_income', sa.NUMERIC(precision=15, scale=2), autoincrement=False, nullable=True),
    sa.Column('annual_spending_retirement', sa.NUMERIC(precision=15, scale=2), autoincrement=False, nullable=False),
    sa.Column('pre_retirement_return', sa.NUMERIC(precision=5, scale=2), autoincrement=False, nullable=False),
    sa.Column('post_retirement_return', sa.NUMERIC(precision=5, scale=2), autoincrement=False, nullable=False),
    sa.Column('volatility', sa.NUMERIC(precision=5, scale=2), autoincrement=False, nullable=False),
    sa.Column('inflation_rate', sa.NUMERIC(precision=5, scale=2), autoincrement=False, nullable=False),
    sa.Column('medical_inflation_rate', sa.NUMERIC(precision=5, scale=2), autoincrement=False, nullable=False),
    sa.Column('social_security_monthly', sa.NUMERIC(precision=10, scale=2), autoincrement=False, nullable=True),
    sa.Column('social_security_start_age', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('use_estimated_pia', sa.BOOLEAN(), autoincrement=False, nullable=False),
    sa.Column('spouse_social_security_monthly', sa.NUMERIC(precision=10, scale=2), autoincrement=False, nullable=True),
    sa.Column('spouse_social_security_start_age', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('withdrawal_strategy', postgresql.ENUM('TAX_OPTIMIZED', 'SIMPLE_RATE', 'PRO_RATA', name='withdrawalstrategy'), autoincrement=False, nullable=False),
    sa.Column('withdrawal_rate', sa.NUMERIC(precision=5, scale=2), autoincrement=False, nullable=False),
    sa.Column('federal_tax_rate', sa.NUMERIC(precision=5, scale=2), autoincrement=False, nullable=False),
    sa.Column('state_tax_rate', sa.NUMERIC(precision=5, scale=2), autoincrement=False, nullable=False),
    sa.Column('capital_gains_rate', sa.NUMERIC(precision=5, scale=2), autoincrement=False, nullable=False),
    sa.Column('healthcare_pre65_override', sa.NUMERIC(precision=10, scale=2), autoincrement=False, nullable=True),
    sa.Column('healthcare_medicare_override', sa.NUMERIC(precision=10, scale=2), autoincrement=False, nullable=True),
    sa.Column('healthcare_ltc_override', sa.NUMERIC(precision=10, scale=2), autoincrement=False, nullable=True),
    sa.Column('num_simulations', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('inflation_adjusted', sa.BOOLEAN(), server_default=sa.text('true'), autoincrement=False, nullable=False),
    sa.Column('distribution_type', postgresql.ENUM('NORMAL', 'LOG_NORMAL', 'HISTORICAL_BOOTSTRAP', name='distributiontype'), server_default=sa.text("'NORMAL'::distributiontype"), autoincrement=False, nullable=False),
    sa.Column('is_shared', sa.BOOLEAN(), autoincrement=False, nullable=False),
    sa.Column('include_all_members', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=False),
    sa.Column('household_member_hash', sa.VARCHAR(length=64), autoincrement=False, nullable=True),
    sa.Column('household_member_ids', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('spending_phases', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('is_archived', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=False),
    sa.Column('archived_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('archived_reason', sa.VARCHAR(length=200), autoincrement=False, nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name='retirement_scenarios_organization_id_fkey', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='retirement_scenarios_user_id_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='retirement_scenarios_pkey'),
    postgresql_ignore_search_path=False
    )
    op.create_index('ix_retirement_scenarios_user_id', 'retirement_scenarios', ['user_id'], unique=False)
    op.create_index('ix_retirement_scenarios_organization_id', 'retirement_scenarios', ['organization_id'], unique=False)
    op.create_index('ix_retirement_scenario_org_user', 'retirement_scenarios', ['organization_id', 'user_id'], unique=False)
    op.create_table('retirement_simulation_results',
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('scenario_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('computed_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('scenario_hash', sa.VARCHAR(length=64), autoincrement=False, nullable=False),
    sa.Column('num_simulations', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('compute_time_ms', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('success_rate', sa.NUMERIC(precision=5, scale=2), autoincrement=False, nullable=False),
    sa.Column('readiness_score', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('median_portfolio_at_retirement', sa.NUMERIC(precision=15, scale=2), autoincrement=False, nullable=True),
    sa.Column('median_portfolio_at_end', sa.NUMERIC(precision=15, scale=2), autoincrement=False, nullable=True),
    sa.Column('median_depletion_age', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('estimated_pia', sa.NUMERIC(precision=10, scale=2), autoincrement=False, nullable=True),
    sa.Column('projections_json', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('withdrawal_comparison_json', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['scenario_id'], ['retirement_scenarios.id'], name='retirement_simulation_results_scenario_id_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='retirement_simulation_results_pkey')
    )
    op.create_index('ix_sim_result_scenario_date', 'retirement_simulation_results', ['scenario_id', 'computed_at'], unique=False)
    op.create_index('ix_retirement_simulation_results_scenario_id', 'retirement_simulation_results', ['scenario_id'], unique=False)
    op.create_table('budget_suggestions',
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('organization_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('user_id', sa.UUID(), autoincrement=False, nullable=True),
    sa.Column('category_id', sa.UUID(), autoincrement=False, nullable=True),
    sa.Column('category_primary_raw', sa.VARCHAR(length=200), autoincrement=False, nullable=True),
    sa.Column('category_name', sa.VARCHAR(length=200), autoincrement=False, nullable=False),
    sa.Column('suggested_amount', sa.NUMERIC(precision=15, scale=2), autoincrement=False, nullable=False),
    sa.Column('suggested_period', sa.VARCHAR(length=20), autoincrement=False, nullable=False),
    sa.Column('avg_monthly_spend', sa.NUMERIC(precision=15, scale=2), autoincrement=False, nullable=False),
    sa.Column('total_spend', sa.NUMERIC(precision=15, scale=2), autoincrement=False, nullable=False),
    sa.Column('month_count', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('transaction_count', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('generated_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['category_id'], ['categories.id'], name='budget_suggestions_category_id_fkey', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name='budget_suggestions_organization_id_fkey', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='budget_suggestions_user_id_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='budget_suggestions_pkey')
    )
    op.create_index('ix_budget_suggestions_user_id', 'budget_suggestions', ['user_id'], unique=False)
    op.create_index('ix_budget_suggestions_organization_id', 'budget_suggestions', ['organization_id'], unique=False)
    op.create_index('ix_budget_suggestions_org_user', 'budget_suggestions', ['organization_id', 'user_id'], unique=False)
    op.create_index('ix_budget_suggestions_generated_at', 'budget_suggestions', ['generated_at'], unique=False)
    # ### end Alembic commands ###
