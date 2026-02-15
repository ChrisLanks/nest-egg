/**
 * Dashboard page with financial overview
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
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  Spinner,
  Center,
  SimpleGrid,
  Divider,
  Button,
  ButtonGroup,
} from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '../features/auth/stores/authStore';
import { useUserView } from '../contexts/UserViewContext';
import api from '../services/api';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { useState, useMemo } from 'react';

interface DashboardData {
  summary: {
    net_worth: number;
    total_assets: number;
    total_debts: number;
    monthly_spending: number;
    monthly_income: number;
    monthly_net: number;
  };
  recent_transactions: Array<{
    id: string;
    date: string;
    amount: number;
    merchant_name: string;
    category_primary: string;
    is_pending: boolean;
  }>;
  top_expenses: Array<{
    category: string;
    total: number;
    count: number;
  }>;
  account_balances: Array<{
    id: string;
    name: string;
    type: string;
    balance: number;
    institution: string;
  }>;
  cash_flow_trend: Array<{
    month: string;
    income: number;
    expenses: number;
    net: number;
  }>;
}

interface HistoricalSnapshot {
  id: string;
  snapshot_date: string;
  total_value: number;
  total_cost_basis: number | null;
  total_gain_loss: number | null;
}

export const DashboardPage = () => {
  const { user } = useAuthStore();
  const { selectedUserId } = useUserView();
  const [timeRange, setTimeRange] = useState<'1M' | '3M' | '6M' | '1Y' | 'ALL'>('1Y');

  const { data: dashboardData, isLoading } = useQuery({
    queryKey: ['dashboard', selectedUserId],
    queryFn: async () => {
      const params = selectedUserId ? { user_id: selectedUserId } : {};
      const response = await api.get<DashboardData>('/dashboard/', { params });
      return response.data;
    },
  });

  // Fetch historical net worth data
  const { data: historicalData } = useQuery({
    queryKey: ['historical-net-worth', timeRange],
    queryFn: async () => {
      const now = new Date();
      let startDate: Date;

      switch (timeRange) {
        case '1M':
          startDate = new Date(now.getFullYear(), now.getMonth() - 1, now.getDate());
          break;
        case '3M':
          startDate = new Date(now.getFullYear(), now.getMonth() - 3, now.getDate());
          break;
        case '6M':
          startDate = new Date(now.getFullYear(), now.getMonth() - 6, now.getDate());
          break;
        case '1Y':
          startDate = new Date(now.getFullYear() - 1, now.getMonth(), now.getDate());
          break;
        case 'ALL':
          startDate = new Date(now.getFullYear() - 10, 0, 1); // 10 years ago
          break;
      }

      const response = await api.get<HistoricalSnapshot[]>('/holdings/historical', {
        params: {
          start_date: startDate.toISOString().split('T')[0],
        },
      });
      return response.data;
    },
  });

  // Sort account balances by balance (descending)
  const sortedAccountBalances = useMemo(() => {
    if (!dashboardData?.account_balances) return [];
    return [...dashboardData.account_balances].sort((a, b) => b.balance - a.balance);
  }, [dashboardData?.account_balances]);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  };

  const formatDate = (dateStr: string) => {
    const [year, month, day] = dateStr.split('-').map(Number);
    return new Date(year, month - 1, day).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
  };

  if (isLoading) {
    return (
      <Center h="100vh">
        <Spinner size="xl" color="brand.500" />
      </Center>
    );
  }

  const summary = dashboardData?.summary;
  const monthlyNet = (summary?.monthly_net || 0);
  const netWorth = summary?.net_worth || 0;

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={8} align="stretch">
        {/* Header */}
        <Box>
          <Heading size="lg">Welcome back, {user?.first_name || 'User'}!</Heading>
          <Text color="gray.600" mt={2}>
            Here's your financial overview
          </Text>
        </Box>

        {/* Summary Cards */}
        <SimpleGrid columns={{ base: 1, md: 3 }} spacing={6}>
          <Card>
            <CardBody>
              <Stat>
                <StatLabel>Net Worth</StatLabel>
                <StatNumber color={netWorth >= 0 ? 'green.600' : 'red.600'}>
                  {formatCurrency(netWorth)}
                </StatNumber>
                <StatHelpText>Assets - Debts</StatHelpText>
              </Stat>
            </CardBody>
          </Card>

          <Card>
            <CardBody>
              <Stat>
                <StatLabel>Total Assets</StatLabel>
                <StatNumber>{formatCurrency(summary?.total_assets || 0)}</StatNumber>
                <StatHelpText>Checking, Savings, Investments</StatHelpText>
              </Stat>
            </CardBody>
          </Card>

          <Card>
            <CardBody>
              <Stat>
                <StatLabel>Total Debts</StatLabel>
                <StatNumber color="red.600">
                  {formatCurrency(summary?.total_debts || 0)}
                </StatNumber>
                <StatHelpText>Credit Cards, Loans</StatHelpText>
              </Stat>
            </CardBody>
          </Card>
        </SimpleGrid>

        {/* Income vs Expenses */}
        <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
          <Card>
            <CardBody>
              <Stat>
                <StatLabel>Monthly Income</StatLabel>
                <StatNumber color="green.600">
                  {formatCurrency(summary?.monthly_income || 0)}
                </StatNumber>
                <StatHelpText>This month</StatHelpText>
              </Stat>
            </CardBody>
          </Card>

          <Card>
            <CardBody>
              <Stat>
                <StatLabel>Monthly Spending</StatLabel>
                <StatNumber color="red.600">
                  {formatCurrency(summary?.monthly_spending || 0)}
                </StatNumber>
                <StatHelpText>
                  Net:
                  <Text
                    as="span"
                    ml={2}
                    color={monthlyNet >= 0 ? 'green.600' : 'red.600'}
                    fontWeight="bold"
                  >
                    {formatCurrency(monthlyNet)}
                  </Text>
                </StatHelpText>
              </Stat>
            </CardBody>
          </Card>
        </SimpleGrid>

        {/* Net Worth Over Time Chart */}
        {historicalData && historicalData.length > 0 && (
          <Card>
            <CardBody>
              <HStack justify="space-between" mb={4}>
                <Heading size="md">Net Worth Over Time</Heading>
                <ButtonGroup size="sm" isAttached variant="outline">
                  <Button
                    onClick={() => setTimeRange('1M')}
                    colorScheme={timeRange === '1M' ? 'brand' : 'gray'}
                  >
                    1M
                  </Button>
                  <Button
                    onClick={() => setTimeRange('3M')}
                    colorScheme={timeRange === '3M' ? 'brand' : 'gray'}
                  >
                    3M
                  </Button>
                  <Button
                    onClick={() => setTimeRange('6M')}
                    colorScheme={timeRange === '6M' ? 'brand' : 'gray'}
                  >
                    6M
                  </Button>
                  <Button
                    onClick={() => setTimeRange('1Y')}
                    colorScheme={timeRange === '1Y' ? 'brand' : 'gray'}
                  >
                    1Y
                  </Button>
                  <Button
                    onClick={() => setTimeRange('ALL')}
                    colorScheme={timeRange === 'ALL' ? 'brand' : 'gray'}
                  >
                    ALL
                  </Button>
                </ButtonGroup>
              </HStack>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart
                  data={historicalData.map((snapshot) => ({
                    date: new Date(snapshot.snapshot_date).toLocaleDateString('en-US', {
                      month: 'short',
                      day: 'numeric',
                    }),
                    value: Number(snapshot.total_value),
                  }))}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip
                    formatter={(value: number) => formatCurrency(value)}
                    contentStyle={{ backgroundColor: 'white', border: '1px solid #ccc' }}
                  />
                  <Legend />
                  <defs>
                    <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3182CE" stopOpacity={0.8}/>
                      <stop offset="95%" stopColor="#3182CE" stopOpacity={0.1}/>
                    </linearGradient>
                  </defs>
                  <Area
                    type="monotone"
                    dataKey="value"
                    stroke="#3182CE"
                    strokeWidth={2}
                    fill="url(#colorValue)"
                    name="Net Worth"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </CardBody>
          </Card>
        )}

        {/* Cash Flow Trend Chart */}
        {dashboardData?.cash_flow_trend && dashboardData.cash_flow_trend.length > 0 && (
          <Card>
            <CardBody>
              <Heading size="md" mb={4}>
                Cash Flow Trend
              </Heading>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={dashboardData.cash_flow_trend}>
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
                </BarChart>
              </ResponsiveContainer>
            </CardBody>
          </Card>
        )}

        {/* Top Expenses and Recent Transactions */}
        <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
          {/* Top Expense Categories */}
          {dashboardData?.top_expenses && dashboardData.top_expenses.length > 0 && (
            <Card>
              <CardBody>
                <Heading size="md" mb={4}>
                  Top Expense Categories
                </Heading>
                <VStack align="stretch" spacing={3}>
                  {dashboardData.top_expenses.map((expense, index) => (
                    <Box key={index}>
                      <HStack justify="space-between" mb={1}>
                        <Text fontWeight="medium">{expense.category}</Text>
                        <Text fontWeight="bold" color="red.600">
                          {formatCurrency(expense.total)}
                        </Text>
                      </HStack>
                      <Text fontSize="sm" color="gray.600">
                        {expense.count} transaction{expense.count !== 1 ? 's' : ''}
                      </Text>
                      {index < dashboardData.top_expenses.length - 1 && <Divider mt={3} />}
                    </Box>
                  ))}
                </VStack>
              </CardBody>
            </Card>
          )}

          {/* Recent Transactions */}
          {dashboardData?.recent_transactions && dashboardData.recent_transactions.length > 0 && (
            <Card>
              <CardBody>
                <Heading size="md" mb={4}>
                  Recent Transactions
                </Heading>
                <VStack align="stretch" spacing={3}>
                  {dashboardData.recent_transactions.map((txn) => (
                    <Box key={txn.id}>
                      <HStack justify="space-between" mb={1}>
                        <VStack align="start" spacing={0}>
                          <Text fontWeight="medium">{txn.merchant_name || 'Unknown'}</Text>
                          <HStack spacing={2}>
                            <Text fontSize="sm" color="gray.600">
                              {formatDate(txn.date)}
                            </Text>
                            {txn.is_pending && (
                              <Badge colorScheme="orange" size="sm">
                                Pending
                              </Badge>
                            )}
                          </HStack>
                        </VStack>
                        <Text
                          fontWeight="bold"
                          color={txn.amount >= 0 ? 'green.600' : 'red.600'}
                        >
                          {txn.amount >= 0 ? '+' : ''}
                          {formatCurrency(txn.amount)}
                        </Text>
                      </HStack>
                      {txn.category_primary && (
                        <Badge colorScheme="blue" size="sm">
                          {txn.category_primary}
                        </Badge>
                      )}
                    </Box>
                  ))}
                </VStack>
              </CardBody>
            </Card>
          )}
        </SimpleGrid>

        {/* Account Balances */}
        {sortedAccountBalances.length > 0 && (
          <Card>
            <CardBody>
              <Heading size="md" mb={4}>
                Account Balances
              </Heading>
              <Table variant="simple" size="sm">
                <Thead>
                  <Tr>
                    <Th>Account</Th>
                    <Th>Type</Th>
                    <Th>Institution</Th>
                    <Th isNumeric>Balance</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {sortedAccountBalances.map((account) => (
                    <Tr key={account.id}>
                      <Td fontWeight="medium">{account.name}</Td>
                      <Td>
                        <Badge>{account.type.replace('_', ' ')}</Badge>
                      </Td>
                      <Td color="gray.600">{account.institution || 'Manual'}</Td>
                      <Td isNumeric fontWeight="bold">
                        {formatCurrency(account.balance)}
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            </CardBody>
          </Card>
        )}
      </VStack>
    </Container>
  );
};
