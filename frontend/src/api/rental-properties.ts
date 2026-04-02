/**
 * Rental Properties P&L API client
 */

import api from "../services/api";

export interface RentalProperty {
  account_id: string;
  name: string;
  current_value: number;
  rental_monthly_income: number;
  rental_address: string;
  property_type: string | null;
  user_id: string;
}

export interface ExpenseBreakdownItem {
  category: string;
  amount: number;
}

export interface MonthlyData {
  month: number;
  income: number;
  expenses: number;
  net: number;
}

export interface PropertyPnl {
  account_id: string;
  name: string;
  rental_address: string;
  current_value: number;
  year: number;
  gross_income: number;
  total_expenses: number;
  net_income: number;
  cap_rate: number;
  expense_breakdown: ExpenseBreakdownItem[];
  monthly: MonthlyData[];
}

export interface PropertySummaryItem {
  account_id: string;
  name: string;
  rental_address: string;
  current_value: number;
  rental_monthly_income: number;
  gross_income: number;
  total_expenses: number;
  net_income: number;
  cap_rate: number;
}

export interface PropertiesSummary {
  year: number;
  total_income: number;
  total_expenses: number;
  total_net_income: number;
  average_cap_rate: number;
  property_count: number;
  properties: PropertySummaryItem[];
}

export interface RentalFieldsUpdate {
  is_rental_property?: boolean;
  rental_monthly_income?: number;
  rental_address?: string;
  rental_type?: string;
}

export const rentalPropertiesApi = {
  listProperties: async (params?: {
    user_id?: string;
  }): Promise<RentalProperty[]> => {
    const { data } = await api.get<RentalProperty[]>("/rental-properties", {
      params,
    });
    return data;
  },

  getSummary: async (params?: {
    year?: number;
    user_id?: string;
  }): Promise<PropertiesSummary> => {
    const { data } = await api.get<PropertiesSummary>(
      "/rental-properties/summary",
      { params },
    );
    return data;
  },

  getPropertyPnl: async (
    accountId: string,
    params?: { year?: number },
  ): Promise<PropertyPnl> => {
    const { data } = await api.get<PropertyPnl>(
      `/rental-properties/${accountId}/pnl`,
      { params },
    );
    return data;
  },

  updateRentalFields: async (
    accountId: string,
    body: RentalFieldsUpdate,
  ): Promise<any> => {
    const { data } = await api.patch(`/rental-properties/${accountId}`, body);
    return data;
  },
};
