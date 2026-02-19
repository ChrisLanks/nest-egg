/**
 * Form for adding private debt accounts (private credit funds, loans made)
 */

import {
  VStack,
  FormControl,
  FormLabel,
  Input,
  FormErrorMessage,
  NumberInput,
  NumberInputField,
  Button,
  HStack,
  Text,
  FormHelperText,
} from '@chakra-ui/react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { ArrowBackIcon } from '@chakra-ui/icons';
import {
  privateDebtAccountSchema,
  type PrivateDebtAccountFormData,
} from '../../schemas/manualAccountSchemas';

interface PrivateDebtAccountFormProps {
  onSubmit: (data: PrivateDebtAccountFormData) => void;
  onBack: () => void;
  isLoading?: boolean;
}

export const PrivateDebtAccountForm = ({
  onSubmit,
  onBack,
  isLoading,
}: PrivateDebtAccountFormProps) => {
  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = useForm<PrivateDebtAccountFormData>({
    resolver: zodResolver(privateDebtAccountSchema),
    defaultValues: {
      account_type: 'private_debt' as any,
    },
  });

  const handleFormSubmit = (data: PrivateDebtAccountFormData) => {
    onSubmit(data);
  };

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)}>
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
          Add Private Debt Account
        </Text>

        <Text fontSize="sm" color="gray.600">
          Track private credit funds or loans you've made to businesses or individuals.
        </Text>

        {/* Investment Name */}
        <FormControl isInvalid={!!errors.name}>
          <FormLabel>Investment Name</FormLabel>
          <Input {...register('name')} placeholder="e.g., Private Credit Fund or Loan to Business X" />
          <FormErrorMessage>{errors.name?.message}</FormErrorMessage>
        </FormControl>

        {/* Institution/Fund (optional) */}
        <FormControl>
          <FormLabel>Institution/Fund (Optional)</FormLabel>
          <Input {...register('institution')} placeholder="e.g., Ares Private Credit" />
          <FormHelperText>Name of the fund or institution managing the debt</FormHelperText>
        </FormControl>

        {/* Current Balance */}
        <FormControl isInvalid={!!errors.balance}>
          <FormLabel>Current Balance</FormLabel>
          <Controller
            name="balance"
            control={control}
            render={({ field }) => (
              <NumberInput {...field} onChange={(_, val) => field.onChange(val)} min={0} precision={2}>
                <NumberInputField placeholder="e.g., 50000.00" />
              </NumberInput>
            )}
          />
          <FormHelperText>Current remaining balance of the loan or investment</FormHelperText>
          <FormErrorMessage>{errors.balance?.message}</FormErrorMessage>
        </FormControl>

        {/* Principal Amount */}
        <FormControl isInvalid={!!errors.principal_amount}>
          <FormLabel>Principal Amount (Optional)</FormLabel>
          <Controller
            name="principal_amount"
            control={control}
            render={({ field }) => (
              <NumberInput {...field} onChange={(_, val) => field.onChange(val)} min={0} precision={2}>
                <NumberInputField placeholder="e.g., 50000.00" />
              </NumberInput>
            )}
          />
          <FormHelperText>Original principal amount of the loan</FormHelperText>
          <FormErrorMessage>{errors.principal_amount?.message}</FormErrorMessage>
        </FormControl>

        {/* Interest Rate */}
        <FormControl isInvalid={!!errors.interest_rate}>
          <FormLabel>Interest Rate (%) (Optional)</FormLabel>
          <Controller
            name="interest_rate"
            control={control}
            render={({ field }) => (
              <NumberInput {...field} onChange={(_, val) => field.onChange(val)} min={0} max={100} precision={2}>
                <NumberInputField placeholder="e.g., 5.5" />
              </NumberInput>
            )}
          />
          <FormHelperText>Annual interest rate as a percentage</FormHelperText>
          <FormErrorMessage>{errors.interest_rate?.message}</FormErrorMessage>
        </FormControl>

        {/* Maturity Date */}
        <FormControl isInvalid={!!errors.maturity_date}>
          <FormLabel>Maturity Date (Optional)</FormLabel>
          <Input type="date" {...register('maturity_date')} />
          <FormHelperText>Date when the loan is expected to be paid back in full</FormHelperText>
          <FormErrorMessage>{errors.maturity_date?.message}</FormErrorMessage>
        </FormControl>

        <Button
          type="submit"
          colorScheme="blue"
          size="lg"
          w="full"
          isLoading={isLoading}
        >
          Add Account
        </Button>
      </VStack>
    </form>
  );
};
