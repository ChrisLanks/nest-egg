/**
 * Budget card component showing budget progress
 */

import {
  Card,
  CardHeader,
  CardBody,
  Heading,
  Text,
  Progress,
  HStack,
  VStack,
  Badge,
  IconButton,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  useToast,
  Box,
} from '@chakra-ui/react';
import { EditIcon, DeleteIcon, SettingsIcon } from '@chakra-ui/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { Budget } from '../../../types/budget';
import { BudgetPeriod } from '../../../types/budget';
import { budgetsApi } from '../../../api/budgets';
import { labelsApi } from '../../../api/labels';

interface BudgetCardProps {
  budget: Budget;
  onEdit: (budget: Budget) => void;
  canEdit?: boolean;
}

export default function BudgetCard({ budget, onEdit, canEdit = true }: BudgetCardProps) {
  const toast = useToast();
  const queryClient = useQueryClient();

  // Get spending data
  const { data: spending } = useQuery({
    queryKey: ['budgets', budget.id, 'spending'],
    queryFn: () => budgetsApi.getSpending(budget.id),
  });

  // Fetch labels to resolve label name (uses shared cache, no extra network call)
  const { data: allLabels = [] } = useQuery({
    queryKey: ['labels'],
    queryFn: () => labelsApi.getAll(),
    enabled: !!budget.label_id,
  });
  const labelName = budget.label_id
    ? allLabels.find((l) => l.id === budget.label_id)?.name ?? null
    : null;

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: () => budgetsApi.delete(budget.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] });
      toast({
        title: 'Budget deleted',
        status: 'success',
        duration: 3000,
      });
    },
    onError: () => {
      toast({
        title: 'Failed to delete budget',
        status: 'error',
        duration: 3000,
      });
    },
  });

  const percentage = Number(spending?.percentage ?? 0);
  const getProgressColor = () => {
    if (percentage >= 100) return 'red';
    if (percentage >= budget.alert_threshold * 100) return 'orange';
    return 'green';
  };

  const formatPeriod = (period: BudgetPeriod) => {
    switch (period) {
      case BudgetPeriod.MONTHLY:
        return 'Monthly';
      case BudgetPeriod.QUARTERLY:
        return 'Quarterly';
      case BudgetPeriod.YEARLY:
        return 'Yearly';
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  return (
    <Card>
      <CardHeader pb={2}>
        <HStack justify="space-between">
          <VStack align="start" spacing={1}>
            <Heading size="md">{budget.name}</Heading>
            <HStack>
              <Badge colorScheme="blue" size="sm">
                {formatPeriod(budget.period)}
              </Badge>
              {labelName && (
                <Badge colorScheme="purple" size="sm">
                  {labelName}
                </Badge>
              )}
              {!budget.is_active && (
                <Badge colorScheme="gray" size="sm">
                  Inactive
                </Badge>
              )}
            </HStack>
          </VStack>

          <Menu>
            <MenuButton
              as={IconButton}
              icon={<SettingsIcon />}
              variant="ghost"
              size="sm"
            />
            <MenuList>
              <MenuItem icon={<EditIcon />} isDisabled={!canEdit} onClick={() => onEdit(budget)}>
                Edit
              </MenuItem>
              <MenuItem
                icon={<DeleteIcon />}
                onClick={() => deleteMutation.mutate()}
                isDisabled={!canEdit || deleteMutation.isPending}
                color="red.600"
              >
                Delete
              </MenuItem>
            </MenuList>
          </Menu>
        </HStack>
      </CardHeader>

      <CardBody>
        <VStack align="stretch" spacing={3}>
          {/* Progress bar */}
          <Box>
            <HStack justify="space-between" mb={2}>
              <Text fontSize="sm" fontWeight="medium">
                {formatCurrency(spending?.spent ?? 0)} of {formatCurrency(budget.amount)}
              </Text>
              <Text fontSize="sm" color={getProgressColor()}>
                {percentage.toFixed(1)}%
              </Text>
            </HStack>
            <Progress
              value={percentage}
              colorScheme={getProgressColor()}
              size="lg"
              borderRadius="md"
            />
          </Box>

          {/* Remaining amount */}
          <HStack justify="space-between">
            <Text fontSize="sm" color="gray.600">
              Remaining
            </Text>
            <Text
              fontSize="sm"
              fontWeight="medium"
              color={spending?.remaining && spending.remaining < 0 ? 'red.600' : 'green.600'}
            >
              {formatCurrency(spending?.remaining ?? budget.amount)}
            </Text>
          </HStack>

          {/* Period dates */}
          {spending && (
            <Text fontSize="xs" color="gray.500">
              {new Date(spending.period_start).toLocaleDateString()} -{' '}
              {new Date(spending.period_end).toLocaleDateString()}
            </Text>
          )}
        </VStack>
      </CardBody>
    </Card>
  );
}
