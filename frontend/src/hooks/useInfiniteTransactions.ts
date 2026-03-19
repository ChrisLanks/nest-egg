/**
 * Custom hook for infinite scroll transaction loading.
 *
 * Caps accumulated transactions at MAX_RENDERED_ROWS to prevent
 * unbounded DOM growth as users scroll through large datasets.
 *
 * Uses useReducer to batch state updates and avoid cascading re-renders.
 */

import { useReducer, useEffect, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { transactionApi } from "../services/transactionApi";
import type { Transaction } from "../types/transaction";

/** Maximum number of transactions to keep in DOM at once */
const MAX_RENDERED_ROWS = 500;

interface UseInfiniteTransactionsParams {
  accountId?: string;
  userId?: string;
  startDate?: string;
  endDate?: string;
  search?: string;
  flagged?: boolean;
  minAmount?: number;
  maxAmount?: number;
  isIncome?: boolean;
  pageSize?: number;
  enabled?: boolean;
}

interface UseInfiniteTransactionsReturn {
  transactions: Transaction[];
  isLoading: boolean;
  isLoadingMore: boolean;
  hasMore: boolean;
  total: number;
  loadMore: () => void;
  refetch: () => void;
}

interface State {
  allTransactions: Transaction[];
  currentCursor: string | null;
  nextCursor: string | null;
  hasMore: boolean;
  isLoadingMore: boolean;
  total: number;
}

type Action =
  | { type: "RESET" }
  | { type: "LOAD_MORE"; cursor: string }
  | {
      type: "DATA_RECEIVED";
      transactions: Transaction[];
      nextCursor: string | null;
      hasMore: boolean;
      total: number;
      isAppend: boolean;
    };

const initialState: State = {
  allTransactions: [],
  currentCursor: null,
  nextCursor: null,
  hasMore: false,
  isLoadingMore: false,
  total: 0,
};

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "RESET":
      return initialState;
    case "LOAD_MORE":
      return { ...state, isLoadingMore: true, currentCursor: action.cursor };
    case "DATA_RECEIVED": {
      let allTransactions: Transaction[];
      if (action.isAppend) {
        const combined = [...state.allTransactions, ...action.transactions];
        allTransactions =
          combined.length > MAX_RENDERED_ROWS
            ? combined.slice(combined.length - MAX_RENDERED_ROWS)
            : combined;
      } else {
        allTransactions = action.transactions;
      }
      return {
        ...state,
        allTransactions,
        nextCursor: action.nextCursor,
        hasMore: action.hasMore,
        total: action.total > 0 ? action.total : state.total,
        isLoadingMore: false,
      };
    }
    default:
      return state;
  }
}

export const useInfiniteTransactions = ({
  accountId,
  userId,
  startDate,
  endDate,
  search,
  flagged,
  minAmount,
  maxAmount,
  isIncome,
  pageSize = 100,
  enabled = true,
}: UseInfiniteTransactionsParams): UseInfiniteTransactionsReturn => {
  const [state, dispatch] = useReducer(reducer, initialState);

  // Reset state when filters change
  useEffect(() => {
    dispatch({ type: "RESET" });
  }, [
    accountId,
    userId,
    startDate,
    endDate,
    search,
    flagged,
    minAmount,
    maxAmount,
    isIncome,
  ]);

  const {
    data,
    isLoading,
    refetch: queryRefetch,
  } = useQuery({
    queryKey: [
      "infinite-transactions",
      accountId,
      userId,
      startDate,
      endDate,
      search,
      flagged,
      minAmount,
      maxAmount,
      isIncome,
      state.currentCursor,
    ],
    queryFn: async () => {
      return await transactionApi.listTransactions({
        page_size: pageSize,
        account_id: accountId,
        user_id: userId,
        start_date: startDate,
        end_date: endDate,
        search,
        flagged,
        min_amount: minAmount,
        max_amount: maxAmount,
        is_income: isIncome,
        cursor: state.currentCursor || undefined,
      });
    },
    enabled,
    refetchOnMount: true,
  });

  // Single effect to sync query data → local state (single dispatch, no cascading renders)
  useEffect(() => {
    if (!data) return;

    dispatch({
      type: "DATA_RECEIVED",
      transactions: data.transactions,
      nextCursor: data.next_cursor || null,
      hasMore: data.has_more,
      total: data.total,
      isAppend: !!state.currentCursor,
    });
  }, [data, state.currentCursor]);

  const loadMore = useCallback(() => {
    if (state.nextCursor && !state.isLoadingMore && !isLoading) {
      dispatch({ type: "LOAD_MORE", cursor: state.nextCursor });
    }
  }, [state.nextCursor, state.isLoadingMore, isLoading]);

  const refetch = useCallback(() => {
    dispatch({ type: "RESET" });
    queryRefetch();
  }, [queryRefetch]);

  return {
    transactions: state.allTransactions,
    isLoading,
    isLoadingMore: state.isLoadingMore,
    hasMore: state.hasMore,
    total: state.total,
    loadMore,
    refetch,
  };
};
