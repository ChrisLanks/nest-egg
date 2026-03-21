/**
 * Savings goal card component
 */

import {
  AlertDialog,
  AlertDialogBody,
  AlertDialogContent,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogOverlay,
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
  Button,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  NumberInput,
  NumberInputField,
  FormControl,
  FormLabel,
  useDisclosure,
  useToast,
  Box,
  Checkbox,
  Tooltip,
  Icon,
  Divider,
  useColorModeValue,
} from '@chakra-ui/react';
import { EditIcon, DeleteIcon, SettingsIcon, RepeatIcon, AddIcon } from '@chakra-ui/icons';
import { FiMove, FiCheckSquare, FiLink, FiRefreshCw } from 'react-icons/fi';
import { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { SavingsGoal } from '../../../types/savings-goal';
import { savingsGoalsApi } from '../../../api/savings-goals';
import { accountsApi } from '../../../api/accounts';
import { useHouseholdMembers } from '../../../hooks/useHouseholdMembers';

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
  const { data: householdMembers = [] } = useHouseholdMembers();
  const { isOpen: isContribOpen, onOpen: onContribOpen, onClose: onContribClose } = useDisclosure();
  const { isOpen: isDeleteOpen, onOpen: onDeleteOpen, onClose: onDeleteClose } = useDisclosure();
  const deleteCancelRef = useRef<HTMLButtonElement>(null);
  const [contributionAmount, setContributionAmount] = useState('');

  // Build shared tooltip label
  const sharedLabel = (() => {
    if (!goal.is_shared) return '';
    if (!goal.shared_user_ids) return 'Shared with all members';
    const names = goal.shared_user_ids
      .map(id => householdMembers.find(m => m.id === id))
      .filter(Boolean)
      .map(m => m!.display_name || m!.first_name || m!.email);
    return `Shared with ${names.join(', ')}`;
  })();

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

  // Contribution mutation
  const contributionMutation = useMutation({
    mutationFn: (amount: number) => savingsGoalsApi.recordContribution(goal.id, amount),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['goals'] });
      onContribClose();
      setContributionAmount('');
      toast({
        title: `$${result.contribution_amount.toLocaleString()} contributed`,
        description: `New total: $${result.current_amount.toLocaleString()} of $${result.target_amount.toLocaleString()}`,
        status: 'success',
        duration: 4000,
      });
    },
    onError: () => {
      toast({ title: 'Failed to record contribution', status: 'error', duration: 3000 });
    },
  });

  const handleContribute = () => {
    const parsed = parseFloat(contributionAmount);
    if (!parsed || parsed <= 0) return;
    contributionMutation.mutate(parsed);
  };

  const percentage = progress?.progress_percentage ?? (
    goal.target_amount > 0 ? (goal.current_amount / goal.target_amount) * 100 : 0
  );

  // Blue in light mode (matches budgets), cyan in dark mode (better visibility)
  const accent = useColorModeValue('blue', 'cyan');

  const getProgressColor = () => {
    if (goal.is_funded) return 'purple';
    if (goal.is_completed) return 'green';
    if (progress?.on_track === false) return 'orange';
    return accent;
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
              {goal.is_shared && (
                <Tooltip label={sharedLabel} placement="top">
                  <Badge colorScheme="teal" cursor="default">Shared</Badge>
                </Tooltip>
              )}
              {goal.is_funded && <Badge colorScheme="purple">Funded</Badge>}
            </HStack>
            <Box minH="1.25rem">
              {goal.description && (
                <Text fontSize="sm" color="text.secondary" noOfLines={1}>
                  {goal.description}
                </Text>
              )}
            </Box>
            </VStack>
          </HStack>

          <HStack spacing={1} flexShrink={0}>
            {!goal.is_completed && !goal.is_funded && canEdit && (
              <Tooltip label="Record a contribution" placement="top">
                <IconButton
                  icon={<AddIcon />}
                  aria-label="Add contribution"
                  variant="ghost"
                  size="sm"
                  colorScheme="blue"
                  onClick={onContribOpen}
                />
              </Tooltip>
            )}
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
                  onClick={onDeleteOpen}
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
                <Text fontSize="xs" color="text.secondary">
                  Remaining
                </Text>
                <Text fontSize="sm" fontWeight="medium">
                  {formatCurrency(progress.remaining_amount)}
                </Text>
              </VStack>

              {progress.days_remaining !== null && (
                <VStack align="start" spacing={0}>
                  <Text fontSize="xs" color="text.secondary">
                    Days Left
                  </Text>
                  <Text fontSize="sm" fontWeight="medium">
                    {progress.days_remaining}
                  </Text>
                </VStack>
              )}

              {progress.monthly_required !== null && (
                <VStack align="start" spacing={0}>
                  <Text fontSize="xs" color="text.secondary">
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
            <Text fontSize="xs" color="text.muted">
              Target: {new Date(goal.target_date).toLocaleDateString()}
            </Text>
          )}

          {/* Member contributions */}
          {goal.member_contributions && Object.keys(goal.member_contributions).length > 0 && (
            <>
              <Divider />
              <VStack align="stretch" spacing={1}>
                <Text fontSize="xs" fontWeight="semibold" color="text.secondary">
                  Contributions
                </Text>
                {Object.entries(goal.member_contributions).map(([userId, amount]) => {
                  const member = householdMembers.find(m => m.id === userId);
                  const name = member?.display_name || member?.first_name || member?.email || userId;
                  return (
                    <HStack key={userId} justify="space-between">
                      <Text fontSize="xs" color="text.muted">{name}</Text>
                      <Text fontSize="xs" fontWeight="medium">{formatCurrency(amount)}</Text>
                    </HStack>
                  );
                })}
              </VStack>
            </>
          )}

          {/* Account & auto-sync metadata */}
          {linkedAccount && (
            <>
              <Divider />
              <HStack spacing={5}>
                <HStack spacing={1.5}>
                  <Icon as={FiLink} boxSize={3} color="text.muted" />
                  <Text fontSize="xs" color="text.muted">{linkedAccount.name}</Text>
                </HStack>
                <HStack spacing={1.5}>
                  <Icon as={FiRefreshCw} boxSize={3} color={goal.auto_sync ? 'cyan.400' : 'text.muted'} />
                  <Text fontSize="xs" color={goal.auto_sync ? 'cyan.500' : 'text.muted'}>
                    Auto-sync {goal.auto_sync ? 'on' : 'off'}
                  </Text>
                </HStack>
              </HStack>
            </>
          )}
        </VStack>
      </CardBody>

      {/* Add Contribution Modal */}
      <Modal isOpen={isContribOpen} onClose={onContribClose} size="sm">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Add Contribution</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <FormControl>
              <FormLabel fontSize="sm">Amount</FormLabel>
              <NumberInput
                min={0.01}
                precision={2}
                value={contributionAmount}
                onChange={(val) => setContributionAmount(val)}
              >
                <NumberInputField placeholder="0.00" autoFocus />
              </NumberInput>
            </FormControl>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onContribClose}>
              Cancel
            </Button>
            <Button
              colorScheme="blue"
              onClick={handleContribute}
              isLoading={contributionMutation.isPending}
              isDisabled={!contributionAmount || parseFloat(contributionAmount) <= 0}
            >
              Record Contribution
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Delete confirmation dialog */}
      <AlertDialog
        isOpen={isDeleteOpen}
        leastDestructiveRef={deleteCancelRef}
        onClose={onDeleteClose}
      >
        <AlertDialogOverlay>
          <AlertDialogContent>
            <AlertDialogHeader fontSize="lg" fontWeight="bold">
              Delete Goal
            </AlertDialogHeader>
            <AlertDialogBody>
              Are you sure you want to delete "{goal.name}"? This action cannot
              be undone.
            </AlertDialogBody>
            <AlertDialogFooter>
              <Button ref={deleteCancelRef} onClick={onDeleteClose}>
                Cancel
              </Button>
              <Button
                colorScheme="red"
                ml={3}
                isLoading={deleteMutation.isPending}
                onClick={() => {
                  deleteMutation.mutate(undefined, {
                    onSettled: onDeleteClose,
                  });
                }}
              >
                Delete
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>
    </Card>
  );
}
