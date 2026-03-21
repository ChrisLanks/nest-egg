/**
 * Rules API client
 */

import api from '../services/api';
import type { RuleCreate } from '../types/rule';

export interface RuleTestTransaction {
  id: string;
  date: string;
  merchant: string;
  amount: number;
  category: string;
  changes: Array<{ field: string; from: string; to: string }>;
}

export interface RuleTestResult {
  matching_count: number;
  matching_transactions: RuleTestTransaction[];
  total_tested: number;
  message: string;
}

export const rulesApi = {
  /**
   * Test a rule against existing transactions without saving it.
   */
  testRule: async (ruleData: RuleCreate): Promise<RuleTestResult> => {
    const { data } = await api.post<RuleTestResult>('/rules/test', ruleData);
    return data;
  },
};
