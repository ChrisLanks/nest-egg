/**
 * Custom hook for infinite scroll transaction loading.
 *
 * Caps accumulated transactions at MAX_RENDERED_ROWS to prevent
 * unbounded DOM growth as users scroll through large datasets.
 */

import { useState, useEffect, useCallback } from "react";
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

export const useInfiniteTransactions = ({
  accountId,
  userId,
  startDate,
  endDate,
  search,
  flagged,
  pageSize = 100,
  enabled = true,
}: UseInfiniteTransactionsParams): UseInfiniteTransactionsReturn => {
  const [allTransactions, setAllTransactions] = useState<Transaction[]>([]);
  const [currentCursor, setCurrentCursor] = useState<string | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [total, setTotal] = useState(0);

  // Reset state when filters change
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setAllTransactions([]);
    setCurrentCursor(null);
    setNextCursor(null);
    setHasMore(false);
    setTotal(0);
  }, [accountId, userId, startDate, endDate, search, flagged]);

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
      currentCursor,
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
        cursor: currentCursor || undefined,
      });
    },
    enabled,
    refetchOnMount: true, // Refetch only when stale (respects staleTime)
  });

  // Single effect to sync query data → local state (eliminates duplicate sync)
  useEffect(() => {
    if (!data) return;

    if (currentCursor) {
      // Append new page, cap total to MAX_RENDERED_ROWS
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setAllTransactions((prev) => {
        const combined = [...prev, ...data.transactions];
        if (combined.length > MAX_RENDERED_ROWS) {
          return combined.slice(combined.length - MAX_RENDERED_ROWS);
        }
        return combined;
      });
    } else {
      // First page / reset
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setAllTransactions(data.transactions);
    }

    setNextCursor(data.next_cursor || null);
    setHasMore(data.has_more);
    if (data.total > 0) {
      setTotal(data.total);
    }
    setIsLoadingMore(false);
  }, [data, currentCursor]);

  const loadMore = useCallback(() => {
    if (nextCursor && !isLoadingMore && !isLoading) {
      setIsLoadingMore(true);
      setCurrentCursor(nextCursor);
    }
  }, [nextCursor, isLoadingMore, isLoading]);

  const refetch = useCallback(() => {
    setAllTransactions([]);
    setCurrentCursor(null);
    setNextCursor(null);
    setHasMore(false);
    setTotal(0);
    queryRefetch();
  }, [queryRefetch]);

  return {
    transactions: allTransactions,
    isLoading,
    isLoadingMore,
    hasMore,
    total,
    loadMore,
    refetch,
  };
};
