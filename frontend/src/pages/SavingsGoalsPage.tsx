/**
 * Savings Goals page - manage all savings goals
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Button,
  ButtonGroup,
  Card,
  CardBody,
  Heading,
  HStack,
  Icon,
  Text,
  VStack,
  useDisclosure,
  useToast,
  Spinner,
  Center,
  Badge,
  Tabs,
  TabList,
  Tab,
  TabPanels,
  TabPanel,
  Tooltip,
  SimpleGrid,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
} from '@chakra-ui/react';
import { AddIcon } from '@chakra-ui/icons';
import { FiLock, FiTarget, FiShield } from 'react-icons/fi';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  DndContext,
  closestCenter,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
  arrayMove,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { savingsGoalsApi } from '../api/savings-goals';
import { accountsApi } from '../api/accounts';
import type { SavingsGoal } from '../types/savings-goal';
import type { Account } from '../types/account';
import GoalCard from '../features/goals/components/GoalCard';
import GoalForm from '../features/goals/components/GoalForm';
import { useUserView } from '../contexts/UserViewContext';
import { EmptyState } from '../components/EmptyState';

// ---------------------------------------------------------------------------
// SortableGoalCard — wraps GoalCard with dnd-kit drag-and-drop support
// ---------------------------------------------------------------------------

interface SortableGoalCardProps {
  goal: SavingsGoal;
  onEdit: (goal: SavingsGoal) => void;
  method: 'waterfall' | 'proportional';
}

function SortableGoalCard({ goal, onEdit, method }: SortableGoalCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: goal.id });

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div ref={setNodeRef} style={style}>
      <GoalCard
        goal={goal}
        onEdit={onEdit}
        showFundButton
        dragHandleListeners={listeners as Record<string, unknown>}
        dragHandleAttributes={attributes as Record<string, unknown>}
        method={method}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// AccountGroup — collapsible accordion section for goals under one account
// ---------------------------------------------------------------------------

interface AccountGroupProps {
  accountName: string;
  goals: SavingsGoal[];
  onEdit: (goal: SavingsGoal) => void;
}

function AccountGroup({ accountName, goals, onEdit }: AccountGroupProps) {
  return (
    <AccordionItem border="1px solid" borderColor="gray.200" borderRadius="md" overflow="hidden">
      <AccordionButton bg="gray.50" _expanded={{ bg: 'blue.50' }} py={3} px={4}>
        <HStack flex={1} textAlign="left" spacing={3}>
          <Text fontWeight="semibold" fontSize="md">
            {accountName}
          </Text>
          <Badge colorScheme="blue" size="sm">
            {goals.length} {goals.length === 1 ? 'goal' : 'goals'}
          </Badge>
        </HStack>
        <AccordionIcon />
      </AccordionButton>
      <AccordionPanel pb={4} pt={3} px={4}>
        <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={4}>
          {goals.map((goal) => (
            <GoalCard key={goal.id} goal={goal} onEdit={onEdit} showFundButton />
          ))}
        </SimpleGrid>
      </AccordionPanel>
    </AccordionItem>
  );
}

// ---------------------------------------------------------------------------
// SavingsGoalsPage
// ---------------------------------------------------------------------------

type ViewMode = 'priority' | 'account';

export default function SavingsGoalsPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedGoal, setSelectedGoal] = useState<SavingsGoal | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('priority');
  const { canEdit, isOtherUserView } = useUserView();
  const queryClient = useQueryClient();
  const toast = useToast();

  // Allocation method — persisted in localStorage
  const [allocationMethod, setAllocationMethod] = useState<'waterfall' | 'proportional'>(
    () => (localStorage.getItem('savingsGoalAllocMethod') as 'waterfall' | 'proportional') ?? 'waterfall'
  );

  const handleMethodChange = (m: 'waterfall' | 'proportional') => {
    setAllocationMethod(m);
    localStorage.setItem('savingsGoalAllocMethod', m);
  };

  // Get all goals
  const { data: goals = [], isLoading: goalsLoading } = useQuery({
    queryKey: ['goals'],
    queryFn: () => savingsGoalsApi.getAll(),
  });

  // Get accounts for name lookup (shared cache — no extra network calls if already fetched)
  const { data: accounts = [] } = useQuery({
    queryKey: ['accounts'],
    queryFn: () => accountsApi.getAccounts(),
  });

  // Build account lookup map: id → Account
  const accountMap = new Map<string, Account>(accounts.map((a) => [a.id, a]));

  // Key built from auto-sync goals' id+account_id pairs
  const autoSyncKey = goals
    .filter((g) => !g.is_completed && !g.is_funded && g.auto_sync && g.account_id)
    .map((g) => `${g.id}:${g.account_id}`)
    .join(',');

  useEffect(() => {
    if (!autoSyncKey) return;
    savingsGoalsApi
      .autoSync(allocationMethod)
      .then(() => queryClient.invalidateQueries({ queryKey: ['goals'] }))
      .catch(() => {/* silently ignore — goals still display with last known values */});
  }, [autoSyncKey, allocationMethod]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleEdit = (goal: SavingsGoal) => {
    setSelectedGoal(goal);
    onOpen();
  };

  const handleCreate = () => {
    setSelectedGoal(null);
    onOpen();
  };

  const handleClose = () => {
    setSelectedGoal(null);
    onClose();
  };

  const activeGoals = goals.filter((g) => !g.is_completed && !g.is_funded);
  const completedGoals = goals.filter((g) => g.is_completed || g.is_funded);
  const hasAutoSyncGoals = activeGoals.some((g) => g.auto_sync && g.account_id);

  // Emergency Fund quick-start — hide if one already exists
  const hasEmergencyFundGoal = goals.some((g) =>
    g.name.toLowerCase().includes('emergency')
  );

  const createFromTemplateMutation = useMutation({
    mutationFn: () => savingsGoalsApi.createFromTemplate('emergency_fund'),
    onSuccess: (goal) => {
      queryClient.invalidateQueries({ queryKey: ['goals'] });
      toast({
        title: 'Emergency Fund created',
        description: `Target set to $${Number(goal.target_amount).toLocaleString()} — edit anytime to adjust.`,
        status: 'success',
        duration: 5000,
        isClosable: true,
      });
    },
    onError: () => {
      toast({ title: 'Could not create goal', status: 'error', duration: 3000 });
    },
  });

  // Group active goals by account_id for the "By Account" view
  const goalsByAccount = (() => {
    const groups = new Map<string | null, SavingsGoal[]>();
    for (const goal of activeGoals) {
      const key = goal.account_id ?? null;
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key)!.push(goal);
    }
    return groups;
  })();

  // Sorted account entries (alphabetical by account name), unlinked always last
  const linkedAccountEntries = Array.from(goalsByAccount.entries())
    .filter(([id]) => id !== null)
    .sort(([aId], [bId]) => {
      const aName = accountMap.get(aId!)?.name ?? '';
      const bName = accountMap.get(bId!)?.name ?? '';
      return aName.localeCompare(bName);
    }) as [string, SavingsGoal[]][];

  const unlinkedGoals = goalsByAccount.get(null) ?? [];

  // Number of accordion sections to open by default (all of them)
  const defaultOpenIndices = Array.from(
    { length: linkedAccountEntries.length + (unlinkedGoals.length > 0 ? 1 : 0) },
    (_, i) => i
  );

  // Drag-and-drop reorder (priority view only)
  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      if (!over || active.id === over.id) return;

      const oldIndex = activeGoals.findIndex((g) => g.id === active.id);
      const newIndex = activeGoals.findIndex((g) => g.id === over.id);
      if (oldIndex === -1 || newIndex === -1) return;

      const newIds = arrayMove(activeGoals, oldIndex, newIndex).map((g) => g.id);

      // Optimistic update
      queryClient.setQueryData<SavingsGoal[]>(['goals'], (old) => {
        if (!old) return old;
        const reordered = arrayMove(activeGoals, oldIndex, newIndex);
        const rest = old.filter((g) => g.is_completed || g.is_funded);
        return [...reordered, ...rest];
      });

      savingsGoalsApi.reorder(newIds).catch(() => {
        queryClient.invalidateQueries({ queryKey: ['goals'] });
      });
    },
    [activeGoals, queryClient]
  );

  return (
    <Box p={8}>
      <VStack align="stretch" spacing={6}>
        {/* Header */}
        <HStack justify="space-between">
          <VStack align="start" spacing={1}>
            <Heading size="lg">Savings Goals</Heading>
            <Text color="gray.600">
              Track progress toward your financial goals
            </Text>
          </VStack>
          <Tooltip
            label={!canEdit ? "Read-only: You can only create goals for your own data" : ""}
            placement="top"
            isDisabled={canEdit}
          >
            <Button
              leftIcon={canEdit ? <AddIcon /> : <FiLock />}
              colorScheme="blue"
              onClick={handleCreate}
              isDisabled={!canEdit}
            >
              New Goal
            </Button>
          </Tooltip>
        </HStack>

        {/* Controls row — view toggle + allocation method */}
        {!goalsLoading && goals.length > 0 && (
          <HStack spacing={6} flexWrap="wrap">
            {/* View mode toggle */}
            <HStack spacing={2}>
              <Text fontSize="sm" fontWeight="medium" color="gray.600">View:</Text>
              <ButtonGroup size="sm" isAttached variant="outline">
                <Button
                  colorScheme={viewMode === 'priority' ? 'blue' : 'gray'}
                  variant={viewMode === 'priority' ? 'solid' : 'outline'}
                  onClick={() => setViewMode('priority')}
                >
                  Priority Order
                </Button>
                <Button
                  colorScheme={viewMode === 'account' ? 'blue' : 'gray'}
                  variant={viewMode === 'account' ? 'solid' : 'outline'}
                  onClick={() => setViewMode('account')}
                >
                  By Account
                </Button>
              </ButtonGroup>
            </HStack>

            {/* Allocation method — shown when auto-sync goals exist */}
            {hasAutoSyncGoals && (
              <HStack spacing={2}>
                <Text fontSize="sm" fontWeight="medium" color="gray.600">Balance allocation:</Text>
                <ButtonGroup size="sm" isAttached variant="outline">
                  <Button
                    colorScheme={allocationMethod === 'waterfall' ? 'blue' : 'gray'}
                    variant={allocationMethod === 'waterfall' ? 'solid' : 'outline'}
                    onClick={() => handleMethodChange('waterfall')}
                  >
                    Priority Waterfall
                  </Button>
                  <Button
                    colorScheme={allocationMethod === 'proportional' ? 'blue' : 'gray'}
                    variant={allocationMethod === 'proportional' ? 'solid' : 'outline'}
                    onClick={() => handleMethodChange('proportional')}
                  >
                    Proportional
                  </Button>
                </ButtonGroup>
                <Tooltip
                  label={
                    allocationMethod === 'waterfall'
                      ? 'Goal 1 claims its full target first, then Goal 2, and so on.'
                      : "Balance is split proportionally based on each goal's target amount."
                  }
                  placement="right"
                >
                  <Text fontSize="xs" color="gray.400" cursor="help">(?)</Text>
                </Tooltip>
              </HStack>
            )}
          </HStack>
        )}

        {/* Loading state */}
        {goalsLoading && (
          <Center py={12}>
            <Spinner size="xl" />
          </Center>
        )}

        {/* Empty state */}
        {!goalsLoading && goals.length === 0 && (
          <EmptyState
            icon={FiTarget}
            title={isOtherUserView ? "This user has no savings goals yet" : "No savings goals yet"}
            description="Set savings goals to track progress toward vacations, emergency funds, down payments, and more."
            actionLabel="Create Your First Goal"
            onAction={handleCreate}
            showAction={!isOtherUserView}
          />
        )}

        {/* Emergency Fund quick-start card */}
        {!goalsLoading && !isOtherUserView && canEdit && !hasEmergencyFundGoal && (
          <Card variant="outline" borderColor="blue.200" bg="blue.50">
            <CardBody>
              <HStack justify="space-between" flexWrap="wrap" spacing={4}>
                <HStack spacing={3}>
                  <Icon as={FiShield} boxSize={6} color="blue.500" />
                  <VStack align="start" spacing={0}>
                    <Text fontWeight="semibold" color="blue.800">
                      Emergency Fund
                    </Text>
                    <Text fontSize="sm" color="blue.600">
                      Auto-calculates your 6-month target from spending history
                    </Text>
                  </VStack>
                </HStack>
                <Button
                  colorScheme="blue"
                  size="sm"
                  onClick={() => createFromTemplateMutation.mutate()}
                  isLoading={createFromTemplateMutation.isPending}
                >
                  Create Goal
                </Button>
              </HStack>
            </CardBody>
          </Card>
        )}

        {/* Goals tabs */}
        {!goalsLoading && goals.length > 0 && (
          <Tabs variant="enclosed" colorScheme="brand">
            <TabList>
              <Tab>
                Active Goals{' '}
                <Badge ml={2} colorScheme="blue">
                  {activeGoals.length}
                </Badge>
              </Tab>
              <Tab>
                Completed Goals{' '}
                <Badge ml={2} colorScheme="green">
                  {completedGoals.length}
                </Badge>
              </Tab>
            </TabList>

            <TabPanels>
              {/* Active goals */}
              <TabPanel>
                {activeGoals.length === 0 ? (
                  <Center py={8}>
                    <Text color="gray.500">No active goals</Text>
                  </Center>
                ) : viewMode === 'priority' ? (
                  /* Priority order — DnD sortable vertical list */
                  <DndContext collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
                    <SortableContext
                      items={activeGoals.map((g) => g.id)}
                      strategy={verticalListSortingStrategy}
                    >
                      <VStack align="stretch" spacing={4}>
                        {activeGoals.map((goal) => (
                          <SortableGoalCard
                            key={goal.id}
                            goal={goal}
                            onEdit={handleEdit}
                            method={allocationMethod}
                          />
                        ))}
                      </VStack>
                    </SortableContext>
                  </DndContext>
                ) : (
                  /* By Account — collapsible accordion groups */
                  <Accordion allowMultiple defaultIndex={defaultOpenIndices}>
                    <VStack align="stretch" spacing={3}>
                      {linkedAccountEntries.map(([accountId, groupGoals]) => (
                        <AccountGroup
                          key={accountId}
                          accountName={accountMap.get(accountId)?.name ?? 'Unknown Account'}
                          goals={groupGoals}
                          onEdit={handleEdit}
                        />
                      ))}
                      {unlinkedGoals.length > 0 && (
                        <AccountGroup
                          key="unlinked"
                          accountName="Not linked to an account"
                          goals={unlinkedGoals}
                          onEdit={handleEdit}
                        />
                      )}
                    </VStack>
                  </Accordion>
                )}
              </TabPanel>

              {/* Completed goals — static grid */}
              <TabPanel>
                {completedGoals.length === 0 ? (
                  <Center py={8}>
                    <Text color="gray.500">No completed goals yet</Text>
                  </Center>
                ) : (
                  <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={4}>
                    {completedGoals.map((goal) => (
                      <GoalCard key={goal.id} goal={goal} onEdit={handleEdit} />
                    ))}
                  </SimpleGrid>
                )}
              </TabPanel>
            </TabPanels>
          </Tabs>
        )}
      </VStack>

      {/* Goal form modal — key forces remount so defaultValues reset on each open */}
      <GoalForm key={selectedGoal?.id ?? 'new'} isOpen={isOpen} onClose={handleClose} goal={selectedGoal} />
    </Box>
  );
}
