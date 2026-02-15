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
} from '@chakra-ui/react';
import { RepeatIcon, DeleteIcon } from '@chakra-ui/icons';
import { FiLock, FiRepeat } from 'react-icons/fi';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { recurringTransactionsApi } from '../api/recurring-transactions';
import { RecurringFrequency } from '../types/recurring-transaction';
import { useUserView } from '../contexts/UserViewContext';
import { EmptyState } from '../components/EmptyState';

export default function RecurringTransactionsPage() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const { canEdit, isOtherUserView } = useUserView();

  // Get all recurring patterns
  const { data: patterns = [], isLoading } = useQuery({
    queryKey: ['recurring-transactions'],
    queryFn: () => recurringTransactionsApi.getAll(),
  });

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
            <Heading size="lg">Recurring Transactions</Heading>
            <Text color="gray.600">
              Auto-detected patterns in your transaction history
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

        {/* Patterns table */}
        {!isLoading && patterns.length > 0 && (
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
        )}

        {/* Info box */}
        {!isLoading && patterns.length > 0 && (
          <Box p={4} bg="blue.50" borderRadius="md">
            <Text fontSize="sm" color="gray.700">
              💡 <strong>Tip:</strong> These patterns are auto-detected based on your transaction
              history. High confidence patterns are more reliable. You can delete any patterns that
              don't look right.
            </Text>
          </Box>
        )}
      </VStack>
    </Box>
  );
}
