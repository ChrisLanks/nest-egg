"""Retirement planning schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.retirement import LifeEventCategory, WithdrawalStrategy


# --- Life Events ---


class LifeEventCreate(BaseModel):
    """Schema for creating a life event."""

    name: str = Field(max_length=200)
    category: LifeEventCategory
    start_age: int = Field(ge=0, le=120)
    end_age: Optional[int] = Field(None, ge=0, le=120)
    annual_cost: Optional[Decimal] = None
    one_time_cost: Optional[Decimal] = None
    income_change: Optional[Decimal] = None
    use_medical_inflation: bool = False
    custom_inflation_rate: Optional[Decimal] = Field(None, ge=0, le=50)
    sort_order: int = 0


class LifeEventUpdate(BaseModel):
    """Schema for updating a life event."""

    name: Optional[str] = Field(None, max_length=200)
    category: Optional[LifeEventCategory] = None
    start_age: Optional[int] = Field(None, ge=0, le=120)
    end_age: Optional[int] = Field(None, ge=0, le=120)
    annual_cost: Optional[Decimal] = None
    one_time_cost: Optional[Decimal] = None
    income_change: Optional[Decimal] = None
    use_medical_inflation: Optional[bool] = None
    custom_inflation_rate: Optional[Decimal] = Field(None, ge=0, le=50)
    sort_order: Optional[int] = None


class LifeEventResponse(BaseModel):
    """Schema for life event response."""

    id: UUID
    scenario_id: UUID
    name: str
    category: LifeEventCategory
    start_age: int
    end_age: Optional[int]
    annual_cost: Optional[Decimal]
    one_time_cost: Optional[Decimal]
    income_change: Optional[Decimal]
    use_medical_inflation: bool
    custom_inflation_rate: Optional[Decimal]
    is_preset: bool
    preset_key: Optional[str]
    sort_order: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LifeEventPresetRequest(BaseModel):
    """Schema for adding a life event from a preset."""

    preset_key: str
    start_age: Optional[int] = None  # Override default start age


class LifeEventPreset(BaseModel):
    """Schema for a life event preset definition."""

    key: str
    name: str
    category: LifeEventCategory
    description: str
    annual_cost: Optional[Decimal] = None
    one_time_cost: Optional[Decimal] = None
    income_change: Optional[Decimal] = None
    duration_years: Optional[int] = None
    use_medical_inflation: bool = False
    icon: str = "event"


# --- Scenarios ---


class RetirementScenarioCreate(BaseModel):
    """Schema for creating a retirement scenario."""

    name: str = Field(max_length=200)
    description: Optional[str] = None
    retirement_age: int = Field(ge=15, le=95)
    life_expectancy: int = Field(default=95, ge=15, le=120)
    current_annual_income: Optional[Decimal] = None
    annual_spending_retirement: Decimal = Field(gt=0)

    # Return assumptions
    pre_retirement_return: Decimal = Field(default=Decimal("7.00"), ge=0, le=30)
    post_retirement_return: Decimal = Field(default=Decimal("5.00"), ge=0, le=30)
    volatility: Decimal = Field(default=Decimal("15.00"), ge=0, le=50)
    inflation_rate: Decimal = Field(default=Decimal("3.00"), ge=0, le=20)
    medical_inflation_rate: Decimal = Field(default=Decimal("6.00"), ge=0, le=20)

    # Social Security
    social_security_monthly: Optional[Decimal] = None
    social_security_start_age: Optional[int] = Field(default=67, ge=62, le=70)
    use_estimated_pia: bool = True
    spouse_social_security_monthly: Optional[Decimal] = None
    spouse_social_security_start_age: Optional[int] = Field(None, ge=62, le=70)

    # Withdrawal
    withdrawal_strategy: WithdrawalStrategy = WithdrawalStrategy.TAX_OPTIMIZED
    withdrawal_rate: Decimal = Field(default=Decimal("4.00"), ge=0, le=20)

    # Tax
    federal_tax_rate: Decimal = Field(default=Decimal("22.00"), ge=0, le=50)
    state_tax_rate: Decimal = Field(default=Decimal("5.00"), ge=0, le=20)
    capital_gains_rate: Decimal = Field(default=Decimal("15.00"), ge=0, le=30)

    # Healthcare cost overrides (annual, None = use estimate)
    healthcare_pre65_override: Optional[Decimal] = Field(None, ge=0)
    healthcare_medicare_override: Optional[Decimal] = Field(None, ge=0)
    healthcare_ltc_override: Optional[Decimal] = Field(None, ge=0)

    # Config
    num_simulations: int = Field(default=1000, ge=100, le=10000)
    is_shared: bool = True


class RetirementScenarioUpdate(BaseModel):
    """Schema for updating a retirement scenario. All fields optional."""

    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    retirement_age: Optional[int] = Field(None, ge=15, le=95)
    life_expectancy: Optional[int] = Field(None, ge=15, le=120)
    current_annual_income: Optional[Decimal] = None
    annual_spending_retirement: Optional[Decimal] = Field(None, gt=0)

    pre_retirement_return: Optional[Decimal] = Field(None, ge=0, le=30)
    post_retirement_return: Optional[Decimal] = Field(None, ge=0, le=30)
    volatility: Optional[Decimal] = Field(None, ge=0, le=50)
    inflation_rate: Optional[Decimal] = Field(None, ge=0, le=20)
    medical_inflation_rate: Optional[Decimal] = Field(None, ge=0, le=20)

    social_security_monthly: Optional[Decimal] = None
    social_security_start_age: Optional[int] = Field(None, ge=62, le=70)
    use_estimated_pia: Optional[bool] = None
    spouse_social_security_monthly: Optional[Decimal] = None
    spouse_social_security_start_age: Optional[int] = Field(None, ge=62, le=70)

    withdrawal_strategy: Optional[WithdrawalStrategy] = None
    withdrawal_rate: Optional[Decimal] = Field(None, ge=0, le=20)

    federal_tax_rate: Optional[Decimal] = Field(None, ge=0, le=50)
    state_tax_rate: Optional[Decimal] = Field(None, ge=0, le=20)
    capital_gains_rate: Optional[Decimal] = Field(None, ge=0, le=30)

    healthcare_pre65_override: Optional[Decimal] = Field(None, ge=0)
    healthcare_medicare_override: Optional[Decimal] = Field(None, ge=0)
    healthcare_ltc_override: Optional[Decimal] = Field(None, ge=0)

    num_simulations: Optional[int] = Field(None, ge=100, le=10000)
    is_shared: Optional[bool] = None


class RetirementScenarioResponse(BaseModel):
    """Full scenario response with life events."""

    id: UUID
    organization_id: UUID
    user_id: UUID
    name: str
    description: Optional[str]
    is_default: bool

    retirement_age: int
    life_expectancy: int
    current_annual_income: Optional[Decimal]
    annual_spending_retirement: Decimal

    pre_retirement_return: Decimal
    post_retirement_return: Decimal
    volatility: Decimal
    inflation_rate: Decimal
    medical_inflation_rate: Decimal

    social_security_monthly: Optional[Decimal]
    social_security_start_age: Optional[int]
    use_estimated_pia: bool
    spouse_social_security_monthly: Optional[Decimal]
    spouse_social_security_start_age: Optional[int]

    withdrawal_strategy: WithdrawalStrategy
    withdrawal_rate: Decimal

    federal_tax_rate: Decimal
    state_tax_rate: Decimal
    capital_gains_rate: Decimal

    healthcare_pre65_override: Optional[Decimal] = None
    healthcare_medicare_override: Optional[Decimal] = None
    healthcare_ltc_override: Optional[Decimal] = None

    num_simulations: int
    is_shared: bool

    life_events: List[LifeEventResponse] = []

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RetirementScenarioSummary(BaseModel):
    """Lightweight summary for list view."""

    id: UUID
    name: str
    retirement_age: int
    is_default: bool
    readiness_score: Optional[int] = None
    success_rate: Optional[float] = None
    updated_at: datetime

    class Config:
        from_attributes = True


# --- Simulation Results ---


class ProjectionDataPoint(BaseModel):
    """A single year's projection data."""

    age: int
    p10: float
    p25: float
    p50: float
    p75: float
    p90: float
    depletion_pct: float
    income_sources: Optional[Dict[str, float]] = None


