/**
 * Savings goal types and interfaces
 */

export interface SavingsGoal {
  id: string;
  organization_id: string;
  name: string;
  description: string | null;
  target_amount: number;
  current_amount: number;
  start_date: string;
  target_date: string | null;
  account_id: string | null;
  auto_sync: boolean;
  priority: number | null;
  is_completed: boolean;
  completed_at: string | null;
  is_funded: boolean;
  funded_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface SavingsGoalCreate {
  name: string;
  description?: string | null;
  target_amount: number;
  current_amount?: number;
  start_date: string;
  target_date?: string | null;
  account_id?: string | null;
  auto_sync?: boolean;
}

export interface SavingsGoalUpdate {
  name?: string;
  description?: string | null;
  target_amount?: number;
  current_amount?: number;
  start_date?: string;
  target_date?: string | null;
  account_id?: string | null;
  auto_sync?: boolean;
}

export interface SavingsGoalProgress {
  goal_id: string;
  name: string;
  current_amount: number;
  target_amount: number;
  progress_percentage: number;
  remaining_amount: number;
  days_elapsed: number;
  days_remaining: number | null;
  monthly_required: number | null;
  on_track: boolean | null;
  is_completed: boolean;
}
