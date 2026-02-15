/**
 * Contributions API client
 */

import { apiClient } from './client';
import type { Contribution, ContributionCreate, ContributionUpdate } from '../types/contribution';

export const contributionsApi = {
  /**
   * Create a new contribution for an account
   */
  createContribution: async (accountId: string, data: ContributionCreate): Promise<Contribution> => {
    const response = await apiClient.post(`/accounts/${accountId}/contributions`, data);
    return response.data;
  },

  /**
   * List all contributions for an account
   */
  listContributions: async (accountId: string, includeInactive = false): Promise<Contribution[]> => {
    const response = await apiClient.get(`/accounts/${accountId}/contributions`, {
      params: { include_inactive: includeInactive },
    });
    return response.data;
  },

  /**
   * Get a specific contribution
   */
  getContribution: async (contributionId: string): Promise<Contribution> => {
    const response = await apiClient.get(`/contributions/${contributionId}`);
    return response.data;
  },

  /**
   * Update a contribution
   */
  updateContribution: async (contributionId: string, data: ContributionUpdate): Promise<Contribution> => {
    const response = await apiClient.patch(`/contributions/${contributionId}`, data);
    return response.data;
  },

  /**
   * Delete a contribution
   */
  deleteContribution: async (contributionId: string): Promise<void> => {
    await apiClient.delete(`/contributions/${contributionId}`);
  },
};
