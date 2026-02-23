/**
 * Savings goal card component
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
  Checkbox,
  Tooltip,
  Icon,
  Divider,
} from '@chakra-ui/react';
import { EditIcon, DeleteIcon, SettingsIcon, RepeatIcon } from '@chakra-ui/icons';
import { FiMove, FiCheckSquare, FiLink, FiRefreshCw } from 'react-icons/fi';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { SavingsGoal } from '../../../types/savings-goal';
import { savingsGoalsApi } from '../../../api/savings-goals';
import { accountsApi } from '../../../api/accounts';

interface GoalCardProps {
  goal: SavingsGoal;
  onEdit: (goal: SavingsGoal) => void;
  showFundButton?: boolean;
  canEdit?: boolean;
  dragHandleListeners?: Record<string, unknown>;
  dragHandleAttributes?: Record<string, unknown>;
  method?: 'waterfall' | 'proportional';
}

export default function GoalCard({
  goal,
  onEdit,
  showFundButton,
  dragHandleListeners,
  dragHandleAttributes,
  method = 'waterfall',
  canEdit = true,
}: GoalCardProps) {
  const toast = useToast();
  const queryClient = useQueryClient();

  // Get progress data
  const { data: progress } = useQuery({
    queryKey: ['goals', goal.id, 'progress'],
    queryFn: () => savingsGoalsApi.getProgress(goal.id),
  });

  // Get accounts (served from cache — same query key used in GoalForm)
  const { data: accounts = [] } = useQuery({
    queryKey: ['accounts'],
    queryFn: accountsApi.getAccounts,
  });
  const linkedAccount = goal.account_id ? accounts.find(a => a.id === goal.account_id) : null;

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: () => savingsGoalsApi.delete(goal.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['goals'] });
      toast({
        title: 'Goal deleted',
        status: 'success',
        duration: 3000,
      });
    },
  });

  // Sync mutation
  const syncMutation = useMutation({
    mutationFn: () => savingsGoalsApi.syncFromAccount(goal.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['goals'] });
      toast({
        title: 'Goal synced from account',
        status: 'success',
        duration: 3000,
      });
    },
  });

  // Complete/uncomplete mutation
  const completeMutation = useMutation({
    mutationFn: () => savingsGoalsApi.update(goal.id, { is_completed: !goal.is_completed }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['goals'] });
    },
    onError: () => {
      toast({ title: 'Failed to update goal', status: 'error', duration: 3000 });
    },
  });

  // Fund mutation
  const fundMutation = useMutation({
    mutationFn: () => savingsGoalsApi.fund(goal.id, method),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['goals'] });
      toast({
        title: 'Goal marked as funded',
        description: 'Remaining goals have been recalculated.',
        status: 'success',
        duration: 4000,
      });
    },
    onError: () => {
      toast({ title: 'Failed to fund goal', status: 'error', duration: 3000 });
    },
  });

  const percentage = progress?.progress_percentage ?? (
    goal.target_amount > 0 ? (goal.current_amount / goal.target_amount) * 100 : 0
  );

  const getProgressColor = () => {
    if (goal.is_funded) return 'purple';
    if (goal.is_completed) return 'green';
    if (progress?.on_track === false) return 'orange';
    return 'blue';
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
          <HStack spacing={3} flex={1} minW={0} align="flex-start">
            {!goal.is_funded && (
              <Tooltip label={goal.is_completed ? 'Mark as incomplete' : 'Mark as complete'} placement="top">
                <Checkbox
                  isChecked={goal.is_completed}
                  onChange={() => completeMutation.mutate()}
                  isDisabled={!canEdit || completeMutation.isPending}
                  colorScheme="green"
                  size="lg"
                  flexShrink={0}
                />
              </Tooltip>
            )}
            <VStack align="start" spacing={1} minW={0}>
            <HStack flexWrap="wrap">
              <Heading size="md" noOfLines={1}>{goal.name}</Heading>
              {goal.is_funded && <Badge colorScheme="purple">Funded</Badge>}
            </HStack>
            <Box minH="1.25rem">
              {goal.description && (
                <Text fontSize="sm" color="gray.600" noOfLines={1}>
                  {goal.description}
                </Text>
              )}
            </Box>
            </VStack>
          </HStack>

          <HStack spacing={1} flexShrink={0}>
            {dragHandleListeners && (
              <IconButton
                icon={<FiMove />}
                aria-label="Drag to reorder"
                variant="ghost"
                size="sm"
                cursor="grab"
                {...(dragHandleListeners as object)}
                {...(dragHandleAttributes as object)}
              />
            )}
            <Menu>
              <MenuButton
                as={IconButton}
                icon={<SettingsIcon />}
                variant="ghost"
                size="sm"
              />
              <MenuList>
                {showFundButton && !goal.is_funded && (
                  <MenuItem
                    icon={<FiCheckSquare />}
                    onClick={() => fundMutation.mutate()}
                    isDisabled={!canEdit || fundMutation.isPending}
                  >
                    Mark as Funded
                  </MenuItem>
                )}
                {goal.account_id && !goal.auto_sync && (
                  <MenuItem
                    icon={<RepeatIcon />}
                    onClick={() => syncMutation.mutate()}
                    isDisabled={!canEdit || syncMutation.isPending}
                  >
                    Sync from Account
                  </MenuItem>
                )}
                <MenuItem icon={<EditIcon />} isDisabled={!canEdit} onClick={() => onEdit(goal)}>
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
        </HStack>
      </CardHeader>

      <CardBody>
        <VStack align="stretch" spacing={3}>
          {/* Progress bar */}
          <Box>
            <HStack justify="space-between" mb={2}>
              <Text fontSize="sm" fontWeight="medium">
                {formatCurrency(goal.current_amount)} of {formatCurrency(goal.target_amount)}
              </Text>
              <Text fontSize="sm" color={getProgressColor()}>
                {Math.min(percentage, 100).toFixed(1)}%
              </Text>
            </HStack>
            <Progress
              value={Math.min(percentage, 100)}
              colorScheme={getProgressColor()}
              size="lg"
              borderRadius="md"
            />
          </Box>

          {/* Stats grid */}
          {progress && (
            <HStack spacing={4} justify="space-between">
              <VStack align="start" spacing={0}>
                <Text fontSize="xs" color="gray.600">
                  Remaining
                </Text>
                <Text fontSize="sm" fontWeight="medium">
                  {formatCurrency(progress.remaining_amount)}
                </Text>
              </VStack>

              {progress.days_remaining !== null && (
                <VStack align="start" spacing={0}>
                  <Text fontSize="xs" color="gray.600">
                    Days Left
                  </Text>
                  <Text fontSize="sm" fontWeight="medium">
                    {progress.days_remaining}
                  </Text>
                </VStack>
              )}

              {progress.monthly_required !== null && (
                <VStack align="start" spacing={0}>
                  <Text fontSize="xs" color="gray.600">
                    Per Month
                  </Text>
                  <Text fontSize="sm" fontWeight="medium">
                    {formatCurrency(progress.monthly_required)}
                  </Text>
                </VStack>
              )}
            </HStack>
          )}

          {/* Status badges */}
          {!goal.is_funded && progress && progress.on_track !== null && !goal.is_completed && (
            <Badge
              colorScheme={progress.on_track ? 'green' : 'orange'}
              alignSelf="flex-start"
            >
              {progress.on_track ? 'On Track' : 'Behind Schedule'}
            </Badge>
          )}

          {/* Target date */}
          {goal.target_date && (
            <Text fontSize="xs" color="gray.500">
              Target: {new Date(goal.target_date).toLocaleDateString()}
            </Text>
          )}

          {/* Account & auto-sync metadata */}
          {linkedAccount && (
            <>
              <Divider />
              <HStack spacing={5}>
                <HStack spacing={1.5}>
                  <Icon as={FiLink} boxSize={3} color="gray.400" />
                  <Text fontSize="xs" color="gray.500">{linkedAccount.name}</Text>
                </HStack>
                <HStack spacing={1.5}>
                  <Icon as={FiRefreshCw} boxSize={3} color={goal.auto_sync ? 'blue.400' : 'gray.300'} />
                  <Text fontSize="xs" color={goal.auto_sync ? 'blue.500' : 'gray.400'}>
                    Auto-sync {goal.auto_sync ? 'on' : 'off'}
                  </Text>
                </HStack>
              </HStack>
            </>
          )}
        </VStack>
      </CardBody>
    </Card>
  );
}
