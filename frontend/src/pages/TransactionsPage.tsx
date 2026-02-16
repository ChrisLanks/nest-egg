/**
 * Transactions page
 */

import {
  Box,
  Container,
  Heading,
  Text,
  VStack,
  HStack,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  Spinner,
  Center,
  Button,
  Checkbox,
  useToast,
  Input,
  InputGroup,
  InputLeftElement,
  InputRightElement,
  IconButton,
  Wrap,
  WrapItem,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  Tooltip,
  AlertDialog,
  AlertDialogBody,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogContent,
  AlertDialogOverlay,
  AlertDialogCloseButton,
  Card,
  CardBody,
  useBreakpointValue,
  Divider,
  Stack,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  useDisclosure,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Select,
  FormControl,
  FormLabel,
  CloseButton,
  Popover,
  PopoverTrigger,
  PopoverContent,
  PopoverHeader,
  PopoverBody,
  PopoverArrow,
  PopoverCloseButton,
  Code,
  List,
  ListItem,
} from '@chakra-ui/react';
import { SearchIcon, ChevronUpIcon, ChevronDownIcon, ViewIcon, DownloadIcon, QuestionIcon } from '@chakra-ui/icons';
import { FiLock } from 'react-icons/fi';
import React, { useState, useMemo, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { TransactionDetailModal } from '../components/TransactionDetailModal';
import { RuleBuilderModal } from '../components/RuleBuilderModal';
import { DateRangePicker, type DateRange } from '../components/DateRangePicker';
import { InfiniteScrollSentinel } from '../components/InfiniteScrollSentinel';
import { useInfiniteTransactions } from '../hooks/useInfiniteTransactions';
import { useUserView } from '../contexts/UserViewContext';
import type { Transaction } from '../types/transaction';
import api from '../services/api';
import { TransactionsSkeleton } from '../components/LoadingSkeleton';
import { EmptyState } from '../components/EmptyState';
import { FiInbox } from 'react-icons/fi';

const STORAGE_KEY = 'transactions-date-range';

// Helper to get default date range (this month)
const getDefaultDateRange = (): DateRange => {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), 1); // First day of current month
  return {
    start: start.toISOString().split('T')[0],
    end: now.toISOString().split('T')[0],
    label: 'This Month',
  };
};

// Helper to load date range from localStorage
const loadDateRange = (): DateRange => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch (error) {
    console.error('Failed to load date range from localStorage:', error);
  }
  return getDefaultDateRange();
};

type SortField = 'date' | 'merchant_name' | 'amount' | 'category_primary' | 'account_name' | 'labels' | 'status';
type SortDirection = 'asc' | 'desc';

