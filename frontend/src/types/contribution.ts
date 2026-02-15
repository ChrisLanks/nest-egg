/**
 * Contribution types
 */

export enum ContributionType {
  FIXED_AMOUNT = 'fixed_amount',
  SHARES = 'shares',
  PERCENTAGE_GROWTH = 'percentage_growth',
}

export enum ContributionFrequency {
  WEEKLY = 'weekly',
  BIWEEKLY = 'biweekly',
  MONTHLY = 'monthly',
  QUARTERLY = 'quarterly',
  ANNUALLY = 'annually',
}

export interface Contribution {
  id: string;
  organization_id: string;
  account_id: string;
  contribution_type: ContributionType;
  amount: number;
  frequency: ContributionFrequency;
  start_date: string;
  end_date: string | null;
  is_active: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ContributionCreate {
  contribution_type: ContributionType;
  amount: number;
  frequency: ContributionFrequency;
  start_date: string;
  end_date?: string | null;
  is_active?: boolean;
  notes?: string | null;
}

export interface ContributionUpdate {
  contribution_type?: ContributionType;
  amount?: number;
  frequency?: ContributionFrequency;
  start_date?: string;
  end_date?: string | null;
  is_active?: boolean;
  notes?: string | null;
}
