/**
 * Education Planning API client
 */

import api from "../services/api";

export interface EducationPlanAccount {
  account_id: string;
  account_name: string;
  current_balance: number;
  monthly_contribution: number;
  user_id: string;
}

export interface EducationPlansResponse {
  plans: EducationPlanAccount[];
  total_529_savings: number;
}

export interface ProjectionDataPoint {
  year: number;
  projected_savings: number;
}

export interface EducationProjectionResponse {
  current_balance: number;
  monthly_contribution: number;
  years_until_college: number;
  college_type: string;
  annual_return: number;
  projected_balance: number;
  total_college_cost: number;
  funding_percentage: number;
  funding_gap: number;
  funding_surplus: number;
  recommended_monthly_to_close_gap: number;
  projections: ProjectionDataPoint[];
}

export interface ProjectionParams {
  current_balance: number;
  monthly_contribution: number;
  years_until_college: number;
  college_type: string;
  annual_return?: number;
}

export const educationApi = {
  getPlans: async (userId?: string): Promise<EducationPlansResponse> => {
    const params = userId ? { user_id: userId } : {};
    const { data } = await api.get<EducationPlansResponse>("/education/plans", {
      params,
    });
    return data;
  },

  getProjection: async (
    params: ProjectionParams,
  ): Promise<EducationProjectionResponse> => {
    const { data } = await api.get<EducationProjectionResponse>(
      "/education/projection",
      { params },
    );
    return data;
  },
};
