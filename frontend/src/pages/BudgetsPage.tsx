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
import { useHouseholdMembers } from '../hooks/useHouseholdMembers';
import { useAuthStore } from '../features/auth/stores/authStore';

type FilterTab = 'all' | 'category' | 'label';

export default function BudgetsPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedBudget, setSelectedBudget] = useState<Budget | null>(null);
  const [filterTab, setFilterTab] = useState<FilterTab>('all');
  const [filterUserId, setFilterUserId] = useState<string | null>(null);
  const { canWriteResource, isOtherUserView, isCombinedView, isSelfView, selectedUserId } = useUserView();
  const canEdit = canWriteResource('budget');

  // Household members for user filter (only in combined view)
  const { data: householdMembers = [] } = useHouseholdMembers();
  const currentUser = useAuthStore((s) => s.user);
  const showUserFilter = isCombinedView && householdMembers.length > 1;

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

  // Apply view-based and user filter
  const filterByUser = (list: Budget[]) => {
    // Self view: show budgets you created + shared budgets you're part of
    if (isSelfView && currentUser) {
      return list.filter(b => {
        // Your own budget
        if (b.user_id === currentUser.id) return true;
        // Shared with all members
        if (b.is_shared && !b.shared_user_ids) return true;
        // Shared with you specifically
        if (b.is_shared && b.shared_user_ids?.includes(currentUser.id)) return true;
        // Legacy budgets without user_id (pre-migration) — show them
        if (!b.user_id) return true;
        return false;
      });
    }
    // Combined view with member filter active
    if (filterUserId) {
      return list.filter(b => {
        // Budget created by the selected member
        if (b.user_id === filterUserId) return true;
        // Shared with all members
        if (b.is_shared && !b.shared_user_ids) return true;
        // Shared with the selected member specifically
        if (b.is_shared && b.shared_user_ids?.includes(filterUserId)) return true;
        return false;
      });
    }
    return list;
  };

  // Apply filter tab
  const filterBudgets = (list: Budget[]) => {
    let filtered = filterByUser(list);
    if (filterTab === 'category') filtered = filtered.filter(b => !!b.category_id);
    if (filterTab === 'label') filtered = filtered.filter(b => !!b.label_id);
    return filtered;
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
            <Text color="text.secondary">
              Track spending and stay within your budget goals
            </Text>
          </VStack>
          <Tooltip
            label={
              filterUserId
                ? "Switch to 'All' or your own view to create budgets"
                : !canEdit ? "Read-only: You can only create budgets for your own data" : ""
            }
            placement="top"
            isDisabled={canEdit && !filterUserId}
          >
            <Button
              leftIcon={canEdit && !filterUserId ? <AddIcon /> : <FiLock />}
              colorScheme="blue"
              onClick={handleCreate}
              isDisabled={!canEdit || !!filterUserId}
            >
              New Budget
            </Button>
          </Tooltip>
        </HStack>

        {/* Member filter — always visible in combined household view */}
        {showUserFilter && (
          <HStack spacing={2}>
            <Text fontSize="sm" fontWeight="medium" color="text.secondary">Member:</Text>
            <ButtonGroup size="sm" isAttached variant="outline">
              <Button
                colorScheme={!filterUserId ? 'blue' : 'gray'}
                variant={!filterUserId ? 'solid' : 'outline'}
                onClick={() => setFilterUserId(null)}
              >
                All
              </Button>
              {householdMembers.map((member) => (
                <Button
                  key={member.id}
                  colorScheme={filterUserId === member.id ? 'blue' : 'gray'}
                  variant={filterUserId === member.id ? 'solid' : 'outline'}
                  onClick={() => setFilterUserId(member.id)}
                >
                  {member.display_name || member.first_name || member.email.split('@')[0]}
                </Button>
              ))}
            </ButtonGroup>
          </HStack>
        )}

        {/* Filter row */}
        {!isLoading && budgets.length > 0 && (
          <HStack spacing={6} flexWrap="wrap">
            {/* Type filter */}
            <HStack spacing={2}>
              <Text fontSize="sm" fontWeight="medium" color="text.secondary">Filter:</Text>
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
            </HStack>
          </HStack>
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
            title={
              filterUserId
                ? `${householdMembers.find((m) => m.id === filterUserId)?.display_name || householdMembers.find((m) => m.id === filterUserId)?.first_name || 'This member'} has no budgets yet`
                : isOtherUserView ? "This user has no budgets yet" : "No budgets yet"
            }
            description="Create budgets to track spending by category and stay on top of your financial goals."
            actionLabel="Create Your First Budget"
            onAction={handleCreate}
            showAction={canEdit && !filterUserId}
          />
        )}

        {/* Empty state — filter returns nothing */}
        {!isLoading && budgets.length > 0 && filteredEmpty && (
          <Center py={8}>
            <Text color="text.muted">
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
                <BudgetCard key={budget.id} budget={budget} onEdit={handleEdit} canEdit={canEdit} />
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
                <BudgetCard key={budget.id} budget={budget} onEdit={handleEdit} canEdit={canEdit} />
              ))}
            </SimpleGrid>
          </VStack>
        )}
      </VStack>

      {/* Budget form modal — key forces remount so defaultValues reset on each open */}
      <BudgetForm key={selectedBudget?.id ?? 'new'} isOpen={isOpen} onClose={handleClose} budget={selectedBudget} />
    </Box>
  );
}
