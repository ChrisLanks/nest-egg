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
import { DateRangePicker } from '../../../components/DateRangePicker';
import type { DateRange } from '../../../components/DateRangePicker';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import type { Transaction } from '../../../types/transaction';
import { TransactionDetailModal } from '../../../components/TransactionDetailModal';
import { RuleBuilderModal } from '../../../components/RuleBuilderModal';

interface CategoryBreakdown {
  category: string;
  amount: number;
  count: number;
  percentage: number;
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

  // Default to current month
  const now = new Date();
  const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
  const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0);

  const [dateRange, setDateRange] = useState<DateRange>({
    start: firstDay.toISOString().split('T')[0],
    end: lastDay.toISOString().split('T')[0],
    label: 'This Month',
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

  const [groupBy, setGroupBy] = useState<'category' | 'label'>('category');
  const [hiddenItems, setHiddenItems] = useState<Set<string>>(new Set());

  // Fetch organization settings for custom month boundaries
  const { data: orgSettings } = useQuery({
    queryKey: ['orgPreferences'],
    queryFn: async () => {
      const response = await api.get('/settings/organization');
      return response.data;
    },
  });

  const customMonthStartDay = orgSettings?.monthly_start_day || 1;

  // Update date range when custom month boundary loads
  useEffect(() => {
    if (!orgSettings) return; // Wait for settings to load

    const now = new Date();
    const start = new Date();
    const end = new Date();

    if (customMonthStartDay === 1) {
      // Standard calendar month - from 1st to today
      start.setDate(1);
      end.setHours(23, 59, 59, 999);
    } else {
      // Custom month boundary - from custom start day to today
      const currentDay = now.getDate();
      if (currentDay >= customMonthStartDay) {
        // We're past the boundary in current month
        start.setDate(customMonthStartDay);
      } else {
        // We haven't reached the boundary yet, use previous month's boundary
        start.setMonth(start.getMonth() - 1);
        start.setDate(customMonthStartDay);
      }
      // End is always today for "This Month"
      end.setHours(23, 59, 59, 999);
    }

    setDateRange({
      start: start.toISOString().split('T')[0],
      end: end.toISOString().split('T')[0],
      label: 'This Month',
    });
  }, [orgSettings, customMonthStartDay]);

  // Reset drill-down states when groupBy changes
  useEffect(() => {
    setIncomeDrillDown({ level: 'categories' });
    setExpenseDrillDown({ level: 'categories' });
    setHiddenItems(new Set()); // Clear hidden items when switching grouping
  }, [groupBy]);

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['income-expenses-summary', dateRange.start, dateRange.end, groupBy],
    queryFn: async () => {
      const endpoint = groupBy === 'label' ? '/income-expenses/label-summary' : '/income-expenses/summary';
      const response = await api.get<IncomeExpenseSummary>(
        `${endpoint}?start_date=${dateRange.start}&end_date=${dateRange.end}`
      );
      return response.data;
    },
  });

  const { data: trend, isLoading: trendLoading } = useQuery({
    queryKey: ['income-expenses-trend', dateRange.start, dateRange.end],
    queryFn: async () => {
      const response = await api.get<MonthlyTrend[]>(
        `/income-expenses/trend?start_date=${dateRange.start}&end_date=${dateRange.end}`
      );
      return response.data;
    },
  });

  // Fetch merchant breakdown when drilling down
  const { data: incomeMerchants } = useQuery({
    queryKey: ['income-merchants', dateRange.start, dateRange.end, incomeDrillDown.category, groupBy],
    queryFn: async () => {
      const endpoint = groupBy === 'label' ? '/income-expenses/label-merchants' : '/income-expenses/merchants';
      const paramName = groupBy === 'label' ? 'label' : 'category';
      const response = await api.get<CategoryBreakdown[]>(
        `${endpoint}?start_date=${dateRange.start}&end_date=${dateRange.end}&transaction_type=income&${paramName}=${incomeDrillDown.category || ''}`
      );
      return response.data;
    },
    enabled: incomeDrillDown.level === 'merchants' || incomeDrillDown.level === 'transactions',
  });

  const { data: expenseMerchants } = useQuery({
    queryKey: ['expense-merchants', dateRange.start, dateRange.end, expenseDrillDown.category, groupBy],
    queryFn: async () => {
      const endpoint = groupBy === 'label' ? '/income-expenses/label-merchants' : '/income-expenses/merchants';
      const paramName = groupBy === 'label' ? 'label' : 'category';
      const response = await api.get<CategoryBreakdown[]>(
        `${endpoint}?start_date=${dateRange.start}&end_date=${dateRange.end}&transaction_type=expense&${paramName}=${expenseDrillDown.category || ''}`
      );
      return response.data;
    },
    enabled: expenseDrillDown.level === 'merchants' || expenseDrillDown.level === 'transactions',
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

    // Filter by category/label if drilling down
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
      } else {
        // Filter by category
        filtered = filtered.filter(t => t.category_primary === incomeDrillDown.category);
      }
    }

    // Filter by merchant if drilling down to that level
    if (incomeDrillDown.merchant) {
      filtered = filtered.filter(t => t.merchant_name === incomeDrillDown.merchant);
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

    // Filter by category/label if drilling down
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

    const total = incomeTransactions.reduce((sum, t) => sum + t.amount, 0);

    return incomeTransactions.map(t => ({
      category: `${t.merchant_name} - ${formatDate(t.date)}`,
      amount: t.amount,
      count: 1,
      percentage: (t.amount / total) * 100,
      transaction: t,
    }));
  }, [incomeTransactions]);

  const expenseTransactionBreakdown = useMemo(() => {
    if (!expenseTransactions) return [];

    const total = expenseTransactions.reduce((sum, t) => sum + Math.abs(t.amount), 0);

    return expenseTransactions.map(t => ({
      category: `${t.merchant_name} - ${formatDate(t.date)}`,
      amount: Math.abs(t.amount),
      count: 1,
      percentage: (Math.abs(t.amount) / total) * 100,
      transaction: t,
    }));
  }, [expenseTransactions]);

  const handleCategoryClick = (category: string, type: 'income' | 'expense') => {
    if (type === 'income') {
      setIncomeDrillDown({ level: 'merchants', category });
    } else {
      setExpenseDrillDown({ level: 'merchants', category });
    }
  };

  const handleMerchantClick = (merchant: string, type: 'income' | 'expense') => {
    if (type === 'income') {
      setIncomeDrillDown(prev => ({ ...prev, level: 'transactions', merchant }));
    } else {
      setExpenseDrillDown(prev => ({ ...prev, level: 'transactions', merchant }));
    }
  };

  const handleBreadcrumbClick = (type: 'income' | 'expense', level: DrillDownLevel) => {
    if (type === 'income') {
      if (level === 'categories') {
        setIncomeDrillDown({ level: 'categories' });
      } else if (level === 'merchants') {
        setIncomeDrillDown(prev => ({ level: 'merchants', category: prev.category }));
      }
    } else {
      if (level === 'categories') {
        setExpenseDrillDown({ level: 'categories' });
      } else if (level === 'merchants') {
        setExpenseDrillDown(prev => ({ level: 'merchants', category: prev.category }));
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
    return (
      <Center h="100vh">
        <Spinner size="xl" color="brand.500" />
      </Center>
    );
  }

  const renderChart = (
    data: CategoryBreakdown[] | any[],
    type: 'income' | 'expense',
    chartType: ChartType,
    drillDown: DrillDownState
  ) => {
    if (chartType === 'pie') {
      return (
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={data}
              dataKey="amount"
              nameKey="category"
              cx="50%"
              cy="50%"
              outerRadius={100}
              label={(entry) => formatCurrency(entry.amount)}
              onClick={(entry) => {
                if (drillDown.level === 'categories') {
                  handleCategoryClick(entry.category, type);
                } else if (drillDown.level === 'merchants') {
                  handleMerchantClick(entry.category, type);
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
                        {data.percentage.toFixed(1)}%
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

                return (
                  <Box mt={4}>
                    <Wrap spacing={2} justify="center">
                      {payload.map((entry: any, index: number) => {
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
                                  handleCategoryClick(data.category, type);
                                } else if (drillDown.level === 'merchants') {
                                  handleMerchantClick(data.category, type);
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
                  handleCategoryClick(entry.category, type);
                } else if (drillDown.level === 'merchants') {
                  handleMerchantClick(entry.category, type);
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
            <Heading size="lg">Cash Flow</Heading>
            <Text color="gray.600" mt={2}>
              Analyze your income sources and spending patterns
            </Text>
          </Box>
          <DateRangePicker value={dateRange} onChange={setDateRange} customMonthStartDay={customMonthStartDay} />
        </HStack>

        {/* Group By Toggle */}
        <HStack>
          <Text fontSize="sm" fontWeight="medium" color="gray.600">
            Group by:
          </Text>
          <ButtonGroup size="sm" isAttached variant="outline">
            <Button
              colorScheme={groupBy === 'category' ? 'brand' : 'gray'}
              onClick={() => setGroupBy('category')}
              bg={groupBy === 'category' ? 'brand.50' : 'white'}
            >
              Category
            </Button>
            <Button
              colorScheme={groupBy === 'label' ? 'brand' : 'gray'}
              onClick={() => setGroupBy('label')}
              bg={groupBy === 'label' ? 'brand.50' : 'white'}
            >
              Labels
            </Button>
          </ButtonGroup>

          {/* Filter Dropdown */}
          {uniqueItems.length > 0 && (
            <Menu closeOnSelect={false}>
              <MenuButton as={Button} size="sm" variant="outline" ml={4}>
                Hide {groupBy === 'category' ? 'Categories' : 'Labels'} ({hiddenItems.size})
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
            <Tabs>
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
                      {summary && filteredSummary.income_categories.length > 0 && (
                        <VStack align="stretch" spacing={4}>
                          <HStack justify="space-between">
                            <Heading size="sm">{groupBy === 'label' ? 'Income by Label' : 'Income by Category'}</Heading>
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
                                {groupBy === 'label' ? 'All Labels' : 'All Categories'}
                              </BreadcrumbLink>
                            </BreadcrumbItem>
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
                          {incomeDrillDown.level === 'categories'
                            ? renderChart(filteredSummary.income_categories, 'income', incomeChartType, incomeDrillDown)
                            : incomeDrillDown.level === 'merchants' && incomeMerchants
                            ? renderChart(incomeMerchants, 'income', incomeChartType, incomeDrillDown)
                            : renderChart(incomeTransactionBreakdown, 'income', incomeChartType, incomeDrillDown)
                          }
                          <Box>
                            <Heading size="xs" mb={3} color="gray.600">
                              Transactions {incomeDrillDown.category && `in ${incomeDrillDown.category}`}
                              {incomeDrillDown.merchant && ` at ${incomeDrillDown.merchant}`}
                            </Heading>
                            {renderTransactionTable(incomeTransactions, 'income', incomeSortField, incomeSortDirection)}
                          </Box>
                        </VStack>
                      )}

                      {/* Expense Section */}
                      {summary && filteredSummary.expense_categories.length > 0 && (
                        <VStack align="stretch" spacing={4}>
                          <HStack justify="space-between">
                            <Heading size="sm">{groupBy === 'label' ? 'Expenses by Label' : 'Expenses by Category'}</Heading>
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
                                {groupBy === 'label' ? 'All Labels' : 'All Categories'}
                              </BreadcrumbLink>
                            </BreadcrumbItem>
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
                          {expenseDrillDown.level === 'categories'
                            ? renderChart(filteredSummary.expense_categories, 'expense', expenseChartType, expenseDrillDown)
                            : expenseDrillDown.level === 'merchants' && expenseMerchants
                            ? renderChart(expenseMerchants, 'expense', expenseChartType, expenseDrillDown)
                            : renderChart(expenseTransactionBreakdown, 'expense', expenseChartType, expenseDrillDown)
                          }
                          <Box>
                            <Heading size="xs" mb={3} color="gray.600">
                              Transactions {expenseDrillDown.category && `in ${expenseDrillDown.category}`}
                              {expenseDrillDown.merchant && ` at ${expenseDrillDown.merchant}`}
                            </Heading>
                            {renderTransactionTable(expenseTransactions, 'expense', expenseSortField, expenseSortDirection)}
                          </Box>
                        </VStack>
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

                    {summary && filteredSummary.income_categories.length > 0 ? (
                      <>
                        <HStack justify="space-between">
                          <Heading size="md">{groupBy === 'label' ? 'Income by Label' : 'Income by Category'}</Heading>
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
                            ? renderChart(filteredSummary.income_categories, 'income', incomeChartType, incomeDrillDown)
                            : incomeDrillDown.level === 'merchants' && incomeMerchants
                            ? renderChart(incomeMerchants, 'income', incomeChartType, incomeDrillDown)
                            : renderChart(incomeTransactionBreakdown, 'income', incomeChartType, incomeDrillDown)
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
                      <Text color="gray.500">No income transactions found</Text>
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

                    {summary && filteredSummary.expense_categories.length > 0 ? (
                      <>
                        <HStack justify="space-between">
                          <Heading size="md">{groupBy === 'label' ? 'Expenses by Label' : 'Expenses by Category'}</Heading>
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
                            ? renderChart(filteredSummary.expense_categories, 'expense', expenseChartType, expenseDrillDown)
                            : expenseDrillDown.level === 'merchants' && expenseMerchants
                            ? renderChart(expenseMerchants, 'expense', expenseChartType, expenseDrillDown)
                            : renderChart(expenseTransactionBreakdown, 'expense', expenseChartType, expenseDrillDown)
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
                      <Text color="gray.500">No expense transactions found</Text>
                    )}
                  </VStack>
                </TabPanel>
              </TabPanels>
            </Tabs>
          </CardBody>
        </Card>

        {/* Empty State */}
        {summary && filteredSummary.income_categories.length === 0 && filteredSummary.expense_categories.length === 0 && (
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
