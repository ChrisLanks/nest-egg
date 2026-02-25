"""Retirement planning models."""

import enum
import uuid
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.utils.datetime_utils import utc_now_lambda


class LifeEventCategory(str, enum.Enum):
    """Categories of life events for retirement planning."""

    CHILD = "child"
    PET = "pet"
    HOME_PURCHASE = "home_purchase"
    HOME_DOWNSIZE = "home_downsize"
    CAREER_CHANGE = "career_change"
    BONUS = "bonus"
    HEALTHCARE = "healthcare"
    TRAVEL = "travel"
    VEHICLE = "vehicle"
    ELDER_CARE = "elder_care"
    CUSTOM = "custom"


class WithdrawalStrategy(str, enum.Enum):
    """Withdrawal ordering strategies for retirement."""

    TAX_OPTIMIZED = "tax_optimized"
    SIMPLE_RATE = "simple_rate"
    PRO_RATA = "pro_rata"


class RetirementScenario(Base):
    """A saved retirement planning scenario with all configuration."""

    __tablename__ = "retirement_scenarios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Identity
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False, nullable=False)

    # Core assumptions
    retirement_age = Column(Integer, nullable=False)
    life_expectancy = Column(Integer, default=95, nullable=False)
    current_annual_income = Column(Numeric(15, 2), nullable=True)
    annual_spending_retirement = Column(Numeric(15, 2), nullable=False)

    # Return assumptions (percentages)
    pre_retirement_return = Column(Numeric(5, 2), default=Decimal("7.00"), nullable=False)
    post_retirement_return = Column(Numeric(5, 2), default=Decimal("5.00"), nullable=False)
    volatility = Column(Numeric(5, 2), default=Decimal("15.00"), nullable=False)
    inflation_rate = Column(Numeric(5, 2), default=Decimal("3.00"), nullable=False)
    medical_inflation_rate = Column(Numeric(5, 2), default=Decimal("6.00"), nullable=False)

    # Social Security
    social_security_monthly = Column(Numeric(10, 2), nullable=True)
    social_security_start_age = Column(Integer, default=67, nullable=True)
    use_estimated_pia = Column(Boolean, default=True, nullable=False)
    spouse_social_security_monthly = Column(Numeric(10, 2), nullable=True)
    spouse_social_security_start_age = Column(Integer, nullable=True)

    # Withdrawal strategy
    withdrawal_strategy = Column(
        SQLEnum(WithdrawalStrategy), default=WithdrawalStrategy.TAX_OPTIMIZED, nullable=False
    )
    withdrawal_rate = Column(Numeric(5, 2), default=Decimal("4.00"), nullable=False)

    # Tax assumptions (percentages)
    federal_tax_rate = Column(Numeric(5, 2), default=Decimal("22.00"), nullable=False)
    state_tax_rate = Column(Numeric(5, 2), default=Decimal("5.00"), nullable=False)
    capital_gains_rate = Column(Numeric(5, 2), default=Decimal("15.00"), nullable=False)

    # Healthcare cost overrides (annual, nullable = use estimate)
    healthcare_pre65_override = Column(Numeric(10, 2), nullable=True)
    healthcare_medicare_override = Column(Numeric(10, 2), nullable=True)
    healthcare_ltc_override = Column(Numeric(10, 2), nullable=True)

    # Simulation config
    num_simulations = Column(Integer, default=1000, nullable=False)

    # Sharing within household
    is_shared = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)
    updated_at = Column(DateTime, default=utc_now_lambda, onupdate=utc_now_lambda, nullable=False)

    # Relationships
    life_events = relationship(
        "LifeEvent",
        back_populates="scenario",
        cascade="all, delete-orphan",
        order_by="LifeEvent.start_age",
    )
    simulation_results = relationship(
        "RetirementSimulationResult",
        back_populates="scenario",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_retirement_scenario_org_user", "organization_id", "user_id"),
    )


class LifeEvent(Base):
    """A life event within a retirement scenario (kids, home, healthcare, etc.)."""

    __tablename__ = "life_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scenario_id = Column(
        UUID(as_uuid=True),
        ForeignKey("retirement_scenarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Event details
    name = Column(String(200), nullable=False)
    category = Column(SQLEnum(LifeEventCategory), nullable=False)

    # Timing (age-based)
    start_age = Column(Integer, nullable=False)
    end_age = Column(Integer, nullable=True)  # NULL = one-time event

    # Cost (today's dollars)
    annual_cost = Column(Numeric(15, 2), nullable=True)  # Recurring annual cost
    one_time_cost = Column(Numeric(15, 2), nullable=True)  # One-time cost at start_age
    income_change = Column(Numeric(15, 2), nullable=True)  # Annual income delta (+/-)

    # Inflation treatment
    use_medical_inflation = Column(Boolean, default=False, nullable=False)
    custom_inflation_rate = Column(Numeric(5, 2), nullable=True)

    # Preset metadata
    is_preset = Column(Boolean, default=False, nullable=False)
    preset_key = Column(String(100), nullable=True)

    # Ordering
    sort_order = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)
    updated_at = Column(DateTime, default=utc_now_lambda, onupdate=utc_now_lambda, nullable=False)

    # Relationships
    scenario = relationship("RetirementScenario", back_populates="life_events")


class RetirementSimulationResult(Base):
    """Cached Monte Carlo simulation results for a retirement scenario."""

    __tablename__ = "retirement_simulation_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scenario_id = Column(
        UUID(as_uuid=True),
        ForeignKey("retirement_scenarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Simulation metadata
    computed_at = Column(DateTime, nullable=False, default=utc_now_lambda)
    scenario_hash = Column(String(64), nullable=False)
    num_simulations = Column(Integer, nullable=False)
    compute_time_ms = Column(Integer, nullable=True)

    # Summary stats
    success_rate = Column(Numeric(5, 2), nullable=False)
    readiness_score = Column(Integer, nullable=False)
    median_portfolio_at_retirement = Column(Numeric(15, 2), nullable=True)
    median_portfolio_at_end = Column(Numeric(15, 2), nullable=True)
    median_depletion_age = Column(Integer, nullable=True)

    # Social Security
    estimated_pia = Column(Numeric(10, 2), nullable=True)

    # Year-by-year projections (JSON)
    projections_json = Column(Text, nullable=False)

    # Withdrawal strategy comparison (JSON)
    withdrawal_comparison_json = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=utc_now_lambda, nullable=False)

    # Relationships
    scenario = relationship("RetirementScenario", back_populates="simulation_results")

    __table_args__ = (
        Index("ix_sim_result_scenario_date", "scenario_id", "computed_at"),
    )
