/**
 * Budgets API client
 */

import api from "../services/api";
import type {
  Budget,
  BudgetCreate,
  BudgetUpdate,
  BudgetSpending,
  BudgetSuggestion,
  BudgetSuggestionsResponse,
} from "../types/budget";

export const budgetsApi = {
  /**
   * Create a new budget
   */
  create: async (budget: BudgetCreate): Promise<Budget> => {
    const { data } = await api.post<Budget>("/budgets/", budget);
    return data;
  },

  /**
   * Get all budgets
   */
  getAll: async (params?: {
    is_active?: boolean;
    user_id?: string;
  }): Promise<Budget[]> => {
    const { data } = await api.get<Budget[]>("/budgets/", { params });
    return data;
  },

  /**
   * Get budget by ID
   */
  getById: async (budgetId: string): Promise<Budget> => {
    const { data } = await api.get<Budget>(`/budgets/${budgetId}`);
    return data;
  },

  /**
   * Update budget
   */
  update: async (budgetId: string, updates: BudgetUpdate): Promise<Budget> => {
    const { data } = await api.patch<Budget>(`/budgets/${budgetId}`, updates);
    return data;
  },

  /**
   * Delete budget
   */
  delete: async (budgetId: string): Promise<void> => {
    await api.delete(`/budgets/${budgetId}`);
  },

  /**
   * Get budget spending for current period
   */
  getSpending: async (budgetId: string): Promise<BudgetSpending> => {
    const { data } = await api.get<BudgetSpending>(
      `/budgets/${budgetId}/spending`,
    );
    return data;
  },

  /**
   * Get smart budget suggestions based on spending history
   */
  getSuggestions: async (opts?: { months?: number; user_id?: string }): Promise<BudgetSuggestionsResponse> => {
    const params: Record<string, unknown> = {};
    if (opts?.months) params.months = opts.months;
    if (opts?.user_id) params.user_id = opts.user_id;
    const { data } = await api.get<BudgetSuggestionsResponse>("/budgets/suggestions", {
      params: Object.keys(params).length ? params : undefined,
    });
    return data;
  },

  /**
   * Check all budgets and create alerts
   */
  checkAlerts: async (): Promise<{
    alerts_created: number;
    budgets_alerted: any[];
  }> => {
    const { data } = await api.post<{
      alerts_created: number;
      budgets_alerted: any[];
    }>("/budgets/check-alerts");
    return data;
  },
};
