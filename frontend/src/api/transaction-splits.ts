/**
 * Transaction Splits API client
 */

import api from '../services/api';
import type {
  MemberBalance,
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

  /**
   * Get per-member settlement balances derived from assigned splits.
   * since: optional ISO date string (YYYY-MM-DD) to filter from.
   */
  getMemberBalances: async (since?: string): Promise<MemberBalance[]> => {
    const params = since ? { since } : {};
    const { data } = await api.get<MemberBalance[]>('/transaction-splits/member-balances', {
      params,
    });
    return data;
  },

  /**
   * Mark all unsettled splits assigned to a member as settled.
   */
  settleMember: async (memberId: string, since?: string): Promise<{ settled_count: number }> => {
    const { data } = await api.post<{ settled_count: number }>('/transaction-splits/settle', {
      member_id: memberId,
      since: since ?? null,
    });
    return data;
  },
};
