/**
 * Transactions API client
 */

import api from '../services/api';

export interface MerchantSummary {
  merchant_name: string;
  count: number;
}

export const transactionsApi = {
  /**
   * Return distinct merchant names with transaction counts, sorted by count desc.
   */
  listMerchants: async (): Promise<MerchantSummary[]> => {
    const { data } = await api.get<MerchantSummary[]>('/transactions/merchants');
    return data;
  },
};
