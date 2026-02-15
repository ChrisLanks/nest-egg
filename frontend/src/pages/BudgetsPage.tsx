/**
 * Budgets page - manage all budgets
 */

import {
  Box,
  Button,
  Heading,
  HStack,
  SimpleGrid,
  Text,
  VStack,
  useDisclosure,
  Spinner,
  Center,
  Badge,
  Tooltip,
} from '@chakra-ui/react';
import { AddIcon } from '@chakra-ui/icons';
import { FiLock, FiDollarSign } from 'react-icons/fi';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { budgetsApi } from '../api/budgets';
import type { Budget } from '../types/budget';
import BudgetCard from '../features/budgets/components/BudgetCard';
import BudgetForm from '../features/budgets/components/BudgetForm';
import { useUserView } from '../contexts/UserViewContext';
import { EmptyState } from '../components/EmptyState';

export default function BudgetsPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedBudget, setSelectedBudget] = useState<Budget | null>(null);
  const { canEdit, isOtherUserView } = useUserView();

  // Get all budgets
  const { data: budgets = [], isLoading } = useQuery({
    queryKey: ['budgets'],
    queryFn: () => budgetsApi.getAll(),
  });

  const handleEdit = (budget: Budget) => {
    setSelectedBudget(budget);
    onOpen();
  };

  const handleCreate = () => {
    setSelectedBudget(null);
    onOpen();
  };

  const handleClose = () => {
    setSelectedBudget(null);
    onClose();
  };

  const activeBudgets = budgets.filter(b => b.is_active);
  const inactiveBudgets = budgets.filter(b => !b.is_active);

  return (
    <Box p={8}>
      <VStack align="stretch" spacing={6}>
        {/* Header */}
        <HStack justify="space-between">
          <VStack align="start" spacing={1}>
            <Heading size="lg">Budgets</Heading>
            <Text color="gray.600">
              Track spending and stay within your budget goals
            </Text>
          </VStack>
          <Tooltip
            label={!canEdit ? "Read-only: You can only create budgets for your own data" : ""}
            placement="top"
            isDisabled={canEdit}
          >
            <Button
              leftIcon={canEdit ? <AddIcon /> : <FiLock />}
              colorScheme="blue"
              onClick={handleCreate}
              isDisabled={!canEdit}
            >
              New Budget
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
        {!isLoading && budgets.length === 0 && (
          <EmptyState
            icon={FiDollarSign}
            title={isOtherUserView ? "This user has no budgets yet" : "No budgets yet"}
            description="Create budgets to track spending by category and stay on top of your financial goals."
            actionLabel="Create Your First Budget"
            onAction={handleCreate}
            showAction={!isOtherUserView}
          />
        )}

        {/* Active budgets */}
        {!isLoading && activeBudgets.length > 0 && (
          <VStack align="stretch" spacing={4}>
            <Heading size="md">
              Active Budgets{' '}
              <Badge colorScheme="green" ml={2}>
                {activeBudgets.length}
              </Badge>
            </Heading>
            <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={4}>
              {activeBudgets.map((budget) => (
                <BudgetCard key={budget.id} budget={budget} onEdit={handleEdit} />
              ))}
            </SimpleGrid>
          </VStack>
        )}

        {/* Inactive budgets */}
        {!isLoading && inactiveBudgets.length > 0 && (
          <VStack align="stretch" spacing={4}>
            <Heading size="md">
              Inactive Budgets{' '}
              <Badge colorScheme="gray" ml={2}>
                {inactiveBudgets.length}
              </Badge>
            </Heading>
            <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={4}>
              {inactiveBudgets.map((budget) => (
                <BudgetCard key={budget.id} budget={budget} onEdit={handleEdit} />
              ))}
            </SimpleGrid>
          </VStack>
        )}
      </VStack>

      {/* Budget form modal */}
      <BudgetForm isOpen={isOpen} onClose={handleClose} budget={selectedBudget} />
    </Box>
  );
}