export const TransactionsPage = () => {
  const [selectedTransaction, setSelectedTransaction] = useState<Transaction | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isRuleBuilderOpen, setIsRuleBuilderOpen] = useState(false);
  const [ruleTransaction, setRuleTransaction] = useState<Transaction | null>(null);
  const [selectedTransactions, setSelectedTransactions] = useState<Set<string>>(new Set());
  const [lastSelectedIndex, setLastSelectedIndex] = useState<number | null>(null);
  const [dateRange, setDateRange] = useState<DateRange>(loadDateRange());
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState('');
  const [sortField, setSortField] = useState<SortField>('date');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [showStatusColumn, setShowStatusColumn] = useState(false);
  const [bulkActionType, setBulkActionType] = useState<'mark' | 'unmark' | null>(null);
  const [isConfirmDialogOpen, setIsConfirmDialogOpen] = useState(false);
  const cancelRef = useRef<HTMLButtonElement>(null);

  // Bulk edit modal
  const { isOpen: isBulkEditOpen, onOpen: onBulkEditOpen, onClose: onBulkEditClose } = useDisclosure();
  const [pendingLabelsToAdd, setPendingLabelsToAdd] = useState<string[]>([]);
  const [pendingLabelsToRemove, setPendingLabelsToRemove] = useState<string[]>([]);
  const [selectedLabelToAdd, setSelectedLabelToAdd] = useState<string>('');
  const [selectedLabelToRemove, setSelectedLabelToRemove] = useState<string>('');

  const toast = useToast();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { canEdit, isOtherUserView } = useUserView();
  const isMobile = useBreakpointValue({ base: true, md: false });

  // Fetch current user for ownership checks
  const { data: currentUser } = useQuery({
    queryKey: ['current-user'],
    queryFn: async () => {
      const response = await api.get('/users/me');
      return response.data;
    },
  });

  // Fetch all accounts to check transaction ownership
  const { data: accounts = [] } = useQuery({
    queryKey: ['accounts-all'],
    queryFn: async () => {
      const response = await api.get('/accounts', {
        params: { include_hidden: true }
      });
      return response.data;
    },
  });

  // Create account ownership map
  const accountOwnershipMap = useMemo(() => {
    const map = new Map<string, string>();
    accounts.forEach((account: any) => {
      map.set(account.id, account.user_id);
    });
    return map;
  }, [accounts]);

  // Check if user owns a transaction (via its account)
  const canModifyTransaction = (transaction: Transaction): boolean => {
    if (!currentUser || !transaction.account_id) return false;
    const accountUserId = accountOwnershipMap.get(transaction.account_id);
    return accountUserId === currentUser.id;
  };

  // Fetch organization preferences for monthly_start_day
  const { data: orgPrefs } = useQuery({
    queryKey: ['orgPreferences'],
    queryFn: async () => {
      const response = await api.get('/settings/organization');
      return response.data;
    },
  });

  const monthlyStartDay = orgPrefs?.monthly_start_day || 1;

  // Persist date range to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(dateRange));
    } catch (error) {
      console.error('Failed to save date range to localStorage:', error);
    }
  }, [dateRange]);

  // Debounce search query (300ms delay)
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchQuery(searchQuery);
    }, 300);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Fetch available labels
  const { data: availableLabels = [] } = useQuery({
    queryKey: ['labels'],
    queryFn: async () => {
      const response = await api.get('/labels/');
      return response.data;
    },
  });

  // Fetch available categories
  const { data: availableCategories = [] } = useQuery({
    queryKey: ['categories'],
    queryFn: async () => {
      const response = await api.get('/categories/');
      return response.data;
    },
  });

  // Use infinite transactions hook
  const {
    transactions: allTransactions,
    isLoading,
    isLoadingMore,
    hasMore,
    total,
    loadMore,
    refetch,
  } = useInfiniteTransactions({
    startDate: dateRange.start,
    endDate: dateRange.end,
    pageSize: 100,
  });

  // Mutation for bulk marking transactions as transfers
  const bulkMarkTransferMutation = useMutation({
    mutationFn: async ({ transactionIds, isTransfer }: { transactionIds: string[]; isTransfer: boolean }) => {
      // Filter to only transactions user owns
      const ownedTransactionIds = transactionIds.filter(id => {
        const transaction = allTransactions.find(t => t.id === id);
        return transaction && canModifyTransaction(transaction);
      });

      if (ownedTransactionIds.length === 0) {
        throw new Error('No owned transactions to modify');
      }

      // Update each transaction
      const promises = ownedTransactionIds.map((id) =>
        api.patch(`/transactions/${id}`, { is_transfer: isTransfer })
      );
      await Promise.all(promises);
      return { attempted: transactionIds.length, modified: ownedTransactionIds.length, isTransfer };
    },
    onSuccess: (result) => {
      const action = result.isTransfer ? 'marked as transfers' : 'unmarked as transfers';
      const skipped = result.attempted - result.modified;
      toast({
        title: `${result.modified} transaction(s) ${action}`,
        description: skipped > 0 ? `${skipped} transaction(s) skipped (not owned by you)` : undefined,
        status: skipped > 0 ? 'warning' : 'success',
        duration: 3000,
      });
      // Refetch transactions to get updated labels
      refetch();
      // Invalidate income-expenses queries
      queryClient.invalidateQueries({ queryKey: ['income-expenses'] });
      // Clear selection
      setSelectedTransactions(new Set());
      setBulkSelectMode(false);
    },
    onError: (error: any) => {
      const message = error.message === 'No owned transactions to modify'
        ? 'You can only modify your own transactions'
        : 'Failed to update transactions';
      toast({
        title: message,
        status: 'error',
        duration: 5000,
      });
    },
  });

  // Mutation for bulk adding labels
  const bulkAddLabelMutation = useMutation({
    mutationFn: async ({ transactionIds, labelId }: { transactionIds: string[]; labelId: string }) => {
      // Filter to only transactions user owns
      const ownedTransactionIds = transactionIds.filter(id => {
        const transaction = allTransactions.find(t => t.id === id);
        return transaction && canModifyTransaction(transaction);
      });

      if (ownedTransactionIds.length === 0) {
        throw new Error('No owned transactions to modify');
      }

      const promises = ownedTransactionIds.map((id) =>
        api.post(`/transactions/${id}/labels/${labelId}`)
      );
      await Promise.all(promises);
      return { attempted: transactionIds.length, modified: ownedTransactionIds.length };
    },
    onSuccess: (result, variables) => {
      const skipped = result.attempted - result.modified;
      toast({
        title: `Label added to ${result.modified} transaction(s)`,
        description: skipped > 0 ? `${skipped} transaction(s) skipped (not owned by you)` : undefined,
        status: skipped > 0 ? 'warning' : 'success',
        duration: 3000,
      });
      refetch();
      queryClient.invalidateQueries({ queryKey: ['income-expenses'] });
    },
    onError: (error: any) => {
      const message = error.message === 'No owned transactions to modify'
        ? 'You can only add labels to your own transactions'
        : 'Failed to add labels';
      toast({
        title: message,
        status: 'error',
        duration: 5000,
      });
    },
  });

  // Mutation for bulk removing labels
  const bulkRemoveLabelMutation = useMutation({
    mutationFn: async ({ transactionIds, labelId }: { transactionIds: string[]; labelId: string }) => {
      // Filter to only transactions user owns
      const ownedTransactionIds = transactionIds.filter(id => {
        const transaction = allTransactions.find(t => t.id === id);
        return transaction && canModifyTransaction(transaction);
      });

      if (ownedTransactionIds.length === 0) {
        throw new Error('No owned transactions to modify');
      }

      const promises = ownedTransactionIds.map((id) =>
        api.delete(`/transactions/${id}/labels/${labelId}`)
      );
      await Promise.all(promises);
      return { attempted: transactionIds.length, modified: ownedTransactionIds.length };
    },
    onSuccess: (result, variables) => {
      const skipped = result.attempted - result.modified;
      toast({
        title: `Label removed from ${result.modified} transaction(s)`,
        description: skipped > 0 ? `${skipped} transaction(s) skipped (not owned by you)` : undefined,
        status: skipped > 0 ? 'warning' : 'success',
        duration: 3000,
      });
      refetch();
      queryClient.invalidateQueries({ queryKey: ['income-expenses'] });
    },
    onError: (error: any) => {
      const message = error.message === 'No owned transactions to modify'
        ? 'You can only remove labels from your own transactions'
        : 'Failed to remove labels';
      toast({
        title: message,
        status: 'error',
        duration: 5000,
      });
    },
  });

  // Mutation for bulk category change
  const bulkChangeCategoryMutation = useMutation({
    mutationFn: async ({ transactionIds, category }: { transactionIds: string[]; category: string }) => {
      // Filter to only transactions user owns
      const ownedTransactionIds = transactionIds.filter(id => {
        const transaction = allTransactions.find(t => t.id === id);
        return transaction && canModifyTransaction(transaction);
      });

      if (ownedTransactionIds.length === 0) {
        throw new Error('No owned transactions to modify');
      }

      const promises = ownedTransactionIds.map((id) =>
        api.patch(`/transactions/${id}`, { category_primary: category })
      );
      await Promise.all(promises);
      return { attempted: transactionIds.length, modified: ownedTransactionIds.length };
    },
    onSuccess: (result, variables) => {
      const skipped = result.attempted - result.modified;
      toast({
        title: `Category updated for ${result.modified} transaction(s)`,
        description: skipped > 0 ? `${skipped} transaction(s) skipped (not owned by you)` : undefined,
        status: skipped > 0 ? 'warning' : 'success',
        duration: 3000,
      });
      refetch();
      queryClient.invalidateQueries({ queryKey: ['income-expenses'] });
    },
    onError: (error: any) => {
      const message = error.message === 'No owned transactions to modify'
        ? 'You can only update categories for your own transactions'
        : 'Failed to update categories';
      toast({
        title: message,
        status: 'error',
        duration: 5000,
      });
    },
  });

  // Bulk edit handlers
  const handleAddLabelToPending = () => {
    if (selectedLabelToAdd && !pendingLabelsToAdd.includes(selectedLabelToAdd)) {
      setPendingLabelsToAdd([...pendingLabelsToAdd, selectedLabelToAdd]);
      setSelectedLabelToAdd('');
    }
  };

  const handleRemoveLabelFromAddPending = (labelId: string) => {
    setPendingLabelsToAdd(pendingLabelsToAdd.filter(id => id !== labelId));
  };

  const handleAddLabelToRemovePending = () => {
    if (selectedLabelToRemove && !pendingLabelsToRemove.includes(selectedLabelToRemove)) {
      setPendingLabelsToRemove([...pendingLabelsToRemove, selectedLabelToRemove]);
      setSelectedLabelToRemove('');
    }
  };

  const handleRemoveLabelFromRemovePending = (labelId: string) => {
    setPendingLabelsToRemove(pendingLabelsToRemove.filter(id => id !== labelId));
  };

  const handleApplyBulkLabelChanges = async () => {
    const transactionIds = Array.from(selectedTransactions);

    // Filter out labels that are in both add and remove lists
    const labelsToAdd = pendingLabelsToAdd.filter(id => !pendingLabelsToRemove.includes(id));
    const labelsToRemove = pendingLabelsToRemove.filter(id => !pendingLabelsToAdd.includes(id));

    try {
      // Apply additions
      for (const labelId of labelsToAdd) {
        await bulkAddLabelMutation.mutateAsync({ transactionIds, labelId });
      }

      // Apply removals
      for (const labelId of labelsToRemove) {
        await bulkRemoveLabelMutation.mutateAsync({ transactionIds, labelId });
      }

      // Success message
      const totalChanges = labelsToAdd.length + labelsToRemove.length;
      if (totalChanges > 0) {
        toast({
          title: `Applied ${totalChanges} label change(s) to ${transactionIds.length} transaction(s)`,
          status: 'success',
          duration: 3000,
        });
      }

      // Reset and close
      setPendingLabelsToAdd([]);
      setPendingLabelsToRemove([]);
      onBulkEditClose();
    } catch (error) {
      toast({
        title: 'Failed to apply some label changes',
        status: 'error',
        duration: 5000,
      });
    }
  };

  const handleBulkEditClose = () => {
    // Reset pending labels when modal closes
    setPendingLabelsToAdd([]);
    setPendingLabelsToRemove([]);
    setSelectedLabelToAdd('');
    setSelectedLabelToRemove('');
    onBulkEditClose();
  };

  // Client-side filtering and sorting (no pagination)
  const processedTransactions = useMemo(() => {
    if (!allTransactions.length) return [];

    let filtered = [...allTransactions];

    // Filter by search query with intelligent parsing (debounced)
    if (debouncedSearchQuery) {
      const query = debouncedSearchQuery.toLowerCase();

      // Parse special search syntax: labels:<x,y>, categories:<x,y>, accounts:<x,y>
      // Support both quoted strings (with spaces), unquoted strings (no spaces), and empty quotes
      const labelsMatch = query.match(/labels?:((?:"[^"]*"|[^\s,]+)(?:,(?:"[^"]*"|[^\s,]+))*)/i);
      const categoryMatch = query.match(/categor(?:y|ies):((?:"[^"]*"|[^\s,]+)(?:,(?:"[^"]*"|[^\s,]+))*)/i);
      const accountMatch = query.match(/accounts?:((?:"[^"]*"|[^\s,]+)(?:,(?:"[^"]*"|[^\s,]+))*)/i);

      // Remove special syntax from query to get plain text search
      const plainQuery = query
        .replace(/labels?:(?:"[^"]*"|[^\s,]+)(?:,(?:"[^"]*"|[^\s,]+))*/gi, '')
        .replace(/categor(?:y|ies):(?:"[^"]*"|[^\s,]+)(?:,(?:"[^"]*"|[^\s,]+))*/gi, '')
        .replace(/accounts?:(?:"[^"]*"|[^\s,]+)(?:,(?:"[^"]*"|[^\s,]+))*/gi, '')
        .trim();

      filtered = filtered.filter((txn) => {
        // Helper to parse comma-separated values and remove quotes
        // Handles commas inside quoted strings properly
        const parseValues = (str: string): string[] => {
          const values: string[] = [];
          let current = '';
          let inQuotes = false;

          for (let i = 0; i < str.length; i++) {
            const char = str[i];

            if (char === '"') {
              inQuotes = !inQuotes;
            } else if (char === ',' && !inQuotes) {
              // Comma outside quotes = separator
              if (current.trim()) {
                values.push(current.trim().toLowerCase());
              }
              current = '';
            } else {
              current += char;
            }
          }

          // Add final value
          if (current.trim()) {
            values.push(current.trim().toLowerCase());
          }

          return values;
        };

        // Check labels filter
        if (labelsMatch) {
          const labelNames = parseValues(labelsMatch[1]);

          // Check if searching for empty labels (labels:"")
          const searchingForEmpty = labelNames.includes('');

          if (searchingForEmpty) {
            // Empty label search: transaction must have no labels
            if (txn.labels && txn.labels.length > 0) return false;
          } else {
            // Normal label search: transaction must have at least one matching label
            const hasMatchingLabel = txn.labels?.some((label) =>
              labelNames.some(ln => label.name.toLowerCase().includes(ln))
            );
            if (!hasMatchingLabel) return false;
          }
        }

        // Check category filter
        if (categoryMatch) {
          const categoryNames = parseValues(categoryMatch[1]);
          const categoryName = (txn.category?.name || txn.category_primary || '').toLowerCase();
          const parentName = (txn.category?.parent_name || '').toLowerCase();
          const hasMatchingCategory = categoryNames.some(cn =>
            categoryName.includes(cn) || parentName.includes(cn)
          );
          if (!hasMatchingCategory) return false;
        }

        // Check account filter
        if (accountMatch) {
          const accountNames = parseValues(accountMatch[1]);
          const accountName = (txn.account_name || '').toLowerCase();
          const hasMatchingAccount = accountNames.some(acc =>
            accountName.includes(acc)
          );
          if (!hasMatchingAccount) return false;
        }

        // Check plain text search (merchant, account, category, description, labels)
        if (plainQuery) {
          return (
            txn.merchant_name?.toLowerCase().includes(plainQuery) ||
            txn.account_name?.toLowerCase().includes(plainQuery) ||
            txn.category?.name?.toLowerCase().includes(plainQuery) ||
            txn.category?.parent_name?.toLowerCase().includes(plainQuery) ||
            txn.description?.toLowerCase().includes(plainQuery) ||
            txn.labels?.some((label) => label.name.toLowerCase().includes(plainQuery))
          );
        }

        return true;
      });
    }

    // Sort
    filtered.sort((a, b) => {
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
          aVal = Number(a.amount);
          bVal = Number(b.amount);
          break;
        case 'category_primary':
          // Sort by parent name if exists, otherwise by category name
          aVal = (a.category?.parent_name || a.category?.name || '').toLowerCase();
          bVal = (b.category?.parent_name || b.category?.name || '').toLowerCase();
          break;
        case 'account_name':
          aVal = a.account_name?.toLowerCase() || '';
          bVal = b.account_name?.toLowerCase() || '';
          break;
        case 'labels':
          // Sort by first label name, or empty if no labels
          aVal = a.labels?.[0]?.name?.toLowerCase() || '';
          bVal = b.labels?.[0]?.name?.toLowerCase() || '';
          break;
        case 'status':
          // Sort by pending status (pending first when desc)
          aVal = a.is_pending ? 1 : 0;
          bVal = b.is_pending ? 1 : 0;
          break;
        default:
          return 0;
      }

      if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });

    return filtered;
  }, [allTransactions, debouncedSearchQuery, sortField, sortDirection]);

  // Group transactions by custom month periods based on monthly_start_day
  const transactionsByMonth = useMemo(() => {
    if (!processedTransactions.length) return [];

    // Function to get the month period key for a transaction date
    const getMonthPeriodKey = (dateStr: string): string => {
      const [year, month, day] = dateStr.split('-').map(Number);
      const txnDate = new Date(year, month - 1, day);

      // Period runs from (monthlyStartDay + 1) to monthlyStartDay of next month
      // If the day is <= monthlyStartDay, the period started in the previous month
      if (day <= monthlyStartDay) {
        // Transaction belongs to period that started in previous month
        const periodStart = new Date(year, month - 2, monthlyStartDay + 1);
        const periodEnd = new Date(year, month - 1, monthlyStartDay);
        // Display end date first (newest to oldest)
        return `${periodEnd.toLocaleDateString('en-US', { month: 'short', year: 'numeric', day: 'numeric' })} - ${periodStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`;
      } else {
        // Transaction belongs to period that started in current month
        const periodStart = new Date(year, month - 1, monthlyStartDay + 1);
        const periodEnd = new Date(year, month, monthlyStartDay);
        // Display end date first (newest to oldest)
        return `${periodEnd.toLocaleDateString('en-US', { month: 'short', year: 'numeric', day: 'numeric' })} - ${periodStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`;
      }
    };

    // Group transactions by month period
    const groups: { [key: string]: Transaction[] } = {};
    const periodKeys: string[] = [];

    processedTransactions.forEach(txn => {
      const periodKey = getMonthPeriodKey(txn.date);
      if (!groups[periodKey]) {
        groups[periodKey] = [];
        periodKeys.push(periodKey);
      }
      groups[periodKey].push(txn);
    });

    // Convert to array format for rendering
    return periodKeys.map(key => ({
      period: key,
      transactions: groups[key],
    }));
  }, [processedTransactions, monthlyStartDay]);

  const handleTransactionClick = (txn: Transaction) => {
    if (bulkSelectMode) {
      // In bulk select mode, clicking toggles checkbox
      toggleTransactionSelection(txn.id);
    } else {
      // In normal mode, open detail modal
      setSelectedTransaction(txn);
      setIsModalOpen(true);
    }
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedTransaction(null);
  };

  const handleCreateRule = (transaction: Transaction) => {
    setRuleTransaction(transaction);
    setIsRuleBuilderOpen(true);
  };

  const handleCloseRuleBuilder = () => {
    setIsRuleBuilderOpen(false);
    setRuleTransaction(null);
  };

  const toggleTransactionSelection = (txnId: string, event?: React.MouseEvent, index?: number) => {
    const newSelected = new Set(selectedTransactions);

    // Shift-click: Select range
    if (event?.shiftKey && lastSelectedIndex !== null && index !== undefined) {
      const start = Math.min(lastSelectedIndex, index);
      const end = Math.max(lastSelectedIndex, index);

      // Select all transactions in range
      for (let i = start; i <= end; i++) {
        if (processedTransactions[i]) {
          newSelected.add(processedTransactions[i].id);
        }
      }

      setSelectedTransactions(newSelected);
      setLastSelectedIndex(index);
      return;
    }

    // Regular click: Toggle selection
    if (newSelected.has(txnId)) {
      newSelected.delete(txnId);
    } else {
      newSelected.add(txnId);
    }

    setSelectedTransactions(newSelected);

    // Update last selected index
    if (index !== undefined) {
      setLastSelectedIndex(index);
    }
  };

  const toggleSelectAll = () => {
    if (!processedTransactions.length) return;

    if (selectedTransactions.size === processedTransactions.length) {
      setSelectedTransactions(new Set());
    } else {
      setSelectedTransactions(new Set(processedTransactions.map(t => t.id)));
    }
  };

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      // Toggle direction if same field
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      // New field, default to desc for date/amount/status, asc for text
      setSortField(field);
      setSortDirection(field === 'date' || field === 'amount' || field === 'status' ? 'desc' : 'asc');
    }
  };

  const handleCategoryClick = (category: string, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent opening transaction modal

    // Check if this category is already in the search
    const quotedCategory = `"${category}"`;
    const hasQuotedVersion = searchQuery.includes(`categories:${quotedCategory}`) || searchQuery.includes(`category:${quotedCategory}`);
    const hasUnquotedVersion = searchQuery.includes(`categories:${category}`) || searchQuery.includes(`category:${category}`);

    if (hasQuotedVersion || hasUnquotedVersion) {
      return; // Already in search, don't add again
    }

    // Add quotes if category contains spaces or commas
    const formattedCategory = (category.includes(' ') || category.includes(',')) ? quotedCategory : category;
    const newFilter = `categories:${formattedCategory}`;
    // Append to existing search if present
    setSearchQuery(searchQuery ? `${searchQuery} ${newFilter}` : newFilter);
  };

  const handleLabelClick = (labelName: string, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent opening transaction modal

    // Check if this label is already in the search
    const quotedLabel = `"${labelName}"`;
    const hasQuotedVersion = searchQuery.includes(`labels:${quotedLabel}`) || searchQuery.includes(`label:${quotedLabel}`);
    const hasUnquotedVersion = searchQuery.includes(`labels:${labelName}`) || searchQuery.includes(`label:${labelName}`);

    if (hasQuotedVersion || hasUnquotedVersion) {
      return; // Already in search, don't add again
    }

    // Add quotes if label contains spaces or commas
    const formattedLabel = (labelName.includes(' ') || labelName.includes(',')) ? quotedLabel : labelName;
    const newFilter = `labels:${formattedLabel}`;
    // Append to existing search if present
    setSearchQuery(searchQuery ? `${searchQuery} ${newFilter}` : newFilter);
  };

  const handleAccountClick = (accountName: string, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent opening transaction modal

    // Check if this account is already in the search
    const quotedAccount = `"${accountName}"`;
    const hasQuotedVersion = searchQuery.includes(`accounts:${quotedAccount}`) || searchQuery.includes(`account:${quotedAccount}`);
    const hasUnquotedVersion = searchQuery.includes(`accounts:${accountName}`) || searchQuery.includes(`account:${accountName}`);

    if (hasQuotedVersion || hasUnquotedVersion) {
      return; // Already in search, don't add again
    }

    // Add quotes if account name contains spaces or commas
    const formattedAccount = (accountName.includes(' ') || accountName.includes(',')) ? quotedAccount : accountName;
    const newFilter = `account:${formattedAccount}`;
    // Append to existing search if present
    setSearchQuery(searchQuery ? `${searchQuery} ${newFilter}` : newFilter);
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return null;
    return sortDirection === 'asc' ? <ChevronUpIcon /> : <ChevronDownIcon />;
  };

  const handleBulkCreateRule = () => {
    if (selectedTransactions.size === 0) {
      toast({
        title: 'No transactions selected',
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    // Find common merchant if all selected have same merchant
    const selected = processedTransactions.filter(t =>
      selectedTransactions.has(t.id)
    );

    const merchants = new Set(selected.map(t => t.merchant_name));
    const categoryIds = new Set(selected.map(t => t.category?.id).filter(Boolean));

    // Create a synthetic transaction with commonalities
    const commonTransaction: Transaction = {
      id: 'bulk',
      merchant_name: merchants.size === 1 ? Array.from(merchants)[0] : 'Multiple merchants',
      category_primary: null,
      category_detailed: null,
      category: categoryIds.size === 1 ? selected[0]?.category : undefined,
      amount: 0,
      date: new Date().toISOString(),
      account_id: selected[0]?.account_id || '',
      account_name: selected[0]?.account_name || '',
      organization_id: selected[0]?.organization_id || '',
      is_pending: false,
      is_transfer: false,
      deduplication_hash: '',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    setRuleTransaction(commonTransaction);
    setIsRuleBuilderOpen(true);
  };

  const handleBulkMarkTransfer = (isTransfer: boolean) => {
    if (selectedTransactions.size === 0) {
      toast({
        title: 'No transactions selected',
        status: 'warning',
        duration: 3000,
      });
      return;
    }

    setBulkActionType(isTransfer ? 'mark' : 'unmark');
    setIsConfirmDialogOpen(true);
  };

  const confirmBulkAction = () => {
    if (bulkActionType !== null) {
      bulkMarkTransferMutation.mutate({
        transactionIds: Array.from(selectedTransactions),
        isTransfer: bulkActionType === 'mark',
      });
    }
    setIsConfirmDialogOpen(false);
    setBulkActionType(null);
  };

  const handleExportCSV = async () => {
    try {
      const params = new URLSearchParams({
        start_date: dateRange.start,
        end_date: dateRange.end,
      });

      const response = await api.get(`/transactions/export/csv?${params.toString()}`, {
        responseType: 'blob',
      });

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `transactions_${dateRange.start}_to_${dateRange.end}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      toast({
        title: 'Export successful',
        description: `${processedTransactions.length} transactions exported`,
        status: 'success',
        duration: 3000,
      });
    } catch (error) {
      toast({
        title: 'Export failed',
        description: 'Failed to export transactions',
        status: 'error',
        duration: 5000,
      });
    }
  };

  if (isLoading) {
    return <TransactionsSkeleton />;
  }

  const formatCurrency = (amount: number) => {
    const isNegative = amount < 0;
    const formatted = new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(Math.abs(amount));
    return { formatted, isNegative };
  };

  const formatDate = (dateStr: string) => {
    // Parse as local date to avoid timezone conversion issues
    const [year, month, day] = dateStr.split('-').map(Number);
    return new Date(year, month - 1, day).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={6} align="stretch">
        {/* Read-only banner */}
        {isOtherUserView && (
          <Box p={4} bg="orange.50" borderRadius="md" borderWidth={1} borderColor="orange.200">
            <HStack>
              <FiLock size={16} color="orange.600" />
              <Text fontSize="sm" color="orange.800" fontWeight="medium">
                Read-only view: You can view transactions but cannot bulk select or create rules for another household member.
              </Text>
            </HStack>
          </Box>
        )}

        <HStack justify="space-between" align="start">
          <Box flex={1}>
            <Heading size="lg">Transactions</Heading>
            <Text color="gray.600" mt={2}>
              Showing {processedTransactions.length} transactions
              {total > 0 && ` (${total} total)`}
              {selectedTransactions.size > 0 && `. ${selectedTransactions.size} selected`}
              {hasMore && '. Scroll down to load more'}
              {selectedTransactions.size === 0 && !hasMore && '.'}
            </Text>
          </Box>
          <HStack spacing={2}>
            <Button
              leftIcon={<DownloadIcon />}
              variant="outline"
              onClick={handleExportCSV}
              size="sm"
              colorScheme="green"
            >
              Export CSV
            </Button>
            <Button
              variant="ghost"
              onClick={() => navigate('/categories')}
              size="sm"
            >
              Categories
            </Button>
            <Button
              variant="ghost"
              onClick={() => navigate('/rules')}
              size="sm"
            >
              Rules
            </Button>
          </HStack>
        </HStack>

        {/* Search Bar and Controls */}
        <HStack spacing={3} justify="space-between">
          <InputGroup maxW="500px">
            <InputLeftElement pointerEvents="none">
              <SearchIcon color="gray.400" />
            </InputLeftElement>
            <Input
              placeholder="Search or try: labels:Transfer accounts:Chase"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              pr="10"
            />
            <InputRightElement>
              <Popover placement="bottom-start">
                <PopoverTrigger>
                  <IconButton
                    aria-label="Search help"
                    icon={<QuestionIcon />}
                    size="sm"
                    variant="ghost"
                    colorScheme="gray"
                  />
                </PopoverTrigger>
                <PopoverContent width="400px">
                  <PopoverArrow />
                  <PopoverCloseButton />
                  <PopoverHeader fontWeight="bold">Search Syntax Guide</PopoverHeader>
                  <PopoverBody>
                    <VStack align="stretch" spacing={3} fontSize="sm">
                      <Box>
                        <Text fontWeight="semibold" mb={1}>Basic Search</Text>
                        <Text color="gray.600">
                          Just type to search merchant names, descriptions, and amounts.
                        </Text>
                      </Box>

                      <Divider />

                      <Box>
                        <Text fontWeight="semibold" mb={1}>Advanced Filters</Text>
                        <List spacing={2}>
                          <ListItem>
                            <Code fontSize="xs">labels:Transfer</Code>
                            <Text color="gray.600" mt={1}>Search by label name</Text>
                          </ListItem>
                          <ListItem>
                            <Code fontSize="xs">categories:Groceries</Code>
                            <Text color="gray.600" mt={1}>Search by category</Text>
                          </ListItem>
                          <ListItem>
                            <Code fontSize="xs">accounts:Chase</Code>
                            <Text color="gray.600" mt={1}>Search by account</Text>
                          </ListItem>
                          <ListItem>
                            <Code fontSize="xs">labels:""</Code>
                            <Text color="gray.600" mt={1}>Find transactions with no labels</Text>
                          </ListItem>
                        </List>
                      </Box>

                      <Divider />

                      <Box>
                        <Text fontWeight="semibold" mb={1}>Multiple Values</Text>
                        <List spacing={2}>
                          <ListItem>
                            <Code fontSize="xs">categories:"Food and Drink","Service"</Code>
                            <Text color="gray.600" mt={1}>Search for multiple categories (OR logic)</Text>
                          </ListItem>
                          <ListItem>
                            <Code fontSize="xs">labels:Work,Personal</Code>
                            <Text color="gray.600" mt={1}>Multiple labels without spaces</Text>
                          </ListItem>
                        </List>
                      </Box>

                      <Divider />

                      <Box>
                        <Text fontWeight="semibold" mb={1}>Quotes</Text>
                        <Text color="gray.600" mb={2}>
                          Use quotes for names with spaces or commas:
                        </Text>
                        <List spacing={2}>
                          <ListItem>
                            <Code fontSize="xs">categories:"Food and Drink"</Code>
                          </ListItem>
                          <ListItem>
                            <Code fontSize="xs">accounts:"Wells Fargo Checking"</Code>
                          </ListItem>
                        </List>
                      </Box>

                      <Divider />

                      <Box>
                        <Text fontWeight="semibold" mb={1}>💡 Pro Tip</Text>
                        <Text color="gray.600">
                          Click any category, label, or account badge to automatically add it to your search!
                        </Text>
                      </Box>
                    </VStack>
                  </PopoverBody>
                </PopoverContent>
              </Popover>
            </InputRightElement>
          </InputGroup>

          <HStack spacing={2}>
            <DateRangePicker
              value={dateRange}
              onChange={setDateRange}
              customMonthStartDay={monthlyStartDay}
            />

            {/* Columns Menu */}
            <Menu closeOnSelect={false}>
              <MenuButton as={Button} size="sm" leftIcon={<ViewIcon />} variant="outline">
                Columns
              </MenuButton>
              <MenuList>
                <MenuItem>
                  <Checkbox
                    isChecked={showStatusColumn}
                    onChange={(e) => setShowStatusColumn(e.target.checked)}
                  >
                    Status
                  </Checkbox>
                </MenuItem>
              </MenuList>
            </Menu>
          </HStack>
        </HStack>

        {selectedTransactions.size > 0 && (
          <Box
            p={4}
            bg="blue.50"
            borderRadius="md"
            borderWidth={1}
            borderColor="blue.200"
          >
            <HStack justify="space-between">
              <Text fontWeight="medium">
                {selectedTransactions.size} transaction(s) selected
              </Text>
              <HStack spacing={2}>
                <Button
                  colorScheme="brand"
                  size="sm"
                  onClick={onBulkEditOpen}
                >
                  Bulk Edit
                </Button>
                <Button
                  colorScheme="blue"
                  size="sm"
                  variant="outline"
                  onClick={handleBulkCreateRule}
                >
                  Create Rule
                </Button>
              </HStack>
            </HStack>
          </Box>
        )}

        {/* Empty State */}
        {processedTransactions.length === 0 && !isLoading && (
          <EmptyState
            icon={FiInbox}
            title="No transactions found"
            description={
              debouncedSearchQuery || selectedAccountId || selectedLabelId
                ? "Try adjusting your filters or search query."
                : "Connect your accounts to start tracking transactions."
            }
            actionLabel={!debouncedSearchQuery && !selectedAccountId && !selectedLabelId ? "Go to Accounts" : undefined}
            onAction={() => navigate('/accounts')}
            showAction={!debouncedSearchQuery && !selectedAccountId && !selectedLabelId}
          />
        )}

        {/* Desktop Table View */}
        {!isMobile && processedTransactions.length > 0 && (
          <Box bg="white" borderRadius="lg" boxShadow="sm" overflow="hidden">
            <Table variant="simple" size="sm">
            <Thead bg="gray.50">
              <Tr>
                <Th width="40px">
                  <HStack spacing={1}>
                    <Checkbox
                      isChecked={
                        processedTransactions.length > 0 &&
                        selectedTransactions.size === processedTransactions.length
                      }
                      onChange={toggleSelectAll}
                    />
                    <Tooltip
                      label="Tip: Hold Shift and click to select multiple transactions in a range"
                      placement="right"
                      hasArrow
                    >
                      <QuestionIcon boxSize={3} color="gray.400" cursor="help" />
                    </Tooltip>
                  </HStack>
                </Th>
                <Th
                  cursor="pointer"
                  onClick={() => handleSort('date')}
                  _hover={{ bg: 'gray.100' }}
                  minWidth="120px"
                  maxWidth="140px"
                >
                  <HStack spacing={1}>
                    <Text>Date</Text>
                    <SortIcon field="date" />
                  </HStack>
                </Th>
                <Th
                  cursor="pointer"
                  onClick={() => handleSort('merchant_name')}
                  _hover={{ bg: 'gray.100' }}
                >
                  <HStack spacing={1}>
                    <Text>Merchant</Text>
                    <SortIcon field="merchant_name" />
                  </HStack>
                </Th>
                <Th
                  cursor="pointer"
                  onClick={() => handleSort('account_name')}
                  _hover={{ bg: 'gray.100' }}
                >
                  <HStack spacing={1}>
                    <Text>Account</Text>
                    <SortIcon field="account_name" />
                  </HStack>
                </Th>
                <Th
                  cursor="pointer"
                  onClick={() => handleSort('category_primary')}
                  _hover={{ bg: 'gray.100' }}
                >
                  <HStack spacing={1}>
                    <Text>Category</Text>
                    <SortIcon field="category_primary" />
                  </HStack>
                </Th>
                <Th
                  cursor="pointer"
                  onClick={() => handleSort('labels')}
                  _hover={{ bg: 'gray.100' }}
                >
                  <HStack spacing={1}>
                    <Text>Labels</Text>
                    <SortIcon field="labels" />
                  </HStack>
                </Th>
                <Th
                  isNumeric
                  cursor="pointer"
                  onClick={() => handleSort('amount')}
                  _hover={{ bg: 'gray.100' }}
                >
                  <HStack spacing={1} justify="flex-end">
                    <Text>Amount</Text>
                    <SortIcon field="amount" />
                  </HStack>
                </Th>
                {showStatusColumn && (
                  <Th
                    cursor="pointer"
                    onClick={() => handleSort('status')}
                    _hover={{ bg: 'gray.100' }}
                  >
                    <HStack spacing={1}>
                      <Text>Status</Text>
                      <SortIcon field="status" />
                    </HStack>
                  </Th>
                )}
              </Tr>
            </Thead>
            <Tbody>
              {transactionsByMonth.map((monthGroup) => {
                // Calculate starting index for this month group
                let globalStartIndex = 0;
                for (const group of transactionsByMonth) {
                  if (group.period === monthGroup.period) break;
                  globalStartIndex += group.transactions.length;
                }

                return (
                  <React.Fragment key={monthGroup.period}>
                    {/* Month Period Header */}
                    <Tr bg="gray.100">
                      <Td
                        colSpan={showStatusColumn ? 8 : 7}
                        py={2}
                      >
                        <Text fontWeight="bold" fontSize="sm" color="gray.700">
                          {monthGroup.period}
                        </Text>
                      </Td>
                    </Tr>

                    {/* Transactions for this month */}
                    {monthGroup.transactions.map((txn, localIndex) => {
                      const globalIndex = globalStartIndex + localIndex;
                      const { formatted, isNegative } = formatCurrency(txn.amount);
                      const isSelected = selectedTransactions.has(txn.id);
                      return (
                        <Tr
                          key={txn.id}
                          onClick={() => handleTransactionClick(txn)}
                          cursor="pointer"
                          _hover={{ bg: 'gray.50' }}
                          bg={isSelected ? 'blue.50' : undefined}
                        >
                          <Td width="40px" onClick={(e) => e.stopPropagation()}>
                            <Checkbox
                              isChecked={isSelected}
                              onChange={(e) => toggleTransactionSelection(txn.id, e.nativeEvent as any, globalIndex)}
                            />
                          </Td>
                        <Td>{formatDate(txn.date)}</Td>
                        <Td>
                          <Text fontWeight="medium">{txn.merchant_name}</Text>
                          {txn.description && (
                            <Text fontSize="sm" color="gray.600">
                              {txn.description}
                            </Text>
                          )}
                        </Td>
                        <Td
                          onClick={(e) =>
                            txn.account_name && handleAccountClick(txn.account_name, e)
                          }
                        >
                          <Text
                            fontSize="sm"
                            color="brand.600"
                            cursor="pointer"
                            _hover={{ textDecoration: 'underline' }}
                          >
                            {txn.account_name}
                            {txn.account_mask && ` ****${txn.account_mask}`}
                          </Text>
                        </Td>
                        <Td
                          onClick={(e) => {
                            const categoryName = txn.category?.name || txn.category_primary;
                            if (categoryName) handleCategoryClick(categoryName, e);
                          }}
                        >
                          {(txn.category || txn.category_primary) && (
                            <Badge
                              colorScheme={txn.category?.color ? undefined : 'blue'}
                              bg={txn.category?.color || undefined}
                              color={txn.category?.color ? 'white' : undefined}
                              fontSize="xs"
                              cursor="pointer"
                              _hover={{ transform: 'scale(1.05)' }}
                              transition="transform 0.2s"
                            >
                              {txn.category
                                ? txn.category.parent_name
                                  ? `${txn.category.parent_name} (${txn.category.name})`
                                  : txn.category.name
                                : txn.category_primary}
                            </Badge>
                          )}
                        </Td>
                        <Td>
                          <Wrap spacing={1}>
                            {txn.labels?.map((label) => (
                              <WrapItem key={label.id}>
                                <Badge
                                  colorScheme={
                                    label.color
                                      ? undefined
                                      : label.is_income
                                      ? 'green'
                                      : 'purple'
                                  }
                                  bg={label.color || undefined}
                                  color={label.color ? 'white' : undefined}
                                  fontSize="xs"
                                  cursor="pointer"
                                  _hover={{ transform: 'scale(1.05)' }}
                                  transition="transform 0.2s"
                                  onClick={(e) => handleLabelClick(label.name, e)}
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
                            color={isNegative ? 'red.600' : 'green.600'}
                          >
                            {isNegative ? '-' : '+'}
                            {formatted}
                          </Text>
                        </Td>
                        {showStatusColumn && (
                          <Td>
                            <HStack spacing={2}>
                              {txn.is_pending && (
                                <Badge colorScheme="orange">Pending</Badge>
                              )}
                              {txn.is_transfer && (
                                <Badge colorScheme="purple">Transfer</Badge>
                              )}
                            </HStack>
                          </Td>
                        )}
                      </Tr>
                    );
                  })}
                </React.Fragment>
                );
              })}
            </Tbody>
          </Table>
        </Box>
        )}

        {/* Mobile Card View */}
        {isMobile && processedTransactions.length > 0 && (
          <VStack spacing={4} align="stretch">
            {transactionsByMonth.map((monthGroup) => {
              // Calculate starting index for this month group
              let globalStartIndex = 0;
              for (const group of transactionsByMonth) {
                if (group.period === monthGroup.period) break;
                globalStartIndex += group.transactions.length;
              }

              return (
                <Box key={`mobile-month-${monthGroup.period}`}>
                  {/* Month Header */}
                  <Box mb={3} px={2}>
                    <Text fontWeight="bold" fontSize="md" color="gray.700">
                      {monthGroup.period}
                    </Text>
                  </Box>

                  {/* Transaction Cards */}
                  <VStack spacing={2} align="stretch">
                    {monthGroup.transactions.map((txn, localIndex) => {
                      const globalIndex = globalStartIndex + localIndex;
                      const { formatted, isNegative } = formatCurrency(txn.amount);
                      const isSelected = selectedTransactions.has(txn.id);

                      return (
                        <Card
                          key={txn.id}
                          variant="outline"
                          cursor="pointer"
                          onClick={() => handleTransactionClick(txn)}
                          bg={isSelected ? 'blue.50' : 'white'}
                          borderColor={isSelected ? 'blue.300' : 'gray.200'}
                          _hover={{ borderColor: 'brand.300', shadow: 'sm' }}
                        >
                          <CardBody p={4}>
                            <VStack align="stretch" spacing={3}>
                              {/* Header Row: Merchant + Amount */}
                              <HStack justify="space-between" align="start">
                                <Box flex={1}>
                                  <Checkbox
                                    isChecked={isSelected}
                                    onChange={(e) => {
                                      e.stopPropagation();
                                      toggleTransactionSelection(txn.id, e.nativeEvent as any, globalIndex);
                                    }}
                                    mb={2}
                                  />
                                <Text fontWeight="bold" fontSize="md">
                                  {txn.merchant_name}
                                </Text>
                                {txn.description && (
                                  <Text fontSize="sm" color="gray.600" mt={1}>
                                    {txn.description}
                                  </Text>
                                )}
                              </Box>
                              <Text
                                fontWeight="bold"
                                fontSize="lg"
                                color={isNegative ? 'red.600' : 'green.600'}
                                flexShrink={0}
                              >
                                {isNegative ? '-' : '+'}{formatted}
                              </Text>
                            </HStack>

                            <Divider />

                            {/* Details Grid */}
                            <Stack spacing={2}>
                              {/* Date */}
                              <HStack justify="space-between">
                                <Text fontSize="sm" color="gray.500">Date</Text>
                                <Text fontSize="sm">{formatDate(txn.date)}</Text>
                              </HStack>

                              {/* Account */}
                              {txn.account_name && (
                                <HStack justify="space-between">
                                  <Text fontSize="sm" color="gray.500">Account</Text>
                                  <Text
                                    fontSize="sm"
                                    color="brand.600"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleAccountClick(txn.account_name!, e);
                                    }}
                                  >
                                    {txn.account_name}
                                    {txn.account_mask && ` ****${txn.account_mask}`}
                                  </Text>
                                </HStack>
                              )}

                              {/* Category */}
                              {(txn.category || txn.category_primary) && (
                                <HStack justify="space-between">
                                  <Text fontSize="sm" color="gray.500">Category</Text>
                                  <Badge
                                    colorScheme={txn.category?.color ? undefined : 'blue'}
                                    bg={txn.category?.color || undefined}
                                    color={txn.category?.color ? 'white' : undefined}
                                    fontSize="xs"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      const categoryName = txn.category?.name || txn.category_primary;
                                      if (categoryName) handleCategoryClick(categoryName, e);
                                    }}
                                  >
                                    {txn.category
                                      ? txn.category.parent_name
                                        ? `${txn.category.parent_name} (${txn.category.name})`
                                        : txn.category.name
                                      : txn.category_primary}
                                  </Badge>
                                </HStack>
                              )}

                              {/* Labels */}
                              {txn.labels && txn.labels.length > 0 && (
                                <HStack justify="space-between" align="start">
                                  <Text fontSize="sm" color="gray.500">Labels</Text>
                                  <Wrap spacing={1} justify="flex-end">
                                    {txn.labels.map((label) => (
                                      <WrapItem key={label.id}>
                                        <Badge
                                          colorScheme={
                                            label.color
                                              ? undefined
                                              : label.is_income
                                              ? 'green'
                                              : 'purple'
                                          }
                                          bg={label.color || undefined}
                                          color={label.color ? 'white' : undefined}
                                          fontSize="xs"
                                          cursor="pointer"
                                          _hover={{ transform: 'scale(1.05)' }}
                                          transition="transform 0.2s"
                                          onClick={(e) => {
                                            e.stopPropagation();
                                            handleLabelClick(label.name, e);
                                          }}
                                        >
                                          {label.name}
                                        </Badge>
                                      </WrapItem>
                                    ))}
                                  </Wrap>
                                </HStack>
                              )}

                              {/* Status Badges */}
                              {(showStatusColumn || txn.is_pending || txn.is_transfer) && (
                                <HStack justify="flex-end" spacing={1}>
                                  {txn.is_pending && (
                                    <Badge colorScheme="yellow" fontSize="xs">Pending</Badge>
                                  )}
                                  {txn.is_transfer && (
                                    <Badge colorScheme="purple" fontSize="xs">Transfer</Badge>
                                  )}
                                </HStack>
                              )}
                            </Stack>
                          </VStack>
                        </CardBody>
                      </Card>
                    );
                  })}
                </VStack>
              </Box>
              );
            })}
          </VStack>
        )}

        {/* Infinite Scroll Sentinel */}
        <InfiniteScrollSentinel
          hasMore={hasMore}
          isLoading={isLoading || isLoadingMore}
          onLoadMore={loadMore}
          loadingText="Loading more transactions..."
          endText="No more transactions to load"
          showEndIndicator={allTransactions.length > 0}
        />

        <TransactionDetailModal
          transaction={selectedTransaction}
          isOpen={isModalOpen}
          onClose={handleCloseModal}
          onCreateRule={handleCreateRule}
        />

        <RuleBuilderModal
          isOpen={isRuleBuilderOpen}
          onClose={handleCloseRuleBuilder}
          prefilledTransaction={ruleTransaction || undefined}
        />

        {/* Bulk Action Confirmation Dialog */}
        <AlertDialog
          isOpen={isConfirmDialogOpen}
          leastDestructiveRef={cancelRef}
          onClose={() => {
            setIsConfirmDialogOpen(false);
            setBulkActionType(null);
          }}
        >
          <AlertDialogOverlay>
            <AlertDialogContent>
              <AlertDialogHeader fontSize="lg" fontWeight="bold">
                Confirm Bulk Action
              </AlertDialogHeader>
              <AlertDialogCloseButton />

              <AlertDialogBody>
                {bulkActionType === 'mark' ? (
                  <>
                    <Text>
                      Are you sure you want to mark <strong>{selectedTransactions.size} transaction(s)</strong> as transfers?
                    </Text>
                    <Text mt={2} color="orange.600" fontSize="sm">
                      Transfers are excluded from cash flow calculations and budgets.
                      This action affects how your financial reports are calculated.
                    </Text>
                  </>
                ) : (
                  <>
                    <Text>
                      Are you sure you want to unmark <strong>{selectedTransactions.size} transaction(s)</strong> as transfers?
                    </Text>
                    <Text mt={2} color="blue.600" fontSize="sm">
                      These transactions will be included in cash flow calculations and budgets again.
                    </Text>
                  </>
                )}
              </AlertDialogBody>

              <AlertDialogFooter>
                <Button
                  ref={cancelRef}
                  onClick={() => {
                    setIsConfirmDialogOpen(false);
                    setBulkActionType(null);
                  }}
                >
                  Cancel
                </Button>
                <Button
                  colorScheme={bulkActionType === 'mark' ? 'purple' : 'blue'}
                  onClick={confirmBulkAction}
                  ml={3}
                  isLoading={bulkMarkTransferMutation.isPending}
                >
                  {bulkActionType === 'mark' ? 'Mark as Transfer' : 'Unmark Transfer'}
                </Button>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialogOverlay>
        </AlertDialog>

        {/* Bulk Edit Modal */}
        <Modal isOpen={isBulkEditOpen} onClose={handleBulkEditClose} size="xl">
          <ModalOverlay />
          <ModalContent>
            <ModalHeader>Bulk Edit {selectedTransactions.size} Transaction(s)</ModalHeader>
            <ModalCloseButton />
            <ModalBody>
              <Tabs>
                <TabList>
                  <Tab>Labels</Tab>
                  <Tab>Category</Tab>
                </TabList>

                <TabPanels>
                  {/* Labels Tab */}
                  <TabPanel>
                    <VStack align="stretch" spacing={4}>
                      <Text fontSize="sm" color="gray.600" mb={2}>
                        💡 <strong>Tip:</strong> To mark transactions as transfers, add/remove the "Transfer" label.
                      </Text>

                      {/* Add Labels Section */}
                      <FormControl>
                        <FormLabel>Add Labels</FormLabel>
                        <HStack>
                          <Select
                            placeholder="Select label to add..."
                            value={selectedLabelToAdd}
                            onChange={(e) => setSelectedLabelToAdd(e.target.value)}
                          >
                            {availableLabels
                              .filter((label: any) => !pendingLabelsToAdd.includes(label.id))
                              .map((label: any) => (
                                <option key={label.id} value={label.id}>
                                  {label.name}
                                </option>
                              ))}
                          </Select>
                          <Button
                            onClick={handleAddLabelToPending}
                            isDisabled={!selectedLabelToAdd}
                            colorScheme="brand"
                          >
                            Add
                          </Button>
                        </HStack>
                        {pendingLabelsToAdd.length > 0 && (
                          <Wrap mt={2}>
                            {pendingLabelsToAdd.map((labelId) => {
                              const label = availableLabels.find((l: any) => l.id === labelId);
                              return (
                                <WrapItem key={labelId}>
                                  <Badge
                                    colorScheme="green"
                                    px={2}
                                    py={1}
                                    display="flex"
                                    alignItems="center"
                                    gap={1}
                                  >
                                    {label?.name}
                                    <CloseButton
                                      size="sm"
                                      onClick={() => handleRemoveLabelFromAddPending(labelId)}
                                    />
                                  </Badge>
                                </WrapItem>
                              );
                            })}
                          </Wrap>
                        )}
                      </FormControl>

                      {/* Remove Labels Section */}
                      <FormControl>
                        <FormLabel>Remove Labels</FormLabel>
                        <HStack>
                          <Select
                            placeholder="Select label to remove..."
                            value={selectedLabelToRemove}
                            onChange={(e) => setSelectedLabelToRemove(e.target.value)}
                          >
                            {availableLabels
                              .filter((label: any) => !pendingLabelsToRemove.includes(label.id))
                              .map((label: any) => (
                                <option key={label.id} value={label.id}>
                                  {label.name}
                                </option>
                              ))}
                          </Select>
                          <Button
                            onClick={handleAddLabelToRemovePending}
                            isDisabled={!selectedLabelToRemove}
                            colorScheme="red"
                            variant="outline"
                          >
                            Add
                          </Button>
                        </HStack>
                        {pendingLabelsToRemove.length > 0 && (
                          <Wrap mt={2}>
                            {pendingLabelsToRemove.map((labelId) => {
                              const label = availableLabels.find((l: any) => l.id === labelId);
                              return (
                                <WrapItem key={labelId}>
                                  <Badge
                                    colorScheme="red"
                                    px={2}
                                    py={1}
                                    display="flex"
                                    alignItems="center"
                                    gap={1}
                                  >
                                    {label?.name}
                                    <CloseButton
                                      size="sm"
                                      onClick={() => handleRemoveLabelFromRemovePending(labelId)}
                                    />
                                  </Badge>
                                </WrapItem>
                              );
                            })}
                          </Wrap>
                        )}
                      </FormControl>

                      {availableLabels.length === 0 && (
                        <Text color="gray.500" fontSize="sm">
                          No labels available. Create labels from the Labels page.
                        </Text>
                      )}
                    </VStack>
                  </TabPanel>

                  {/* Category Tab */}
                  <TabPanel>
                    <VStack align="stretch" spacing={4}>
                      <FormControl>
                        <FormLabel>Change Category</FormLabel>
                        <Select
                          placeholder="Select category..."
                          onChange={(e) => {
                            if (e.target.value) {
                              bulkChangeCategoryMutation.mutate({
                                transactionIds: Array.from(selectedTransactions),
                                category: e.target.value,
                              });
                            }
                          }}
                          isDisabled={bulkChangeCategoryMutation.isPending}
                        >
                          {availableCategories.map((category: any) => (
                            <option key={category.id} value={category.name}>
                              {category.parent_name
                                ? `${category.parent_name} > ${category.name}`
                                : category.name}
                            </option>
                          ))}
                        </Select>
                      </FormControl>

                      {availableCategories.length === 0 && (
                        <Text color="gray.500" fontSize="sm">
                          No custom categories available. Create categories from the Categories page.
                        </Text>
                      )}
                    </VStack>
                  </TabPanel>
                </TabPanels>
              </Tabs>
            </ModalBody>

            <ModalFooter>
              {(pendingLabelsToAdd.length > 0 || pendingLabelsToRemove.length > 0) ? (
                <>
                  <Button
                    colorScheme="brand"
                    onClick={handleApplyBulkLabelChanges}
                    isLoading={bulkAddLabelMutation.isPending || bulkRemoveLabelMutation.isPending}
                  >
                    Apply Label Changes
                  </Button>
                  <Button ml={3} onClick={handleBulkEditClose}>
                    Cancel
                  </Button>
                </>
              ) : (
                <Button onClick={handleBulkEditClose}>Close</Button>
              )}
            </ModalFooter>
          </ModalContent>
        </Modal>
      </VStack>
    </Container>
  );
};
