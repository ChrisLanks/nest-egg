/**
 * Savings Goals API client
 */

import api from '../services/api';
import type {
  SavingsGoal,
  SavingsGoalCreate,
  SavingsGoalUpdate,
  SavingsGoalProgress,
} from '../types/savings-goal';

export const savingsGoalsApi = {
  /**
   * Create a new savings goal
   */
  create: async (goal: SavingsGoalCreate): Promise<SavingsGoal> => {
    const { data } = await api.post<SavingsGoal>('/savings-goals/', goal);
    return data;
  },

  /**
   * Get all savings goals
   */
  getAll: async (params?: { is_completed?: boolean }): Promise<SavingsGoal[]> => {
    const { data } = await api.get<SavingsGoal[]>('/savings-goals/', { params });
    return data;
  },

  /**
   * Get savings goal by ID
   */
  getById: async (goalId: string): Promise<SavingsGoal> => {
    const { data } = await api.get<SavingsGoal>(`/savings-goals/${goalId}`);
    return data;
  },

  /**
   * Update savings goal
   */
  update: async (goalId: string, updates: SavingsGoalUpdate): Promise<SavingsGoal> => {
    const { data } = await api.patch<SavingsGoal>(`/savings-goals/${goalId}`, updates);
    return data;
  },

  /**
   * Delete savings goal
   */
  delete: async (goalId: string): Promise<void> => {
    await api.delete(`/savings-goals/${goalId}`);
  },

  /**
   * Sync goal amount from linked account
   */
  syncFromAccount: async (goalId: string): Promise<SavingsGoal> => {
    const { data} = await api.post<SavingsGoal>(`/savings-goals/${goalId}/sync`);
    return data;
  },

  /**
   * Get goal progress metrics
   */
  getProgress: async (goalId: string): Promise<SavingsGoalProgress> => {
    const { data } = await api.get<SavingsGoalProgress>(`/savings-goals/${goalId}/progress`);
    return data;
  },
};
