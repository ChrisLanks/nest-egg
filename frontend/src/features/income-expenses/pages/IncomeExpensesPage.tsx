/**
 * Income vs Expenses analysis page with drill-down capabilities
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
  Progress,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Button,
  ButtonGroup,
  IconButton,
  useDisclosure,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
} from '@chakra-ui/react';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ViewIcon, ViewOffIcon } from '@chakra-ui/icons';
import api from '../../../services/api';
import { DateRangePicker } from '../../../components/DateRangePicker';
import type { DateRange } from '../../../components/DateRangePicker';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import type { Transaction } from '../../../types/transaction';

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

  const [chartType, setChartType] = useState<ChartType>('pie');
  const [selectedCategory, setSelectedCategory] = useState<{ category: string; type: 'income' | 'expense' } | null>(null);
  const { isOpen, onOpen, onClose } = useDisclosure();

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

  // Fetch transactions for selected category
  const { data: categoryTransactions } = useQuery({
    queryKey: ['category-transactions', selectedCategory?.category, dateRange.start, dateRange.end],
    queryFn: async () => {
      if (!selectedCategory) return null;
      const response = await api.get<{ transactions: Transaction[] }>(
        `/transactions/?start_date=${dateRange.start}&end_date=${dateRange.end}&category=${selectedCategory.category}&page=1&page_size=1000`
      );
      return response.data.transactions;
    },
    enabled: !!selectedCategory,
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
    setSelectedCategory({ category, type });
    onOpen();
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

  const renderCategoryChart = (categories: CategoryBreakdown[], type: 'income' | 'expense') => {
    if (chartType === 'pie') {
      return (
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={categories}
              dataKey="amount"
              nameKey="category"
              cx="50%"
              cy="50%"
              outerRadius={100}
              label={(entry) => `${entry.percentage.toFixed(1)}%`}
              onClick={(data) => handleCategoryClick(data.category, type)}
              style={{ cursor: 'pointer' }}
            >
              {categories.map((entry, index) => (
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
          <BarChart data={categories} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" />
            <YAxis dataKey="category" type="category" width={150} />
            <Tooltip formatter={(value: number) => formatCurrency(value)} />
            <Bar
              dataKey="amount"
              fill={type === 'income' ? '#48BB78' : '#F56565'}
              onClick={(data) => handleCategoryClick(data.category, type)}
              style={{ cursor: 'pointer' }}
            />
          </BarChart>
        </ResponsiveContainer>
      );
    }
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
          <HStack>
            <ButtonGroup size="sm" isAttached variant="outline">
              <IconButton
                aria-label="Pie chart"
                icon={<ViewIcon />}
                onClick={() => setChartType('pie')}
                colorScheme={chartType === 'pie' ? 'brand' : 'gray'}
              />
              <IconButton
                aria-label="Bar chart"
                icon={<ViewOffIcon />}
                onClick={() => setChartType('bar')}
                colorScheme={chartType === 'bar' ? 'brand' : 'gray'}
              />
            </ButtonGroup>
            <DateRangePicker value={dateRange} onChange={setDateRange} />
          </HStack>
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
                      {/* Income Categories */}
                      {summary && summary.income_categories.length > 0 && (
                        <Box>
                          <Heading size="sm" mb={4}>
                            Income by Category
                          </Heading>
                          {renderCategoryChart(summary.income_categories, 'income')}
                        </Box>
                      )}

                      {/* Expense Categories */}
                      {summary && summary.expense_categories.length > 0 && (
                        <Box>
                          <Heading size="sm" mb={4}>
                            Expenses by Category
                          </Heading>
                          {renderCategoryChart(summary.expense_categories, 'expense')}
                        </Box>
                      )}
                    </SimpleGrid>
                  </VStack>
                </TabPanel>

                {/* Income Tab */}
                <TabPanel>
                  <VStack spacing={6}>
                    {summary && summary.income_categories.length > 0 ? (
                      <>
                        <Box w="full">
                          <Heading size="md" mb={4}>
                            Income by Category
                          </Heading>
                          {renderCategoryChart(summary.income_categories, 'income')}
                        </Box>

                        {/* Category List */}
                        <Table variant="simple" size="sm">
                          <Thead>
                            <Tr>
                              <Th>Category</Th>
                              <Th isNumeric>Amount</Th>
                              <Th isNumeric>Count</Th>
                              <Th isNumeric>%</Th>
                            </Tr>
                          </Thead>
                          <Tbody>
                            {summary.income_categories.map((cat, index) => (
                              <Tr
                                key={cat.category}
                                onClick={() => handleCategoryClick(cat.category, 'income')}
                                cursor="pointer"
                                _hover={{ bg: 'gray.50' }}
                              >
                                <Td>
                                  <HStack spacing={2}>
                                    <Box w={3} h={3} bg={COLORS[index % COLORS.length]} borderRadius="sm" />
                                    <Text>{cat.category}</Text>
                                  </HStack>
                                </Td>
                                <Td isNumeric fontWeight="medium">{formatCurrency(cat.amount)}</Td>
                                <Td isNumeric>{cat.count}</Td>
                                <Td isNumeric>
                                  <Text fontSize="sm" color="gray.600">
                                    {cat.percentage.toFixed(1)}%
                                  </Text>
                                </Td>
                              </Tr>
                            ))}
                          </Tbody>
                        </Table>
                      </>
                    ) : (
                      <Text color="gray.500">No income transactions found</Text>
                    )}
                  </VStack>
                </TabPanel>

                {/* Expenses Tab */}
                <TabPanel>
                  <VStack spacing={6}>
                    {summary && summary.expense_categories.length > 0 ? (
                      <>
                        <Box w="full">
                          <Heading size="md" mb={4}>
                            Expenses by Category
                          </Heading>
                          {renderCategoryChart(summary.expense_categories, 'expense')}
                        </Box>

                        {/* Category List with Progress Bars */}
                        <VStack align="stretch" spacing={3} w="full">
                          {summary.expense_categories.map((cat, index) => (
                            <Box
                              key={cat.category}
                              p={3}
                              borderWidth={1}
                              borderRadius="md"
                              cursor="pointer"
                              _hover={{ bg: 'gray.50' }}
                              onClick={() => handleCategoryClick(cat.category, 'expense')}
                            >
                              <HStack justify="space-between" mb={2}>
                                <HStack spacing={2}>
                                  <Box w={3} h={3} bg={COLORS[index % COLORS.length]} borderRadius="sm" />
                                  <Text fontSize="sm" fontWeight="medium">{cat.category}</Text>
                                </HStack>
                                <Text fontSize="sm" fontWeight="bold">
                                  {formatCurrency(cat.amount)}
                                </Text>
                              </HStack>
                              <Progress
                                value={cat.percentage}
                                size="sm"
                                colorScheme="red"
                                borderRadius="full"
                              />
                              <Text fontSize="xs" color="gray.600" mt={1}>
                                {cat.count} transaction{cat.count !== 1 ? 's' : ''} • {cat.percentage.toFixed(1)}%
                              </Text>
                            </Box>
                          ))}
                        </VStack>
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

      {/* Category Drill-down Modal */}
      <Modal isOpen={isOpen} onClose={onClose} size="xl">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>
            {selectedCategory?.category} Transactions
            <Badge ml={2} colorScheme={selectedCategory?.type === 'income' ? 'green' : 'red'}>
              {selectedCategory?.type}
            </Badge>
          </ModalHeader>
          <ModalCloseButton />
          <ModalBody pb={6}>
            {categoryTransactions && categoryTransactions.length > 0 ? (
              <VStack align="stretch" spacing={3}>
                {categoryTransactions.map((txn) => (
                  <Box key={txn.id} p={3} borderWidth={1} borderRadius="md">
                    <HStack justify="space-between" mb={1}>
                      <VStack align="start" spacing={0}>
                        <Text fontWeight="medium">{txn.merchant_name || 'Unknown'}</Text>
                        <Text fontSize="sm" color="gray.600">
                          {formatDate(txn.date)}
                        </Text>
                      </VStack>
                      <Text
                        fontWeight="bold"
                        color={txn.amount >= 0 ? 'green.600' : 'red.600'}
                      >
                        {txn.amount >= 0 ? '+' : ''}
                        {formatCurrency(txn.amount)}
                      </Text>
                    </HStack>
                    {txn.description && (
                      <Text fontSize="xs" color="gray.500" mt={1}>
                        {txn.description}
                      </Text>
                    )}
                  </Box>
                ))}
              </VStack>
            ) : (
              <Text color="gray.500" textAlign="center" py={8}>
                No transactions found
              </Text>
            )}
          </ModalBody>
        </ModalContent>
      </Modal>
    </Container>
  );
};
