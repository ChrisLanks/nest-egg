/**
 * Labels API client
 */

import api from '../services/api';
import type { Label } from '../types/transaction';

export const labelsApi = {
  /**
   * Get all labels for the current organization
   */
  getAll: async (params?: { is_income?: boolean }): Promise<Label[]> => {
    const { data } = await api.get<Label[]>('/labels/', { params });
    return data;
  },
};
