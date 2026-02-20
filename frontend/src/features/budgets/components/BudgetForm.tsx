/**
 * Budget form for creating/editing budgets
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
  Switch,
  useToast,
  Slider,
  SliderTrack,
  SliderFilledTrack,
  SliderThumb,
  HStack,
  Text,
} from '@chakra-ui/react';
import { useForm, Controller } from 'react-hook-form';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { Budget, BudgetCreate } from '../../../types/budget';
import { BudgetPeriod } from '../../../types/budget';
import { budgetsApi } from '../../../api/budgets';
import { categoriesApi } from '../../../api/categories';

interface BudgetFormProps {
  isOpen: boolean;
  onClose: () => void;
  budget?: Budget | null;
}

export default function BudgetForm({ isOpen, onClose, budget }: BudgetFormProps) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const isEditing = !!budget;

  const { register, handleSubmit, control, watch, formState: { errors, isSubmitting } } = useForm<BudgetCreate>({
    defaultValues: budget ? {
      name: budget.name,
      amount: budget.amount,
      period: budget.period,
      start_date: budget.start_date,
      end_date: budget.end_date ?? undefined,
      category_id: budget.category_id ?? undefined,
      rollover_unused: budget.rollover_unused,
      alert_threshold: budget.alert_threshold,
    } : {
      period: BudgetPeriod.MONTHLY,
      rollover_unused: false,
      alert_threshold: 0.8,
      start_date: new Date().toISOString().split('T')[0],
    },
  });

  // Get categories for dropdown (only custom categories with IDs)
  const { data: allCategories = [] } = useQuery({
    queryKey: ['categories'],
    queryFn: categoriesApi.getCategories,
  });

  // Filter to only categories with IDs (custom categories that can be linked to budgets)
  const categories = allCategories.filter(cat => cat.id !== null);

  // Create/update mutation
  const mutation = useMutation({
    mutationFn: (data: BudgetCreate) => {
      if (isEditing && budget) {
        return budgetsApi.update(budget.id, data);
      }
      return budgetsApi.create(data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budgets'] });
      toast({
        title: isEditing ? 'Budget updated' : 'Budget created',
        status: 'success',
        duration: 3000,
      });
      onClose();
    },
    onError: () => {
      toast({
        title: `Failed to ${isEditing ? 'update' : 'create'} budget`,
        status: 'error',
        duration: 3000,
      });
    },
  });

  const onSubmit = (data: BudgetCreate) => {
    mutation.mutate({
      ...data,
      end_date: data.end_date || undefined,
    });
  };

  const alertThreshold = watch('alert_threshold');

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>{isEditing ? 'Edit Budget' : 'Create Budget'}</ModalHeader>
        <ModalCloseButton />

        <form onSubmit={handleSubmit(onSubmit)}>
          <ModalBody>
            <VStack spacing={4}>
              {/* Name */}
              <FormControl isRequired isInvalid={!!errors.name}>
                <FormLabel>Budget Name</FormLabel>
                <Input
                  {...register('name', { required: 'Name is required' })}
                  placeholder="e.g., Groceries, Entertainment"
                />
              </FormControl>

              {/* Amount */}
              <FormControl isRequired isInvalid={!!errors.amount}>
                <FormLabel>Budget Amount</FormLabel>
                <Controller
                  name="amount"
                  control={control}
                  rules={{ required: 'Amount is required', min: { value: 0.01, message: 'Must be greater than 0' } }}
                  render={({ field }) => (
                    <NumberInput {...field} min={0} step={0.01}>
                      <NumberInputField placeholder="0.00" />
                    </NumberInput>
                  )}
                />
              </FormControl>

              {/* Period */}
              <FormControl isRequired>
                <FormLabel>Period</FormLabel>
                <Select {...register('period', { required: true })}>
                  <option value={BudgetPeriod.MONTHLY}>Monthly</option>
                  <option value={BudgetPeriod.QUARTERLY}>Quarterly</option>
                  <option value={BudgetPeriod.YEARLY}>Yearly</option>
                </Select>
              </FormControl>

              {/* Category */}
              <FormControl>
                <FormLabel>Category (Optional)</FormLabel>
                <Select {...register('category_id')} placeholder="All spending">
                  {categories.map((cat) => (
                    <option key={cat.id} value={cat.id}>
                      {cat.name}
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

              {/* End Date */}
              <FormControl>
                <FormLabel>End Date (Optional)</FormLabel>
                <Input type="date" {...register('end_date')} />
              </FormControl>

              {/* Alert Threshold */}
              <FormControl>
                <FormLabel>
                  Alert at {((alertThreshold ?? 0.8) * 100).toFixed(0)}% spent
                </FormLabel>
                <Controller
                  name="alert_threshold"
                  control={control}
                  render={({ field }) => (
                    <Slider
                      {...field}
                      min={0.5}
                      max={1}
                      step={0.05}
                      value={field.value as number}
                      onChange={field.onChange}
                    >
                      <SliderTrack>
                        <SliderFilledTrack />
                      </SliderTrack>
                      <SliderThumb />
                    </Slider>
                  )}
                />
              </FormControl>

              {/* Rollover */}
              <FormControl>
                <HStack justify="space-between">
                  <FormLabel mb={0}>Roll over unused budget</FormLabel>
                  <Controller
                    name="rollover_unused"
                    control={control}
                    render={({ field }) => (
                      <Switch
                        isChecked={field.value}
                        onChange={field.onChange}
                      />
                    )}
                  />
                </HStack>
                <Text fontSize="xs" color="gray.600">
                  Unused budget carries over to next period
                </Text>
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
