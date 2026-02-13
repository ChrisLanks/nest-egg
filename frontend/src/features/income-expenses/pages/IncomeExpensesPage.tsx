/**
 * Income vs Expenses analysis page with drill-down capabilities and transaction tables
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
} from '@chakra-ui/react';
import { useState } from 'react';
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
type DrillDownLevel = 'categories' | 'merchants';

interface DrillDownState {
  level: DrillDownLevel;
  category?: string;
}

type SortField = 'date' | 'merchant_name' | 'amount';
type SortDirection = 'asc' | 'desc';

export const IncomeExpensesPage = () => {
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

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['income-expenses-summary', dateRange.start, dateRange.end],
    queryFn: async () => {
      const response = await api.get<IncomeExpenseSummary>(
        `/income-expenses/summary?start_date=${dateRange.start}&end_date=${dateRange.end}`
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
    queryKey: ['income-merchants', dateRange.start, dateRange.end, incomeDrillDown.category],
    queryFn: async () => {
      const response = await api.get<CategoryBreakdown[]>(
        `/income-expenses/merchants?start_date=${dateRange.start}&end_date=${dateRange.end}&transaction_type=income&category=${incomeDrillDown.category || ''}`
      );
      return response.data;
    },
    enabled: incomeDrillDown.level === 'merchants',
  });

  const { data: expenseMerchants } = useQuery({
    queryKey: ['expense-merchants', dateRange.start, dateRange.end, expenseDrillDown.category],
    queryFn: async () => {
      const response = await api.get<CategoryBreakdown[]>(
        `/income-expenses/merchants?start_date=${dateRange.start}&end_date=${dateRange.end}&transaction_type=expense&category=${expenseDrillDown.category || ''}`
      );
      return response.data;
    },
    enabled: expenseDrillDown.level === 'merchants',
  });

  // Fetch transactions for the current drill-down level
  const { data: incomeTransactions } = useQuery({
    queryKey: ['income-transactions', dateRange.start, dateRange.end, incomeDrillDown.category],
    queryFn: async () => {
      let url = `/transactions/?start_date=${dateRange.start}&end_date=${dateRange.end}&page=1&page_size=1000`;
      if (incomeDrillDown.category) {
        url += `&category=${incomeDrillDown.category}`;
      }
      const response = await api.get<{ transactions: Transaction[] }>(url);
      // Filter for income only
      return response.data.transactions.filter(t => t.amount > 0);
    },
  });

  const { data: expenseTransactions } = useQuery({
    queryKey: ['expense-transactions', dateRange.start, dateRange.end, expenseDrillDown.category],
    queryFn: async () => {
      let url = `/transactions/?start_date=${dateRange.start}&end_date=${dateRange.end}&page=1&page_size=1000`;
      if (expenseDrillDown.category) {
        url += `&category=${expenseDrillDown.category}`;
      }
      const response = await api.get<{ transactions: Transaction[] }>(url);
      // Filter for expenses only
      return response.data.transactions.filter(t => t.amount < 0);
    },
  });

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

  const handleCategoryClick = (category: string, type: 'income' | 'expense') => {
    if (type === 'income') {
      setIncomeDrillDown({ level: 'merchants', category });
    } else {
      setExpenseDrillDown({ level: 'merchants', category });
    }
  };

  const handleBreadcrumbClick = (type: 'income' | 'expense', level: DrillDownLevel) => {
    if (type === 'income') {
      if (level === 'categories') {
        setIncomeDrillDown({ level: 'categories' });
      }
    } else {
      if (level === 'categories') {
        setExpenseDrillDown({ level: 'categories' });
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

  const COLORS = [
    '#48BB78', '#4299E1', '#9F7AEA', '#ED8936', '#F56565',
    '#38B2AC', '#DD6B20', '#805AD5', '#D69E2E', '#E53E3E',
  ];

  if (summaryLoading || trendLoading) {
    return (
      <Center h="100vh">
        <Spinner size="xl" color="brand.500" />
      </Center>
    );
  }

  const net = summary?.net || 0;

  const renderChart = (
    data: CategoryBreakdown[],
    type: 'income' | 'expense',
    chartType: ChartType
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
              label={(entry) => `${entry.percentage.toFixed(1)}%`}
              onClick={(entry) => handleCategoryClick(entry.category, type)}
              style={{ cursor: 'pointer' }}
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip formatter={(value: number) => formatCurrency(value)} />
            <Legend />
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
              fill={type === 'income' ? '#48BB78' : '#F56565'}
              onClick={(entry) => handleCategoryClick(entry.category, type)}
              style={{ cursor: 'pointer' }}
            />
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
            <Heading size="lg">Income vs Expenses</Heading>
            <Text color="gray.600" mt={2}>
              Analyze your income sources and spending patterns
            </Text>
          </Box>
          <DateRangePicker value={dateRange} onChange={setDateRange} />
        </HStack>

        {/* Summary Cards */}
        <SimpleGrid columns={{ base: 1, md: 3 }} spacing={6}>
          <Card>
            <CardBody>
              <Stat>
                <StatLabel>Total Income</StatLabel>
                <StatNumber color="green.600">
                  {formatCurrency(summary?.total_income || 0)}
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
                  {formatCurrency(summary?.total_expenses || 0)}
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

        {/* Tabs for Income, Expenses, Both */}
        <Card>
          <CardBody>
            <Tabs>
              <TabList>
                <Tab>Both</Tab>
                <Tab>Income</Tab>
                <Tab>Expenses</Tab>
              </TabList>

              <TabPanels>
                {/* Both Tab */}
                <TabPanel>
                  <VStack spacing={6}>
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
                      {summary && summary.income_categories.length > 0 && (
                        <VStack align="stretch" spacing={4}>
                          <HStack justify="space-between">
                            <Heading size="sm">Income by Category</Heading>
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
                            {incomeDrillDown.level === 'merchants' && (
                              <BreadcrumbItem isCurrentPage>
                                <BreadcrumbLink color="brand.600" fontWeight="bold">
                                  {incomeDrillDown.category}
                                </BreadcrumbLink>
                              </BreadcrumbItem>
                            )}
                          </Breadcrumb>
                          {incomeDrillDown.level === 'categories'
                            ? renderChart(summary.income_categories, 'income', incomeChartType)
                            : incomeMerchants && renderChart(incomeMerchants, 'income', incomeChartType)
                          }
                          <Box>
                            <Heading size="xs" mb={3} color="gray.600">Transactions</Heading>
                            {renderTransactionTable(incomeTransactions, 'income', incomeSortField, incomeSortDirection)}
                          </Box>
                        </VStack>
                      )}

                      {/* Expense Section */}
                      {summary && summary.expense_categories.length > 0 && (
                        <VStack align="stretch" spacing={4}>
                          <HStack justify="space-between">
                            <Heading size="sm">Expenses by Category</Heading>
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
                            {expenseDrillDown.level === 'merchants' && (
                              <BreadcrumbItem isCurrentPage>
                                <BreadcrumbLink color="brand.600" fontWeight="bold">
                                  {expenseDrillDown.category}
                                </BreadcrumbLink>
                              </BreadcrumbItem>
                            )}
                          </Breadcrumb>
                          {expenseDrillDown.level === 'categories'
                            ? renderChart(summary.expense_categories, 'expense', expenseChartType)
                            : expenseMerchants && renderChart(expenseMerchants, 'expense', expenseChartType)
                          }
                          <Box>
                            <Heading size="xs" mb={3} color="gray.600">Transactions</Heading>
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
                    {summary && summary.income_categories.length > 0 ? (
                      <>
                        <HStack justify="space-between">
                          <Heading size="md">Income by Category</Heading>
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
                          {incomeDrillDown.level === 'merchants' && (
                            <BreadcrumbItem isCurrentPage>
                              <BreadcrumbLink color="brand.600" fontWeight="bold">
                                {incomeDrillDown.category}
                              </BreadcrumbLink>
                            </BreadcrumbItem>
                          )}
                        </Breadcrumb>
                        <Box>
                          {incomeDrillDown.level === 'categories'
                            ? renderChart(summary.income_categories, 'income', incomeChartType)
                            : incomeMerchants && renderChart(incomeMerchants, 'income', incomeChartType)
                          }
                        </Box>
                        <Box>
                          <Heading size="sm" mb={4}>Transactions</Heading>
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
                    {summary && summary.expense_categories.length > 0 ? (
                      <>
                        <HStack justify="space-between">
                          <Heading size="md">Expenses by Category</Heading>
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
                          {expenseDrillDown.level === 'merchants' && (
                            <BreadcrumbItem isCurrentPage>
                              <BreadcrumbLink color="brand.600" fontWeight="bold">
                                {expenseDrillDown.category}
                              </BreadcrumbLink>
                            </BreadcrumbItem>
                          )}
                        </Breadcrumb>
                        <Box>
                          {expenseDrillDown.level === 'categories'
                            ? renderChart(summary.expense_categories, 'expense', expenseChartType)
                            : expenseMerchants && renderChart(expenseMerchants, 'expense', expenseChartType)
                          }
                        </Box>
                        <Box>
                          <Heading size="sm" mb={4}>Transactions</Heading>
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
        {summary && summary.income_categories.length === 0 && summary.expense_categories.length === 0 && (
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
