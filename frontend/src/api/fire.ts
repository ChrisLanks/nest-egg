/**
 * FIRE (Financial Independence, Retire Early) API client
 */

import api from "../services/api";

export interface FIRatioResponse {
  fi_ratio: number;
  investable_assets: number;
  annual_expenses: number;
  fi_number: number;
}

export interface SavingsRateResponse {
  savings_rate: number;
  income: number;
  spending: number;
  savings: number;
  months: number;
}

export interface YearsToFIResponse {
  years_to_fi: number | null;
  fi_number: number;
  investable_assets: number;
  annual_savings: number;
  withdrawal_rate: number;
  expected_return: number;
  already_fi: boolean;
}

export interface CoastFIResponse {
  coast_fi_number: number;
  fi_number: number;
  investable_assets: number;
  is_coast_fi: boolean;
  retirement_age: number;
  years_until_retirement: number;
  expected_return: number;
}

export interface FireMetricsResponse {
  fi_ratio: FIRatioResponse;
  savings_rate: SavingsRateResponse;
  years_to_fi: YearsToFIResponse;
  coast_fi: CoastFIResponse;
}

export interface FireMetricsParams {
  user_id?: string;
  withdrawal_rate?: number;
  expected_return?: number;
  retirement_age?: number;
}

export const fireApi = {
  getMetrics: async (
    params?: FireMetricsParams,
  ): Promise<FireMetricsResponse> => {
    const { data } = await api.get<FireMetricsResponse>("/fire/metrics", {
      params,
    });
    return data;
  },
};
