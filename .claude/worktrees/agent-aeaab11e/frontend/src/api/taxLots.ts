/**
 * Tax Lots API client
 */

import api from "../services/api";

export interface TaxLot {
  id: string;
  holding_id: string;
  acquired_date: string;
  quantity: number;
  remaining_quantity: number;
  cost_basis_per_share: number;
  total_cost_basis: number;
  holding_period: "SHORT_TERM" | "LONG_TERM";
  is_closed: boolean;
  closed_date: string | null;
}

export interface SaleRequest {
  quantity: number;
  sale_price_per_share: number;
  sale_date: string;
  cost_basis_method: "FIFO" | "LIFO" | "HIFO" | "SPECIFIC_ID";
  specific_lot_ids?: string[];
}

export interface SaleResult {
  lots_sold: number;
  total_proceeds: number;
  total_cost_basis: number;
  realized_gain_loss: number;
  short_term_gain_loss: number;
  long_term_gain_loss: number;
}

export interface UnrealizedGainItem {
  holding_id: string;
  ticker: string;
  lot_id: string;
  acquired_date: string;
  quantity: number;
  cost_basis: number;
  current_value: number;
  unrealized_gain: number;
  holding_period: "SHORT_TERM" | "LONG_TERM";
}

export interface UnrealizedGainsSummary {
  items: UnrealizedGainItem[];
  total_unrealized_gain: number;
  total_cost_basis: number;
  total_current_value: number;
}

export interface RealizedGainsSummary {
  year: number;
  total_realized: number;
  short_term_gains: number;
  long_term_gains: number;
  total_proceeds: number;
  total_cost_basis: number;
}

export const taxLotsApi = {
  getHoldingTaxLots: async (
    holdingId: string,
    includeClosed = false,
  ): Promise<TaxLot[]> => {
    const { data } = await api.get(`/tax-lots/holdings/${holdingId}/tax-lots`, {
      params: { include_closed: includeClosed },
    });
    return data;
  },

  recordSale: async (
    holdingId: string,
    sale: SaleRequest,
  ): Promise<SaleResult> => {
    const { data } = await api.post(
      `/tax-lots/holdings/${holdingId}/sell`,
      sale,
    );
    return data;
  },

  importLots: async (holdingId: string): Promise<TaxLot> => {
    const { data } = await api.post(
      `/tax-lots/holdings/${holdingId}/import-lots`,
    );
    return data;
  },

  getUnrealizedGains: async (
    accountId: string,
  ): Promise<UnrealizedGainsSummary> => {
    const { data } = await api.get(
      `/tax-lots/accounts/${accountId}/unrealized-gains`,
    );
    return data;
  },

  getRealizedGains: async (
    accountId: string,
    year?: number,
  ): Promise<RealizedGainsSummary> => {
    const { data } = await api.get(
      `/tax-lots/accounts/${accountId}/realized-gains`,
      {
        params: year ? { year } : undefined,
      },
    );
    return data;
  },

  updateCostBasisMethod: async (
    accountId: string,
    method: string,
  ): Promise<void> => {
    await api.put(`/tax-lots/accounts/${accountId}/cost-basis-method`, {
      method,
    });
  },
};
