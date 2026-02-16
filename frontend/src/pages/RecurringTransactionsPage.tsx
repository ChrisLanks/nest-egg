/**
 * Recurring Transactions page - view and manage recurring patterns
 */

import {
  Box,
  Button,
  Heading,
  HStack,
  Text,
  VStack,
  Spinner,
  Center,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  IconButton,
  useToast,
  Card,
  CardBody,
  Tooltip,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  SimpleGrid,
} from '@chakra-ui/react';
import { RepeatIcon, DeleteIcon } from '@chakra-ui/icons';
import { FiLock, FiRepeat } from 'react-icons/fi';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, useMemo } from 'react';
import { recurringTransactionsApi } from '../api/recurring-transactions';
import { RecurringFrequency } from '../types/recurring-transaction';
import { useUserView } from '../contexts/UserViewContext';
import { EmptyState } from '../components/EmptyState';

export default function RecurringTransactionsPage() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const { canEdit, isOtherUserView } = useUserView();
  const [tabIndex, setTabIndex] = useState(0);

  // Get all recurring patterns
  const { data: patterns = [], isLoading } = useQuery({
    queryKey: ['recurring-transactions'],
    queryFn: () => recurringTransactionsApi.getAll(),
  });

  // Filter for subscriptions: monthly/yearly with high confidence (>70%)
  const subscriptions = useMemo(() => {
    return patterns.filter(
      (pattern) =>
        (pattern.frequency === RecurringFrequency.MONTHLY ||
          pattern.frequency === RecurringFrequency.YEARLY) &&
        (pattern.confidence_score ?? 0) >= 0.7
    );
  }, [patterns]);

  // Calculate subscription summary
  const subscriptionSummary = useMemo(() => {
    const monthlyTotal = subscriptions.reduce((sum, sub) => {
      const amount = Math.abs(sub.average_amount);
      if (sub.frequency === RecurringFrequency.MONTHLY) {
        return sum + amount;
      } else if (sub.frequency === RecurringFrequency.YEARLY) {
        return sum + amount / 12;
      }
      return sum;
    }, 0);

    return {
      count: subscriptions.length,
      monthlyTotal,
      yearlyTotal: monthlyTotal * 12,
    };
  }, [subscriptions]);

  // Detect patterns mutation
  const detectMutation = useMutation({
    mutationFn: () => recurringTransactionsApi.detectPatterns(),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['recurring-transactions'] });
      toast({
        title: `Detected ${data.detected_patterns} recurring patterns`,
        status: 'success',
        duration: 3000,
      });
    },
    onError: () => {
      toast({
        title: 'Failed to detect patterns',
        status: 'error',
        duration: 3000,
      });
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => recurringTransactionsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recurring-transactions'] });
      toast({
        title: 'Pattern deleted',
        status: 'success',
        duration: 2000,
      });
    },
  });

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const formatFrequency = (frequency: RecurringFrequency) => {
    switch (frequency) {
      case RecurringFrequency.WEEKLY:
        return 'Weekly';
      case RecurringFrequency.BIWEEKLY:
        return 'Bi-weekly';
      case RecurringFrequency.MONTHLY:
        return 'Monthly';
      case RecurringFrequency.QUARTERLY:
        return 'Quarterly';
      case RecurringFrequency.YEARLY:
        return 'Yearly';
    }
  };

  return (
    <Box p={8}>
      <VStack align="stretch" spacing={6}>
        {/* Read-only banner */}
        {isOtherUserView && (
          <Box p={4} bg="orange.50" borderRadius="md" borderWidth={1} borderColor="orange.200">
            <HStack>
              <FiLock size={16} color="orange.600" />
              <Text fontSize="sm" color="orange.800" fontWeight="medium">
                Read-only view: You can view patterns but cannot detect new ones or delete existing patterns for another household member.
              </Text>
            </HStack>
          </Box>
        )}

        {/* Header */}
        <HStack justify="space-between">
          <VStack align="start" spacing={1}>
            <Heading size="lg">Recurring Transactions & Subscriptions</Heading>
            <Text color="gray.600">
              Auto-detected patterns and subscription charges
            </Text>
          </VStack>
          <Tooltip
            label={!canEdit ? "Read-only: You can only detect patterns for your own data" : ""}
            placement="top"
            isDisabled={canEdit}
          >
            <Button
              leftIcon={canEdit ? <RepeatIcon /> : <FiLock />}
              colorScheme="blue"
              onClick={() => detectMutation.mutate()}
              isLoading={detectMutation.isPending}
              isDisabled={!canEdit}
            >
              Detect Patterns
            </Button>
          </Tooltip>
        </HStack>

        {/* Loading state */}
        {isLoading && (
          <Center py={12}>
            <Spinner size="xl" />
          </Center>
        )}

        {/* Empty state */}
        {!isLoading && patterns.length === 0 && (
          <EmptyState
            icon={FiRepeat}
            title={isOtherUserView
              ? "This user has no recurring patterns detected yet"
              : "No recurring patterns detected yet"}
            description="Automatically detect subscription payments, bills, and other recurring transactions in your history."
            actionLabel="Detect Patterns Now"
            onAction={() => detectMutation.mutate()}
            showAction={!isOtherUserView}
          />
        )}

        {/* Tabs for All Recurring vs Subscriptions */}
        {!isLoading && patterns.length > 0 && (
          <Tabs index={tabIndex} onChange={setTabIndex} colorScheme="brand">
            <TabList>
              <Tab>All Recurring ({patterns.length})</Tab>
              <Tab>Subscriptions ({subscriptions.length})</Tab>
            </TabList>

            <TabPanels>
              {/* All Recurring Tab */}
              <TabPanel px={0}>
                <VStack align="stretch" spacing={6}>
                  <Card>
                    <CardBody p={0}>
                      <Box overflowX="auto">
                        <Table variant="simple">
                          <Thead>
                            <Tr>
                              <Th>Merchant</Th>
                              <Th>Frequency</Th>
                              <Th isNumeric>Amount</Th>
                              <Th>Occurrences</Th>
                              <Th>Next Expected</Th>
                              <Th>Confidence</Th>
                              <Th>Type</Th>
                              <Th>Actions</Th>
                            </Tr>
                          </Thead>
                          <Tbody>
                            {patterns.map((pattern) => (
                              <Tr key={pattern.id}>
                                <Td fontWeight="medium">{pattern.merchant_name}</Td>
                                <Td>
                                  <Badge colorScheme="blue">
                                    {formatFrequency(pattern.frequency)}
                                  </Badge>
                                </Td>
                                <Td isNumeric>{formatCurrency(pattern.average_amount)}</Td>
                                <Td>{pattern.occurrence_count}×</Td>
                                <Td>
                                  {pattern.next_expected_date
                                    ? new Date(pattern.next_expected_date).toLocaleDateString()
                                    : '—'}
                                </Td>
                                <Td>
                                  {pattern.confidence_score !== null && (
                                    <Badge
                                      colorScheme={
                                        pattern.confidence_score >= 0.8
                                          ? 'green'
                                          : pattern.confidence_score >= 0.6
                                          ? 'yellow'
                                          : 'orange'
                                      }
                                    >
                                      {(pattern.confidence_score * 100).toFixed(0)}%
                                    </Badge>
                                  )}
                                </Td>
                                <Td>
                                  <Badge colorScheme={pattern.is_user_created ? 'purple' : 'gray'}>
                                    {pattern.is_user_created ? 'Manual' : 'Auto'}
                                  </Badge>
                                </Td>
                                <Td>
                                  <Tooltip
                                    label={!canEdit ? "Read-only: You can only delete your own patterns" : ""}
                                    placement="top"
                                    isDisabled={canEdit}
                                  >
                                    <IconButton
                                      aria-label="Delete"
                                      icon={!canEdit ? <FiLock /> : <DeleteIcon />}
                                      size="sm"
                                      variant="ghost"
                                      colorScheme={!canEdit ? "gray" : "red"}
                                      onClick={() => deleteMutation.mutate(pattern.id)}
                                      isLoading={deleteMutation.isPending}
                                      isDisabled={!canEdit}
                                    />
                                  </Tooltip>
                                </Td>
                              </Tr>
                            ))}
                          </Tbody>
                        </Table>
                      </Box>
                    </CardBody>
                  </Card>

                  <Box p={4} bg="blue.50" borderRadius="md">
                    <Text fontSize="sm" color="gray.700">
                      💡 <strong>Tip:</strong> These patterns are auto-detected based on your transaction
                      history. High confidence patterns are more reliable. You can delete any patterns that
                      don't look right.
                    </Text>
                  </Box>
                </VStack>
              </TabPanel>

              {/* Subscriptions Tab */}
              <TabPanel px={0}>
                <VStack align="stretch" spacing={6}>
                  {/* Summary Cards */}
                  <SimpleGrid columns={{ base: 1, md: 3 }} spacing={6}>
                    <Card>
                      <CardBody>
                        <Stat>
                          <StatLabel>Active Subscriptions</StatLabel>
                          <StatNumber>{subscriptionSummary.count}</StatNumber>
                          <StatHelpText>Monthly & yearly charges</StatHelpText>
                        </Stat>
                      </CardBody>
                    </Card>

                    <Card>
                      <CardBody>
                        <Stat>
                          <StatLabel>Monthly Cost</StatLabel>
                          <StatNumber color="red.600">
                            {formatCurrency(subscriptionSummary.monthlyTotal)}
                          </StatNumber>
                          <StatHelpText>Recurring charges</StatHelpText>
                        </Stat>
                      </CardBody>
                    </Card>

                    <Card>
                      <CardBody>
                        <Stat>
                          <StatLabel>Yearly Cost</StatLabel>
                          <StatNumber>
                            {formatCurrency(subscriptionSummary.yearlyTotal)}
                          </StatNumber>
                          <StatHelpText>Annual total</StatHelpText>
                        </Stat>
                      </CardBody>
                    </Card>
                  </SimpleGrid>

                  {/* Subscriptions table */}
                  {subscriptions.length > 0 ? (
                    <Card>
                      <CardBody p={0}>
                        <Box overflowX="auto">
                          <Table variant="simple">
                            <Thead>
                              <Tr>
                                <Th>Service</Th>
                                <Th>Frequency</Th>
                                <Th isNumeric>Amount</Th>
                                <Th>Next Charge</Th>
                                <Th>Confidence</Th>
                                <Th>Actions</Th>
                              </Tr>
                            </Thead>
                            <Tbody>
                              {subscriptions.map((sub) => (
                                <Tr key={sub.id}>
                                  <Td fontWeight="medium">{sub.merchant_name}</Td>
                                  <Td>
                                    <Badge colorScheme="purple">
                                      {formatFrequency(sub.frequency)}
                                    </Badge>
                                  </Td>
                                  <Td isNumeric>{formatCurrency(Math.abs(sub.average_amount))}</Td>
                                  <Td>
                                    {sub.next_expected_date
                                      ? new Date(sub.next_expected_date).toLocaleDateString()
                                      : '—'}
                                  </Td>
                                  <Td>
                                    <Badge
                                      colorScheme={sub.confidence_score >= 0.85 ? 'green' : 'yellow'}
                                    >
                                      {((sub.confidence_score ?? 0) * 100).toFixed(0)}%
                                    </Badge>
                                  </Td>
                                  <Td>
                                    <Tooltip
                                      label={!canEdit ? "Read-only: You can only delete your own patterns" : "Not a subscription"}
                                      placement="top"
                                    >
                                      <IconButton
                                        aria-label="Delete"
                                        icon={!canEdit ? <FiLock /> : <DeleteIcon />}
                                        size="sm"
                                        variant="ghost"
                                        colorScheme={!canEdit ? "gray" : "red"}
                                        onClick={() => deleteMutation.mutate(sub.id)}
                                        isLoading={deleteMutation.isPending}
                                        isDisabled={!canEdit}
                                      />
                                    </Tooltip>
                                  </Td>
                                </Tr>
                              ))}
                            </Tbody>
                          </Table>
                        </Box>
                      </CardBody>
                    </Card>
                  ) : (
                    <EmptyState
                      icon={FiRepeat}
                      title="No subscriptions detected"
                      description="We'll automatically detect recurring monthly and yearly charges as transactions are imported."
                    />
                  )}

                  <Box p={4} bg="purple.50" borderRadius="md">
                    <Text fontSize="sm" color="gray.700">
                      💡 <strong>Subscriptions</strong> are recurring charges that happen monthly or yearly
                      with high confidence (70%+). If you see something that's not actually a subscription,
                      you can remove it.
                    </Text>
                  </Box>
                </VStack>
              </TabPanel>
            </TabPanels>
          </Tabs>
        )}
      </VStack>
    </Box>
  );
}
