/**
 * Transaction types
 */

export interface Label {
  id: string;
  name: string;
  color?: string;
  is_income: boolean;
}

export interface Category {
  id: string | null; // null for Plaid categories not yet in database
  name: string;
  color?: string | null;
  parent_id?: string;
  parent_name?: string;
  parent_category_id?: string | null;
  plaid_category_name?: string | null;
  is_custom?: boolean;
  transaction_count?: number;
  organization_id?: string;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface Transaction {
  id: string;
  account_id: string;
  organization_id?: string;
  date: string; // ISO date string
  amount: number;
  merchant_name: string | null;
  description: string | null;
  category_primary: string | null;
  category_detailed: string | null;
  is_pending: boolean;
  is_transfer: boolean;
  account_name: string | null;
  account_mask: string | null;
  category?: Category;
  labels?: Label[];
  deduplication_hash?: string;
  created_at?: string;
  updated_at?: string;
}

export interface TransactionListResponse {
  transactions: Transaction[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
  next_cursor?: string | null;
}
