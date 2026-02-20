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
  RadioGroup,
  Radio,
  Stack,
} from '@chakra-ui/react';
import React, { useEffect, useState } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { Budget, BudgetCreate } from '../../../types/budget';
import { BudgetPeriod } from '../../../types/budget';
import { budgetsApi } from '../../../api/budgets';
import { categoriesApi } from '../../../api/categories';
import { labelsApi } from '../../../api/labels';

interface BudgetFormProps {
  isOpen: boolean;
  onClose: () => void;
  budget?: Budget | null;
}

type FilterBy = 'all' | 'category' | 'label';

function getInitialFilterBy(budget: Budget | null | undefined): FilterBy {
  if (!budget) return 'all';
  if (budget.label_id) return 'label';
  if (budget.category_id) return 'category';
  return 'all';
}

export default function BudgetForm({ isOpen, onClose, budget }: BudgetFormProps) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const isEditing = !!budget;

  const { register, handleSubmit, control, watch, setValue, reset, formState: { errors, isSubmitting } } = useForm<BudgetCreate>({
    defaultValues: budget ? {
      name: budget.name,
      amount: budget.amount,
      period: budget.period,
      start_date: budget.start_date,
      end_date: budget.end_date ?? undefined,
      category_id: budget.category_id ?? undefined,
      label_id: budget.label_id ?? undefined,
      rollover_unused: budget.rollover_unused,
      alert_threshold: budget.alert_threshold,
    } : {
      period: BudgetPeriod.MONTHLY,
      rollover_unused: false,
      alert_threshold: 0.8,
      start_date: new Date().toISOString().split('T')[0],
    },
  });

  // Tracks when a provider category (no UUID) is selected so we can auto-create it on save
  const [providerCategoryName, setProviderCategoryName] = useState<string | null>(null);
  // Whether the budget filters by "all", "category", or "label"
  const [filterBy, setFilterBy] = useState<FilterBy>(getInitialFilterBy(budget));

  // Reset form when the modal opens or the budget changes (defaultValues only applies on initial mount)
  useEffect(() => {
    if (isOpen) {
      reset(budget ? {
        name: budget.name,
        amount: budget.amount,
        period: budget.period,
        start_date: budget.start_date,
        end_date: budget.end_date ?? undefined,
        category_id: budget.category_id ?? undefined,
        label_id: budget.label_id ?? undefined,
        rollover_unused: budget.rollover_unused,
        alert_threshold: budget.alert_threshold,
      } : {
        period: BudgetPeriod.MONTHLY,
        rollover_unused: false,
        alert_threshold: 0.8,
        start_date: new Date().toISOString().split('T')[0],
      });
      setProviderCategoryName(null);
      setFilterBy(getInitialFilterBy(budget));
    }
  }, [isOpen, budget]);

  // When filterBy changes, clear the other field
  const handleFilterByChange = (value: FilterBy) => {
    setFilterBy(value);
    if (value !== 'category') {
      setValue('category_id', undefined);
      setProviderCategoryName(null);
    }
    if (value !== 'label') {
      setValue('label_id', undefined);
    }
  };

  // All categories — both custom (with UUID) and provider (without UUID, from Plaid/Teller)
  const { data: allCategories = [] } = useQuery({
    queryKey: ['categories'],
    queryFn: categoriesApi.getCategories,
  });

  const { data: allLabels = [] } = useQuery({
    queryKey: ['labels'],
    queryFn: () => labelsApi.getAll(),
  });

  // The current select value: UUID for custom categories, "provider::Name" for provider categories
  const watchedCategoryId = watch('category_id');
  const categorySelectValue = providerCategoryName
    ? `provider::${providerCategoryName}`
    : (watchedCategoryId ?? '');

  const handleCategoryChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    if (!val) {
      setValue('category_id', undefined);
      setProviderCategoryName(null);
    } else if (val.startsWith('provider::')) {
      setValue('category_id', undefined);
      setProviderCategoryName(val.slice(10));
    } else {
      setValue('category_id', val);
      setProviderCategoryName(null);
    }
  };

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

  const onSubmit = async (data: BudgetCreate) => {
    let resolvedCategoryId = filterBy === 'category' ? data.category_id : undefined;
    const resolvedLabelId = filterBy === 'label' ? data.label_id : undefined;

    // If a provider category (no UUID) was selected, create a custom category for it first
    if (filterBy === 'category' && !resolvedCategoryId && providerCategoryName) {
      try {
        const newCat = await categoriesApi.create({ name: providerCategoryName });
        resolvedCategoryId = newCat.id ?? undefined;
        queryClient.invalidateQueries({ queryKey: ['categories'] });
      } catch {
        toast({ title: 'Failed to create category', status: 'error', duration: 3000 });
        return;
      }
    }

    mutation.mutate({
      ...data,
      category_id: resolvedCategoryId,
      label_id: resolvedLabelId,
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

              {/* Filter by */}
              <FormControl>
                <FormLabel>Track spending for</FormLabel>
                <RadioGroup value={filterBy} onChange={(v) => handleFilterByChange(v as FilterBy)}>
                  <Stack direction="row" spacing={4}>
                    <Radio value="all">All spending</Radio>
                    <Radio value="category">Category</Radio>
                    <Radio value="label">Label</Radio>
                  </Stack>
                </RadioGroup>
              </FormControl>

              {/* Category dropdown — only shown when filterBy === 'category' */}
              {filterBy === 'category' && (
                <FormControl>
                  <FormLabel>Category</FormLabel>
                  <Select value={categorySelectValue} onChange={handleCategoryChange}>
                    <option value="">Select a category...</option>
                    {allCategories.map((cat) => (
                      <option
                        key={cat.id ?? cat.name}
                        value={cat.id ? cat.id : `provider::${cat.name}`}
                      >
                        {cat.name}
                      </option>
                    ))}
                  </Select>
                </FormControl>
              )}

              {/* Label dropdown — only shown when filterBy === 'label' */}
              {filterBy === 'label' && (
                <FormControl>
                  <FormLabel>Label</FormLabel>
                  <Controller
                    name="label_id"
                    control={control}
                    render={({ field }) => (
                      <Select
                        value={field.value ?? ''}
                        onChange={(e) => field.onChange(e.target.value || undefined)}
                      >
                        <option value="">Select a label...</option>
                        {allLabels.map((label) => (
                          <option key={label.id} value={label.id}>
                            {label.name}
                          </option>
                        ))}
                      </Select>
                    )}
                  />
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