class SimulationResultResponse(BaseModel):
    """Simulation result response."""

    id: UUID
    scenario_id: UUID
    computed_at: datetime
    num_simulations: int
    compute_time_ms: Optional[int]

    success_rate: float
    readiness_score: int
    median_portfolio_at_retirement: Optional[float]
    median_portfolio_at_end: Optional[float]
    median_depletion_age: Optional[int]
    estimated_pia: Optional[float]

    projections: List[ProjectionDataPoint]
    withdrawal_comparison: Optional[Dict] = None

    class Config:
        from_attributes = True


# --- Quick Simulate (no DB save) ---


class QuickSimulationRequest(BaseModel):
    """Lightweight request for slider-driven exploration."""

    current_portfolio: Decimal = Field(gt=0)
    annual_contributions: Decimal = Field(default=Decimal("0"), ge=0)
    retirement_age: int = Field(ge=15, le=95)
    current_age: int = Field(ge=18, le=100)
    life_expectancy: int = Field(default=95, ge=15, le=120)
    annual_spending: Decimal = Field(gt=0)
    pre_retirement_return: float = Field(default=7.0, ge=0, le=30)
    post_retirement_return: float = Field(default=5.0, ge=0, le=30)
    volatility: float = Field(default=15.0, ge=0, le=50)
    inflation_rate: float = Field(default=3.0, ge=0, le=20)
    withdrawal_rate: float = Field(default=4.0, ge=0, le=20)
    social_security_monthly: Optional[float] = None
    social_security_start_age: int = Field(default=67, ge=62, le=70)


