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
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  ModalFooter,
  useDisclosure,
  Divider,
  Checkbox,
  ButtonGroup,
  IconButton,
  FormHelperText,
} from '@chakra-ui/react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, useEffect } from 'react';
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

const SELECTED_ACCOUNTS_KEY = 'debt-payoff-selected-accounts';

export default function DebtPayoffPage() {
  const { selectedUserId } = useUserView();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [extraPayment, setExtraPayment] = useState('500');
  const [selectedStrategy, setSelectedStrategy] = useState<StrategyResult | null>(null);
  const { isOpen, onOpen, onClose } = useDisclosure();
  const {
    isOpen: isEditOpen,
    onOpen: onEditOpen,
    onClose: onEditClose,
  } = useDisclosure();
  const [selectedAccounts, setSelectedAccounts] = useState<Set<string>>(new Set());
  const [editingDebt, setEditingDebt] = useState<DebtAccount | null>(null);
  const [editForm, setEditForm] = useState({
    interest_rate: '',
    minimum_payment: '',
    payment_due_day: '',
  });

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

  // Load selected accounts from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem(SELECTED_ACCOUNTS_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setSelectedAccounts(new Set(parsed));
      } catch (e) {
        console.error('Failed to parse selected accounts from localStorage');
      }
    }
  }, []);

  // Initialize selected accounts when debts load
  useEffect(() => {
    if (debts && debts.length > 0 && selectedAccounts.size === 0) {
      // If no saved selection, select all accounts by default
      const allAccountIds = debts.map((d) => d.account_id);
      setSelectedAccounts(new Set(allAccountIds));
    }
  }, [debts]);

  // Save selected accounts to localStorage whenever it changes
  useEffect(() => {
    if (selectedAccounts.size > 0) {
      localStorage.setItem(SELECTED_ACCOUNTS_KEY, JSON.stringify(Array.from(selectedAccounts)));
    }
  }, [selectedAccounts]);

  const toggleAccount = (accountId: string) => {
    const newSelected = new Set(selectedAccounts);
    if (newSelected.has(accountId)) {
      newSelected.delete(accountId);
    } else {
      newSelected.add(accountId);
    }
    setSelectedAccounts(newSelected);
  };

  const selectAll = () => {
    if (debts) {
      setSelectedAccounts(new Set(debts.map((d) => d.account_id)));
    }
  };

  const deselectAll = () => {
    setSelectedAccounts(new Set());
  };

  const handleEditDebt = (debt: DebtAccount) => {
    setEditingDebt(debt);
    setEditForm({
      interest_rate: debt.interest_rate?.toString() || '',
      minimum_payment: debt.minimum_payment?.toString() || '',
      payment_due_day: '', // Will be added if available
    });
    onEditOpen();
  };

  const updateDebtMutation = useMutation({
    mutationFn: async (data: { account_id: string; updates: any }) => {
      const response = await api.patch(`/accounts/${data.account_id}`, data.updates);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['debt-accounts'] });
      queryClient.invalidateQueries({ queryKey: ['debt-summary'] });
      queryClient.invalidateQueries({ queryKey: ['debt-comparison'] });
      toast({
        title: 'Debt details updated',
        status: 'success',
        duration: 3000,
      });
      onEditClose();
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to update debt',
        description: error?.response?.data?.detail || 'An error occurred',
        status: 'error',
        duration: 5000,
      });
    },
  });

  const handleSaveEdit = () => {
    if (!editingDebt) return;

    const updates: any = {};
    if (editForm.interest_rate) {
      updates.interest_rate = parseFloat(editForm.interest_rate);
    }
    if (editForm.minimum_payment) {
      updates.minimum_payment = parseFloat(editForm.minimum_payment);
    }
    if (editForm.payment_due_day) {
      updates.payment_due_day = parseInt(editForm.payment_due_day);
    }

    updateDebtMutation.mutate({
      account_id: editingDebt.account_id,
      updates,
    });
  };

  // Fetch strategy comparison
  const { data: comparison, isLoading: comparisonLoading, refetch } = useQuery<ComparisonResult>({
    queryKey: ['debt-comparison', extraPayment, selectedUserId, Array.from(selectedAccounts)],
    queryFn: async () => {
      const params: any = {
        extra_payment: parseFloat(extraPayment) || 0,
      };
      if (selectedUserId) params.user_id = selectedUserId;

      // Only include selected accounts
      if (selectedAccounts.size > 0) {
        params.account_ids = Array.from(selectedAccounts).join(',');
      }

      const response = await api.get('/debt-payoff/compare', { params });
      return response.data;
    },
    enabled: !!debts && debts.length > 0 && selectedAccounts.size > 0,
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
              <Card
                cursor="pointer"
                _hover={{ shadow: 'md', transform: 'translateY(-2px)', transition: 'all 0.2s' }}
                onClick={() => {
                  setSelectedStrategy(comparison.snowball);
                  onOpen();
                }}
              >
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
              <Card
                borderWidth={comparison.recommendation === 'AVALANCHE' ? 2 : 1}
                borderColor={comparison.recommendation === 'AVALANCHE' ? 'blue.500' : 'gray.200'}
                cursor="pointer"
                _hover={{ shadow: 'md', transform: 'translateY(-2px)', transition: 'all 0.2s' }}
                onClick={() => {
                  setSelectedStrategy(comparison.avalanche);
                  onOpen();
                }}
              >
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
              <Card
                cursor="pointer"
                _hover={{ shadow: 'md', transform: 'translateY(-2px)', transition: 'all 0.2s' }}
                onClick={() => {
                  setSelectedStrategy(comparison.current_pace);
                  onOpen();
                }}
              >
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
              <HStack justify="space-between">
                <Heading size="md">Your Debts</Heading>
                <ButtonGroup size="sm" variant="outline">
                  <Button onClick={selectAll}>Select All</Button>
                  <Button onClick={deselectAll}>Deselect All</Button>
                </ButtonGroup>
              </HStack>
              {selectedAccounts.size === 0 && (
                <Box bg="orange.50" p={3} borderRadius="md">
                  <Text fontSize="sm" color="orange.700">
                    ⚠️ Select at least one account to see payoff strategies
                  </Text>
                </Box>
              )}
              <Table variant="simple" size="sm">
                <Thead>
                  <Tr>
                    <Th width="40px">Include</Th>
                    <Th>Account</Th>
                    <Th>Type</Th>
                    <Th isNumeric>Balance</Th>
                    <Th isNumeric>Interest Rate</Th>
                    <Th isNumeric>Min Payment</Th>
                    <Th width="80px">Actions</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {debts.map((debt) => (
                    <Tr
                      key={debt.account_id}
                      opacity={selectedAccounts.has(debt.account_id) ? 1 : 0.5}
                      bg={selectedAccounts.has(debt.account_id) ? 'transparent' : 'gray.50'}
                    >
                      <Td>
                        <Checkbox
                          isChecked={selectedAccounts.has(debt.account_id)}
                          onChange={() => toggleAccount(debt.account_id)}
                          colorScheme="blue"
                        />
                      </Td>
                      <Td fontWeight="medium">{debt.name}</Td>
                      <Td>
                        <Badge colorScheme="purple">
                          {debt.account_type.replace('_', ' ')}
                        </Badge>
                      </Td>
                      <Td isNumeric>{formatCurrency(debt.balance)}</Td>
                      <Td isNumeric>{debt.interest_rate.toFixed(2)}%</Td>
                      <Td isNumeric>{formatCurrency(debt.minimum_payment)}</Td>
                      <Td>
                        <Button
                          size="xs"
                          variant="ghost"
                          colorScheme="blue"
                          onClick={() => handleEditDebt(debt)}
                        >
                          Edit
                        </Button>
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            </VStack>
          </CardBody>
        </Card>

        {/* Strategy Detail Modal */}
        <Modal isOpen={isOpen} onClose={onClose} size="4xl" scrollBehavior="inside">
          <ModalOverlay />
          <ModalContent>
            <ModalHeader>
              {selectedStrategy?.strategy === 'SNOWBALL' && '❄️ Snowball Strategy Details'}
              {selectedStrategy?.strategy === 'AVALANCHE' && '🔥 Avalanche Strategy Details'}
              {selectedStrategy?.strategy === 'CURRENT' && '🐢 Current Pace Details'}
            </ModalHeader>
            <ModalCloseButton />
            <ModalBody>
              {selectedStrategy && (
                <VStack align="stretch" spacing={6}>
                  {/* Summary */}
                  <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
                    <Box>
                      <Text fontSize="sm" color="gray.600">
                        Debt-Free Date
                      </Text>
                      <Text fontSize="2xl" fontWeight="bold">
                        {formatDate(selectedStrategy.debt_free_date)}
                      </Text>
                      <Text fontSize="sm" color="gray.500">
                        {selectedStrategy.total_months} months
                      </Text>
                    </Box>
                    <Box>
                      <Text fontSize="sm" color="gray.600">
                        Total Interest Paid
                      </Text>
                      <Text fontSize="2xl" fontWeight="bold" color="red.600">
                        {formatCurrency(selectedStrategy.total_interest)}
                      </Text>
                    </Box>
                    <Box>
                      <Text fontSize="sm" color="gray.600">
                        Total Amount Paid
                      </Text>
                      <Text fontSize="2xl" fontWeight="bold">
                        {formatCurrency(selectedStrategy.total_paid)}
                      </Text>
                    </Box>
                  </SimpleGrid>

                  {selectedStrategy.interest_saved_vs_current !== undefined && (
                    <Box bg="green.50" p={4} borderRadius="md">
                      <Text fontSize="md" fontWeight="semibold" color="green.700">
                        💰 Save {formatCurrency(selectedStrategy.interest_saved_vs_current)} in interest
                      </Text>
                      <Text fontSize="sm" color="green.700">
                        Become debt-free {selectedStrategy.months_saved_vs_current} months faster than minimum payments
                      </Text>
                    </Box>
                  )}

                  <Divider />

                  {/* Payment Schedule by Account */}
                  <Box>
                    <Heading size="md" mb={4}>
                      Payment Schedule
                    </Heading>
                    <Text fontSize="sm" color="gray.600" mb={4}>
                      {selectedStrategy.strategy === 'SNOWBALL' &&
                        'Debts are paid off in order from smallest balance to largest, with extra payments accelerating each payoff.'}
                      {selectedStrategy.strategy === 'AVALANCHE' &&
                        'Debts are paid off in order from highest interest rate to lowest, maximizing interest savings.'}
                      {selectedStrategy.strategy === 'CURRENT' &&
                        'Making only minimum payments on all debts.'}
                    </Text>

                    {selectedStrategy.debts && selectedStrategy.debts.length > 0 ? (
                      <VStack align="stretch" spacing={4}>
                        {selectedStrategy.debts.map((debt: any, idx: number) => (
                          <Card key={idx} variant="outline">
                            <CardBody>
                              <VStack align="stretch" spacing={3}>
                                <HStack justify="space-between">
                                  <Box>
                                    <Text fontWeight="bold" fontSize="lg">
                                      {debt.name || `Debt ${idx + 1}`}
                                    </Text>
                                    <Badge colorScheme="purple" mt={1}>
                                      {debt.account_type?.replace('_', ' ') || 'Account'}
                                    </Badge>
                                  </Box>
                                  <Box textAlign="right">
                                    <Text fontSize="sm" color="gray.600">
                                      Payoff Order
                                    </Text>
                                    <Text fontSize="2xl" fontWeight="bold" color="blue.600">
                                      #{idx + 1}
                                    </Text>
                                  </Box>
                                </HStack>

                                <SimpleGrid columns={{ base: 2, md: 4 }} spacing={3}>
                                  <Box>
                                    <Text fontSize="xs" color="gray.600">
                                      Starting Balance
                                    </Text>
                                    <Text fontWeight="semibold">
                                      {formatCurrency(debt.starting_balance || 0)}
                                    </Text>
                                  </Box>
                                  <Box>
                                    <Text fontSize="xs" color="gray.600">
                                      Interest Rate
                                    </Text>
                                    <Text fontWeight="semibold">{debt.interest_rate?.toFixed(2) || 0}%</Text>
                                  </Box>
                                  <Box>
                                    <Text fontSize="xs" color="gray.600">
                                      Months to Payoff
                                    </Text>
                                    <Text fontWeight="semibold">{debt.months_to_payoff || 0} months</Text>
                                  </Box>
                                  <Box>
                                    <Text fontSize="xs" color="gray.600">
                                      Total Interest
                                    </Text>
                                    <Text fontWeight="semibold" color="red.600">
                                      {formatCurrency(debt.total_interest || 0)}
                                    </Text>
                                  </Box>
                                </SimpleGrid>

                                {debt.payoff_date && (
                                  <Box bg="gray.50" p={2} borderRadius="md">
                                    <Text fontSize="sm">
                                      <Text as="span" fontWeight="semibold">
                                        Paid off:
                                      </Text>{' '}
                                      {formatDate(debt.payoff_date)}
                                    </Text>
                                  </Box>
                                )}
                              </VStack>
                            </CardBody>
                          </Card>
                        ))}
                      </VStack>
                    ) : (
                      <Box textAlign="center" py={8} bg="gray.50" borderRadius="md">
                        <Text color="gray.600">No detailed payment schedule available</Text>
                      </Box>
                    )}
                  </Box>
                </VStack>
              )}
            </ModalBody>
            <ModalFooter>
              <Button colorScheme="blue" onClick={onClose}>
                Close
              </Button>
            </ModalFooter>
          </ModalContent>
        </Modal>

        {/* Edit Debt Details Modal */}
        <Modal isOpen={isEditOpen} onClose={onEditClose} size="lg">
          <ModalOverlay />
          <ModalContent>
            <ModalHeader>Edit Debt Details - {editingDebt?.name}</ModalHeader>
            <ModalCloseButton />
            <ModalBody>
              <VStack spacing={4} align="stretch">
                <FormControl>
                  <FormLabel>Interest Rate (APR %)</FormLabel>
                  <Input
                    type="number"
                    step="0.01"
                    value={editForm.interest_rate}
                    onChange={(e) =>
                      setEditForm({ ...editForm, interest_rate: e.target.value })
                    }
                    placeholder="18.99"
                  />
                  <FormHelperText>Annual Percentage Rate (e.g., 18.99 for 18.99%)</FormHelperText>
                </FormControl>

                <FormControl>
                  <FormLabel>Minimum Monthly Payment</FormLabel>
                  <Input
                    type="number"
                    step="0.01"
                    value={editForm.minimum_payment}
                    onChange={(e) =>
                      setEditForm({ ...editForm, minimum_payment: e.target.value })
                    }
                    placeholder="150.00"
                  />
                  <FormHelperText>Required minimum payment each month</FormHelperText>
                </FormControl>

                <FormControl>
                  <FormLabel>Payment Due Day (Optional)</FormLabel>
                  <Input
                    type="number"
                    min="1"
                    max="31"
                    value={editForm.payment_due_day}
                    onChange={(e) =>
                      setEditForm({ ...editForm, payment_due_day: e.target.value })
                    }
                    placeholder="15"
                  />
                  <FormHelperText>Day of month payment is due (1-31)</FormHelperText>
                </FormControl>

                <Box bg="blue.50" p={3} borderRadius="md">
                  <Text fontSize="sm" color="blue.700">
                    💡 <Text as="span" fontWeight="semibold">Tip:</Text> Interest rate
                    and minimum payment are used to calculate payoff strategies. More
                    accurate values lead to better projections.
                  </Text>
                </Box>
              </VStack>
            </ModalBody>
            <ModalFooter>
              <ButtonGroup>
                <Button variant="ghost" onClick={onEditClose}>
                  Cancel
                </Button>
                <Button
                  colorScheme="blue"
                  onClick={handleSaveEdit}
                  isLoading={updateDebtMutation.isPending}
                >
                  Save Changes
                </Button>
              </ButtonGroup>
            </ModalFooter>
          </ModalContent>
        </Modal>
      </VStack>
    </Container>
  );
}
