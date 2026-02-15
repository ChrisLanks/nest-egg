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
  IconButton,
  Wrap,
  WrapItem,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  Tooltip,
} from '@chakra-ui/react';
import { SearchIcon, ChevronUpIcon, ChevronDownIcon, ViewIcon } from '@chakra-ui/icons';
import { FiLock } from 'react-icons/fi';
import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { TransactionDetailModal } from '../components/TransactionDetailModal';
import { RuleBuilderModal } from '../components/RuleBuilderModal';
import { DateRangePicker, type DateRange } from '../components/DateRangePicker';
import { InfiniteScrollSentinel } from '../components/InfiniteScrollSentinel';
import { useInfiniteTransactions } from '../hooks/useInfiniteTransactions';
import { useUserView } from '../contexts/UserViewContext';
import type { Transaction } from '../types/transaction';
import api from '../services/api';

// Helper to get default date range (all time)
const getDefaultDateRange = (): DateRange => {
  const now = new Date();
  const start = new Date();
  start.setFullYear(start.getFullYear() - 10); // 10 years back
  return {
    start: start.toISOString().split('T')[0],
    end: now.toISOString().split('T')[0],
    label: 'All Time',
  };
};

type SortField = 'date' | 'merchant_name' | 'amount' | 'category_primary' | 'account_name' | 'labels' | 'status';
type SortDirection = 'asc' | 'desc';

