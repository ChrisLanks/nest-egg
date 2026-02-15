/**
 * Accounts API client
 */

import api from '../services/api';
import type { Account } from '../types/account';

export const accountsApi = {
  /**
   * Get all accounts
   */
  getAccounts: async (): Promise<Account[]> => {
    const { data } = await api.get<Account[]>('/accounts/');
    return data;
  },
};
