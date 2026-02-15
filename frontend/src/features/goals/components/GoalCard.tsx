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
  Button,
} from '@chakra-ui/react';
import { EditIcon, DeleteIcon, SettingsIcon, RepeatIcon, CheckCircleIcon } from '@chakra-ui/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { SavingsGoal } from '../../../types/savings-goal';
import { savingsGoalsApi } from '../../../api/savings-goals';

interface GoalCardProps {
  goal: SavingsGoal;
  onEdit: (goal: SavingsGoal) => void;
}

export default function GoalCard({ goal, onEdit }: GoalCardProps) {
  const toast = useToast();
  const queryClient = useQueryClient();

  // Get progress data
  const { data: progress } = useQuery({
    queryKey: ['goals', goal.id, 'progress'],
    queryFn: () => savingsGoalsApi.getProgress(goal.id),
  });

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

  const percentage = progress?.progress_percentage ?? 0;
  const getProgressColor = () => {
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
          <VStack align="start" spacing={1}>
            <HStack>
              <Heading size="md">{goal.name}</Heading>
              {goal.is_completed && <CheckCircleIcon color="green.500" />}
            </HStack>
            {goal.description && (
              <Text fontSize="sm" color="gray.600">
                {goal.description}
              </Text>
            )}
          </VStack>

          <Menu>
            <MenuButton
              as={IconButton}
              icon={<SettingsIcon />}
              variant="ghost"
              size="sm"
            />
            <MenuList>
              {goal.account_id && (
                <MenuItem
                  icon={<RepeatIcon />}
                  onClick={() => syncMutation.mutate()}
                  isDisabled={syncMutation.isPending}
                >
                  Sync from Account
                </MenuItem>
              )}
              <MenuItem icon={<EditIcon />} onClick={() => onEdit(goal)}>
                Edit
              </MenuItem>
              <MenuItem
                icon={<DeleteIcon />}
                onClick={() => deleteMutation.mutate()}
                isDisabled={deleteMutation.isPending}
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
                {formatCurrency(goal.current_amount)} of {formatCurrency(goal.target_amount)}
              </Text>
              <Text fontSize="sm" color={getProgressColor()}>
                {percentage.toFixed(1)}%
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

          {/* On track indicator */}
          {progress && progress.on_track !== null && !goal.is_completed && (
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
        </VStack>
      </CardBody>
    </Card>
  );
}
