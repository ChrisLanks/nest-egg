/**
 * Financial Planning API client.
 *
 * Covers three endpoints:
 *   GET /api/v1/financial-planning/mortgage
 *   GET /api/v1/financial-planning/ss-claiming
 *   GET /api/v1/financial-planning/tax-projection
 */

import api from "../services/api";

// ── Mortgage ──────────────────────────────────────────────────────────────

export interface AmortizationRow {
  month: number;
  payment: number;
  principal: number;
  interest: number;
  balance: number;
  cumulative_interest: number;
}

export interface LoanSummary {
  monthly_payment: number;
  total_paid: number;
  total_interest: number;
  total_principal: number;
  payoff_months: number;
  payoff_date: string;
}

export interface RefinanceComparison {
  current: LoanSummary;
  refinanced: LoanSummary;
  monthly_savings: number;
  lifetime_interest_savings: number;
  break_even_months: number;
  break_even_date: string;
  recommendation: string;
}

export interface ExtraPaymentImpact {
  original_payoff_months: number;
  new_payoff_months: number;
  months_saved: number;
  interest_saved: number;
  original_total_interest: number;
  new_total_interest: number;
}

export interface EquityMilestone {
  equity_pct: number;
  month: number;
  date: string;
  balance_at_milestone: number;
}

export interface MortgageAnalysisResponse {
  loan_balance: number;
  interest_rate: number;
  monthly_payment: number;
  remaining_months: number;
  amortization: AmortizationRow[];
  summary: LoanSummary;
  refinance: RefinanceComparison | null;
  extra_payment: ExtraPaymentImpact | null;
  equity_milestones: EquityMilestone[];
  has_mortgage: boolean;
}

export interface MortgageParams {
  user_id?: string;
  account_id?: string;
  refinance_rate?: number;
  refinance_term_months?: number;
  closing_costs?: number;
  extra_monthly_payment?: number;
}

// ── Social Security ───────────────────────────────────────────────────────

export interface ClaimingAgeOption {
  claiming_age: number;
  monthly_benefit: number;
  annual_benefit: number;
  lifetime_pessimistic: number;
  lifetime_base: number;
  lifetime_optimistic: number;
  breakeven_vs_62_months: number | null;
}

export interface SpousalBenefit {
  higher_earner_pia: number;
  spousal_monthly_at_fra: number;
  spousal_monthly_at_62: number;
  spousal_monthly_at_70: number;
  note: string;
}

export interface SSClaimingResponse {
  current_age: number;
  fra_age: number;
  estimated_pia: number;
  options: ClaimingAgeOption[];
  optimal_age_base_scenario: number;
  optimal_age_pessimistic_scenario: number;
  optimal_age_optimistic_scenario: number;
  spousal: SpousalBenefit | null;
  summary: string;
}

export interface SSClaimingParams {
  user_id?: string;
  current_salary: number;
  birth_year: number;
  career_start_age?: number;
  manual_pia?: number;
  spouse_pia?: number;
}

// ── Tax Projection ────────────────────────────────────────────────────────

export interface TaxBracketBreakdown {
  rate: number;
  income_in_bracket: number;
  tax_owed: number;
}

export interface QuarterlyPayment {
  quarter: string;
  due_date: string;
  amount_due: number;
  paid: boolean;
}

export interface TaxProjectionResponse {
  tax_year: number;
  filing_status: string;
  ordinary_income: number;
  self_employment_income: number;
  estimated_capital_gains: number;
  total_gross_income: number;
  standard_deduction: number;
  se_deduction: number;
  additional_deductions: number;
  total_deductions: number;
  taxable_income: number;
  ordinary_tax: number;
  se_tax: number;
  ltcg_tax: number;
  total_tax_before_credits: number;
  effective_rate: number;
  marginal_rate: number;
  state: string | null;
  state_tax: number;
  state_tax_rate: number;
  combined_tax: number;
  combined_effective_rate: number;
  quarterly_payments: QuarterlyPayment[];
  total_quarterly_due: number;
  prior_year_tax: number | null;
  safe_harbour_amount: number | null;
  safe_harbour_met: boolean | null;
  bracket_breakdown: TaxBracketBreakdown[];
  summary: string;
}

export interface TaxProjectionParams {
  user_id?: string;
  filing_status?: "single" | "married";
  self_employment_income?: number;
  estimated_capital_gains?: number;
  additional_deductions?: number;
  prior_year_tax?: number;
  state?: string;
}

// ── Withholding Check ─────────────────────────────────────────────────────

export interface WithholdingCheckRequest {
  filing_status?: "single" | "married";
  annual_salary: number;
  ytd_withheld?: number;
  months_remaining: number;
  other_income?: number;
  capital_gains_expected?: number;
  ira_contributions?: number;
  prior_year_tax?: number;
  year?: number;
}

export interface WithholdingCheckResponse {
  projected_tax: number;
  safe_harbour_amount: number;
  ytd_withheld: number;
  projected_year_end_withholding: number;
  underpayment_risk: boolean;
  recommended_additional_withholding_per_paycheck: number;
  w4_extra_amount: number;
  notes: string[];
  tax_year: number;
}

// ── API client ────────────────────────────────────────────────────────────

export const financialPlanningApi = {
  getMortgage: async (
    params?: MortgageParams,
  ): Promise<MortgageAnalysisResponse> => {
    const res = await api.get("/financial-planning/mortgage", { params });
    return res.data;
  },

  getSSClaiming: async (
    params: SSClaimingParams,
  ): Promise<SSClaimingResponse> => {
    const res = await api.get("/financial-planning/ss-claiming", { params });
    return res.data;
  },

  getTaxProjection: async (
    params?: TaxProjectionParams,
  ): Promise<TaxProjectionResponse> => {
    const res = await api.get("/financial-planning/tax-projection", { params });
    return res.data;
  },

  checkWithholding: async (
    body: WithholdingCheckRequest,
  ): Promise<WithholdingCheckResponse> => {
    const res = await api.post("/what-if/withholding-check", body);
    return res.data;
  },
};
