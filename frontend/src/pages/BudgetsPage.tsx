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
  ButtonGroup,
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

type FilterTab = 'all' | 'category' | 'label';

export default function BudgetsPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedBudget, setSelectedBudget] = useState<Budget | null>(null);
  const [filterTab, setFilterTab] = useState<FilterTab>('all');
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

  // Apply filter tab
  const filterBudgets = (list: Budget[]) => {
    if (filterTab === 'category') return list.filter(b => !!b.category_id);
    if (filterTab === 'label') return list.filter(b => !!b.label_id);
    return list;
  };

  const activeBudgets = filterBudgets(budgets.filter(b => b.is_active));
  const inactiveBudgets = filterBudgets(budgets.filter(b => !b.is_active));

  // Count for filter badges
  const categoryCount = budgets.filter(b => !!b.category_id).length;
  const labelCount = budgets.filter(b => !!b.label_id).length;

  const filteredEmpty = activeBudgets.length === 0 && inactiveBudgets.length === 0;

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

        {/* Filter tabs */}
        {!isLoading && budgets.length > 0 && (
          <ButtonGroup size="sm" isAttached variant="outline">
            <Button
              colorScheme={filterTab === 'all' ? 'blue' : 'gray'}
              variant={filterTab === 'all' ? 'solid' : 'outline'}
              onClick={() => setFilterTab('all')}
            >
              All{' '}
              <Badge ml={1} colorScheme={filterTab === 'all' ? 'blue' : 'gray'}>
                {budgets.length}
              </Badge>
            </Button>
            <Button
              colorScheme={filterTab === 'category' ? 'blue' : 'gray'}
              variant={filterTab === 'category' ? 'solid' : 'outline'}
              onClick={() => setFilterTab('category')}
            >
              By Category{' '}
              <Badge ml={1} colorScheme={filterTab === 'category' ? 'blue' : 'gray'}>
                {categoryCount}
              </Badge>
            </Button>
            <Button
              colorScheme={filterTab === 'label' ? 'blue' : 'gray'}
              variant={filterTab === 'label' ? 'solid' : 'outline'}
              onClick={() => setFilterTab('label')}
            >
              By Label{' '}
              <Badge ml={1} colorScheme={filterTab === 'label' ? 'blue' : 'gray'}>
                {labelCount}
              </Badge>
            </Button>
          </ButtonGroup>
        )}

        {/* Loading state */}
        {isLoading && (
          <Center py={12}>
            <Spinner size="xl" />
          </Center>
        )}

        {/* Empty state — no budgets at all */}
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

        {/* Empty state — filter returns nothing */}
        {!isLoading && budgets.length > 0 && filteredEmpty && (
          <Center py={8}>
            <Text color="gray.500">
              No budgets match the selected filter.
            </Text>
          </Center>
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
