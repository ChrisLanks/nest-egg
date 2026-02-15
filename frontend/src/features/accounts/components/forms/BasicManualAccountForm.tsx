/**
 * Form for adding basic manual accounts (checking, savings, loans, etc.)
 */

import {
  VStack,
  FormControl,
  FormLabel,
  Input,
  FormErrorMessage,
  Select,
  NumberInput,
  NumberInputField,
  Button,
  HStack,
  Text,
} from '@chakra-ui/react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { ArrowBackIcon } from '@chakra-ui/icons';
import {
  basicManualAccountSchema,
  type BasicManualAccountFormData,
  ACCOUNT_TYPES,
  type AccountType,
} from '../../schemas/manualAccountSchemas';

interface BasicManualAccountFormProps {
  defaultAccountType: AccountType;
  onSubmit: (data: BasicManualAccountFormData) => void;
  onBack: () => void;
  isLoading?: boolean;
}

export const BasicManualAccountForm = ({
  defaultAccountType,
  onSubmit,
  onBack,
  isLoading,
}: BasicManualAccountFormProps) => {
  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = useForm<BasicManualAccountFormData>({
    resolver: zodResolver(basicManualAccountSchema),
    defaultValues: {
      account_type: defaultAccountType as any,
    },
  });

  // Map account type to display name
  const accountTypeLabels: Record<string, string> = {
    [ACCOUNT_TYPES.CHECKING]: 'Checking',
    [ACCOUNT_TYPES.SAVINGS]: 'Savings',
    [ACCOUNT_TYPES.MONEY_MARKET]: 'Money Market',
    [ACCOUNT_TYPES.CD]: 'CD',
    [ACCOUNT_TYPES.CREDIT_CARD]: 'Credit Card',
    [ACCOUNT_TYPES.LOAN]: 'Loan',
    [ACCOUNT_TYPES.STUDENT_LOAN]: 'Student Loan',
    [ACCOUNT_TYPES.MORTGAGE]: 'Mortgage',
    [ACCOUNT_TYPES.MANUAL]: 'Other',
    [ACCOUNT_TYPES.OTHER]: 'Other',
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <VStack spacing={6} align="stretch">
        <HStack>
          <Button
            variant="ghost"
            leftIcon={<ArrowBackIcon />}
            onClick={onBack}
            size="sm"
          >
            Back
          </Button>
        </HStack>

        <Text fontSize="lg" fontWeight="bold">
          Add {accountTypeLabels[defaultAccountType] || 'Manual'} Account
        </Text>

        <FormControl isInvalid={!!errors.name}>
          <FormLabel>Account Name</FormLabel>
          <Input
            {...register('name')}
            placeholder="e.g., Chase Checking"
          />
          <FormErrorMessage>{errors.name?.message}</FormErrorMessage>
        </FormControl>

        <FormControl isInvalid={!!errors.institution}>
          <FormLabel>Institution (Optional)</FormLabel>
          <Input
            {...register('institution')}
            placeholder="e.g., Chase Bank"
          />
          <FormErrorMessage>{errors.institution?.message}</FormErrorMessage>
        </FormControl>

        <FormControl isInvalid={!!errors.account_type}>
          <FormLabel>Account Type</FormLabel>
          <Select {...register('account_type')}>
            <option value={ACCOUNT_TYPES.CHECKING}>Checking</option>
            <option value={ACCOUNT_TYPES.SAVINGS}>Savings</option>
            <option value={ACCOUNT_TYPES.CREDIT_CARD}>Credit Card</option>
            <option value={ACCOUNT_TYPES.LOAN}>Loan</option>
            <option value={ACCOUNT_TYPES.MORTGAGE}>Mortgage</option>
            <option value={ACCOUNT_TYPES.MANUAL}>Other</option>
          </Select>
          <FormErrorMessage>{errors.account_type?.message}</FormErrorMessage>
        </FormControl>

        <FormControl isInvalid={!!errors.balance}>
          <FormLabel>
            {defaultAccountType === ACCOUNT_TYPES.CREDIT_CARD ? 'Current Balance (Amount Owed)' : 'Current Balance'}
          </FormLabel>
          <Controller
            name="balance"
            control={control}
            render={({ field: { onChange, value, ...field } }) => (
              <NumberInput
                {...field}
                value={value as number}
                onChange={(valueString) => onChange(parseFloat(valueString) || 0)}
                precision={2}
                step={0.01}
              >
                <NumberInputField placeholder="0.00" />
              </NumberInput>
            )}
          />
          <FormErrorMessage>{errors.balance?.message}</FormErrorMessage>
        </FormControl>

        <FormControl isInvalid={!!errors.account_number_last4}>
          <FormLabel>Last 4 Digits (Optional)</FormLabel>
          <Input
            {...register('account_number_last4')}
            placeholder="1234"
            maxLength={4}
          />
          <FormErrorMessage>{errors.account_number_last4?.message}</FormErrorMessage>
        </FormControl>

        <HStack justify="flex-end" spacing={3} pt={4}>
          <Button variant="ghost" onClick={onBack}>
            Cancel
          </Button>
          <Button
            type="submit"
            colorScheme="brand"
            isLoading={isLoading}
          >
            Add Account
          </Button>
        </HStack>
      </VStack>
    </form>
  );
};
