/**
 * Recurring Transactions API client
 */

import api from '../services/api';
import type {
  RecurringTransaction,
  RecurringTransactionCreate,
  RecurringTransactionUpdate,
  DetectRecurringRequest,
  DetectRecurringResponse,
} from '../types/recurring-transaction';

export const recurringTransactionsApi = {
  /**
   * Auto-detect recurring patterns
   */
  detectPatterns: async (params?: DetectRecurringRequest): Promise<DetectRecurringResponse> => {
    const { data } = await api.post<DetectRecurringResponse>(
      '/recurring-transactions/detect',
      null,
      { params }
    );
    return data;
  },

  /**
   * Create a manual recurring pattern
   */
  create: async (pattern: RecurringTransactionCreate): Promise<RecurringTransaction> => {
    const { data } = await api.post<RecurringTransaction>('/recurring-transactions/', pattern);
    return data;
  },

  /**
   * Get all recurring patterns
   */
  getAll: async (params?: { is_active?: boolean }): Promise<RecurringTransaction[]> => {
    const { data } = await api.get<RecurringTransaction[]>('/recurring-transactions/', { params });
    return data;
  },

  /**
   * Update recurring pattern
   */
  update: async (
    recurringId: string,
    updates: RecurringTransactionUpdate
  ): Promise<RecurringTransaction> => {
    const { data } = await api.patch<RecurringTransaction>(
      `/recurring-transactions/${recurringId}`,
      updates
    );
    return data;
  },

  /**
   * Delete recurring pattern
   */
  delete: async (recurringId: string): Promise<void> => {
    await api.delete(`/recurring-transactions/${recurringId}`);
  },
};
