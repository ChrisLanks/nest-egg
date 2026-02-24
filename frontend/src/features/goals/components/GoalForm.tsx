/**
 * Savings goal form for creating/editing goals
 */

import { useEffect } from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  Button,
  FormControl,
  FormLabel,
  FormHelperText,
  Input,
  Select,
  VStack,
  HStack,
  NumberInput,
  NumberInputField,
  Textarea,
  Switch,
  Checkbox,
  useToast,
  Box,
} from '@chakra-ui/react';
import { useForm, Controller, useWatch } from 'react-hook-form';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { SavingsGoal, SavingsGoalCreate } from '../../../types/savings-goal';
import { savingsGoalsApi } from '../../../api/savings-goals';
import { accountsApi } from '../../../api/accounts';
import { useHouseholdMembers } from '../../../hooks/useHouseholdMembers';
import { useAuthStore } from '../../auth/stores/authStore';

interface GoalFormProps {
  isOpen: boolean;
  onClose: () => void;
  goal?: SavingsGoal | null;
}

export default function GoalForm({ isOpen, onClose, goal }: GoalFormProps) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const isEditing = !!goal;

  const { register, handleSubmit, control, watch, setValue, formState: { errors, isSubmitting } } = useForm<SavingsGoalCreate>({
    defaultValues: goal ? {
      name: goal.name,
      description: goal.description ?? undefined,
      target_amount: goal.target_amount,
      current_amount: goal.current_amount,
      start_date: goal.start_date,
      target_date: goal.target_date ?? undefined,
      account_id: goal.account_id ?? undefined,
      auto_sync: goal.auto_sync,
      is_shared: goal.is_shared,
      shared_user_ids: goal.shared_user_ids ?? null,
    } : {
      current_amount: 0,
      start_date: new Date().toISOString().split('T')[0],
      auto_sync: false,
      is_shared: false,
      shared_user_ids: null,
    },
  });

  // Watch account_id to conditionally show auto_sync toggle
  const watchedAccountId = useWatch({ control, name: 'account_id' });

  // Auto-manage auto_sync based on account selection
  useEffect(() => {
    if (!watchedAccountId) {
      setValue('auto_sync', false);
    } else if (!isEditing) {
      setValue('auto_sync', true);
    }
  }, [watchedAccountId, isEditing, setValue]);

  // Get accounts for dropdown
  const { data: accounts = [] } = useQuery({
    queryKey: ['accounts'],
    queryFn: accountsApi.getAccounts,
  });

  // Household members for shared goal feature
  const { data: householdMembers = [] } = useHouseholdMembers();
  const currentUser = useAuthStore((s) => s.user);
  const otherMembers = householdMembers.filter((m) => m.id !== currentUser?.id);
  const showSharedSection = otherMembers.length > 0;

  // Watch shared fields
  const isShared = watch('is_shared');
  const sharedUserIds = watch('shared_user_ids');
  const allMembersSelected = sharedUserIds === null || sharedUserIds === undefined;

  // Create/update mutation
  const mutation = useMutation({
    mutationFn: (data: SavingsGoalCreate) => {
      if (isEditing && goal) {
        return savingsGoalsApi.update(goal.id, data);
      }
      return savingsGoalsApi.create(data);
    },
    onSuccess: async (savedGoal) => {
      if (isEditing) {
        // Immediately update the cache so the next Edit click has fresh data
        queryClient.setQueryData<SavingsGoal[]>(['goals'], (old) =>
          old?.map(g => g.id === savedGoal.id ? savedGoal : g) ?? []
        );
      }
      if (savedGoal.auto_sync && savedGoal.account_id) {
        const method = (localStorage.getItem('savingsGoalAllocMethod') as 'waterfall' | 'proportional') ?? 'waterfall';
        await savingsGoalsApi.autoSync(method).catch(() => {});
      }
      queryClient.invalidateQueries({ queryKey: ['goals'] });
      toast({
        title: isEditing ? 'Goal updated' : 'Goal created',
        status: 'success',
        duration: 3000,
      });
      onClose();
    },
    onError: () => {
      toast({
        title: `Failed to ${isEditing ? 'update' : 'create'} goal`,
        status: 'error',
        duration: 3000,
      });
    },
  });

  const onSubmit = (data: SavingsGoalCreate) => {
    mutation.mutate({
      ...data,
      target_date: data.target_date || undefined,
      description: data.description || undefined,
      account_id: data.account_id || undefined,
      is_shared: data.is_shared ?? false,
      shared_user_ids: data.is_shared ? (data.shared_user_ids ?? null) : null,
    });
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>{isEditing ? 'Edit Goal' : 'Create Savings Goal'}</ModalHeader>
        <ModalCloseButton />

        <form onSubmit={handleSubmit(onSubmit)}>
          <ModalBody>
            <VStack spacing={4}>
              {/* Name */}
              <FormControl isRequired isInvalid={!!errors.name}>
                <FormLabel>Goal Name</FormLabel>
                <Input
                  {...register('name', { required: 'Name is required' })}
                  placeholder="e.g., Emergency Fund, New Car, Vacation"
                />
              </FormControl>

              {/* Description */}
              <FormControl>
                <FormLabel>Description</FormLabel>
                <Textarea
                  {...register('description')}
                  placeholder="Optional notes about this goal"
                  rows={2}
                />
              </FormControl>

              {/* Target Amount */}
              <FormControl isRequired isInvalid={!!errors.target_amount}>
                <FormLabel>Target Amount</FormLabel>
                <Controller
                  name="target_amount"
                  control={control}
                  rules={{ required: 'Target amount is required', min: { value: 0.01, message: 'Must be greater than 0' } }}
                  render={({ field }) => (
                    <NumberInput {...field} min={0} step={0.01}>
                      <NumberInputField placeholder="0.00" />
                    </NumberInput>
                  )}
                />
              </FormControl>

              {/* Current Amount */}
              <FormControl isRequired isInvalid={!!errors.current_amount}>
                <FormLabel>Current Amount</FormLabel>
                <Controller
                  name="current_amount"
                  control={control}
                  rules={{ required: 'Current amount is required', min: { value: 0, message: 'Must be 0 or greater' } }}
                  render={({ field }) => (
                    <NumberInput {...field} min={0} step={0.01}>
                      <NumberInputField placeholder="0.00" />
                    </NumberInput>
                  )}
                />
              </FormControl>

              {/* Linked Account */}
              <FormControl>
                <FormLabel>Linked Account (Optional)</FormLabel>
                <Select {...register('account_id')} placeholder="None - manual tracking">
                  {accounts.map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.name}
                    </option>
                  ))}
                </Select>
              </FormControl>

              {/* Auto-sync toggle — only shown when an account is linked */}
              {watchedAccountId && (
                <FormControl>
                  <HStack justify="space-between">
                    <FormLabel mb={0}>Auto-sync from account balance</FormLabel>
                    <Controller
                      name="auto_sync"
                      control={control}
                      render={({ field: { value, onChange } }) => (
                        <Switch isChecked={!!value} onChange={onChange} colorScheme="cyan" />
                      )}
                    />
                  </HStack>
                  <FormHelperText>
                    When enabled, this goal's current amount is updated automatically from the linked account on page load.
                  </FormHelperText>
                </FormControl>
              )}

              {/* Shared Goal */}
              {showSharedSection && (
                <FormControl>
                  <HStack justify="space-between">
                    <FormLabel mb={0}>Shared Goal</FormLabel>
                    <Controller
                      name="is_shared"
                      control={control}
                      render={({ field }) => (
                        <Switch
                          isChecked={!!field.value}
                          onChange={(e) => {
                            field.onChange(e.target.checked);
                            if (!e.target.checked) {
                              setValue('shared_user_ids', null);
                            }
                          }}
                          colorScheme="teal"
                        />
                      )}
                    />
                  </HStack>
                  <FormHelperText>
                    Share this goal with household members
                  </FormHelperText>

                  {isShared && (
                    <Box mt={3} pl={2}>
                      <VStack align="start" spacing={2}>
                        <Checkbox
                          isChecked={allMembersSelected}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setValue('shared_user_ids', null);
                            } else {
                              setValue('shared_user_ids', []);
                            }
                          }}
                          colorScheme="teal"
                        >
                          All household members
                        </Checkbox>

                        {!allMembersSelected && otherMembers.map((member) => (
                          <Checkbox
                            key={member.id}
                            isChecked={sharedUserIds?.includes(member.id) ?? false}
                            onChange={(e) => {
                              const current = sharedUserIds ?? [];
                              if (e.target.checked) {
                                setValue('shared_user_ids', [...current, member.id]);
                              } else {
                                setValue('shared_user_ids', current.filter((id) => id !== member.id));
                              }
                            }}
                            colorScheme="teal"
                          >
                            {member.display_name || member.first_name || member.email}
                          </Checkbox>
                        ))}
                      </VStack>
                    </Box>
                  )}
                </FormControl>
              )}

              {/* Start Date */}
              <FormControl isRequired>
                <FormLabel>Start Date</FormLabel>
                <Input
                  type="date"
                  {...register('start_date', { required: true })}
                />
              </FormControl>

              {/* Target Date */}
              <FormControl>
                <FormLabel>Target Date (Optional)</FormLabel>
                <Input type="date" {...register('target_date')} />
              </FormControl>
            </VStack>
          </ModalBody>

          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onClose}>
              Cancel
            </Button>
            <Button
              colorScheme="blue"
              type="submit"
              isLoading={isSubmitting || mutation.isPending}
            >
              {isEditing ? 'Update' : 'Create'}
            </Button>
          </ModalFooter>
        </form>
      </ModalContent>
    </Modal>
  );
}
