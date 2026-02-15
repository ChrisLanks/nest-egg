/**
 * Transaction Splits API client
 */

import api from '../services/api';
import type {
  TransactionSplit,
  CreateSplitsRequest,
  TransactionSplitUpdate,
} from '../types/transaction-split';

export const transactionSplitsApi = {
  /**
   * Create splits for a transaction
   */
  create: async (request: CreateSplitsRequest): Promise<TransactionSplit[]> => {
    const { data } = await api.post<TransactionSplit[]>('/transaction-splits/', request);
    return data;
  },

  /**
   * Get all splits for a transaction
   */
  getByTransaction: async (transactionId: string): Promise<TransactionSplit[]> => {
    const { data } = await api.get<TransactionSplit[]>(
      `/transaction-splits/transaction/${transactionId}`
    );
    return data;
  },

  /**
   * Update a split
   */
  update: async (splitId: string, updates: TransactionSplitUpdate): Promise<TransactionSplit> => {
    const { data } = await api.patch<TransactionSplit>(`/transaction-splits/${splitId}`, updates);
    return data;
  },

  /**
   * Delete all splits for a transaction
   */
  delete: async (transactionId: string): Promise<void> => {
    await api.delete(`/transaction-splits/transaction/${transactionId}`);
  },
};
