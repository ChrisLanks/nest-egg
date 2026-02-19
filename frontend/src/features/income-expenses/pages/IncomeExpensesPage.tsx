/**
 * Cash Flow analysis page with multi-level drill-down capabilities
 */

import {
  Box,
  Container,
  Heading,
  Text,
  VStack,
  HStack,
  Card,
  CardBody,
  SimpleGrid,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  Spinner,
  Center,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  IconButton,
  useDisclosure,
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  Wrap,
  WrapItem,
  Button,
  ButtonGroup,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  Checkbox,
} from '@chakra-ui/react';
import { useState, useMemo, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ChevronRightIcon, ChevronUpIcon, ChevronDownIcon } from '@chakra-ui/icons';
import { IoBarChart, IoPieChart } from 'react-icons/io5';
import api from '../../../services/api';
import { useUserView } from '../../../contexts/UserViewContext';
import { DateRangePicker } from '../../../components/DateRangePicker';
import type { DateRange } from '../../../components/DateRangePicker';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import type { Transaction } from '../../../types/transaction';
import { TransactionDetailModal } from '../../../components/TransactionDetailModal';
import { RuleBuilderModal } from '../../../components/RuleBuilderModal';
import { IncomeExpensesSkeleton } from '../../../components/LoadingSkeleton';

interface CategoryBreakdown {
  category: string;
  amount: number;
  count: number;
  percentage: number;
  has_children?: boolean;
}

interface IncomeExpenseSummary {
  total_income: number;
  total_expenses: number;
  net: number;
  income_categories: CategoryBreakdown[];
  expense_categories: CategoryBreakdown[];
}

interface MonthlyTrend {
  month: string;
  income: number;
  expenses: number;
  net: number;
}

type ChartType = 'pie' | 'bar';
type DrillDownLevel = 'categories' | 'merchants' | 'transactions';

interface DrillDownState {
  level: DrillDownLevel;
  category?: string;
  parentCategory?: string; // For hierarchical categories (parent > child)
  accountId?: string; // For account grouping: account UUID
  merchant?: string;
}

type SortField = 'date' | 'merchant_name' | 'amount';
type SortDirection = 'asc' | 'desc';

const COLORS = [
  '#48BB78', '#4299E1', '#9F7AEA', '#ED8936', '#F56565',
  '#38B2AC', '#DD6B20', '#805AD5', '#D69E2E', '#E53E3E',
  '#06B6D4', '#8B5CF6', '#EC4899', '#F59E0B', '#10B981',
];

