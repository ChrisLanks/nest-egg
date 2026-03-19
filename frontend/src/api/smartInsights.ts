/**
 * Smart Insights API client
 *
 * Three endpoints:
 *   GET /smart-insights              — 8 proactive planning insights
 *   GET /smart-insights/roth-conversion — Roth conversion optimizer
 *   GET /smart-insights/fund-fees    — Fund expense-ratio analysis
 *
 * The has_* flags on each response drive frontend nav visibility:
 *   has_retirement_accounts — user has at least one IRA / 401k / etc.
 *   has_taxable_investments  — user has a brokerage account
 *   has_investment_holdings  — user has holdings with price data
 */

import api from "../services/api";

// ── General Insights ──────────────────────────────────────────────────────

export interface InsightItem {
  type: string;
  title: string;
  message: string;
  action: string;
  priority: "high" | "medium" | "low";
  category: "cash" | "investing" | "tax" | "retirement";
  icon: string;
  priority_score: number;
  amount: number | null;
}

export interface SmartInsightsResponse {
  insights: InsightItem[];
  has_retirement_accounts: boolean;
  has_taxable_investments: boolean;
  has_investment_holdings: boolean;
}

export interface SmartInsightsParams {
  user_id?: string;
  max_insights?: number;
}

// ── Roth Conversion ───────────────────────────────────────────────────────

export interface RothConversionYear {
  year: number;
  age: number;
  optimal_conversion: number;
  marginal_rate_at_conversion: number;
  rmd_amount: number;
  traditional_balance_start: number;
  roth_balance_start: number;
  traditional_balance_end: number;
  roth_balance_end: number;
  tax_cost_of_conversion: number;
  notes: string[];
}

export interface RothConversionResponse {
  years: RothConversionYear[];
  total_converted: number;
  total_tax_cost: number;
  no_conversion_traditional_end: number;
  no_conversion_roth_end: number;
  with_conversion_traditional_end: number;
  with_conversion_roth_end: number;
  estimated_tax_savings: number;
  summary: string;
  has_retirement_accounts: boolean;
}

export interface RothConversionParams {
  user_id?: string;
  current_income: number;
  filing_status?: "single" | "married";
  expected_return?: number;
  years_to_project?: number;
  respect_irmaa?: boolean;
}

// ── Fund Fees ─────────────────────────────────────────────────────────────

export interface HoldingFeeDetail {
  ticker: string | null;
  name: string | null;
  market_value: number;
  expense_ratio: number;
  annual_fee: number;
  ten_year_drag: number;
  twenty_year_drag: number;
  flag: "ok" | "high_cost" | "extreme_cost" | "no_data";
  suggestion: string | null;
}

export interface FundFeeResponse {
  total_invested: number;
  holdings_with_er_data: number;
  holdings_missing_er_data: number;
  annual_fee_drag: number;
  weighted_avg_expense_ratio: number;
  benchmark_expense_ratio: number;
  ten_year_impact_vs_benchmark: number;
  twenty_year_impact_vs_benchmark: number;
  high_cost_count: number;
  holdings: HoldingFeeDetail[];
  summary: string;
  has_investment_holdings: boolean;
}

export interface FundFeeParams {
  user_id?: string;
}

// ── API client ────────────────────────────────────────────────────────────

export const smartInsightsApi = {
  getInsights: async (
    params?: SmartInsightsParams,
  ): Promise<SmartInsightsResponse> => {
    const { data } = await api.get<SmartInsightsResponse>("/smart-insights", {
      params,
    });
    return data;
  },

  getRothConversion: async (
    params: RothConversionParams,
  ): Promise<RothConversionResponse> => {
    const { data } = await api.get<RothConversionResponse>(
      "/smart-insights/roth-conversion",
      { params },
    );
    return data;
  },

  getFundFees: async (params?: FundFeeParams): Promise<FundFeeResponse> => {
    const { data } = await api.get<FundFeeResponse>(
      "/smart-insights/fund-fees",
      { params },
    );
    return data;
  },
};
