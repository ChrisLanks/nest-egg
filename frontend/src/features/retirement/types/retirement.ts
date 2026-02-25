/**
 * TypeScript interfaces for retirement planning, matching backend schemas.
 */

export type LifeEventCategory =
  | 'child'
  | 'pet'
  | 'home_purchase'
  | 'home_downsize'
  | 'career_change'
  | 'bonus'
  | 'healthcare'
  | 'travel'
  | 'vehicle'
  | 'elder_care'
  | 'custom';

export type WithdrawalStrategy = 'tax_optimized' | 'simple_rate' | 'pro_rata';

// --- Life Events ---

export interface LifeEvent {
  id: string;
  scenario_id: string;
  name: string;
  category: LifeEventCategory;
  start_age: number;
  end_age: number | null;
  annual_cost: number | null;
  one_time_cost: number | null;
  income_change: number | null;
  use_medical_inflation: boolean;
  custom_inflation_rate: number | null;
  is_preset: boolean;
  preset_key: string | null;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface LifeEventCreate {
  name: string;
  category: LifeEventCategory;
  start_age: number;
  end_age?: number | null;
  annual_cost?: number | null;
  one_time_cost?: number | null;
  income_change?: number | null;
  use_medical_inflation?: boolean;
  custom_inflation_rate?: number | null;
  sort_order?: number;
}

// --- Scenarios ---

export interface RetirementScenario {
  id: string;
  organization_id: string;
  user_id: string;
  name: string;
  description: string | null;
  is_default: boolean;

  retirement_age: number;
  life_expectancy: number;
  current_annual_income: number | null;
  annual_spending_retirement: number;

  pre_retirement_return: number;
  post_retirement_return: number;
  volatility: number;
  inflation_rate: number;
  medical_inflation_rate: number;

  social_security_monthly: number | null;
  social_security_start_age: number | null;
  use_estimated_pia: boolean;
  spouse_social_security_monthly: number | null;
  spouse_social_security_start_age: number | null;

  withdrawal_strategy: WithdrawalStrategy;
  withdrawal_rate: number;

  federal_tax_rate: number;
  state_tax_rate: number;
  capital_gains_rate: number;

  healthcare_pre65_override: number | null;
  healthcare_medicare_override: number | null;
  healthcare_ltc_override: number | null;

  num_simulations: number;
  is_shared: boolean;

  life_events: LifeEvent[];

  created_at: string;
  updated_at: string;
}

export interface RetirementScenarioSummary {
  id: string;
  name: string;
  retirement_age: number;
  is_default: boolean;
  readiness_score: number | null;
  success_rate: number | null;
  updated_at: string;
}

export interface RetirementScenarioCreate {
  name: string;
  retirement_age: number;
  annual_spending_retirement: number;
  life_expectancy?: number;
  current_annual_income?: number;
  pre_retirement_return?: number;
  post_retirement_return?: number;
  volatility?: number;
  inflation_rate?: number;
  social_security_monthly?: number;
  social_security_start_age?: number;
  withdrawal_strategy?: WithdrawalStrategy;
  withdrawal_rate?: number;
}

// --- Simulation Results ---

export interface ProjectionDataPoint {
  age: number;
  p10: number;
  p25: number;
  p50: number;
  p75: number;
  p90: number;
  depletion_pct: number;
  income_sources?: Record<string, number>;
}

export interface SimulationResult {
  id: string;
  scenario_id: string;
  computed_at: string;
  num_simulations: number;
  compute_time_ms: number | null;

  success_rate: number;
  readiness_score: number;
  median_portfolio_at_retirement: number | null;
  median_portfolio_at_end: number | null;
  median_depletion_age: number | null;
  estimated_pia: number | null;

  projections: ProjectionDataPoint[];
  withdrawal_comparison: Record<string, unknown> | null;
}

// --- Quick Simulate ---

export interface QuickSimulationRequest {
  current_portfolio: number;
  annual_contributions: number;
  current_age: number;
  retirement_age: number;
  life_expectancy?: number;
  annual_spending: number;
  pre_retirement_return?: number;
  post_retirement_return?: number;
  volatility?: number;
  inflation_rate?: number;
  social_security_monthly?: number;
  social_security_start_age?: number;
}

export interface QuickSimulationResponse {
  success_rate: number;
  readiness_score: number;
  projections: ProjectionDataPoint[];
  median_depletion_age: number | null;
}

// --- Life Event Presets ---

export interface LifeEventPreset {
  key: string;
  name: string;
  category: LifeEventCategory;
  description: string;
  annual_cost: number | null;
  one_time_cost: number | null;
  income_change: number | null;
  duration_years: number | null;
  use_medical_inflation: boolean;
  icon: string;
}

// --- Social Security ---

export interface SocialSecurityEstimate {
  estimated_pia: number;
  monthly_at_62: number;
  monthly_at_fra: number;
  monthly_at_70: number;
  fra_age: number;
  claiming_age: number;
  monthly_benefit: number;
}

// --- Healthcare ---

export interface HealthcareCostBreakdown {
  age: number;
  aca_insurance: number;
  medicare_part_b: number;
  medicare_part_d: number;
  medigap: number;
  irmaa_surcharge: number;
  out_of_pocket: number;
  long_term_care: number;
  total: number;
}

export interface HealthcareCostEstimate {
  pre_65_annual: number;
  medicare_annual: number;
  ltc_annual: number;
  total_lifetime: number;
  sample_ages: HealthcareCostBreakdown[];
}

// --- Account Data ---

export interface RetirementAccountItem {
  name: string;
  balance: number;
  bucket: 'pre_tax' | 'roth' | 'taxable' | 'hsa' | 'cash';
  account_type: string;
}

export interface RetirementAccountData {
  total_portfolio: number;
  taxable_balance: number;
  pre_tax_balance: number;
  roth_balance: number;
  hsa_balance: number;
  cash_balance: number;
  pension_monthly: number;
  annual_contributions: number;
  employer_match_annual: number;
  annual_income: number;
  accounts: RetirementAccountItem[];
}

// --- Withdrawal Comparison ---

export interface WithdrawalStrategyResult {
  final_portfolio: number;
  total_taxes_paid: number;
  depleted_age: number | null;
  success: boolean;
}

export interface WithdrawalComparison {
  tax_optimized: WithdrawalStrategyResult;
  simple_rate: WithdrawalStrategyResult;
}

// --- Comparison ---

export interface ScenarioComparisonItem {
  scenario_id: string;
  scenario_name: string;
  retirement_age: number;
  readiness_score: number;
  success_rate: number;
  median_portfolio_at_end: number | null;
  projections: ProjectionDataPoint[];
}
