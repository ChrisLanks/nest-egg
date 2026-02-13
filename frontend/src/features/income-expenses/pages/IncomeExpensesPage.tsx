/**
 * Income vs Expenses analysis page
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
} from '@chakra-ui/react';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '../../../services/api';
import { DateRangePicker, DateRange } from '../../../components/DateRangePicker';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';

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

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
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

        {/* Monthly Trend Chart */}
        {trend && trend.length > 0 && (
          <Card>
            <CardBody>
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
            </CardBody>
          </Card>
        )}

        {/* Category Breakdowns */}
        <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={6}>
          {/* Income Categories */}
          {summary && summary.income_categories.length > 0 && (
            <Card>
              <CardBody>
                <Heading size="md" mb={4}>
                  Income by Category
                </Heading>
                
                {/* Pie Chart */}
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie
                      data={summary.income_categories}
                      dataKey="amount"
                      nameKey="category"
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      label={(entry) => `${entry.category}: ${entry.percentage.toFixed(1)}%`}
                    >
                      {summary.income_categories.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value: number) => formatCurrency(value)} />
                  </PieChart>
                </ResponsiveContainer>

                {/* Category List */}
                <Table variant="simple" size="sm" mt={4}>
                  <Thead>
                    <Tr>
                      <Th>Category</Th>
                      <Th isNumeric>Amount</Th>
                      <Th isNumeric>%</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {summary.income_categories.map((cat, index) => (
                      <Tr key={cat.category}>
                        <Td>
                          <HStack spacing={2}>
                            <Box w={3} h={3} bg={COLORS[index % COLORS.length]} borderRadius="sm" />
                            <Text>{cat.category}</Text>
                          </HStack>
                        </Td>
                        <Td isNumeric fontWeight="medium">{formatCurrency(cat.amount)}</Td>
                        <Td isNumeric>
                          <Text fontSize="sm" color="gray.600">
                            {cat.percentage.toFixed(1)}%
                          </Text>
                        </Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              </CardBody>
            </Card>
          )}

          {/* Expense Categories */}
          {summary && summary.expense_categories.length > 0 && (
            <Card>
              <CardBody>
                <Heading size="md" mb={4}>
                  Expenses by Category
                </Heading>

                {/* Pie Chart */}
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie
                      data={summary.expense_categories}
                      dataKey="amount"
                      nameKey="category"
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      label={(entry) => `${entry.category}: ${entry.percentage.toFixed(1)}%`}
                    >
                      {summary.expense_categories.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value: number) => formatCurrency(value)} />
                  </PieChart>
                </ResponsiveContainer>

                {/* Category List with Progress Bars */}
                <VStack align="stretch" spacing={3} mt={4}>
                  {summary.expense_categories.map((cat, index) => (
                    <Box key={cat.category}>
                      <HStack justify="space-between" mb={1}>
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
              </CardBody>
            </Card>
          )}
        </SimpleGrid>

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
    </Container>
  );
};
