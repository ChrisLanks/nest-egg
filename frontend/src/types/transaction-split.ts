/**
 * Transaction split types and interfaces
 */

export interface TransactionSplit {
  id: string;
  parent_transaction_id: string;
  organization_id: string;
  amount: number;
  description: string | null;
  category_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface TransactionSplitCreate {
  amount: number;
  description?: string | null;
  category_id?: string | null;
}

export interface CreateSplitsRequest {
  transaction_id: string;
  splits: TransactionSplitCreate[];
}

export interface TransactionSplitUpdate {
  amount?: number;
  description?: string | null;
  category_id?: string | null;
}