export const IncomeExpensesPage = () => {
  // Use global user view context
  const { selectedUserId } = useUserView();

  // Utility functions defined first to avoid hoisting issues
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatDate = (dateStr: string) => {
    const [year, month, day] = dateStr.split('-').map(Number);
    return new Date(year, month - 1, day).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  // Initialize dateRange from localStorage or with a default current month
  const [dateRange, setDateRange] = useState<DateRange>(() => {
    // Try to restore from localStorage
    const saved = localStorage.getItem('income-expenses-date-range');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        // Fall through to default
      }
    }

    // Default to current calendar month
    const now = new Date();
    const start = new Date(now.getFullYear(), now.getMonth(), 1);
    const end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
    return {
      start: start.toISOString().split('T')[0],
      end: end.toISOString().split('T')[0],
      label: 'This Month',
    };
  });

  const [incomeChartType, setIncomeChartType] = useState<ChartType>('pie');
  const [expenseChartType, setExpenseChartType] = useState<ChartType>('pie');
  const [incomeDrillDown, setIncomeDrillDown] = useState<DrillDownState>({ level: 'categories' });
  const [expenseDrillDown, setExpenseDrillDown] = useState<DrillDownState>({ level: 'categories' });

  const [selectedTransaction, setSelectedTransaction] = useState<Transaction | null>(null);
  const [ruleTransaction, setRuleTransaction] = useState<Transaction | null>(null);
  const { isOpen: isDetailOpen, onOpen: onDetailOpen, onClose: onDetailClose } = useDisclosure();
  const { isOpen: isRuleOpen, onOpen: onRuleOpen, onClose: onRuleClose } = useDisclosure();

  const [incomeSortField, setIncomeSortField] = useState<SortField>('date');
  const [incomeSortDirection, setIncomeSortDirection] = useState<SortDirection>('desc');
  const [expenseSortField, setExpenseSortField] = useState<SortField>('date');
  const [expenseSortDirection, setExpenseSortDirection] = useState<SortDirection>('desc');

  // Debug logging for drill-down state changes
  useEffect(() => {
    console.log('[DRILL-DOWN STATE CHANGE] Income:', incomeDrillDown);
  }, [incomeDrillDown]);

  useEffect(() => {
    console.log('[DRILL-DOWN STATE CHANGE] Expense:', expenseDrillDown);
  }, [expenseDrillDown]);

  const [groupBy, setGroupBy] = useState<'category' | 'label' | 'merchant' | 'account'>(() => {
    // Try to restore from localStorage
    const saved = localStorage.getItem('income-expenses-group-by');
    if (saved && ['category', 'label', 'merchant', 'account'].includes(saved)) {
      return saved as 'category' | 'label' | 'merchant' | 'account';
    }
    return 'category';
  });
  const [hiddenItems, setHiddenItems] = useState<Set<string>>(new Set());
  const [selectedTab, setSelectedTab] = useState(0); // 0 = Combined, 1 = Income, 2 = Expenses
  const [incomeLegendExpanded, setIncomeLegendExpanded] = useState(false);
  const [expenseLegendExpanded, setExpenseLegendExpanded] = useState(false);

  // Fetch organization settings for custom month boundaries
  const { data: orgSettings } = useQuery({
    queryKey: ['orgPreferences'],
    queryFn: async () => {
      const response = await api.get('/settings/organization');
      return response.data;
    },
  });

  const customMonthStartDay = orgSettings?.monthly_start_day || 1;

  // Update date range when custom month boundary loads (only if no user selection saved)
  useEffect(() => {
    if (!orgSettings) return; // Wait for settings to load

    // Check if user has a saved date range - if so, respect it
    const savedRange = localStorage.getItem('income-expenses-date-range');
    if (savedRange) return;

    const now = new Date();
    const start = new Date();
    const end = new Date();

    if (customMonthStartDay === 1) {
      // Standard calendar month - from 1st to last day of month
      start.setDate(1);
      end.setMonth(end.getMonth() + 1);
      end.setDate(0); // Last day of current month
      end.setHours(23, 59, 59, 999);
    } else {
      // Custom month boundary - from custom start day to day before next boundary
      const currentDay = now.getDate();
      if (currentDay >= customMonthStartDay) {
        // We're past the boundary in current month
        start.setDate(customMonthStartDay);
        // End is day before next boundary (next month, day before customMonthStartDay)
        end.setMonth(end.getMonth() + 1);
        end.setDate(customMonthStartDay - 1);
      } else {
        // We haven't reached the boundary yet, use previous month's boundary
        start.setMonth(start.getMonth() - 1);
        start.setDate(customMonthStartDay);
        // End is day before current month's boundary
        end.setDate(customMonthStartDay - 1);
      }
      end.setHours(23, 59, 59, 999);
    }

    const newRange = {
      start: start.toISOString().split('T')[0],
      end: end.toISOString().split('T')[0],
      label: 'This Month',
    };

    setDateRange(newRange);
    localStorage.setItem('income-expenses-date-range', JSON.stringify(newRange));
  }, [orgSettings, customMonthStartDay]);

  // Wrapper to save date range changes to localStorage
  const handleDateRangeChange = (newRange: DateRange) => {
    setDateRange(newRange);
    localStorage.setItem('income-expenses-date-range', JSON.stringify(newRange));
  };

  // Wrapper to save groupBy changes to localStorage
  const handleGroupByChange = (newGroupBy: 'category' | 'label' | 'merchant' | 'account') => {
    setGroupBy(newGroupBy);
    localStorage.setItem('income-expenses-group-by', newGroupBy);
  };

  // Reset drill-down states when groupBy changes
  useEffect(() => {
    setIncomeDrillDown({ level: 'categories' });
    setExpenseDrillDown({ level: 'categories' });
    setHiddenItems(new Set()); // Clear hidden items when switching grouping
  }, [groupBy]);

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['income-expenses-summary', dateRange.start, dateRange.end, groupBy, selectedUserId],
    queryFn: async () => {
      let endpoint = '/income-expenses/summary';
      if (groupBy === 'label') endpoint = '/income-expenses/label-summary';
      else if (groupBy === 'merchant') endpoint = '/income-expenses/merchant-summary';
      else if (groupBy === 'account') endpoint = '/income-expenses/account-summary';

      const params = new URLSearchParams({
        start_date: dateRange.start,
        end_date: dateRange.end,
      });
      if (selectedUserId) {
        params.append('user_id', selectedUserId);
      }

      const response = await api.get<IncomeExpenseSummary>(`${endpoint}?${params.toString()}`);
      return response.data;
    },
  });

  const { data: trend, isLoading: trendLoading } = useQuery({
    queryKey: ['income-expenses-trend', dateRange.start, dateRange.end, selectedUserId],
    queryFn: async () => {
      const params = new URLSearchParams({
        start_date: dateRange.start,
        end_date: dateRange.end,
      });
      if (selectedUserId) {
        params.append('user_id', selectedUserId);
      }

      const response = await api.get<MonthlyTrend[]>(`/income-expenses/trend?${params.toString()}`);
      return response.data;
    },
  });

  // Fetch category drill-down when clicking on a category
  const { data: categoryDrillDown } = useQuery({
    queryKey: ['income-expenses-category-drill-down', dateRange.start, dateRange.end, incomeDrillDown.category, expenseDrillDown.category, selectedUserId],
    queryFn: async () => {
      const parentCategory = incomeDrillDown.category || expenseDrillDown.category;
      if (!parentCategory) return null;

      const params = new URLSearchParams({
        start_date: dateRange.start,
        end_date: dateRange.end,
        parent_category: parentCategory,
      });
      if (selectedUserId) {
        params.append('user_id', selectedUserId);
      }

      try {
        const response = await api.get<IncomeExpenseSummary>(`/income-expenses/category-drill-down?${params.toString()}`);
        console.log('[CATEGORY DRILL-DOWN] Fetched data for parent:', parentCategory, {
          income_categories: response.data.income_categories,
          expense_categories: response.data.expense_categories
        });
        return response.data;
      } catch (error) {
        console.error('[CATEGORY DRILL-DOWN] Error fetching drill-down:', error);
        return null;
      }
    },
    enabled: groupBy === 'category' && (
      (incomeDrillDown.level === 'merchants' && !!incomeDrillDown.category) ||
      (expenseDrillDown.level === 'merchants' && !!expenseDrillDown.category)
    ),
  });

  // Debug log when categoryDrillDown data changes
  useEffect(() => {
    console.log('[CATEGORY DRILL-DOWN DATA CHANGE]', {
      hasCategoryDrillDown: !!categoryDrillDown,
      incomeCategories: categoryDrillDown?.income_categories?.length || 0,
      expenseCategories: categoryDrillDown?.expense_categories?.length || 0,
      incomeData: categoryDrillDown?.income_categories,
      expenseData: categoryDrillDown?.expense_categories,
    });
  }, [categoryDrillDown]);

  // Fetch merchant breakdown when drilling down
  const { data: incomeMerchants } = useQuery({
    queryKey: ['income-merchants', dateRange.start, dateRange.end, incomeDrillDown.category, incomeDrillDown.accountId, groupBy, selectedUserId],
    queryFn: async () => {
      let endpoint = '/income-expenses/merchants';
      let paramName = 'category';
      let paramValue = incomeDrillDown.category || '';

      if (groupBy === 'label') {
        endpoint = '/income-expenses/label-merchants';
        paramName = 'label';
      } else if (groupBy === 'account') {
        endpoint = '/income-expenses/account-merchants';
        paramName = 'account_id';
        paramValue = incomeDrillDown.accountId || '';
      }

      const params = new URLSearchParams({
        start_date: dateRange.start,
        end_date: dateRange.end,
        transaction_type: 'income',
        [paramName]: paramValue,
      });
      if (selectedUserId) {
        params.append('user_id', selectedUserId);
      }

      const response = await api.get<CategoryBreakdown[]>(`${endpoint}?${params.toString()}`);
      return response.data;
    },
    enabled: incomeDrillDown.level === 'merchants' && (groupBy === 'account' ? !!incomeDrillDown.accountId : !!incomeDrillDown.category),
  });

  const { data: expenseMerchants } = useQuery({
    queryKey: ['expense-merchants', dateRange.start, dateRange.end, expenseDrillDown.category, expenseDrillDown.accountId, groupBy, selectedUserId],
    queryFn: async () => {
      let endpoint = '/income-expenses/merchants';
      let paramName = 'category';
      let paramValue = expenseDrillDown.category || '';

      if (groupBy === 'label') {
        endpoint = '/income-expenses/label-merchants';
        paramName = 'label';
      } else if (groupBy === 'account') {
        endpoint = '/income-expenses/account-merchants';
        paramName = 'account_id';
        paramValue = expenseDrillDown.accountId || '';
      }

      const params = new URLSearchParams({
        start_date: dateRange.start,
        end_date: dateRange.end,
        transaction_type: 'expense',
        [paramName]: paramValue,
      });
      if (selectedUserId) {
        params.append('user_id', selectedUserId);
      }

      const response = await api.get<CategoryBreakdown[]>(`${endpoint}?${params.toString()}`);
      return response.data;
    },
    enabled: expenseDrillDown.level === 'merchants' && (groupBy === 'account' ? !!expenseDrillDown.accountId : !!expenseDrillDown.category),
  });

  // Fetch ALL transactions for the date range (with infinite loading)
  const { data: allTransactionsData, isLoading: transactionsLoading } = useQuery({
    queryKey: ['all-transactions-infinite', dateRange.start, dateRange.end],
    queryFn: async () => {
      let allTransactions: Transaction[] = [];
      let cursor: string | null = null;
      let hasMore = true;

      // Keep fetching until we have all transactions
      while (hasMore) {
        const params = new URLSearchParams({
          start_date: dateRange.start,
          end_date: dateRange.end,
          page_size: '500', // Fetch in batches of 500
        });
        if (cursor) {
          params.append('cursor', cursor);
        }

        const response = await api.get<any>(`/transactions/?${params.toString()}`);
        allTransactions = [...allTransactions, ...response.data.transactions];
        hasMore = response.data.has_more;
        cursor = response.data.next_cursor;
      }

      return allTransactions;
    },
  });

  // Split into income and expense transactions
  const allIncomeTransactions = useMemo(
    () => allTransactionsData?.filter(t => t.amount > 0) || [],
    [allTransactionsData]
  );

  const allExpenseTransactions = useMemo(
    () => allTransactionsData?.filter(t => t.amount < 0) || [],
    [allTransactionsData]
  );

  // Filter summary data to exclude hidden items
  const filteredSummary = useMemo(() => {
    if (!summary || hiddenItems.size === 0) return summary;
    return {
      ...summary,
      income_categories: summary.income_categories?.filter(
        item => !hiddenItems.has(item.category)
      ),
      expense_categories: summary.expense_categories?.filter(
        item => !hiddenItems.has(item.category)
      ),
    };
  }, [summary, hiddenItems]);

  // Get unique items (categories or labels) from summary
  const uniqueItems = useMemo(() => {
    if (!summary) return [];
    const items = new Set<string>();
    summary.income_categories?.forEach(item => items.add(item.category));
    summary.expense_categories?.forEach(item => items.add(item.category));
    return Array.from(items).sort();
  }, [summary]);

  // Filter transactions based on drill-down state and hidden items
  const incomeTransactions = useMemo(() => {
    if (!allIncomeTransactions) return [];

    console.log('[INCOME TRANSACTIONS FILTER]', {
      totalTransactions: allIncomeTransactions.length,
      incomeDrillDown,
      groupBy,
    });

    let filtered = allIncomeTransactions;

    // Filter out transactions with hidden categories/labels
    if (hiddenItems.size > 0) {
      if (groupBy === 'label') {
        // For labels: exclude if transaction has any hidden label
        filtered = filtered.filter(t => {
          if (!t.labels || t.labels.length === 0) return !hiddenItems.has('Unlabeled');
          return !t.labels.some(label => hiddenItems.has(label.name));
        });
      } else {
        // For categories: exclude if transaction category is hidden
        filtered = filtered.filter(t => {
          if (!t.category_primary) return !hiddenItems.has('Uncategorized');
          return !hiddenItems.has(t.category_primary);
        });
      }
    }

    // Filter by category/label/account if drilling down
    if (incomeDrillDown.category) {
      if (groupBy === 'label') {
        // Filter by label - check if transaction has the label
        if (incomeDrillDown.category === 'Unlabeled') {
          filtered = filtered.filter(t => !t.labels || t.labels.length === 0);
        } else {
          filtered = filtered.filter(t =>
            t.labels?.some(label => label.name === incomeDrillDown.category)
          );
        }
      } else if (groupBy === 'account') {
        // Filter by account ID
        if (incomeDrillDown.accountId) {
          filtered = filtered.filter(t => t.account_id === incomeDrillDown.accountId);
        }
      } else {
        // Filter by category
        filtered = filtered.filter(t => t.category_primary === incomeDrillDown.category);
      }
    }

    // Filter by merchant if drilling down to that level
    if (incomeDrillDown.merchant) {
      console.log('[INCOME MERCHANT FILTER]', {
        merchant: incomeDrillDown.merchant,
        beforeFilter: filtered.length,
        uniqueMerchants: [...new Set(filtered.map(t => t.merchant_name))],
      });
      filtered = filtered.filter(t => t.merchant_name === incomeDrillDown.merchant);
      console.log('[INCOME MERCHANT FILTER] After filter:', filtered.length);
    }

    return filtered;
  }, [allIncomeTransactions, incomeDrillDown, groupBy, hiddenItems]);

  const expenseTransactions = useMemo(() => {
    if (!allExpenseTransactions) return [];

    let filtered = allExpenseTransactions;

    // Filter out transactions with hidden categories/labels
    if (hiddenItems.size > 0) {
      if (groupBy === 'label') {
        // For labels: exclude if transaction has any hidden label
        filtered = filtered.filter(t => {
          if (!t.labels || t.labels.length === 0) return !hiddenItems.has('Unlabeled');
          return !t.labels.some(label => hiddenItems.has(label.name));
        });
      } else {
        // For categories: exclude if transaction category is hidden
        filtered = filtered.filter(t => {
          if (!t.category_primary) return !hiddenItems.has('Uncategorized');
          return !hiddenItems.has(t.category_primary);
        });
      }
    }

    // Filter by category/label/account if drilling down
    if (expenseDrillDown.category) {
      if (groupBy === 'label') {
        // Filter by label - check if transaction has the label
        if (expenseDrillDown.category === 'Unlabeled') {
          filtered = filtered.filter(t => !t.labels || t.labels.length === 0);
        } else {
          filtered = filtered.filter(t =>
            t.labels?.some(label => label.name === expenseDrillDown.category)
          );
        }
      } else if (groupBy === 'account') {
        // Filter by account ID
        if (expenseDrillDown.accountId) {
          filtered = filtered.filter(t => t.account_id === expenseDrillDown.accountId);
        }
      } else {
        // Filter by category
        filtered = filtered.filter(t => t.category_primary === expenseDrillDown.category);
      }
    }

    // Filter by merchant if drilling down to that level
    if (expenseDrillDown.merchant) {
      filtered = filtered.filter(t => t.merchant_name === expenseDrillDown.merchant);
    }

    return filtered;
  }, [allExpenseTransactions, expenseDrillDown, groupBy, hiddenItems]);

  // Calculate statistics for both income and expenses
  const incomeStats = useMemo(() => {
    if (!incomeTransactions || incomeTransactions.length === 0) {
      return null;
    }

    const total = incomeTransactions.reduce((sum, t) => sum + Number(t.amount || 0), 0);
    const avg = total / incomeTransactions.length;

    // Find min and max transactions
    const minTransaction = incomeTransactions.reduce((min, t) =>
      Number(t.amount || 0) < Number(min.amount || 0) ? t : min
    );
    const maxTransaction = incomeTransactions.reduce((max, t) =>
      Number(t.amount || 0) > Number(max.amount || 0) ? t : max
    );

    // Top and lowest payees by total amount with transaction references
    const merchantMap = new Map<string, { total: number; count: number; transactions: Transaction[] }>();
    incomeTransactions.forEach(t => {
      const merchant = t.merchant_name || 'Unknown';
      const existing = merchantMap.get(merchant) || { total: 0, count: 0, transactions: [] };
      merchantMap.set(merchant, {
        total: existing.total + Number(t.amount || 0),
        count: existing.count + 1,
        transactions: [...existing.transactions, t],
      });
    });

    const merchantArray = Array.from(merchantMap.entries()).map(([name, data]) => ({
      name,
      ...data,
    }));

    const topPayee = merchantArray.sort((a, b) => b.total - a.total)[0];
    const mostTransactionsMerchant = merchantArray.sort((a, b) => b.count - a.count)[0];

    return {
      totalTransactions: incomeTransactions.length,
      totalAmount: total,
      avgAmount: avg,
      minAmount: Number(minTransaction.amount || 0),
      maxAmount: Number(maxTransaction.amount || 0),
      minTransaction,
      maxTransaction,
      topPayee,
      mostTransactions: mostTransactionsMerchant,
    };
  }, [incomeTransactions]);

  const expenseStats = useMemo(() => {
    if (!expenseTransactions || expenseTransactions.length === 0) {
      return null;
    }

    const total = expenseTransactions.reduce((sum, t) => sum + Math.abs(t.amount || 0), 0);
    const avg = total / expenseTransactions.length;

    // Find min and max transactions
    const minTransaction = expenseTransactions.reduce((min, t) =>
      Math.abs(t.amount || 0) < Math.abs(min.amount || 0) ? t : min
    );
    const maxTransaction = expenseTransactions.reduce((max, t) =>
      Math.abs(t.amount || 0) > Math.abs(max.amount || 0) ? t : max
    );

    // Top and lowest merchants by total amount with transaction references
    const merchantMap = new Map<string, { total: number; count: number; transactions: Transaction[] }>();
    expenseTransactions.forEach(t => {
      const merchant = t.merchant_name || 'Unknown';
      const existing = merchantMap.get(merchant) || { total: 0, count: 0, transactions: [] };
      merchantMap.set(merchant, {
        total: existing.total + Math.abs(t.amount || 0),
        count: existing.count + 1,
        transactions: [...existing.transactions, t],
      });
    });

    const merchantArray = Array.from(merchantMap.entries()).map(([name, data]) => ({
      name,
      ...data,
    }));

    const topMerchant = merchantArray.sort((a, b) => b.total - a.total)[0];
    const mostTransactionsMerchant = merchantArray.sort((a, b) => b.count - a.count)[0];

    return {
      totalTransactions: expenseTransactions.length,
      totalAmount: total,
      avgAmount: avg,
      minAmount: Math.abs(minTransaction.amount || 0),
      maxAmount: Math.abs(maxTransaction.amount || 0),
      minTransaction,
      maxTransaction,
      topMerchant,
      mostTransactions: mostTransactionsMerchant,
    };
  }, [expenseTransactions]);

  const combinedStats = useMemo(() => {
    const allTransactions = [
      ...(allIncomeTransactions || []),
      ...(allExpenseTransactions || []),
    ];

    if (allTransactions.length === 0) {
      return null;
    }

    // Income statistics
    const income = allIncomeTransactions || [];
    const totalIncome = income.reduce((sum, t) => sum + Number(t.amount || 0), 0);
    const avgReceived = income.length > 0 ? totalIncome / income.length : 0;

    const minReceivedTransaction = income.length > 0
      ? income.reduce((min, t) => Number(t.amount || 0) < Number(min.amount || 0) ? t : min)
      : null;
    const maxReceivedTransaction = income.length > 0
      ? income.reduce((max, t) => Number(t.amount || 0) > Number(max.amount || 0) ? t : max)
      : null;

    // Expense statistics
    const expenses = allExpenseTransactions || [];
    const totalExpense = expenses.reduce((sum, t) => sum + Math.abs(t.amount || 0), 0);
    const avgSpent = expenses.length > 0 ? totalExpense / expenses.length : 0;

    const minSpentTransaction = expenses.length > 0
      ? expenses.reduce((min, t) => Math.abs(t.amount || 0) < Math.abs(min.amount || 0) ? t : min)
      : null;
    const maxSpentTransaction = expenses.length > 0
      ? expenses.reduce((max, t) => Math.abs(t.amount || 0) > Math.abs(max.amount || 0) ? t : max)
      : null;

    // Income merchant data
    const incomeSourceMap = new Map<string, { total: number; count: number; transactions: Transaction[] }>();
    income.forEach(t => {
      const source = t.merchant_name || 'Unknown';
      const existing = incomeSourceMap.get(source) || { total: 0, count: 0, transactions: [] };
      incomeSourceMap.set(source, {
        total: existing.total + Number(t.amount || 0),
        count: existing.count + 1,
        transactions: [...existing.transactions, t],
      });
    });

    const incomeSourceArray = Array.from(incomeSourceMap.entries()).map(([name, data]) => ({
      name,
      ...data,
    }));

    const topSource = incomeSourceArray.sort((a, b) => b.total - a.total)[0];
    const mostIncomeTransactions = incomeSourceArray.sort((a, b) => b.count - a.count)[0];

    // Expense merchant data
    const merchantMap = new Map<string, { total: number; count: number; transactions: Transaction[] }>();
    expenses.forEach(t => {
      const merchant = t.merchant_name || 'Unknown';
      const existing = merchantMap.get(merchant) || { total: 0, count: 0, transactions: [] };
      merchantMap.set(merchant, {
        total: existing.total + Math.abs(t.amount || 0),
        count: existing.count + 1,
        transactions: [...existing.transactions, t],
      });
    });

    const merchantArray = Array.from(merchantMap.entries()).map(([name, data]) => ({
      name,
      ...data,
    }));

    const topPayee = merchantArray.sort((a, b) => b.total - a.total)[0];
    const mostExpenseTransactions = merchantArray.sort((a, b) => b.count - a.count)[0];

    return {
      totalTransactions: allTransactions.length,
      // Income stats
      totalReceived: totalIncome,
      avgReceived,
      minReceived: minReceivedTransaction ? Number(minReceivedTransaction.amount || 0) : 0,
      maxReceived: maxReceivedTransaction ? Number(maxReceivedTransaction.amount || 0) : 0,
      minReceivedTransaction,
      maxReceivedTransaction,
      topSource,
      mostIncomeTransactions,
      // Expense stats
      totalSpent: totalExpense,
      avgSpent,
      minSpent: minSpentTransaction ? Math.abs(minSpentTransaction.amount || 0) : 0,
      maxSpent: maxSpentTransaction ? Math.abs(maxSpentTransaction.amount || 0) : 0,
      minSpentTransaction,
      maxSpentTransaction,
      topPayee,
      mostExpenseTransactions,
    };
  }, [allIncomeTransactions, allExpenseTransactions]);

  // Create transaction breakdown for pie chart
  const incomeTransactionBreakdown = useMemo(() => {
    if (!incomeTransactions) return [];

    const total = incomeTransactions.reduce((sum, t) => sum + Number(t.amount || 0), 0);

    console.log('[INCOME TRANSACTION BREAKDOWN]', {
      transactionCount: incomeTransactions.length,
      total,
      sampleAmounts: incomeTransactions.slice(0, 3).map(t => ({ merchant: t.merchant_name, amount: t.amount, type: typeof t.amount })),
    });

    return incomeTransactions.map(t => ({
      category: `${t.merchant_name} - ${formatDate(t.date)}`,
      amount: Number(t.amount || 0),
      count: 1,
      percentage: total > 0 ? (Number(t.amount || 0) / total) * 100 : 0,
      transaction: t,
    }));
  }, [incomeTransactions]);

  const expenseTransactionBreakdown = useMemo(() => {
    if (!expenseTransactions) return [];

    const total = expenseTransactions.reduce((sum, t) => sum + Math.abs(Number(t.amount || 0)), 0);

    return expenseTransactions.map(t => ({
      category: `${t.merchant_name} - ${formatDate(t.date)}`,
      amount: Math.abs(Number(t.amount || 0)),
      count: 1,
      percentage: total > 0 ? (Math.abs(Number(t.amount || 0)) / total) * 100 : 0,
      transaction: t,
    }));
  }, [expenseTransactions]);

  const handleCategoryClick = (category: string, type: 'income' | 'expense', has_children?: boolean) => {
    console.log('[CATEGORY CLICK]', {
      category,
      type,
      has_children,
      groupBy,
      currentLevel: type === 'income' ? incomeDrillDown.level : expenseDrillDown.level
    });

    // When in category grouping mode:
    // - If category has children → drill down to show child categories
    // - If no children → show merchants
    // - If already at merchants level viewing child categories → preserve parent category
    if (type === 'income') {
      const currentState = incomeDrillDown;
      // If we're at merchants level and clicking a child category, preserve the current category as parent
      if (currentState.level === 'merchants' && currentState.category) {
        setIncomeDrillDown({ level: 'merchants', category, parentCategory: currentState.category });
      } else {
        setIncomeDrillDown({ level: 'merchants', category });
      }
    } else {
      const currentState = expenseDrillDown;
      // If we're at merchants level and clicking a child category, preserve the current category as parent
      if (currentState.level === 'merchants' && currentState.category) {
        setExpenseDrillDown({ level: 'merchants', category, parentCategory: currentState.category });
      } else {
        setExpenseDrillDown({ level: 'merchants', category });
      }
    }
  };

  const handleMerchantClick = (merchant: string, type: 'income' | 'expense') => {
    if (type === 'income') {
      setIncomeDrillDown(prev => ({ ...prev, level: 'transactions', merchant }));
    } else {
      setExpenseDrillDown(prev => ({ ...prev, level: 'transactions', merchant }));
    }
  };

  const handleAccountClick = (accountName: string, accountId: string, type: 'income' | 'expense') => {
    console.log('[ACCOUNT CLICK]', {
      accountName,
      accountId,
      type,
      groupBy,
    });

    // For account grouping: drill down to show merchants within this account
    if (type === 'income') {
      setIncomeDrillDown({ level: 'merchants', category: accountName, accountId });
    } else {
      setExpenseDrillDown({ level: 'merchants', category: accountName, accountId });
    }
  };

  const handleBreadcrumbClick = (type: 'income' | 'expense', level: DrillDownLevel) => {
    console.log('[BREADCRUMB CLICK]', {
      type,
      level,
      currentState: type === 'income' ? incomeDrillDown : expenseDrillDown,
      groupBy
    });

    if (type === 'income') {
      if (level === 'categories') {
        setIncomeDrillDown({ level: 'categories' });
      } else if (level === 'merchants') {
        // Preserve parentCategory when going back to merchants level
        setIncomeDrillDown(prev => ({ level: 'merchants', category: prev.category, parentCategory: prev.parentCategory }));
      }
    } else {
      if (level === 'categories') {
        setExpenseDrillDown({ level: 'categories' });
      } else if (level === 'merchants') {
        // Preserve parentCategory when going back to merchants level
        setExpenseDrillDown(prev => ({ level: 'merchants', category: prev.category, parentCategory: prev.parentCategory }));
      }
    }
  };

  const handleTransactionClick = (txn: Transaction) => {
    setSelectedTransaction(txn);
    onDetailOpen();
  };

  const handleCreateRule = (transaction: Transaction) => {
    setRuleTransaction(transaction);
    onRuleOpen();
  };

  const handleSort = (field: SortField, type: 'income' | 'expense') => {
    if (type === 'income') {
      if (incomeSortField === field) {
        setIncomeSortDirection(incomeSortDirection === 'asc' ? 'desc' : 'asc');
      } else {
        setIncomeSortField(field);
        setIncomeSortDirection(field === 'date' || field === 'amount' ? 'desc' : 'asc');
      }
    } else {
      if (expenseSortField === field) {
        setExpenseSortDirection(expenseSortDirection === 'asc' ? 'desc' : 'asc');
      } else {
        setExpenseSortField(field);
        setExpenseSortDirection(field === 'date' || field === 'amount' ? 'desc' : 'asc');
      }
    }
  };

  const sortTransactions = (transactions: Transaction[] | undefined, sortField: SortField, sortDirection: SortDirection) => {
    if (!transactions) return [];

    return [...transactions].sort((a, b) => {
      let aVal: any;
      let bVal: any;

      switch (sortField) {
        case 'date':
          aVal = new Date(a.date).getTime();
          bVal = new Date(b.date).getTime();
          break;
        case 'merchant_name':
          aVal = a.merchant_name?.toLowerCase() || '';
          bVal = b.merchant_name?.toLowerCase() || '';
          break;
        case 'amount':
          aVal = Math.abs(Number(a.amount));
          bVal = Math.abs(Number(b.amount));
          break;
        default:
          return 0;
      }

      if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
  };

  // Calculate totals from filtered summary (must be before early returns for hooks)
  const filteredTotals = useMemo(() => {
    if (!filteredSummary) return { total_income: 0, total_expenses: 0, net: 0 };

    const total_income = filteredSummary.income_categories?.reduce(
      (sum, item) => sum + Number(item.amount || 0),
      0
    ) || 0;

    const total_expenses = Math.abs(
      filteredSummary.expense_categories?.reduce(
        (sum, item) => sum + Number(item.amount || 0),
        0
      ) || 0
    );

    return {
      total_income,
      total_expenses,
      net: total_income - total_expenses,
    };
  }, [filteredSummary]);

  const net = filteredTotals.net;

  if (summaryLoading || trendLoading || transactionsLoading) {
    return <IncomeExpensesSkeleton />;
  }

  const renderChart = (
    data: CategoryBreakdown[] | any[],
    type: 'income' | 'expense',
    chartType: ChartType,
    drillDown: DrillDownState,
    legendExpanded: boolean,
    setLegendExpanded: (expanded: boolean) => void
  ) => {
    // Handle empty data
    if (!data || data.length === 0) {
      return (
        <Box textAlign="center" py={10}>
          <Text color="gray.500">No data to display</Text>
        </Box>
      );
    }

    if (chartType === 'pie') {
      return (
        <ResponsiveContainer width="100%" height={380}>
          <PieChart>
            <Pie
              data={data}
              dataKey="amount"
              nameKey="category"
              cx="50%"
              cy="52%"
              outerRadius={100}
              label={(entry) => formatCurrency(entry.amount)}
              onClick={(entry) => {
                if (drillDown.level === 'categories') {
                  // In merchant grouping mode, top-level items are merchants, not categories
                  if (groupBy === 'merchant') {
                    handleMerchantClick(entry.category, type);
                  } else if (groupBy === 'account') {
                    // In account grouping mode, top-level items are accounts
                    handleAccountClick(entry.category, entry.id, type);
                  } else {
                    handleCategoryClick(entry.category, type, entry.has_children);
                  }
                } else if (drillDown.level === 'merchants') {
                  // Check if this is a child category or a merchant based on metadata
                  if ((entry as any)._isCategoryData) {
                    // This is a child category, update the category for merchant drill-down
                    handleCategoryClick(entry.category, type, entry.has_children);
                  } else if ((entry as any)._isMerchantData) {
                    // This is a merchant, drill down to transactions
                    handleMerchantClick(entry.category, type);
                  }
                } else if (drillDown.level === 'transactions' && entry.transaction) {
                  handleTransactionClick(entry.transaction);
                }
              }}
              style={{ cursor: 'pointer' }}
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: number) => formatCurrency(value)}
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload;
                  return (
                    <Box bg="white" p={3} borderWidth={1} borderRadius="md" boxShadow="md">
                      <Text fontWeight="bold">{data.category}</Text>
                      <Text color={type === 'income' ? 'green.600' : 'red.600'}>
                        {formatCurrency(data.amount)}
                      </Text>
                      <Text fontSize="sm" color="gray.600">
                        {(data.percentage || 0).toFixed(1)}%
                      </Text>
                    </Box>
                  );
                }
                return null;
              }}
            />
            <Legend
              content={(props: any) => {
                const { payload } = props;
                if (!payload || !payload.length) return null;

                const MAX_VISIBLE_ITEMS = 5;
                const displayItems = legendExpanded ? payload : payload.slice(0, MAX_VISIBLE_ITEMS);
                const hasMore = payload.length > MAX_VISIBLE_ITEMS;

                return (
                  <Box mt={4}>
                    <Wrap spacing={2} justify="center">
                      {displayItems.map((entry: any, index: number) => {
                        const data = entry.payload;
                        return (
                          <WrapItem key={`legend-${index}`}>
                            <HStack
                              spacing={2}
                              cursor="pointer"
                              px={2}
                              py={1}
                              borderRadius="md"
                              _hover={{ bg: 'gray.100' }}
                              onClick={() => {
                                if (drillDown.level === 'categories') {
                                  // In merchant grouping mode, top-level items are merchants, not categories
                                  if (groupBy === 'merchant') {
                                    handleMerchantClick(data.category, type);
                                  } else if (groupBy === 'account') {
                                    // In account grouping mode, top-level items are accounts
                                    handleAccountClick(data.category, data.id, type);
                                  } else {
                                    handleCategoryClick(data.category, type, data.has_children);
                                  }
                                } else if (drillDown.level === 'merchants') {
                                  // Check if this is a child category or a merchant based on metadata
                                  if ((data as any)._isCategoryData) {
                                    handleCategoryClick(data.category, type, data.has_children);
                                  } else if ((data as any)._isMerchantData) {
                                    handleMerchantClick(data.category, type);
                                  }
                                } else if (drillDown.level === 'transactions' && data.transaction) {
                                  handleTransactionClick(data.transaction);
                                }
                              }}
                            >
                              <Box w={3} h={3} bg={entry.color} borderRadius="sm" />
                              <Text fontSize="sm">
                                {entry.value} ({data.percentage.toFixed(1)}%)
                              </Text>
                            </HStack>
                          </WrapItem>
                        );
                      })}
                      {hasMore && (
                        <WrapItem>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => setLegendExpanded(!legendExpanded)}
                            rightIcon={legendExpanded ? <ChevronUpIcon /> : <ChevronDownIcon />}
                          >
                            {legendExpanded ? 'Show Less' : `Show ${payload.length - MAX_VISIBLE_ITEMS} More`}
                          </Button>
                        </WrapItem>
                      )}
                    </Wrap>
                  </Box>
                );
              }}
            />
          </PieChart>
        </ResponsiveContainer>
      );
    } else {
      return (
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" />
            <YAxis dataKey="category" type="category" width={150} />
            <Tooltip formatter={(value: number) => formatCurrency(value)} />
            <Bar
              dataKey="amount"
              onClick={(entry) => {
                if (drillDown.level === 'categories') {
                  handleCategoryClick(entry.category, type, entry.has_children);
                } else if (drillDown.level === 'merchants') {
                  // Check if this is a child category or a merchant based on metadata
                  if ((entry as any)._isCategoryData) {
                    // This is a child category, update the category for merchant drill-down
                    handleCategoryClick(entry.category, type, entry.has_children);
                  } else if ((entry as any)._isMerchantData) {
                    // This is a merchant, drill down to transactions
                    handleMerchantClick(entry.category, type);
                  }
                } else if (drillDown.level === 'transactions' && entry.transaction) {
                  handleTransactionClick(entry.transaction);
                }
              }}
              style={{ cursor: 'pointer' }}
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      );
    }
  };

  const SortIcon = ({ field, currentField, direction }: { field: SortField; currentField: SortField; direction: SortDirection }) => {
    if (currentField !== field) return null;
    return direction === 'asc' ? <ChevronUpIcon /> : <ChevronDownIcon />;
  };

  const renderTransactionTable = (
    transactions: Transaction[] | undefined,
    type: 'income' | 'expense',
    sortField: SortField,
    sortDirection: SortDirection
  ) => {
    const sorted = sortTransactions(transactions, sortField, sortDirection);

    if (!sorted || sorted.length === 0) {
      return (
        <Text color="gray.500" textAlign="center" py={8}>
          No transactions found
        </Text>
      );
    }

    return (
      <Box overflowX="auto">
        <Table variant="simple" size="sm">
          <Thead bg="gray.50">
            <Tr>
              <Th
                cursor="pointer"
                onClick={() => handleSort('date', type)}
                _hover={{ bg: 'gray.100' }}
              >
                <HStack spacing={1}>
                  <Text>Date</Text>
                  <SortIcon field="date" currentField={sortField} direction={sortDirection} />
                </HStack>
              </Th>
              <Th
                cursor="pointer"
                onClick={() => handleSort('merchant_name', type)}
                _hover={{ bg: 'gray.100' }}
              >
                <HStack spacing={1}>
                  <Text>Merchant</Text>
                  <SortIcon field="merchant_name" currentField={sortField} direction={sortDirection} />
                </HStack>
              </Th>
              <Th>Category</Th>
              <Th>Labels</Th>
              <Th
                isNumeric
                cursor="pointer"
                onClick={() => handleSort('amount', type)}
                _hover={{ bg: 'gray.100' }}
              >
                <HStack spacing={1} justify="flex-end">
                  <Text>Amount</Text>
                  <SortIcon field="amount" currentField={sortField} direction={sortDirection} />
                </HStack>
              </Th>
            </Tr>
          </Thead>
          <Tbody>
            {sorted.map((txn) => (
              <Tr
                key={txn.id}
                onClick={() => handleTransactionClick(txn)}
                cursor="pointer"
                _hover={{ bg: 'gray.50' }}
              >
                <Td>{formatDate(txn.date)}</Td>
                <Td>
                  <Text fontWeight="medium">{txn.merchant_name}</Text>
                  {txn.description && (
                    <Text fontSize="xs" color="gray.600">
                      {txn.description}
                    </Text>
                  )}
                </Td>
                <Td>
                  {txn.category_primary && (
                    <Badge colorScheme="blue" fontSize="xs">
                      {txn.category_primary}
                    </Badge>
                  )}
                </Td>
                <Td>
                  <Wrap spacing={1}>
                    {txn.labels?.map((label) => (
                      <WrapItem key={label.id}>
                        <Badge
                          colorScheme={label.is_income ? 'green' : 'purple'}
                          fontSize="xs"
                        >
                          {label.name}
                        </Badge>
                      </WrapItem>
                    ))}
                  </Wrap>
                </Td>
                <Td isNumeric>
                  <Text
                    fontWeight="semibold"
                    color={txn.amount >= 0 ? 'green.600' : 'red.600'}
                  >
                    {formatCurrency(Math.abs(txn.amount))}
                  </Text>
                </Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
      </Box>
    );
  };

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={8} align="stretch">
        {/* Header with Date Range Picker */}
        <HStack justify="space-between" align="start">
          <Box>
            <Heading size="lg" mb={2}>Cash Flow</Heading>
            <Text color="gray.600">
              Analyze your income sources and spending patterns
            </Text>
          </Box>
          <DateRangePicker value={dateRange} onChange={handleDateRangeChange} customMonthStartDay={customMonthStartDay} />
        </HStack>

        {/* Group By Toggle */}
        <HStack>
          <Text fontSize="sm" fontWeight="medium" color="gray.600">
            Group by:
          </Text>
          <ButtonGroup size="sm" isAttached variant="outline">
            <Button
              colorScheme={groupBy === 'category' ? 'brand' : 'gray'}
              onClick={() => handleGroupByChange('category')}
              bg={groupBy === 'category' ? 'brand.50' : 'white'}
            >
              Category
            </Button>
            <Button
              colorScheme={groupBy === 'label' ? 'brand' : 'gray'}
              onClick={() => handleGroupByChange('label')}
              bg={groupBy === 'label' ? 'brand.50' : 'white'}
            >
              Labels
            </Button>
            <Button
              colorScheme={groupBy === 'merchant' ? 'brand' : 'gray'}
              onClick={() => handleGroupByChange('merchant')}
              bg={groupBy === 'merchant' ? 'brand.50' : 'white'}
            >
              Merchant
            </Button>
            <Button
              colorScheme={groupBy === 'account' ? 'brand' : 'gray'}
              onClick={() => handleGroupByChange('account')}
              bg={groupBy === 'account' ? 'brand.50' : 'white'}
            >
              Account
            </Button>
          </ButtonGroup>

          {/* Filter Dropdown */}
          {uniqueItems.length > 0 && (
            <Menu closeOnSelect={false}>
              <MenuButton as={Button} size="sm" variant="outline" ml={4}>
                Hide {groupBy === 'category' ? 'Categories' : groupBy === 'label' ? 'Labels' : groupBy === 'merchant' ? 'Merchants' : 'Accounts'} ({hiddenItems.size})
              </MenuButton>
              <MenuList maxH="400px" overflowY="auto">
                {uniqueItems.map((item) => (
                  <MenuItem
                    key={item}
                    onClick={() => {
                      const newHidden = new Set(hiddenItems);
                      if (hiddenItems.has(item)) {
                        newHidden.delete(item);
                      } else {
                        newHidden.add(item);
                      }
                      setHiddenItems(newHidden);
                    }}
                  >
                    <Checkbox isChecked={!hiddenItems.has(item)} pointerEvents="none">
                      {item}
                    </Checkbox>
                  </MenuItem>
                ))}
              </MenuList>
            </Menu>
          )}
        </HStack>

        {/* Summary Cards */}
        <SimpleGrid columns={{ base: 1, md: 3 }} spacing={6}>
          <Card>
            <CardBody>
              <Stat>
                <StatLabel>Total Income</StatLabel>
                <StatNumber color="green.600">
                  {formatCurrency(filteredTotals.total_income)}
                </StatNumber>
                <StatHelpText>{dateRange.label}</StatHelpText>
              </Stat>
            </CardBody>
          </Card>

          <Card>
            <CardBody>
              <Stat>
                <StatLabel>Total Expenses</StatLabel>
                <StatNumber color="red.600">
                  {formatCurrency(filteredTotals.total_expenses)}
                </StatNumber>
                <StatHelpText>{dateRange.label}</StatHelpText>
              </Stat>
            </CardBody>
          </Card>

          <Card>
            <CardBody>
              <Stat>
                <StatLabel>Net</StatLabel>
                <StatNumber color={net >= 0 ? 'green.600' : 'red.600'}>
                  {net >= 0 ? '+' : ''}
                  {formatCurrency(net)}
                </StatNumber>
                <StatHelpText>
                  {net >= 0 ? 'Surplus' : 'Deficit'}
                </StatHelpText>
              </Stat>
            </CardBody>
          </Card>
        </SimpleGrid>

        {/* Tabs for Income, Expenses, Combined */}
        <Card>
          <CardBody>
            <Tabs index={selectedTab} onChange={setSelectedTab}>
              <TabList>
                <Tab>Combined</Tab>
                <Tab>Income</Tab>
                <Tab>Expenses</Tab>
              </TabList>

              <TabPanels>
                {/* Combined Tab */}
                <TabPanel>
                  <VStack spacing={6}>
                    {/* Summary Statistics for Combined View */}
                    {combinedStats && (
                      <>
                        <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4} w="full">
                          <Card size="sm">
                            <CardBody>
                              <Stat size="sm">
                                <StatLabel fontSize="xs">Total Received</StatLabel>
                                <StatNumber fontSize="lg" color="green.600">
                                  {formatCurrency(combinedStats.totalReceived)}
                                </StatNumber>
                              </Stat>
                            </CardBody>
                          </Card>
                          <Card size="sm">
                            <CardBody>
                              <Stat size="sm">
                                <StatLabel fontSize="xs">Total Spent</StatLabel>
                                <StatNumber fontSize="lg" color="red.600">
                                  {formatCurrency(combinedStats.totalSpent)}
                                </StatNumber>
                              </Stat>
                            </CardBody>
                          </Card>
                          <Card size="sm">
                            <CardBody>
                              <Stat size="sm">
                                <StatLabel fontSize="xs">Net Cashflow</StatLabel>
                                <StatNumber fontSize="lg" color={net >= 0 ? 'green.600' : 'red.600'}>
                                  {net >= 0 ? '+' : ''}{formatCurrency(net)}
                                </StatNumber>
                                <StatHelpText fontSize="xs">
                                  {combinedStats.totalTransactions} transactions
                                </StatHelpText>
                              </Stat>
                            </CardBody>
                          </Card>
                        </SimpleGrid>
                      </>
                    )}

                    {/* Monthly Trend Chart */}
                    {trend && trend.length > 0 && (
                      <Box w="full">
                        <Heading size="md" mb={4}>
                          Monthly Trend
                        </Heading>
                        <ResponsiveContainer width="100%" height={350}>
                          <BarChart data={trend}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="month" />
                            <YAxis />
                            <Tooltip
                              formatter={(value: number) => formatCurrency(value)}
                              contentStyle={{ backgroundColor: 'white', border: '1px solid #ccc' }}
                            />
                            <Legend />
                            <Bar dataKey="income" fill="#48BB78" name="Income" />
                            <Bar dataKey="expenses" fill="#F56565" name="Expenses" />
                            <Bar dataKey="net" fill="#4299E1" name="Net" />
                          </BarChart>
                        </ResponsiveContainer>
                      </Box>
                    )}

                    {/* Side by side categories */}
                    <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={6} w="full">
                      {/* Income Section */}
                      {summary && filteredSummary && filteredSummary.income_categories.length > 0 ? (
                        <VStack align="stretch" spacing={4}>
                          <HStack justify="space-between">
                            <Heading size="sm">
                              {groupBy === 'label' ? 'Income by Label' : groupBy === 'merchant' ? 'Income by Merchant' : groupBy === 'account' ? 'Income by Account' : 'Income by Category'}
                            </Heading>
                            <IconButton
                              aria-label={incomeChartType === 'pie' ? 'Switch to bar chart' : 'Switch to pie chart'}
                              icon={incomeChartType === 'pie' ? <IoBarChart /> : <IoPieChart />}
                              size="sm"
                              variant="ghost"
                              onClick={() => setIncomeChartType(incomeChartType === 'pie' ? 'bar' : 'pie')}
                            />
                          </HStack>
                          <Breadcrumb spacing="8px" separator={<ChevronRightIcon color="gray.500" />}>
                            <BreadcrumbItem>
                              <BreadcrumbLink
                                onClick={() => handleBreadcrumbClick('income', 'categories')}
                                color={incomeDrillDown.level === 'categories' ? 'brand.600' : 'gray.600'}
                                fontWeight={incomeDrillDown.level === 'categories' ? 'bold' : 'normal'}
                              >
                                {groupBy === 'label' ? 'All Labels' : groupBy === 'merchant' ? 'All Merchants' : groupBy === 'account' ? 'All Accounts' : 'All Categories'}
                              </BreadcrumbLink>
                            </BreadcrumbItem>
                            {incomeDrillDown.parentCategory && (
                              <BreadcrumbItem>
                                <BreadcrumbLink
                                  onClick={() => {
                                    // Go back to parent category level
                                    setIncomeDrillDown({ level: 'merchants', category: incomeDrillDown.parentCategory });
                                  }}
                                  color="gray.600"
                                  fontWeight="normal"
                                >
                                  {incomeDrillDown.parentCategory}
                                </BreadcrumbLink>
                              </BreadcrumbItem>
                            )}
                            {incomeDrillDown.category && (
                              <BreadcrumbItem>
                                <BreadcrumbLink
                                  onClick={() => handleBreadcrumbClick('income', 'merchants')}
                                  color={incomeDrillDown.level === 'merchants' ? 'brand.600' : 'gray.600'}
                                  fontWeight={incomeDrillDown.level === 'merchants' ? 'bold' : 'normal'}
                                >
                                  {incomeDrillDown.category}
                                </BreadcrumbLink>
                              </BreadcrumbItem>
                            )}
                            {incomeDrillDown.merchant && (
                              <BreadcrumbItem isCurrentPage>
                                <BreadcrumbLink color="brand.600" fontWeight="bold">
                                  {incomeDrillDown.merchant}
                                </BreadcrumbLink>
                              </BreadcrumbItem>
                            )}
                          </Breadcrumb>
                          {(() => {
                            console.log('[INCOME CHART RENDER]', {
                              level: incomeDrillDown.level,
                              groupBy,
                              category: incomeDrillDown.category,
                              hasCategoryDrillDown: !!categoryDrillDown,
                              categoryDrillDownData: categoryDrillDown?.income_categories?.length || 0,
                              hasMerchants: !!incomeMerchants,
                              merchantsCount: incomeMerchants?.length || 0,
                              filteredSummaryCount: filteredSummary?.income_categories?.length || 0,
                            });

                            console.log('[INCOME CHART - RENDERING]', {
                              level: incomeDrillDown.level,
                              groupBy,
                              merchant: incomeDrillDown.merchant,
                              transactionCount: incomeTransactions?.length || 0,
                              breakdownCount: incomeTransactionBreakdown?.length || 0,
                            });

                            if (incomeDrillDown.level === 'categories') {
                              return renderChart(filteredSummary?.income_categories || [], 'income', incomeChartType, incomeDrillDown, incomeLegendExpanded, setIncomeLegendExpanded);
                            } else if (incomeDrillDown.level === 'merchants') {
                              // For category grouping: try child categories first, fall back to merchants if no children
                              let data;
                              let isShowingCategories = false;
                              if (groupBy === 'category') {
                                const childCategories = categoryDrillDown?.income_categories || [];
                                // If no child categories, fall back to merchants (leaf category)
                                if (childCategories.length > 0) {
                                  // Mark as categories by adding a metadata property
                                  data = childCategories.map(cat => ({ ...cat, _isCategoryData: true }));
                                  isShowingCategories = true;
                                } else {
                                  // Mark as merchants by NOT having the metadata property
                                  data = (incomeMerchants || []).map(merch => ({ ...merch, _isMerchantData: true }));
                                  isShowingCategories = false;
                                }
                              } else {
                                data = (incomeMerchants || []).map(merch => ({ ...merch, _isMerchantData: true }));
                                isShowingCategories = false;
                              }
                              console.log('[INCOME CHART RENDER] Rendering', isShowingCategories ? 'child categories' : 'merchants', 'with data:', data.length, 'items');

                              return renderChart(data, 'income', incomeChartType, incomeDrillDown, incomeLegendExpanded, setIncomeLegendExpanded);
                            } else {
                              return renderChart(incomeTransactionBreakdown, 'income', incomeChartType, incomeDrillDown, incomeLegendExpanded, setIncomeLegendExpanded);
                            }
                          })()}
                          <Box>
                            <Heading size="xs" mb={3} color="gray.600">
                              Transactions {incomeDrillDown.category && `in ${incomeDrillDown.category}`}
                              {incomeDrillDown.merchant && ` at ${incomeDrillDown.merchant}`}
                            </Heading>
                            {renderTransactionTable(incomeTransactions, 'income', incomeSortField, incomeSortDirection)}
                          </Box>
                        </VStack>
                      ) : (
                        <Card>
                          <CardBody textAlign="center" py={8}>
                            <Text color="gray.600" fontWeight="semibold">
                              No income for the selected date range
                            </Text>
                            <Text color="gray.500" fontSize="sm" mt={1}>
                              Try selecting a different date range
                            </Text>
                          </CardBody>
                        </Card>
                      )}

                      {/* Expense Section */}
                      {summary && filteredSummary && filteredSummary.expense_categories.length > 0 ? (
                        <VStack align="stretch" spacing={4}>
                          <HStack justify="space-between">
                            <Heading size="sm">
                              {groupBy === 'label' ? 'Expenses by Label' : groupBy === 'merchant' ? 'Expenses by Merchant' : groupBy === 'account' ? 'Expenses by Account' : 'Expenses by Category'}
                            </Heading>
                            <IconButton
                              aria-label={expenseChartType === 'pie' ? 'Switch to bar chart' : 'Switch to pie chart'}
                              icon={expenseChartType === 'pie' ? <IoBarChart /> : <IoPieChart />}
                              size="sm"
                              variant="ghost"
                              onClick={() => setExpenseChartType(expenseChartType === 'pie' ? 'bar' : 'pie')}
                            />
                          </HStack>
                          <Breadcrumb spacing="8px" separator={<ChevronRightIcon color="gray.500" />}>
                            <BreadcrumbItem>
                              <BreadcrumbLink
                                onClick={() => handleBreadcrumbClick('expense', 'categories')}
                                color={expenseDrillDown.level === 'categories' ? 'brand.600' : 'gray.600'}
                                fontWeight={expenseDrillDown.level === 'categories' ? 'bold' : 'normal'}
                              >
                                {groupBy === 'label' ? 'All Labels' : groupBy === 'merchant' ? 'All Merchants' : groupBy === 'account' ? 'All Accounts' : 'All Categories'}
                              </BreadcrumbLink>
                            </BreadcrumbItem>
                            {expenseDrillDown.parentCategory && (
                              <BreadcrumbItem>
                                <BreadcrumbLink
                                  onClick={() => {
                                    // Go back to parent category level
                                    setExpenseDrillDown({ level: 'merchants', category: expenseDrillDown.parentCategory });
                                  }}
                                  color="gray.600"
                                  fontWeight="normal"
                                >
                                  {expenseDrillDown.parentCategory}
                                </BreadcrumbLink>
                              </BreadcrumbItem>
                            )}
                            {expenseDrillDown.category && (
                              <BreadcrumbItem>
                                <BreadcrumbLink
                                  onClick={() => handleBreadcrumbClick('expense', 'merchants')}
                                  color={expenseDrillDown.level === 'merchants' ? 'brand.600' : 'gray.600'}
                                  fontWeight={expenseDrillDown.level === 'merchants' ? 'bold' : 'normal'}
                                >
                                  {expenseDrillDown.category}
                                </BreadcrumbLink>
                              </BreadcrumbItem>
                            )}
                            {expenseDrillDown.merchant && (
                              <BreadcrumbItem isCurrentPage>
                                <BreadcrumbLink color="brand.600" fontWeight="bold">
                                  {expenseDrillDown.merchant}
                                </BreadcrumbLink>
                              </BreadcrumbItem>
                            )}
                          </Breadcrumb>
                          {(() => {
                            console.log('[EXPENSE CHART RENDER]', {
                              level: expenseDrillDown.level,
                              groupBy,
                              category: expenseDrillDown.category,
                              hasCategoryDrillDown: !!categoryDrillDown,
                              categoryDrillDownData: categoryDrillDown?.expense_categories?.length || 0,
                              hasMerchants: !!expenseMerchants,
                              merchantsCount: expenseMerchants?.length || 0,
                              filteredSummaryCount: filteredSummary?.expense_categories?.length || 0,
                            });

                            if (expenseDrillDown.level === 'categories') {
                              return renderChart(filteredSummary?.expense_categories || [], 'expense', expenseChartType, expenseDrillDown, expenseLegendExpanded, setExpenseLegendExpanded);
                            } else if (expenseDrillDown.level === 'merchants') {
                              // For category grouping: try child categories first, fall back to merchants if no children
                              let data;
                              let isShowingCategories = false;
                              if (groupBy === 'category') {
                                const childCategories = categoryDrillDown?.expense_categories || [];
                                // If no child categories, fall back to merchants (leaf category)
                                if (childCategories.length > 0) {
                                  // Mark as categories by adding a metadata property
                                  data = childCategories.map(cat => ({ ...cat, _isCategoryData: true }));
                                  isShowingCategories = true;
                                } else {
                                  // Mark as merchants by NOT having the metadata property
                                  data = (expenseMerchants || []).map(merch => ({ ...merch, _isMerchantData: true }));
                                  isShowingCategories = false;
                                }
                              } else {
                                data = (expenseMerchants || []).map(merch => ({ ...merch, _isMerchantData: true }));
                                isShowingCategories = false;
                              }
                              console.log('[EXPENSE CHART RENDER] Rendering', isShowingCategories ? 'child categories' : 'merchants', 'with data:', data.length, 'items');

                              return renderChart(data, 'expense', expenseChartType, expenseDrillDown, expenseLegendExpanded, setExpenseLegendExpanded);
                            } else {
                              return renderChart(expenseTransactionBreakdown, 'expense', expenseChartType, expenseDrillDown, expenseLegendExpanded, setExpenseLegendExpanded);
                            }
                          })()}
                          <Box>
                            <Heading size="xs" mb={3} color="gray.600">
                              Transactions {expenseDrillDown.category && `in ${expenseDrillDown.category}`}
                              {expenseDrillDown.merchant && ` at ${expenseDrillDown.merchant}`}
                            </Heading>
                            {renderTransactionTable(expenseTransactions, 'expense', expenseSortField, expenseSortDirection)}
                          </Box>
                        </VStack>
                      ) : (
                        <Card>
                          <CardBody textAlign="center" py={8}>
                            <Text color="gray.600" fontWeight="semibold">
                              No expenses for the selected date range
                            </Text>
                            <Text color="gray.500" fontSize="sm" mt={1}>
                              Try selecting a different date range
                            </Text>
                          </CardBody>
                        </Card>
                      )}
                    </SimpleGrid>
                  </VStack>
                </TabPanel>

                {/* Income Tab */}
                <TabPanel>
                  <VStack spacing={6} align="stretch">
                    {/* Income Statistics Cards */}
                    {incomeStats && (
                      <SimpleGrid columns={{ base: 2, md: 4, lg: 7 }} spacing={4} w="full">
                        <Card size="sm">
                          <CardBody>
                            <Stat size="sm">
                              <StatLabel fontSize="xs">Total Transactions</StatLabel>
                              <StatNumber fontSize="lg">{incomeStats.totalTransactions}</StatNumber>
                            </Stat>
                          </CardBody>
                        </Card>
                        <Card size="sm">
                          <CardBody>
                            <Stat size="sm">
                              <StatLabel fontSize="xs">Total Received</StatLabel>
                              <StatNumber fontSize="lg" color="green.600">
                                {formatCurrency(incomeStats.totalAmount)}
                              </StatNumber>
                            </Stat>
                          </CardBody>
                        </Card>
                        <Card size="sm">
                          <CardBody>
                            <Stat size="sm">
                              <StatLabel fontSize="xs">Avg Received</StatLabel>
                              <StatNumber fontSize="lg">
                                {formatCurrency(incomeStats.avgAmount)}
                              </StatNumber>
                            </Stat>
                          </CardBody>
                        </Card>
                        <Card
                          size="sm"
                          cursor="pointer"
                          _hover={{ bg: 'gray.50', transform: 'scale(1.02)', transition: 'all 0.2s' }}
                          onClick={() => incomeStats.minTransaction && handleTransactionClick(incomeStats.minTransaction)}
                        >
                          <CardBody>
                            <Stat size="sm">
                              <StatLabel fontSize="xs">Min Received</StatLabel>
                              <StatNumber fontSize="lg">
                                {formatCurrency(incomeStats.minAmount)}
                              </StatNumber>
                              <StatHelpText fontSize="xs" color="gray.500">
                                Click to view
                              </StatHelpText>
                            </Stat>
                          </CardBody>
                        </Card>
                        <Card
                          size="sm"
                          cursor="pointer"
                          _hover={{ bg: 'gray.50', transform: 'scale(1.02)', transition: 'all 0.2s' }}
                          onClick={() => incomeStats.maxTransaction && handleTransactionClick(incomeStats.maxTransaction)}
                        >
                          <CardBody>
                            <Stat size="sm">
                              <StatLabel fontSize="xs">Max Received</StatLabel>
                              <StatNumber fontSize="lg">
                                {formatCurrency(incomeStats.maxAmount)}
                              </StatNumber>
                              <StatHelpText fontSize="xs" color="gray.500">
                                Click to view
                              </StatHelpText>
                            </Stat>
                          </CardBody>
                        </Card>
                        <Card
                          size="sm"
                          cursor="pointer"
                          _hover={{ bg: 'gray.50', transform: 'scale(1.02)', transition: 'all 0.2s' }}
                          onClick={() => incomeStats.topPayee?.transactions?.[0] && handleTransactionClick(incomeStats.topPayee.transactions[0])}
                        >
                          <CardBody>
                            <Stat size="sm">
                              <StatLabel fontSize="xs">Top Source</StatLabel>
                              <StatNumber fontSize="sm" noOfLines={1}>
                                {incomeStats.topPayee?.name || 'N/A'}
                              </StatNumber>
                              <StatHelpText fontSize="xs">
                                {incomeStats.topPayee && formatCurrency(incomeStats.topPayee.total)}
                              </StatHelpText>
                            </Stat>
                          </CardBody>
                        </Card>
                        <Card
                          size="sm"
                          cursor="pointer"
                          _hover={{ bg: 'gray.50', transform: 'scale(1.02)', transition: 'all 0.2s' }}
                          onClick={() => incomeStats.mostTransactions?.transactions?.[0] && handleTransactionClick(incomeStats.mostTransactions.transactions[0])}
                        >
                          <CardBody>
                            <Stat size="sm">
                              <StatLabel fontSize="xs">Most Transactions</StatLabel>
                              <StatNumber fontSize="sm" noOfLines={1}>
                                {incomeStats.mostTransactions?.name || 'N/A'}
                              </StatNumber>
                              <StatHelpText fontSize="xs">
                                {incomeStats.mostTransactions?.count || 0} txns
                              </StatHelpText>
                            </Stat>
                          </CardBody>
                        </Card>
                      </SimpleGrid>
                    )}

                    {summary && filteredSummary && filteredSummary.income_categories.length > 0 ? (
                      <>
                        <HStack justify="space-between">
                          <Heading size="md">
                            {groupBy === 'label' ? 'Income by Label' : groupBy === 'merchant' ? 'Income by Merchant' : groupBy === 'account' ? 'Income by Account' : 'Income by Category'}
                          </Heading>
                          <IconButton
                            aria-label={incomeChartType === 'pie' ? 'Switch to bar chart' : 'Switch to pie chart'}
                            icon={incomeChartType === 'pie' ? <IoBarChart /> : <IoPieChart />}
                            size="sm"
                            variant="ghost"
                            onClick={() => setIncomeChartType(incomeChartType === 'pie' ? 'bar' : 'pie')}
                          />
                        </HStack>
                        <Breadcrumb spacing="8px" separator={<ChevronRightIcon color="gray.500" />}>
                          <BreadcrumbItem>
                            <BreadcrumbLink
                              onClick={() => handleBreadcrumbClick('income', 'categories')}
                              color={incomeDrillDown.level === 'categories' ? 'brand.600' : 'gray.600'}
                              fontWeight={incomeDrillDown.level === 'categories' ? 'bold' : 'normal'}
                            >
                              All Categories
                            </BreadcrumbLink>
                          </BreadcrumbItem>
                          {incomeDrillDown.parentCategory && (
                            <BreadcrumbItem>
                              <BreadcrumbLink
                                onClick={() => {
                                  // Go back to parent category level
                                  setIncomeDrillDown({ level: 'merchants', category: incomeDrillDown.parentCategory });
                                }}
                                color="gray.600"
                                fontWeight="normal"
                              >
                                {incomeDrillDown.parentCategory}
                              </BreadcrumbLink>
                            </BreadcrumbItem>
                          )}
                          {incomeDrillDown.category && (
                            <BreadcrumbItem>
                              <BreadcrumbLink
                                onClick={() => handleBreadcrumbClick('income', 'merchants')}
                                color={incomeDrillDown.level === 'merchants' ? 'brand.600' : 'gray.600'}
                                fontWeight={incomeDrillDown.level === 'merchants' ? 'bold' : 'normal'}
                              >
                                {incomeDrillDown.category}
                              </BreadcrumbLink>
                            </BreadcrumbItem>
                          )}
                          {incomeDrillDown.merchant && (
                            <BreadcrumbItem isCurrentPage>
                              <BreadcrumbLink color="brand.600" fontWeight="bold">
                                {incomeDrillDown.merchant}
                              </BreadcrumbLink>
                            </BreadcrumbItem>
                          )}
                        </Breadcrumb>
                        <Box>
                          {incomeDrillDown.level === 'categories'
                            ? renderChart(filteredSummary?.income_categories || [], 'income', incomeChartType, incomeDrillDown, incomeLegendExpanded, setIncomeLegendExpanded)
                            : incomeDrillDown.level === 'merchants' && (groupBy === 'category' ? categoryDrillDown?.income_categories : incomeMerchants)
                            ? renderChart(groupBy === 'category' ? (categoryDrillDown?.income_categories || []) : (incomeMerchants || []), 'income', incomeChartType, incomeDrillDown, incomeLegendExpanded, setIncomeLegendExpanded)
                            : renderChart(incomeTransactionBreakdown, 'income', incomeChartType, incomeDrillDown, incomeLegendExpanded, setIncomeLegendExpanded)
                          }
                        </Box>
                        <Box>
                          <Heading size="sm" mb={4}>
                            Transactions {incomeDrillDown.category && `in ${incomeDrillDown.category}`}
                            {incomeDrillDown.merchant && ` at ${incomeDrillDown.merchant}`}
                          </Heading>
                          {renderTransactionTable(incomeTransactions, 'income', incomeSortField, incomeSortDirection)}
                        </Box>
                      </>
                    ) : (
                      <Card>
                        <CardBody textAlign="center" py={12}>
                          <Text color="gray.600" fontSize="lg" fontWeight="semibold">
                            No income for the selected date range
                          </Text>
                          <Text color="gray.500" mt={2}>
                            Try selecting a different date range or check if income transactions have been imported
                          </Text>
                        </CardBody>
                      </Card>
                    )}
                  </VStack>
                </TabPanel>

                {/* Expenses Tab */}
                <TabPanel>
                  <VStack spacing={6} align="stretch">
                    {/* Expense Statistics Cards */}
                    {expenseStats && (
                      <SimpleGrid columns={{ base: 2, md: 4, lg: 7 }} spacing={4} w="full">
                        <Card size="sm">
                          <CardBody>
                            <Stat size="sm">
                              <StatLabel fontSize="xs">Total Transactions</StatLabel>
                              <StatNumber fontSize="lg">{expenseStats.totalTransactions}</StatNumber>
                            </Stat>
                          </CardBody>
                        </Card>
                        <Card size="sm">
                          <CardBody>
                            <Stat size="sm">
                              <StatLabel fontSize="xs">Total Spent</StatLabel>
                              <StatNumber fontSize="lg" color="red.600">
                                {formatCurrency(expenseStats.totalAmount)}
                              </StatNumber>
                            </Stat>
                          </CardBody>
                        </Card>
                        <Card size="sm">
                          <CardBody>
                            <Stat size="sm">
                              <StatLabel fontSize="xs">Avg Spent</StatLabel>
                              <StatNumber fontSize="lg">
                                {formatCurrency(expenseStats.avgAmount)}
                              </StatNumber>
                            </Stat>
                          </CardBody>
                        </Card>
                        <Card
                          size="sm"
                          cursor="pointer"
                          _hover={{ bg: 'gray.50', transform: 'scale(1.02)', transition: 'all 0.2s' }}
                          onClick={() => expenseStats.minTransaction && handleTransactionClick(expenseStats.minTransaction)}
                        >
                          <CardBody>
                            <Stat size="sm">
                              <StatLabel fontSize="xs">Min Spent</StatLabel>
                              <StatNumber fontSize="lg">
                                {formatCurrency(expenseStats.minAmount)}
                              </StatNumber>
                              <StatHelpText fontSize="xs" color="gray.500">
                                Click to view
                              </StatHelpText>
                            </Stat>
                          </CardBody>
                        </Card>
                        <Card
                          size="sm"
                          cursor="pointer"
                          _hover={{ bg: 'gray.50', transform: 'scale(1.02)', transition: 'all 0.2s' }}
                          onClick={() => expenseStats.maxTransaction && handleTransactionClick(expenseStats.maxTransaction)}
                        >
                          <CardBody>
                            <Stat size="sm">
                              <StatLabel fontSize="xs">Max Spent</StatLabel>
                              <StatNumber fontSize="lg">
                                {formatCurrency(expenseStats.maxAmount)}
                              </StatNumber>
                              <StatHelpText fontSize="xs" color="gray.500">
                                Click to view
                              </StatHelpText>
                            </Stat>
                          </CardBody>
                        </Card>
                        <Card
                          size="sm"
                          cursor="pointer"
                          _hover={{ bg: 'gray.50', transform: 'scale(1.02)', transition: 'all 0.2s' }}
                          onClick={() => expenseStats.topMerchant?.transactions?.[0] && handleTransactionClick(expenseStats.topMerchant.transactions[0])}
                        >
                          <CardBody>
                            <Stat size="sm">
                              <StatLabel fontSize="xs">Most Spent</StatLabel>
                              <StatNumber fontSize="sm" noOfLines={1}>
                                {expenseStats.topMerchant?.name || 'N/A'}
                              </StatNumber>
                              <StatHelpText fontSize="xs">
                                {expenseStats.topMerchant && formatCurrency(expenseStats.topMerchant.total)}
                              </StatHelpText>
                            </Stat>
                          </CardBody>
                        </Card>
                        <Card
                          size="sm"
                          cursor="pointer"
                          _hover={{ bg: 'gray.50', transform: 'scale(1.02)', transition: 'all 0.2s' }}
                          onClick={() => expenseStats.mostTransactions?.transactions?.[0] && handleTransactionClick(expenseStats.mostTransactions.transactions[0])}
                        >
                          <CardBody>
                            <Stat size="sm">
                              <StatLabel fontSize="xs">Most Transactions</StatLabel>
                              <StatNumber fontSize="sm" noOfLines={1}>
                                {expenseStats.mostTransactions?.name || 'N/A'}
                              </StatNumber>
                              <StatHelpText fontSize="xs">
                                {expenseStats.mostTransactions?.count || 0} txns
                              </StatHelpText>
                            </Stat>
                          </CardBody>
                        </Card>
                      </SimpleGrid>
                    )}

                    {summary && filteredSummary && filteredSummary.expense_categories.length > 0 ? (
                      <>
                        <HStack justify="space-between">
                          <Heading size="md">
                            {groupBy === 'label' ? 'Expenses by Label' : groupBy === 'merchant' ? 'Expenses by Merchant' : groupBy === 'account' ? 'Expenses by Account' : 'Expenses by Category'}
                          </Heading>
                          <IconButton
                            aria-label={expenseChartType === 'pie' ? 'Switch to bar chart' : 'Switch to pie chart'}
                            icon={expenseChartType === 'pie' ? <IoBarChart /> : <IoPieChart />}
                            size="sm"
                            variant="ghost"
                            onClick={() => setExpenseChartType(expenseChartType === 'pie' ? 'bar' : 'pie')}
                          />
                        </HStack>
                        <Breadcrumb spacing="8px" separator={<ChevronRightIcon color="gray.500" />}>
                          <BreadcrumbItem>
                            <BreadcrumbLink
                              onClick={() => handleBreadcrumbClick('expense', 'categories')}
                              color={expenseDrillDown.level === 'categories' ? 'brand.600' : 'gray.600'}
                              fontWeight={expenseDrillDown.level === 'categories' ? 'bold' : 'normal'}
                            >
                              All Categories
                            </BreadcrumbLink>
                          </BreadcrumbItem>
                          {expenseDrillDown.parentCategory && (
                            <BreadcrumbItem>
                              <BreadcrumbLink
                                onClick={() => {
                                  // Go back to parent category level
                                  setExpenseDrillDown({ level: 'merchants', category: expenseDrillDown.parentCategory });
                                }}
                                color="gray.600"
                                fontWeight="normal"
                              >
                                {expenseDrillDown.parentCategory}
                              </BreadcrumbLink>
                            </BreadcrumbItem>
                          )}
                          {expenseDrillDown.category && (
                            <BreadcrumbItem>
                              <BreadcrumbLink
                                onClick={() => handleBreadcrumbClick('expense', 'merchants')}
                                color={expenseDrillDown.level === 'merchants' ? 'brand.600' : 'gray.600'}
                                fontWeight={expenseDrillDown.level === 'merchants' ? 'bold' : 'normal'}
                              >
                                {expenseDrillDown.category}
                              </BreadcrumbLink>
                            </BreadcrumbItem>
                          )}
                          {expenseDrillDown.merchant && (
                            <BreadcrumbItem isCurrentPage>
                              <BreadcrumbLink color="brand.600" fontWeight="bold">
                                {expenseDrillDown.merchant}
                              </BreadcrumbLink>
                            </BreadcrumbItem>
                          )}
                        </Breadcrumb>
                        <Box>
                          {expenseDrillDown.level === 'categories'
                            ? renderChart(filteredSummary?.expense_categories || [], 'expense', expenseChartType, expenseDrillDown, expenseLegendExpanded, setExpenseLegendExpanded)
                            : expenseDrillDown.level === 'merchants' && (groupBy === 'category' ? categoryDrillDown?.expense_categories : expenseMerchants)
                            ? renderChart(groupBy === 'category' ? (categoryDrillDown?.expense_categories || []) : (expenseMerchants || []), 'expense', expenseChartType, expenseDrillDown, expenseLegendExpanded, setExpenseLegendExpanded)
                            : renderChart(expenseTransactionBreakdown, 'expense', expenseChartType, expenseDrillDown, expenseLegendExpanded, setExpenseLegendExpanded)
                          }
                        </Box>
                        <Box>
                          <Heading size="sm" mb={4}>
                            Transactions {expenseDrillDown.category && `in ${expenseDrillDown.category}`}
                            {expenseDrillDown.merchant && ` at ${expenseDrillDown.merchant}`}
                          </Heading>
                          {renderTransactionTable(expenseTransactions, 'expense', expenseSortField, expenseSortDirection)}
                        </Box>
                      </>
                    ) : (
                      <Card>
                        <CardBody textAlign="center" py={12}>
                          <Text color="gray.600" fontSize="lg" fontWeight="semibold">
                            No expenses for the selected date range
                          </Text>
                          <Text color="gray.500" mt={2}>
                            Try selecting a different date range or check if expense transactions have been imported
                          </Text>
                        </CardBody>
                      </Card>
                    )}
                  </VStack>
                </TabPanel>
              </TabPanels>
            </Tabs>
          </CardBody>
        </Card>

        {/* Empty State */}
        {summary && filteredSummary && filteredSummary.income_categories.length === 0 && filteredSummary.expense_categories.length === 0 && (
          <Card>
            <CardBody textAlign="center" py={12}>
              <Text color="gray.600" fontSize="lg">
                No transactions found for the selected date range
              </Text>
              <Text color="gray.500" mt={2}>
                Try selecting a different date range or add some transactions
              </Text>
            </CardBody>
          </Card>
        )}
      </VStack>

      {/* Transaction Detail Modal */}
      <TransactionDetailModal
        transaction={selectedTransaction}
        isOpen={isDetailOpen}
        onClose={onDetailClose}
        onCreateRule={handleCreateRule}
      />

      {/* Rule Builder Modal */}
      <RuleBuilderModal
        isOpen={isRuleOpen}
        onClose={onRuleClose}
        prefilledTransaction={ruleTransaction || undefined}
      />
    </Container>
  );
};
