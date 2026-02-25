"""Add retirement planning tables.

Revision ID: q9r0s1t2u3v4
Revises: p8q9r0s1t2u3
Create Date: 2026-02-24

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "q9r0s1t2u3v4"
down_revision = "p8q9r0s1t2u3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create PostgreSQL enums first (requires autocommit_block).
    # Use DO $$ ... $$ block to handle pre-existing types gracefully.
    with op.get_context().autocommit_block():
        op.execute("""
            DO $$ BEGIN
                CREATE TYPE lifeeventcategory AS ENUM
                    ('CHILD', 'PET', 'HOME_PURCHASE', 'HOME_DOWNSIZE', 'CAREER_CHANGE',
                     'BONUS', 'HEALTHCARE', 'TRAVEL', 'VEHICLE', 'ELDER_CARE', 'CUSTOM');
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$
        """)
        op.execute("""
            DO $$ BEGIN
                CREATE TYPE withdrawalstrategy AS ENUM
                    ('TAX_OPTIMIZED', 'SIMPLE_RATE', 'PRO_RATA');
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$
        """)

    # Create retirement_scenarios table
    op.create_table(
        "retirement_scenarios",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        # Core assumptions
        sa.Column("retirement_age", sa.Integer(), nullable=False),
        sa.Column("life_expectancy", sa.Integer(), nullable=False, server_default="95"),
        sa.Column("current_annual_income", sa.Numeric(15, 2), nullable=True),
        sa.Column("annual_spending_retirement", sa.Numeric(15, 2), nullable=False),
        # Return assumptions
        sa.Column("pre_retirement_return", sa.Numeric(5, 2), nullable=False, server_default="7.00"),
        sa.Column("post_retirement_return", sa.Numeric(5, 2), nullable=False, server_default="5.00"),
        sa.Column("volatility", sa.Numeric(5, 2), nullable=False, server_default="15.00"),
        sa.Column("inflation_rate", sa.Numeric(5, 2), nullable=False, server_default="3.00"),
        sa.Column("medical_inflation_rate", sa.Numeric(5, 2), nullable=False, server_default="6.00"),
        # Social Security
        sa.Column("social_security_monthly", sa.Numeric(10, 2), nullable=True),
        sa.Column("social_security_start_age", sa.Integer(), nullable=True, server_default="67"),
        sa.Column("use_estimated_pia", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("spouse_social_security_monthly", sa.Numeric(10, 2), nullable=True),
        sa.Column("spouse_social_security_start_age", sa.Integer(), nullable=True),
        # Withdrawal strategy
        sa.Column(
            "withdrawal_strategy",
            postgresql.ENUM("TAX_OPTIMIZED", "SIMPLE_RATE", "PRO_RATA", name="withdrawalstrategy", create_type=False),
            nullable=False,
            server_default="TAX_OPTIMIZED",
        ),
        sa.Column("withdrawal_rate", sa.Numeric(5, 2), nullable=False, server_default="4.00"),
        # Tax assumptions
        sa.Column("federal_tax_rate", sa.Numeric(5, 2), nullable=False, server_default="22.00"),
        sa.Column("state_tax_rate", sa.Numeric(5, 2), nullable=False, server_default="5.00"),
        sa.Column("capital_gains_rate", sa.Numeric(5, 2), nullable=False, server_default="15.00"),
        # Config
        sa.Column("num_simulations", sa.Integer(), nullable=False, server_default="1000"),
        sa.Column("is_shared", sa.Boolean(), nullable=False, server_default="true"),
        # Timestamps
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_retirement_scenarios_organization_id", "retirement_scenarios", ["organization_id"])
    op.create_index("ix_retirement_scenarios_user_id", "retirement_scenarios", ["user_id"])
    op.create_index("ix_retirement_scenario_org_user", "retirement_scenarios", ["organization_id", "user_id"])

    # Create life_events table
    op.create_table(
        "life_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("scenario_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column(
            "category",
            postgresql.ENUM(
                "CHILD", "PET", "HOME_PURCHASE", "HOME_DOWNSIZE", "CAREER_CHANGE",
                "BONUS", "HEALTHCARE", "TRAVEL", "VEHICLE", "ELDER_CARE", "CUSTOM",
                name="lifeeventcategory", create_type=False,
            ),
            nullable=False,
        ),
        # Timing
        sa.Column("start_age", sa.Integer(), nullable=False),
        sa.Column("end_age", sa.Integer(), nullable=True),
        # Cost
        sa.Column("annual_cost", sa.Numeric(15, 2), nullable=True),
        sa.Column("one_time_cost", sa.Numeric(15, 2), nullable=True),
        sa.Column("income_change", sa.Numeric(15, 2), nullable=True),
        # Inflation
        sa.Column("use_medical_inflation", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("custom_inflation_rate", sa.Numeric(5, 2), nullable=True),
        # Preset
        sa.Column("is_preset", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("preset_key", sa.String(100), nullable=True),
        # Ordering
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        # Timestamps
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["scenario_id"], ["retirement_scenarios.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_life_events_scenario_id", "life_events", ["scenario_id"])

    # Create retirement_simulation_results table
    op.create_table(
        "retirement_simulation_results",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("scenario_id", sa.UUID(), nullable=False),
        # Simulation metadata
        sa.Column("computed_at", sa.DateTime(), nullable=False),
        sa.Column("scenario_hash", sa.String(64), nullable=False),
        sa.Column("num_simulations", sa.Integer(), nullable=False),
        sa.Column("compute_time_ms", sa.Integer(), nullable=True),
        # Summary stats
        sa.Column("success_rate", sa.Numeric(5, 2), nullable=False),
        sa.Column("readiness_score", sa.Integer(), nullable=False),
        sa.Column("median_portfolio_at_retirement", sa.Numeric(15, 2), nullable=True),
        sa.Column("median_portfolio_at_end", sa.Numeric(15, 2), nullable=True),
        sa.Column("median_depletion_age", sa.Integer(), nullable=True),
        # Social Security
        sa.Column("estimated_pia", sa.Numeric(10, 2), nullable=True),
        # Projections
        sa.Column("projections_json", sa.Text(), nullable=False),
        sa.Column("withdrawal_comparison_json", sa.Text(), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(), nullable=False),
        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["scenario_id"], ["retirement_scenarios.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_sim_results_scenario_id", "retirement_simulation_results", ["scenario_id"])
    op.create_index(
        "ix_sim_result_scenario_date", "retirement_simulation_results", ["scenario_id", "computed_at"]
    )


def downgrade() -> None:
    op.drop_table("retirement_simulation_results")
    op.drop_table("life_events")
    op.drop_table("retirement_scenarios")
    with op.get_context().autocommit_block():
        op.execute("DROP TYPE IF EXISTS withdrawalstrategy")
        op.execute("DROP TYPE IF EXISTS lifeeventcategory")
