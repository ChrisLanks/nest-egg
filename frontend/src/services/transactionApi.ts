/**
 * Transaction API service
 */

import api from "./api";
import type { Account } from "../types/account";
import type { TransactionListResponse } from "../types/transaction";

export const transactionApi = {
  listAccounts: async (): Promise<Account[]> => {
    const response = await api.get<Account[]>("/accounts/");
    return response.data;
  },

  listTransactions: async (params?: {
    page_size?: number;
    cursor?: string;
    account_id?: string;
    user_id?: string;
    start_date?: string;
    end_date?: string;
    search?: string;
    flagged?: boolean;
    min_amount?: number;
    max_amount?: number;
    is_income?: boolean;
  }): Promise<TransactionListResponse> => {
    const response = await api.get<TransactionListResponse>("/transactions/", {
      params,
    });
    return response.data;
  },

  naturalLanguageSearch: async (
    query: string,
  ): Promise<{
    search: string | null;
    start_date: string | null;
    end_date: string | null;
    min_amount: number | null;
    max_amount: number | null;
    is_income: boolean | null;
    raw_query: string;
  }> => {
    const response = await api.post("/transactions/search/natural", { query });
    return response.data;
  },

  listFlaggedTransactions: async (params?: {
    page_size?: number;
    cursor?: string;
  }): Promise<TransactionListResponse> => {
    const response = await api.get<TransactionListResponse>(
      "/transactions/flagged",
      {
        params,
      },
    );
    return response.data;
  },
};