export const TransactionsPage = () => {
  const [selectedTransaction, setSelectedTransaction] = useState<Transaction | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isRuleBuilderOpen, setIsRuleBuilderOpen] = useState(false);
  const [ruleTransaction, setRuleTransaction] = useState<Transaction | null>(null);
  const [bulkSelectMode, setBulkSelectMode] = useState(false);
  const [selectedTransactions, setSelectedTransactions] = useState<Set<string>>(new Set());
  const [dateRange, setDateRange] = useState<DateRange>(getDefaultDateRange());
  const [searchQuery, setSearchQuery] = useState('');
  const [sortField, setSortField] = useState<SortField>('date');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [showStatusColumn, setShowStatusColumn] = useState(false);

  const toast = useToast();
  const navigate = useNavigate();
  const { canEdit, isOtherUserView } = useUserView();

  // Fetch organization preferences for monthly_start_day
  const { data: orgPrefs } = useQuery({
    queryKey: ['orgPreferences'],
    queryFn: async () => {
      const response = await api.get('/settings/organization');
      return response.data;
    },
  });

  const monthlyStartDay = orgPrefs?.monthly_start_day || 1;

  // Use infinite transactions hook
  const {
    transactions: allTransactions,
    isLoading,
    isLoadingMore,
    hasMore,
    total,
    loadMore,
  } = useInfiniteTransactions({
    startDate: dateRange.start,
    endDate: dateRange.end,
    pageSize: 100,
  });

  // Client-side filtering and sorting (no pagination)
  const processedTransactions = useMemo(() => {
    if (!allTransactions.length) return [];

    let filtered = [...allTransactions];

    // Filter by search query (searches merchant, account, category, description, and labels)
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (txn) =>
          txn.merchant_name?.toLowerCase().includes(query) ||
          txn.account_name?.toLowerCase().includes(query) ||
          txn.category?.name?.toLowerCase().includes(query) ||
          txn.category?.parent_name?.toLowerCase().includes(query) ||
          txn.description?.toLowerCase().includes(query) ||
          txn.labels?.some((label) => label.name.toLowerCase().includes(query))
      );
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
  }, [allTransactions, searchQuery, sortField, sortDirection]);

  // Group transactions by custom month periods based on monthly_start_day
  const transactionsByMonth = useMemo(() => {
    if (!processedTransactions.length) return [];

    // Function to get the month period key for a transaction date
    const getMonthPeriodKey = (dateStr: string): string => {
      const [year, month, day] = dateStr.split('-').map(Number);
      const txnDate = new Date(year, month - 1, day);

      // If the day is before the monthly_start_day, the period started in the previous month
      if (day < monthlyStartDay) {
        const periodStart = new Date(year, month - 2, monthlyStartDay);
        const periodEnd = new Date(year, month - 1, monthlyStartDay - 1);
        return `${periodStart.toLocaleDateString('en-US', { month: 'short', year: 'numeric', day: 'numeric' })} - ${periodEnd.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`;
      } else {
        const periodStart = new Date(year, month - 1, monthlyStartDay);
        const periodEnd = new Date(year, month, monthlyStartDay - 1);
        return `${periodStart.toLocaleDateString('en-US', { month: 'short', year: 'numeric', day: 'numeric' })} - ${periodEnd.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`;
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

  const toggleBulkSelectMode = () => {
    setBulkSelectMode(!bulkSelectMode);
    setSelectedTransactions(new Set());
  };

  const toggleTransactionSelection = (txnId: string) => {
    const newSelected = new Set(selectedTransactions);
    if (newSelected.has(txnId)) {
      newSelected.delete(txnId);
    } else {
      newSelected.add(txnId);
    }
    setSelectedTransactions(newSelected);
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
    setSearchQuery(category);
  };

  const handleAccountClick = (accountName: string, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent opening transaction modal
    // For now, just search by account name
    // TODO: Navigate to account detail page in the future
    setSearchQuery(accountName);
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
      deduplication_hash: '',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    setRuleTransaction(commonTransaction);
    setIsRuleBuilderOpen(true);
  };

  if (isLoading) {
    return (
      <Center h="100vh">
        <Spinner size="xl" color="brand.500" />
      </Center>
    );
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
              {bulkSelectMode && `. ${selectedTransactions.size} selected`}
              {hasMore && '. Scroll down to load more'}
              {!bulkSelectMode && !hasMore && '.'}
            </Text>
          </Box>
          <HStack spacing={2}>
            <DateRangePicker value={dateRange} onChange={setDateRange} />
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
            <Tooltip
              label={!canEdit ? "Read-only: Cannot bulk select when viewing another household member" : ""}
              placement="top"
              isDisabled={canEdit}
            >
              <Button
                colorScheme={bulkSelectMode ? 'red' : 'blue'}
                variant={bulkSelectMode ? 'solid' : 'outline'}
                onClick={toggleBulkSelectMode}
                size="sm"
                isDisabled={!canEdit}
                leftIcon={!canEdit ? <FiLock /> : undefined}
              >
                {bulkSelectMode ? 'Cancel Selection' : 'Select Multiple'}
              </Button>
            </Tooltip>
          </HStack>
        </HStack>

        {/* Search Bar */}
        <HStack spacing={3}>
          <InputGroup maxW="400px">
            <InputLeftElement pointerEvents="none">
              <SearchIcon color="gray.400" />
            </InputLeftElement>
            <Input
              placeholder="Search transactions..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </InputGroup>

          {/* Columns Menu */}
          <Menu closeOnSelect={false}>
            <MenuButton as={Button} size="md" leftIcon={<ViewIcon />} variant="outline">
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

        {bulkSelectMode && selectedTransactions.size > 0 && (
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
              <Button
                colorScheme="brand"
                size="sm"
                onClick={handleBulkCreateRule}
              >
                Create Rule from Selected
              </Button>
            </HStack>
          </Box>
        )}

        <Box bg="white" borderRadius="lg" boxShadow="sm" overflow="hidden">
          <Table variant="simple" size="sm">
            <Thead bg="gray.50">
              <Tr>
                {bulkSelectMode && (
                  <Th width="40px">
                    <Checkbox
                      isChecked={
                        processedTransactions.length > 0 &&
                        selectedTransactions.size === processedTransactions.length
                      }
                      onChange={toggleSelectAll}
                    />
                  </Th>
                )}
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
              {transactionsByMonth.map((monthGroup) => (
                <>
                  {/* Month Period Header */}
                  <Tr key={`header-${monthGroup.period}`} bg="gray.100">
                    <Td
                      colSpan={bulkSelectMode ? (showStatusColumn ? 8 : 7) : (showStatusColumn ? 7 : 6)}
                      py={2}
                    >
                      <Text fontWeight="bold" fontSize="sm" color="gray.700">
                        {monthGroup.period}
                      </Text>
                    </Td>
                  </Tr>

                  {/* Transactions for this month */}
                  {monthGroup.transactions.map((txn) => {
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
                        {bulkSelectMode && (
                          <Td width="40px" onClick={(e) => e.stopPropagation()}>
                            <Checkbox
                              isChecked={isSelected}
                              onChange={() => toggleTransactionSelection(txn.id)}
                            />
                          </Td>
                        )}
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
                            {txn.is_pending && (
                              <Badge colorScheme="orange">Pending</Badge>
                            )}
                          </Td>
                        )}
                      </Tr>
                    );
                  })}
                </>
              ))}
            </Tbody>
          </Table>
        </Box>

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
      </VStack>
    </Container>
  );
};
