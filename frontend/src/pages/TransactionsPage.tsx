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
} from '@chakra-ui/react';
import { SearchIcon, ChevronUpIcon, ChevronDownIcon } from '@chakra-ui/icons';
import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { transactionApi } from '../services/transactionApi';
import { TransactionDetailModal } from '../components/TransactionDetailModal';
import { RuleBuilderModal } from '../components/RuleBuilderModal';
import { DateRangePicker, type DateRange } from '../components/DateRangePicker';
import type { Transaction } from '../types/transaction';

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
  const [currentPage, setCurrentPage] = useState(1);
  const [sortField, setSortField] = useState<SortField>('date');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const itemsPerPage = 50;

  const toast = useToast();
  const navigate = useNavigate();

  const { data: transactions, isLoading } = useQuery({
    queryKey: ['transactions', dateRange.start, dateRange.end],
    queryFn: () =>
      transactionApi.listTransactions({
        page_size: 10000, // Get all for client-side filtering/sorting
        start_date: dateRange.start,
        end_date: dateRange.end,
      }),
  });

  // Client-side filtering, sorting, and pagination
  const processedTransactions = useMemo(() => {
    if (!transactions?.transactions) return [];

    let filtered = [...transactions.transactions];

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
  }, [transactions, searchQuery, sortField, sortDirection]);

  // Paginate
  const paginatedTransactions = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    return processedTransactions.slice(startIndex, endIndex);
  }, [processedTransactions, currentPage, itemsPerPage]);

  const totalPages = Math.ceil(processedTransactions.length / itemsPerPage);

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
    if (!paginatedTransactions) return;

    if (selectedTransactions.size === paginatedTransactions.length) {
      setSelectedTransactions(new Set());
    } else {
      setSelectedTransactions(new Set(paginatedTransactions.map(t => t.id)));
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
    setCurrentPage(1); // Reset to first page on sort
  };

  const handleCategoryClick = (category: string, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent opening transaction modal
    setSearchQuery(category);
    setCurrentPage(1);
  };

  const handleAccountClick = (accountName: string, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent opening transaction modal
    // For now, just search by account name
    // TODO: Navigate to account detail page in the future
    setSearchQuery(accountName);
    setCurrentPage(1);
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
        <HStack justify="space-between" align="start">
          <Box flex={1}>
            <Heading size="lg">Transactions</Heading>
            <Text color="gray.600" mt={2}>
              Showing {paginatedTransactions.length} of{' '}
              {processedTransactions.length} transactions
              {processedTransactions.length !== transactions?.total &&
                ` (${transactions?.total} total)`}.
              {bulkSelectMode && ` ${selectedTransactions.size} selected.`}
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
            <Button
              colorScheme={bulkSelectMode ? 'red' : 'blue'}
              variant={bulkSelectMode ? 'solid' : 'outline'}
              onClick={toggleBulkSelectMode}
              size="sm"
            >
              {bulkSelectMode ? 'Cancel Selection' : 'Select Multiple'}
            </Button>
          </HStack>
        </HStack>

        {/* Search Bar */}
        <InputGroup maxW="400px">
          <InputLeftElement pointerEvents="none">
            <SearchIcon color="gray.400" />
          </InputLeftElement>
          <Input
            placeholder="Search transactions..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCurrentPage(1); // Reset to first page on search
            }}
          />
        </InputGroup>

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
          <Table variant="simple">
            <Thead bg="gray.50">
              <Tr>
                {bulkSelectMode && (
                  <Th width="40px">
                    <Checkbox
                      isChecked={
                        paginatedTransactions.length > 0 &&
                        selectedTransactions.size === paginatedTransactions.length
                      }
                      onChange={toggleSelectAll}
                    />
                  </Th>
                )}
                <Th
                  cursor="pointer"
                  onClick={() => handleSort('date')}
                  _hover={{ bg: 'gray.100' }}
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
              </Tr>
            </Thead>
            <Tbody>
              {paginatedTransactions.map((txn) => {
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
                    <Td>
                      {txn.is_pending && (
                        <Badge colorScheme="orange">Pending</Badge>
                      )}
                    </Td>
                  </Tr>
                );
              })}
            </Tbody>
          </Table>
        </Box>

        {/* Pagination Controls */}
        {totalPages > 1 && (
          <HStack justify="center" spacing={2}>
            <Button
              size="sm"
              onClick={() => setCurrentPage(1)}
              isDisabled={currentPage === 1}
            >
              First
            </Button>
            <Button
              size="sm"
              onClick={() => setCurrentPage(currentPage - 1)}
              isDisabled={currentPage === 1}
            >
              Previous
            </Button>
            <HStack spacing={1}>
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                // Show current page and 2 pages on each side
                let pageNum;
                if (totalPages <= 5) {
                  pageNum = i + 1;
                } else if (currentPage <= 3) {
                  pageNum = i + 1;
                } else if (currentPage >= totalPages - 2) {
                  pageNum = totalPages - 4 + i;
                } else {
                  pageNum = currentPage - 2 + i;
                }

                return (
                  <Button
                    key={pageNum}
                    size="sm"
                    variant={currentPage === pageNum ? 'solid' : 'outline'}
                    colorScheme={currentPage === pageNum ? 'brand' : 'gray'}
                    onClick={() => setCurrentPage(pageNum)}
                  >
                    {pageNum}
                  </Button>
                );
              })}
            </HStack>
            <Button
              size="sm"
              onClick={() => setCurrentPage(currentPage + 1)}
              isDisabled={currentPage === totalPages}
            >
              Next
            </Button>
            <Button
              size="sm"
              onClick={() => setCurrentPage(totalPages)}
              isDisabled={currentPage === totalPages}
            >
              Last
            </Button>
            <Text fontSize="sm" color="gray.600" ml={4}>
              Page {currentPage} of {totalPages}
            </Text>
          </HStack>
        )}

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
