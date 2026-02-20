/**
 * Subscriptions API client
 */

import api from '../services/api';

export interface SubscriptionItem {
  id: string;
  merchant_name: string;
  average_amount: number;
  frequency: string;
  next_expected_date: string | null;
  confidence_score: number;
  account_id: string;
  occurrence_count: number;
}

export interface SubscriptionSummary {
  subscriptions: SubscriptionItem[];
  total_count: number;
  monthly_cost: number;
  yearly_cost: number;
}

export const subscriptionsApi = {
  get: async (): Promise<SubscriptionSummary> => {
    const { data } = await api.get<SubscriptionSummary>('/subscriptions/');
    return data;
  },

  deactivate: async (subscriptionId: string): Promise<void> => {
    await api.patch(`/subscriptions/${subscriptionId}/deactivate`);
  },
};