class QuickSimulationResponse(BaseModel):
    """Lightweight simulation response for sliders."""

    success_rate: float
    readiness_score: int
    projections: List[ProjectionDataPoint]
    median_depletion_age: Optional[int] = None


# --- Social Security ---


class SocialSecurityEstimateResponse(BaseModel):
    """Social Security benefit estimate."""

    estimated_pia: float
    monthly_at_62: float
    monthly_at_fra: float
    monthly_at_70: float
    fra_age: float
    claiming_age: int
    monthly_benefit: float


# --- Healthcare ---


class HealthcareCostBreakdown(BaseModel):
    """Annual healthcare cost breakdown at a specific age."""

    age: int
    aca_insurance: float = 0
    medicare_part_b: float = 0
    medicare_part_d: float = 0
    medigap: float = 0
    irmaa_surcharge: float = 0
    out_of_pocket: float = 0
    long_term_care: float = 0
    total: float = 0


class HealthcareCostEstimateResponse(BaseModel):
    """Healthcare cost estimate response."""

    pre_65_annual: float
    medicare_annual: float
    ltc_annual: float
    total_lifetime: float
    sample_ages: List[HealthcareCostBreakdown]


# --- Scenario Comparison ---


class ScenarioComparisonRequest(BaseModel):
    """Request to compare multiple scenarios."""

    scenario_ids: List[UUID] = Field(min_length=2, max_length=4)


class ScenarioComparisonItem(BaseModel):
    """Single scenario in a comparison."""

    scenario_id: UUID
    scenario_name: str
    retirement_age: int
    readiness_score: int
    success_rate: float
    median_portfolio_at_end: Optional[float]
    projections: List[ProjectionDataPoint]


class ScenarioComparisonResponse(BaseModel):
    """Response for comparing multiple scenarios."""

    scenarios: List[ScenarioComparisonItem]


# --- Account Data for Retirement Page ---


class RetirementAccountItem(BaseModel):
    """Individual account in the portfolio."""

    name: str
    balance: float
    bucket: str  # "pre_tax", "roth", "taxable", "hsa", "cash"
    account_type: str


class RetirementAccountDataResponse(BaseModel):
    """Current account data summary for the retirement planner."""

    total_portfolio: float
    taxable_balance: float
    pre_tax_balance: float
    roth_balance: float
    hsa_balance: float
    cash_balance: float = 0
    pension_monthly: float
    annual_contributions: float
    employer_match_annual: float
    annual_income: float = 0
    accounts: List[RetirementAccountItem] = []
