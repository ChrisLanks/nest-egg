/**
 * Transaction merge types and interfaces
 */

export interface TransactionMerge {
  id: string;
  organization_id: string;
  primary_transaction_id: string;
  duplicate_transaction_id: string;
  merge_reason: string | null;
  is_auto_merged: boolean;
  merged_at: string;
  merged_by_user_id: string | null;
}

export interface DuplicateDetectionRequest {
  transaction_id: string;
  date_window_days?: number;
  amount_tolerance?: number;
}

export interface TransactionMergeRequest {
  primary_transaction_id: string;
  duplicate_transaction_ids: string[];
  merge_reason?: string | null;
}

export interface AutoDetectRequest {
  dry_run?: boolean;
  date_window_days?: number;
}
