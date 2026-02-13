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
  id: string;
  name: string;
  color?: string;
  parent_id?: string;
  parent_name?: string;
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
