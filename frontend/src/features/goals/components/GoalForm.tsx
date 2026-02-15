/**
 * Savings goal form for creating/editing goals
 */

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
  Input,
  Select,
  VStack,
  NumberInput,
  NumberInputField,
  Textarea,
  useToast,
} from '@chakra-ui/react';
import { useForm, Controller } from 'react-hook-form';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { SavingsGoal, SavingsGoalCreate } from '../../../types/savings-goal';
import { savingsGoalsApi } from '../../../api/savings-goals';
import { accountsApi } from '../../../api/accounts';

interface GoalFormProps {
  isOpen: boolean;
  onClose: () => void;
  goal?: SavingsGoal | null;
}

export default function GoalForm({ isOpen, onClose, goal }: GoalFormProps) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const isEditing = !!goal;

  const { register, handleSubmit, control, formState: { errors, isSubmitting } } = useForm<SavingsGoalCreate>({
    defaultValues: goal ? {
      name: goal.name,
      description: goal.description ?? undefined,
      target_amount: goal.target_amount,
      current_amount: goal.current_amount,
      start_date: goal.start_date,
      target_date: goal.target_date ?? undefined,
      account_id: goal.account_id ?? undefined,
    } : {
      current_amount: 0,
      start_date: new Date().toISOString().split('T')[0],
    },
  });

  // Get accounts for dropdown
  const { data: accounts = [] } = useQuery({
    queryKey: ['accounts'],
    queryFn: accountsApi.getAccounts,
  });

  // Create/update mutation
  const mutation = useMutation({
    mutationFn: (data: SavingsGoalCreate) => {
      if (isEditing && goal) {
        return savingsGoalsApi.update(goal.id, data);
      }
      return savingsGoalsApi.create(data);
    },
    onSuccess: () => {
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
    mutation.mutate(data);
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
