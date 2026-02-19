/**
 * Form for adding/editing recurring contributions
 */

import {
  VStack,
  FormControl,
  FormLabel,
  Select,
  NumberInput,
  NumberInputField,
  Input,
  Textarea,
  FormErrorMessage,
  Button,
  HStack,
  Text,
  Box,
} from '@chakra-ui/react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { ContributionType, ContributionFrequency } from '../../../types/contribution';

const contributionSchema = z.object({
  contribution_type: z.nativeEnum(ContributionType),
  amount: z.number().positive('Amount must be greater than 0'),
  frequency: z.nativeEnum(ContributionFrequency),
  start_date: z.string().min(1, 'Start date is required'),
  end_date: z.string().optional().nullable(),
  notes: z.string().max(500).optional().nullable(),
});

type ContributionFormData = z.infer<typeof contributionSchema>;

interface ContributionFormProps {
  onSubmit: (data: ContributionFormData) => void;
  onCancel: () => void;
  defaultValues?: Partial<ContributionFormData>;
  isLoading?: boolean;
  isEdit?: boolean;
}

export const ContributionForm = ({
  onSubmit,
  onCancel,
  defaultValues,
  isLoading,
  isEdit = false,
}: ContributionFormProps) => {
  const {
    register,
    handleSubmit,
    control,
    watch,
    formState: { errors },
  } = useForm<ContributionFormData>({
    resolver: zodResolver(contributionSchema),
    defaultValues: defaultValues || {
      contribution_type: ContributionType.FIXED_AMOUNT,
      frequency: ContributionFrequency.MONTHLY,
      start_date: new Date().toISOString().split('T')[0],
    },
  });

  const contributionType = watch('contribution_type');

  // Get label for amount field based on contribution type
  const getAmountLabel = () => {
    switch (contributionType) {
      case ContributionType.FIXED_AMOUNT:
        return 'Amount ($)';
      case ContributionType.SHARES:
        return 'Number of Shares';
      case ContributionType.PERCENTAGE_GROWTH:
        return 'Growth Rate (%)';
      default:
        return 'Amount';
    }
  };

  // Get helper text for contribution type
  const getHelperText = () => {
    switch (contributionType) {
      case ContributionType.FIXED_AMOUNT:
        return 'Enter a fixed dollar amount contributed each period';
      case ContributionType.SHARES:
        return 'Enter number of shares acquired each period';
      case ContributionType.PERCENTAGE_GROWTH:
        return 'Enter annual growth/interest rate as a percentage (e.g., 0.1% for low-yield accounts)';
      default:
        return '';
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <VStack spacing={4} align="stretch">
        <Text fontSize="lg" fontWeight="bold">
          {isEdit ? 'Edit' : 'Add'} Recurring Contribution
        </Text>

        <FormControl isInvalid={!!errors.contribution_type}>
          <FormLabel>Contribution Type</FormLabel>
          <Select {...register('contribution_type')}>
            <option value={ContributionType.FIXED_AMOUNT}>Fixed Dollar Amount</option>
            <option value={ContributionType.SHARES}>Number of Shares</option>
            <option value={ContributionType.PERCENTAGE_GROWTH}>Percentage Growth (Interest)</option>
          </Select>
          <FormErrorMessage>{errors.contribution_type?.message}</FormErrorMessage>
        </FormControl>

        <Box p={3} bg="blue.50" borderRadius="md" borderWidth={1} borderColor="blue.200">
          <Text fontSize="sm" color="blue.800">
            {getHelperText()}
          </Text>
        </Box>

        <FormControl isInvalid={!!errors.amount}>
          <FormLabel>{getAmountLabel()}</FormLabel>
          <Controller
            name="amount"
            control={control}
            render={({ field: { onChange, value, ...field } }) => (
              <NumberInput
                {...field}
                value={value}
                onChange={(valueString) => onChange(parseFloat(valueString) || 0)}
                precision={contributionType === ContributionType.PERCENTAGE_GROWTH ? 3 : (contributionType === ContributionType.SHARES ? 4 : 2)}
                step={contributionType === ContributionType.FIXED_AMOUNT ? 100 : (contributionType === ContributionType.PERCENTAGE_GROWTH ? 0.01 : 1)}
              >
                <NumberInputField placeholder={contributionType === ContributionType.FIXED_AMOUNT ? '500' : (contributionType === ContributionType.SHARES ? '10.5' : '0.1')} />
              </NumberInput>
            )}
          />
          <FormErrorMessage>{errors.amount?.message}</FormErrorMessage>
        </FormControl>

        <FormControl isInvalid={!!errors.frequency}>
          <FormLabel>Frequency</FormLabel>
          <Select {...register('frequency')}>
            <option value={ContributionFrequency.WEEKLY}>Weekly</option>
            <option value={ContributionFrequency.BIWEEKLY}>Bi-weekly</option>
            <option value={ContributionFrequency.MONTHLY}>Monthly</option>
            <option value={ContributionFrequency.QUARTERLY}>Quarterly</option>
            <option value={ContributionFrequency.ANNUALLY}>Annually</option>
          </Select>
          <FormErrorMessage>{errors.frequency?.message}</FormErrorMessage>
        </FormControl>

        <FormControl isInvalid={!!errors.start_date}>
          <FormLabel>Start Date</FormLabel>
          <Input type="date" {...register('start_date')} />
          <FormErrorMessage>{errors.start_date?.message}</FormErrorMessage>
        </FormControl>

        <FormControl isInvalid={!!errors.end_date}>
          <FormLabel>End Date (Optional)</FormLabel>
          <Input type="date" {...register('end_date')} />
          <FormErrorMessage>{errors.end_date?.message}</FormErrorMessage>
          <Text fontSize="xs" color="gray.600" mt={1}>
            Leave blank for ongoing contributions
          </Text>
        </FormControl>

        <FormControl isInvalid={!!errors.notes}>
          <FormLabel>Notes (Optional)</FormLabel>
          <Textarea
            {...register('notes')}
            placeholder="e.g., Annual bonus, dividend reinvestment, etc."
            rows={2}
          />
          <FormErrorMessage>{errors.notes?.message}</FormErrorMessage>
        </FormControl>

        <HStack justify="flex-end" spacing={3} pt={4}>
          <Button variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
          <Button
            type="submit"
            colorScheme="brand"
            isLoading={isLoading}
          >
            {isEdit ? 'Update' : 'Add'} Contribution
          </Button>
        </HStack>
      </VStack>
    </form>
  );
};
