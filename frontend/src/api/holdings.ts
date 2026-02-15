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
};
