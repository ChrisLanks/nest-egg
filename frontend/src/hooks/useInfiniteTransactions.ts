/**
 * Custom hook for infinite scroll transaction loading
 */

import { useState, useEffect, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { transactionApi } from '../services/transactionApi';
import type { Transaction } from '../types/transaction';

interface UseInfiniteTransactionsParams {
  accountId?: string;
  startDate?: string;
  endDate?: string;
  search?: string;
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
  startDate,
  endDate,
  search,
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
    setAllTransactions([]);
    setCurrentCursor(null);
    setNextCursor(null);
    setHasMore(false);
    setTotal(0);
  }, [accountId, startDate, endDate, search]);

  const { data, isLoading, refetch: queryRefetch } = useQuery({
    queryKey: ['infinite-transactions', accountId, startDate, endDate, search, currentCursor],
    queryFn: async () => {
      const result = await transactionApi.listTransactions({
        page_size: pageSize,
        account_id: accountId,
        start_date: startDate,
        end_date: endDate,
        search,
        cursor: currentCursor || undefined,
      });

      // Update accumulated transactions
      if (currentCursor) {
        setAllTransactions((prev) => [...prev, ...result.transactions]);
      } else {
        setAllTransactions(result.transactions);
      }

      // Update pagination state
      setNextCursor(result.next_cursor || null);
      setHasMore(result.has_more);
      if (result.total > 0) {
        setTotal(result.total);
      }

      return result;
    },
    enabled,
  });

  // Reset isLoadingMore when query completes
  useEffect(() => {
    if (!isLoading) {
      setIsLoadingMore(false);
    }
  }, [isLoading]);

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
