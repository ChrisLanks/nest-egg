/**
 * Debt Payoff Planner page with strategy comparison
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
  StatArrow,
  Button,
  Input,
  FormControl,
  FormLabel,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  Spinner,
  Center,
  useToast,
} from '@chakra-ui/react';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import api from '../services/api';
import { useUserView } from '../contexts/UserViewContext';

interface DebtAccount {
  account_id: string;
  name: string;
  balance: number;
  interest_rate: number;
  minimum_payment: number;
  account_type: string;
}

interface StrategyResult {
  strategy: string;
  total_months: number;
  total_interest: number;
  total_paid: number;
  debt_free_date: string | null;
  interest_saved_vs_current?: number;
  months_saved_vs_current?: number;
  debts: any[];
}

interface ComparisonResult {
  snowball: StrategyResult | null;
  avalanche: StrategyResult | null;
  current_pace: StrategyResult | null;
  recommendation: string | null;
}

export default function DebtPayoffPage() {
  const { selectedUserId } = useUserView();
  const toast = useToast();
  const [extraPayment, setExtraPayment] = useState('500');

  // Fetch debt summary
  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['debt-summary', selectedUserId],
    queryFn: async () => {
      const params: any = {};
      if (selectedUserId) params.user_id = selectedUserId;

      const response = await api.get('/debt-payoff/summary', { params });
      return response.data;
    },
  });

  // Fetch debt accounts
  const { data: debts, isLoading: debtsLoading } = useQuery<DebtAccount[]>({
    queryKey: ['debt-accounts', selectedUserId],
    queryFn: async () => {
      const params: any = {};
      if (selectedUserId) params.user_id = selectedUserId;

      const response = await api.get('/debt-payoff/debts', { params });
      return response.data;
    },
  });

  // Fetch strategy comparison
  const { data: comparison, isLoading: comparisonLoading, refetch } = useQuery<ComparisonResult>({
    queryKey: ['debt-comparison', extraPayment, selectedUserId],
    queryFn: async () => {
      const params: any = {
        extra_payment: parseFloat(extraPayment) || 0,
      };
      if (selectedUserId) params.user_id = selectedUserId;

      const response = await api.get('/debt-payoff/compare', { params });
      return response.data;
    },
    enabled: !!debts && debts.length > 0,
  });

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
  };

  const handleExtraPaymentChange = (value: string) => {
    // Only allow numbers and decimals
    if (/^\d*\.?\d*$/.test(value)) {
      setExtraPayment(value);
    }
  };

  if (summaryLoading || debtsLoading) {
    return (
      <Container maxW="container.xl" py={8}>
        <Center py={20}>
          <Spinner size="xl" color="brand.500" />
        </Center>
      </Container>
    );
  }

  if (!debts || debts.length === 0) {
    return (
      <Container maxW="container.xl" py={8}>
        <VStack spacing={8} align="stretch">
          <Box>
            <Heading size="lg">💳 Debt Payoff Planner</Heading>
            <Text color="gray.600">Strategic debt elimination tool</Text>
          </Box>
          <Card>
            <CardBody>
              <Center py={10}>
                <VStack spacing={4}>
                  <Text fontSize="lg" color="gray.600">
                    No debt accounts found
                  </Text>
                  <Text fontSize="sm" color="gray.500">
                    Add debt accounts (credit cards, loans, mortgages) to use the payoff planner
                  </Text>
                </VStack>
              </Center>
            </CardBody>
          </Card>
        </VStack>
      </Container>
    );
  }

  return (
    <Container maxW="container.xl" py={8}>
      <VStack spacing={8} align="stretch">
        {/* Header */}
        <Box>
          <Heading size="lg">💳 Debt Payoff Planner</Heading>
          <Text color="gray.600">Compare strategies to eliminate debt faster</Text>
        </Box>

        {/* Summary Cards */}
        {summary && (
          <SimpleGrid columns={{ base: 1, md: 4 }} spacing={6}>
            <Card>
              <CardBody>
                <Stat>
                  <StatLabel>Total Debt</StatLabel>
                  <StatNumber color="red.600">{formatCurrency(summary.total_debt)}</StatNumber>
                  <StatHelpText>{summary.debt_count} accounts</StatHelpText>
                </Stat>
              </CardBody>
            </Card>

            <Card>
              <CardBody>
                <Stat>
                  <StatLabel>Total Minimums</StatLabel>
                  <StatNumber>{formatCurrency(summary.total_minimum_payment)}</StatNumber>
                  <StatHelpText>Per month</StatHelpText>
                </Stat>
              </CardBody>
            </Card>

            <Card>
              <CardBody>
                <Stat>
                  <StatLabel>Avg Interest Rate</StatLabel>
                  <StatNumber>{summary.average_interest_rate.toFixed(2)}%</StatNumber>
                  <StatHelpText>Weighted average</StatHelpText>
                </Stat>
              </CardBody>
            </Card>

            <Card>
              <CardBody>
                <FormControl>
                  <FormLabel fontSize="sm">Extra Payment/Month</FormLabel>
                  <Input
                    type="text"
                    value={extraPayment}
                    onChange={(e) => handleExtraPaymentChange(e.target.value)}
                    onBlur={() => refetch()}
                    placeholder="500"
                  />
                </FormControl>
              </CardBody>
            </Card>
          </SimpleGrid>
        )}

        {/* Strategy Comparison */}
        {comparisonLoading ? (
          <Center py={10}>
            <Spinner size="lg" color="brand.500" />
          </Center>
        ) : comparison && (
          <SimpleGrid columns={{ base: 1, md: 3 }} spacing={6}>
            {/* Snowball Strategy */}
            {comparison.snowball && (
              <Card>
                <CardBody>
                  <VStack align="stretch" spacing={4}>
                    <HStack justify="space-between">
                      <Heading size="md">❄️ Snowball</Heading>
                      {comparison.recommendation === 'SNOWBALL' && (
                        <Badge colorScheme="green">Best Psychology</Badge>
                      )}
                    </HStack>
                    <Text fontSize="sm" color="gray.600">
                      Pay smallest balance first
                    </Text>

                    <Box>
                      <Text fontSize="sm" color="gray.600">
                        Debt-Free Date
                      </Text>
                      <Text fontSize="xl" fontWeight="bold">
                        {formatDate(comparison.snowball.debt_free_date)}
                      </Text>
                      <Text fontSize="xs" color="gray.500">
                        {comparison.snowball.total_months} months
                      </Text>
                    </Box>

                    <Box>
                      <Text fontSize="sm" color="gray.600">
                        Total Interest
                      </Text>
                      <Text fontSize="lg" fontWeight="semibold" color="red.600">
                        {formatCurrency(comparison.snowball.total_interest)}
                      </Text>
                    </Box>

                    {comparison.snowball.interest_saved_vs_current !== undefined && (
                      <Box bg="green.50" p={3} borderRadius="md">
                        <Text fontSize="xs" color="green.700" fontWeight="semibold">
                          Save {formatCurrency(comparison.snowball.interest_saved_vs_current)} interest
                        </Text>
                        <Text fontSize="xs" color="green.700">
                          {comparison.snowball.months_saved_vs_current} months faster
                        </Text>
                      </Box>
                    )}
                  </VStack>
                </CardBody>
              </Card>
            )}

            {/* Avalanche Strategy */}
            {comparison.avalanche && (
              <Card borderWidth={comparison.recommendation === 'AVALANCHE' ? 2 : 1} borderColor={comparison.recommendation === 'AVALANCHE' ? 'blue.500' : 'gray.200'}>
                <CardBody>
                  <VStack align="stretch" spacing={4}>
                    <HStack justify="space-between">
                      <Heading size="md">🔥 Avalanche</Heading>
                      {comparison.recommendation === 'AVALANCHE' && (
                        <Badge colorScheme="blue">Best Savings</Badge>
                      )}
                    </HStack>
                    <Text fontSize="sm" color="gray.600">
                      Pay highest interest first
                    </Text>

                    <Box>
                      <Text fontSize="sm" color="gray.600">
                        Debt-Free Date
                      </Text>
                      <Text fontSize="xl" fontWeight="bold">
                        {formatDate(comparison.avalanche.debt_free_date)}
                      </Text>
                      <Text fontSize="xs" color="gray.500">
                        {comparison.avalanche.total_months} months
                      </Text>
                    </Box>

                    <Box>
                      <Text fontSize="sm" color="gray.600">
                        Total Interest
                      </Text>
                      <Text fontSize="lg" fontWeight="semibold" color="red.600">
                        {formatCurrency(comparison.avalanche.total_interest)}
                      </Text>
                    </Box>

                    {comparison.avalanche.interest_saved_vs_current !== undefined && (
                      <Box bg="blue.50" p={3} borderRadius="md">
                        <Text fontSize="xs" color="blue.700" fontWeight="semibold">
                          Save {formatCurrency(comparison.avalanche.interest_saved_vs_current)} interest
                        </Text>
                        <Text fontSize="xs" color="blue.700">
                          {comparison.avalanche.months_saved_vs_current} months faster
                        </Text>
                      </Box>
                    )}
                  </VStack>
                </CardBody>
              </Card>
            )}

            {/* Current Pace */}
            {comparison.current_pace && (
              <Card>
                <CardBody>
                  <VStack align="stretch" spacing={4}>
                    <Heading size="md">🐢 Current Pace</Heading>
                    <Text fontSize="sm" color="gray.600">
                      Minimum payments only
                    </Text>

                    <Box>
                      <Text fontSize="sm" color="gray.600">
                        Debt-Free Date
                      </Text>
                      <Text fontSize="xl" fontWeight="bold">
                        {formatDate(comparison.current_pace.debt_free_date)}
                      </Text>
                      <Text fontSize="xs" color="gray.500">
                        {comparison.current_pace.total_months} months
                      </Text>
                    </Box>

                    <Box>
                      <Text fontSize="sm" color="gray.600">
                        Total Interest
                      </Text>
                      <Text fontSize="lg" fontWeight="semibold" color="red.600">
                        {formatCurrency(comparison.current_pace.total_interest)}
                      </Text>
                    </Box>

                    <Box bg="gray.50" p={3} borderRadius="md">
                      <Text fontSize="xs" color="gray.600">
                        Baseline comparison
                      </Text>
                    </Box>
                  </VStack>
                </CardBody>
              </Card>
            )}
          </SimpleGrid>
        )}

        {/* Debt Accounts List */}
        <Card>
          <CardBody>
            <VStack align="stretch" spacing={4}>
              <Heading size="md">Your Debts</Heading>
              <Table variant="simple" size="sm">
                <Thead>
                  <Tr>
                    <Th>Account</Th>
                    <Th>Type</Th>
                    <Th isNumeric>Balance</Th>
                    <Th isNumeric>Interest Rate</Th>
                    <Th isNumeric>Min Payment</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {debts.map((debt) => (
                    <Tr key={debt.account_id}>
                      <Td fontWeight="medium">{debt.name}</Td>
                      <Td>
                        <Badge colorScheme="purple">
                          {debt.account_type.replace('_', ' ')}
                        </Badge>
                      </Td>
                      <Td isNumeric>{formatCurrency(debt.balance)}</Td>
                      <Td isNumeric>{debt.interest_rate.toFixed(2)}%</Td>
                      <Td isNumeric>{formatCurrency(debt.minimum_payment)}</Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            </VStack>
          </CardBody>
        </Card>
      </VStack>
    </Container>
  );
}
