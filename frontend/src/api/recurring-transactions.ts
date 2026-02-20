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
  UpcomingBill,
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

  /**
   * Apply this bill's label to matching transactions (retroactively)
   */
  applyLabel: async (
    recurringId: string,
    retroactive: boolean = true
  ): Promise<{ applied_count: number; label_id: string }> => {
    const { data } = await api.post(`/recurring-transactions/${recurringId}/apply-label`, {
      retroactive,
    });
    return data;
  },

  /**
   * Preview how many transactions match this bill's merchant + account
   */
  previewLabel: async (recurringId: string): Promise<{ matching_transactions: number }> => {
    const { data } = await api.get(`/recurring-transactions/${recurringId}/preview-label`);
    return data;
  },

  /**
   * Get upcoming bills
   */
  getUpcomingBills: async (daysAhead: number = 30): Promise<UpcomingBill[]> => {
    const { data } = await api.get<UpcomingBill[]>('/recurring-transactions/bills/upcoming', {
      params: { days_ahead: daysAhead },
    });
    return data;
  },

  /**
   * Get expanded calendar entries (all occurrences within N days)
   */
  getCalendar: async (days: number = 90): Promise<CalendarEntry[]> => {
    const { data } = await api.get<CalendarEntry[]>('/recurring-transactions/calendar', {
      params: { days },
    });
    return data;
  },
};

export interface CalendarEntry {
  date: string;          // ISO date string
  merchant_name: string;
  amount: number;
  recurring_transaction_id: string;
  frequency: string;
}
