/**
 * Holdings API client
 */

import api from '../services/api';

export interface StyleBoxItem {
  style_class: string;
  percentage: number;
  one_day_change: number | null;
  value: number;
  holding_count: number;
}

export interface Holding {
  id: string;
  account_id: string;
  ticker: string;
  name: string | null;
  shares: number;
  cost_basis_per_share: number | null;
  total_cost_basis: number | null;
  current_price_per_share: number | null;
  current_value: number | null;
  gain_loss: number | null;
  gain_loss_percentage: number | null;
  asset_type: string | null;
}

export const holdingsApi = {
  /**
   * Get portfolio summary
   */
  getPortfolioSummary: async () => {
    const { data } = await api.get('/holdings/portfolio');
    return data;
  },

  /**
   * Get market cap and style breakdown
   */
  getStyleBox: async (): Promise<StyleBoxItem[]> => {
    const { data } = await api.get<StyleBoxItem[]>('/holdings/style-box');
    return data;
  },

  /**
   * Get all holdings for a specific account
   */
  getAccountHoldings: async (accountId: string): Promise<Holding[]> => {
    const { data } = await api.get<Holding[]>(`/holdings/account/${accountId}`);
    return data;
  },

  /**
   * Delete a holding by ID
   */
  deleteHolding: async (holdingId: string): Promise<void> => {
    await api.delete(`/holdings/${holdingId}`);
  },
};
