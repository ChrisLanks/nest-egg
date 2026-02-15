/**
 * Recurring transaction types and interfaces
 */

export enum RecurringFrequency {
  WEEKLY = 'weekly',
  BIWEEKLY = 'biweekly',
  MONTHLY = 'monthly',
  QUARTERLY = 'quarterly',
  YEARLY = 'yearly',
}

export interface RecurringTransaction {
  id: string;
  organization_id: string;
  account_id: string;
  merchant_name: string;
  description_pattern: string | null;
  frequency: RecurringFrequency;
  average_amount: number;
  amount_variance: number;
  category_id: string | null;
  is_user_created: boolean;
  confidence_score: number | null;
  first_occurrence: string;
  last_occurrence: string | null;
  next_expected_date: string | null;
  occurrence_count: number;
  is_active: boolean;
  is_bill: boolean;
  reminder_days_before: number;
  created_at: string;
  updated_at: string;
}

export interface RecurringTransactionCreate {
  merchant_name: string;
  account_id: string;
  frequency: RecurringFrequency;
  average_amount: number;
  amount_variance?: number;
  category_id?: string | null;
  is_bill?: boolean;
  reminder_days_before?: number;
}

export interface RecurringTransactionUpdate {
  merchant_name?: string;
  frequency?: RecurringFrequency;
  average_amount?: number;
  amount_variance?: number;
  category_id?: string | null;
  is_active?: boolean;
  is_bill?: boolean;
  reminder_days_before?: number;
}

export interface UpcomingBill {
  recurring_transaction_id: string;
  merchant_name: string;
  average_amount: number;
  next_expected_date: string;
  days_until_due: number;
  is_overdue: boolean;
  account_id: string;
  category_id: string | null;
}

export interface DetectRecurringRequest {
  min_occurrences?: number;
  lookback_days?: number;
}

export interface DetectRecurringResponse {
  detected_patterns: number;
  patterns: RecurringTransaction[];
}
