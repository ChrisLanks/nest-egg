/**
 * Budget types and interfaces
 */

export enum BudgetPeriod {
  MONTHLY = "monthly",
  QUARTERLY = "quarterly",
  SEMI_ANNUAL = "semi_annual",
  YEARLY = "yearly",
}

export interface Budget {
  id: string;
  organization_id: string;
  user_id: string | null;
  name: string;
  amount: number;
  period: BudgetPeriod;
  start_date: string;
  end_date: string | null;
  category_id: string | null;
  label_id: string | null;
  rollover_unused: boolean;
  alert_threshold: number;
  is_active: boolean;
  is_shared: boolean;
  shared_user_ids: string[] | null;
  created_at: string;
  updated_at: string;
}

export interface BudgetCreate {
  name: string;
  amount: number;
  period: BudgetPeriod;
  start_date: string;
  end_date?: string | null;
  category_id?: string | null;
  label_id?: string | null;
  rollover_unused?: boolean;
  alert_threshold?: number;
  is_shared?: boolean;
  shared_user_ids?: string[] | null;
}

export interface BudgetUpdate {
  name?: string;
  amount?: number;
  period?: BudgetPeriod;
  start_date?: string;
  end_date?: string | null;
  category_id?: string | null;
  label_id?: string | null;
  rollover_unused?: boolean;
  alert_threshold?: number;
  is_active?: boolean;
  is_shared?: boolean;
  shared_user_ids?: string[] | null;
}

export interface BudgetSuggestion {
  category_name: string;
  category_id: string | null;
  suggested_amount: number;
  suggested_period: BudgetPeriod;
  avg_monthly_spend: number;
  total_spend: number;
  month_count: number;
  transaction_count: number;
}

export interface BudgetSpending {
  budget_amount: number;
  spent: number;
  remaining: number;
  percentage: number;
  period_start: string;
  period_end: string;
}
