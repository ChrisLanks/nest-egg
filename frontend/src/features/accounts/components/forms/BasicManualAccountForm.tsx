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
  Switch,
  FormHelperText,
  Divider,
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
import { formatAccountType } from '../../../../utils/formatAccountType';

interface BasicManualAccountFormProps {
  defaultAccountType: AccountType;
  onSubmit: (data: BasicManualAccountFormData) => void;
  onBack: () => void;
  isLoading?: boolean;
}

// Account types where include_in_networth defaults to false and the toggle is shown
const NETWORTH_TOGGLE_TYPES: AccountType[] = [ACCOUNT_TYPES.COLLECTIBLES, ACCOUNT_TYPES.OTHER, ACCOUNT_TYPES.MANUAL];

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
    watch,
    formState: { errors },
  } = useForm<BasicManualAccountFormData>({
    resolver: zodResolver(basicManualAccountSchema),
    defaultValues: {
      account_type: defaultAccountType as any,
      include_in_networth: NETWORTH_TOGGLE_TYPES.includes(defaultAccountType) ? false : undefined,
    },
  });

  const accountType = watch('account_type');
  const showNetworthToggle = NETWORTH_TOGGLE_TYPES.includes(accountType as AccountType);

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
          Add {formatAccountType(defaultAccountType)} Account
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
            <option value={ACCOUNT_TYPES.MONEY_MARKET}>Money Market</option>
            <option value={ACCOUNT_TYPES.CD}>CD</option>
            <option value={ACCOUNT_TYPES.CREDIT_CARD}>Credit Card</option>
            <option value={ACCOUNT_TYPES.LOAN}>Loan</option>
            <option value={ACCOUNT_TYPES.STUDENT_LOAN}>Student Loan</option>
            <option value={ACCOUNT_TYPES.MORTGAGE}>Mortgage</option>
            <option value={ACCOUNT_TYPES.RETIREMENT_529}>529 Plan</option>
            <option value={ACCOUNT_TYPES.PENSION}>Pension</option>
            <option value={ACCOUNT_TYPES.COLLECTIBLES}>Collectibles</option>
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

        {showNetworthToggle && (
          <>
            <Divider />
            <FormControl>
              <HStack justify="space-between" align="center">
                <FormLabel htmlFor="include-in-networth" mb="0">
                  Include in Net Worth
                </FormLabel>
                <Controller
                  name="include_in_networth"
                  control={control}
                  render={({ field }) => (
                    <Switch
                      id="include-in-networth"
                      isChecked={field.value ?? false}
                      onChange={field.onChange}
                      colorScheme="blue"
                    />
                  )}
                />
              </HStack>
              <FormHelperText>
                {accountType === ACCOUNT_TYPES.COLLECTIBLES
                  ? 'Collectibles are excluded from net worth by default since their value can be uncertain. Enable this to include them.'
                  : 'This account is excluded from net worth by default. Enable this to include it in your net worth calculations.'}
              </FormHelperText>
            </FormControl>
          </>
        )}

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
