/**
 * Budget types and interfaces
 */

export enum BudgetPeriod {
  MONTHLY = 'monthly',
  QUARTERLY = 'quarterly',
  YEARLY = 'yearly',
}

export interface Budget {
  id: string;
  organization_id: string;
  name: string;
  amount: number;
  period: BudgetPeriod;
  start_date: string;
  end_date: string | null;
  category_id: string | null;
  rollover_unused: boolean;
  alert_threshold: number;
  is_active: boolean;
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
  rollover_unused?: boolean;
  alert_threshold?: number;
}

export interface BudgetUpdate {
  name?: string;
  amount?: number;
  period?: BudgetPeriod;
  start_date?: string;
  end_date?: string | null;
  category_id?: string | null;
  rollover_unused?: boolean;
  alert_threshold?: number;
  is_active?: boolean;
}

export interface BudgetSpending {
  budget_amount: number;
  spent: number;
  remaining: number;
  percentage: number;
  period_start: string;
  period_end: string;
}
