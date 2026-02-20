/**
 * Savings Goals page - manage all savings goals
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Button,
  ButtonGroup,
  Heading,
  HStack,
  Text,
  VStack,
  useDisclosure,
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
} from '@chakra-ui/react';
import { AddIcon } from '@chakra-ui/icons';
import { FiLock, FiTarget } from 'react-icons/fi';
import { useQuery, useQueryClient } from '@tanstack/react-query';
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
import type { SavingsGoal } from '../types/savings-goal';
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
// SavingsGoalsPage
// ---------------------------------------------------------------------------

export default function SavingsGoalsPage() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedGoal, setSelectedGoal] = useState<SavingsGoal | null>(null);
  const { canEdit, isOtherUserView } = useUserView();
  const queryClient = useQueryClient();

  // Allocation method — persisted in localStorage
  const [allocationMethod, setAllocationMethod] = useState<'waterfall' | 'proportional'>(
    () => (localStorage.getItem('savingsGoalAllocMethod') as 'waterfall' | 'proportional') ?? 'waterfall'
  );

  const handleMethodChange = (m: 'waterfall' | 'proportional') => {
    setAllocationMethod(m);
    localStorage.setItem('savingsGoalAllocMethod', m);
  };

  // Get all goals
  const { data: goals = [], isLoading } = useQuery({
    queryKey: ['goals'],
    queryFn: () => savingsGoalsApi.getAll(),
  });

  // Key built from auto-sync goals' id+account_id pairs.
  // Changes when a goal is added/removed, OR when its linked account is edited.
  // After auto-sync updates current_amount the key stays the same → no infinite loop.
  const autoSyncKey = goals
    .filter(g => !g.is_completed && !g.is_funded && g.auto_sync && g.account_id)
    .map(g => `${g.id}:${g.account_id}`)
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

  const activeGoals = goals.filter(g => !g.is_completed && !g.is_funded);
  const completedGoals = goals.filter(g => g.is_completed || g.is_funded);
  const hasAutoSyncGoals = activeGoals.some(g => g.auto_sync && g.account_id);

  // Drag-and-drop reorder
  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      if (!over || active.id === over.id) return;

      const oldIndex = activeGoals.findIndex(g => g.id === active.id);
      const newIndex = activeGoals.findIndex(g => g.id === over.id);
      if (oldIndex === -1 || newIndex === -1) return;

      const newIds = arrayMove(activeGoals, oldIndex, newIndex).map(g => g.id);

      // Optimistic update
      queryClient.setQueryData<SavingsGoal[]>(['goals'], old => {
        if (!old) return old;
        const reordered = arrayMove(activeGoals, oldIndex, newIndex);
        const rest = old.filter(g => g.is_completed || g.is_funded);
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

        {/* Allocation method selector — shown when auto-sync goals exist */}
        {hasAutoSyncGoals && (
          <HStack>
            <Text fontSize="sm" fontWeight="medium" color="gray.600">
              Balance allocation:
            </Text>
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
                  : 'Balance is split proportionally based on each goal\'s target amount.'
              }
              placement="right"
            >
              <Text fontSize="xs" color="gray.400" cursor="help">(?)</Text>
            </Tooltip>
          </HStack>
        )}

        {/* Loading state */}
        {isLoading && (
          <Center py={12}>
            <Spinner size="xl" />
          </Center>
        )}

        {/* Empty state */}
        {!isLoading && goals.length === 0 && (
          <EmptyState
            icon={FiTarget}
            title={isOtherUserView ? "This user has no savings goals yet" : "No savings goals yet"}
            description="Set savings goals to track progress toward vacations, emergency funds, down payments, and more."
            actionLabel="Create Your First Goal"
            onAction={handleCreate}
            showAction={!isOtherUserView}
          />
        )}

        {/* Goals tabs */}
        {!isLoading && goals.length > 0 && (
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
              {/* Active goals — sortable vertical list */}
              <TabPanel>
                {activeGoals.length === 0 ? (
                  <Center py={8}>
                    <Text color="gray.500">No active goals</Text>
                  </Center>
                ) : (
                  <DndContext collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
                    <SortableContext
                      items={activeGoals.map(g => g.id)}
                      strategy={verticalListSortingStrategy}
                    >
                      <VStack align="stretch" spacing={4}>
                        {activeGoals.map(goal => (
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
