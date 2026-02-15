/**
 * Transaction Merges API client
 */

import api from '../services/api';
import type {
  TransactionMerge,
  DuplicateDetectionRequest,
  TransactionMergeRequest,
  AutoDetectRequest,
} from '../types/transaction-merge';
import type { Transaction } from '../types/transaction';

export const transactionMergesApi = {
  /**
   * Find potential duplicate transactions
   */
  findDuplicates: async (
    request: DuplicateDetectionRequest
  ): Promise<{
    transaction_id: string;
    potential_duplicates: Transaction[];
    count: number;
  }> => {
    const { data } = await api.post<{
      transaction_id: string;
      potential_duplicates: Transaction[];
      count: number;
    }>('/transaction-merges/find-duplicates', request);
    return data;
  },

  /**
   * Merge transactions
   */
  merge: async (request: TransactionMergeRequest): Promise<TransactionMerge> => {
    const { data } = await api.post<TransactionMerge>('/transaction-merges/', request);
    return data;
  },

  /**
   * Get merge history for a transaction
   */
  getHistory: async (transactionId: string): Promise<TransactionMerge[]> => {
    const { data } = await api.get<TransactionMerge[]>(
      `/transaction-merges/transaction/${transactionId}/history`
    );
    return data;
  },

  /**
   * Auto-detect and optionally merge duplicates
   */
  autoDetect: async (
    params?: AutoDetectRequest
  ): Promise<{
    dry_run: boolean;
    matches_found: number;
    matches: Array<{ primary: Transaction; duplicates: Transaction[] }>;
  }> => {
    const { data } = await api.post<{
      dry_run: boolean;
      matches_found: number;
      matches: Array<{ primary: Transaction; duplicates: Transaction[] }>;
    }>('/transaction-merges/auto-detect', null, { params });
    return data;
  },
};
