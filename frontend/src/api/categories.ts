/**
 * Categories API client
 */

import api from '../services/api';
import type { Category } from '../types/transaction';

export const categoriesApi = {
  /**
   * Get all categories
   */
  getCategories: async (): Promise<Category[]> => {
    const { data } = await api.get<Category[]>('/categories/');
    return data;
  },
};
