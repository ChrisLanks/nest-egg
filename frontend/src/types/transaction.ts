/**
 * Transaction types
 */

export interface Transaction {
  id: string;
  account_id: string;
  date: string; // ISO date string
  amount: number;
  merchant_name: string | null;
  description: string | null;
  category_primary: string | null;
  category_detailed: string | null;
  is_pending: boolean;
  account_name: string | null;
  account_mask: string | null;
}

export interface TransactionListResponse {
  transactions: Transaction[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}
