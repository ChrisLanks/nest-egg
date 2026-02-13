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
} from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '../features/auth/stores/authStore';
import api from '../services/api';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

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

export const DashboardPage = () => {
  const { user } = useAuthStore();

  const { data: dashboardData, isLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn: async () => {
      const response = await api.get<DashboardData>('/dashboard/');
      return response.data;
    },
  });

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
        {dashboardData?.account_balances && dashboardData.account_balances.length > 0 && (
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
                  {dashboardData.account_balances.map((account) => (
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
