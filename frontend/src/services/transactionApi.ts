/**
 * Transaction API service
 */

import api from './api';
import type { Account } from '../types/account';
import type { TransactionListResponse } from '../types/transaction';

export const transactionApi = {
  listAccounts: async (): Promise<Account[]> => {
    const response = await api.get<Account[]>('/accounts/');
    return response.data;
  },

  listTransactions: async (params?: {
    page_size?: number;
    cursor?: string;
    account_id?: string;
    user_id?: string;
    start_date?: string;
    end_date?: string;
    search?: string;
  }): Promise<TransactionListResponse> => {
    const response = await api.get<TransactionListResponse>('/transactions/', {
      params,
    });
    return response.data;
  },
};
