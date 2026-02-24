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
  InputGroup,
  InputRightAddon,
} from '@chakra-ui/react';
import { useState } from 'react';
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
const NETWORTH_TOGGLE_TYPES: AccountType[] = [ACCOUNT_TYPES.COLLECTIBLES, ACCOUNT_TYPES.OTHER, ACCOUNT_TYPES.MANUAL, ACCOUNT_TYPES.PENSION];

// Account types that show loan detail fields
const LOAN_TYPES: AccountType[] = [ACCOUNT_TYPES.MORTGAGE, ACCOUNT_TYPES.LOAN, ACCOUNT_TYPES.STUDENT_LOAN];

// Account types that show pension/annuity income fields
const INCOME_TYPES: AccountType[] = [ACCOUNT_TYPES.PENSION, ACCOUNT_TYPES.ANNUITY];

export const BasicManualAccountForm = ({
  defaultAccountType,
  onSubmit,
  onBack,
  isLoading,
}: BasicManualAccountFormProps) => {
  // Loan term is shown to the user in years but stored as months in the schema
  const [loanTermYears, setLoanTermYears] = useState('');

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
  const showLoanFields = LOAN_TYPES.includes(accountType as AccountType);
  const showIncomeFields = INCOME_TYPES.includes(accountType as AccountType);
  const showCreditCardFields = accountType === ACCOUNT_TYPES.CREDIT_CARD;

  const handleFormSubmit = (data: BasicManualAccountFormData) => {
    const submitData = {
      ...data,
      loan_term_months: loanTermYears ? Math.round(parseFloat(loanTermYears) * 12) : undefined,
    };
    onSubmit(submitData);
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
            <option value={ACCOUNT_TYPES.ANNUITY}>Annuity</option>
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

        {showLoanFields && (
          <>
            <Divider />
            <Text fontWeight="semibold" fontSize="sm" color="text.secondary">
              Loan Details
            </Text>

            {/* Interest Rate */}
            <FormControl isInvalid={!!errors.interest_rate}>
              <FormLabel>Interest Rate (Optional)</FormLabel>
              <Controller
                name="interest_rate"
                control={control}
                render={({ field: { onChange, value, ...field } }) => (
                  <InputGroup>
                    <NumberInput
                      {...field}
                      value={value ?? ''}
                      onChange={(valueString) => onChange(valueString ? parseFloat(valueString) : undefined)}
                      precision={3}
                      step={0.125}
                      min={0}
                      max={100}
                      w="full"
                    >
                      <NumberInputField placeholder="e.g., 6.75" />
                    </NumberInput>
                    <InputRightAddon>%</InputRightAddon>
                  </InputGroup>
                )}
              />
              <FormHelperText>Annual interest rate (APR)</FormHelperText>
              <FormErrorMessage>{errors.interest_rate?.message}</FormErrorMessage>
            </FormControl>

            {/* Loan Term */}
            <FormControl>
              <FormLabel>Loan Term (Optional)</FormLabel>
              <InputGroup>
                <NumberInput
                  value={loanTermYears}
                  onChange={setLoanTermYears}
                  precision={1}
                  step={1}
                  min={1}
                  max={50}
                  w="full"
                >
                  <NumberInputField placeholder="e.g., 30" />
                </NumberInput>
                <InputRightAddon>years</InputRightAddon>
              </InputGroup>
              <FormHelperText>Common terms: 30, 20, 15, or 10 years</FormHelperText>
            </FormControl>

            {/* Origination Date */}
            <FormControl isInvalid={!!errors.origination_date}>
              <FormLabel>Loan Start Date (Optional)</FormLabel>
              <Input type="date" {...register('origination_date')} />
              <FormHelperText>When you took out the loan</FormHelperText>
              <FormErrorMessage>{errors.origination_date?.message}</FormErrorMessage>
            </FormControl>
          </>
        )}

        {/* Credit Card Details */}
        {showCreditCardFields && (
          <>
            <Divider />
            <Text fontWeight="semibold" fontSize="sm" color="text.secondary">
              Credit Card Details (Optional)
            </Text>

            <FormControl isInvalid={!!errors.credit_limit}>
              <FormLabel>Credit Limit</FormLabel>
              <Controller
                name="credit_limit"
                control={control}
                render={({ field: { onChange, value, ...field } }) => (
                  <NumberInput
                    {...field}
                    value={value ?? ''}
                    onChange={(valueString) => onChange(valueString ? parseFloat(valueString) : undefined)}
                    precision={2}
                    min={0}
                  >
                    <NumberInputField placeholder="e.g., 10000" />
                  </NumberInput>
                )}
              />
              <FormHelperText>Your card's total credit limit</FormHelperText>
              <FormErrorMessage>{errors.credit_limit?.message}</FormErrorMessage>
            </FormControl>

            <FormControl isInvalid={!!errors.minimum_payment}>
              <FormLabel>Minimum Payment</FormLabel>
              <Controller
                name="minimum_payment"
                control={control}
                render={({ field: { onChange, value, ...field } }) => (
                  <NumberInput
                    {...field}
                    value={value ?? ''}
                    onChange={(valueString) => onChange(valueString ? parseFloat(valueString) : undefined)}
                    precision={2}
                    min={0}
                  >
                    <NumberInputField placeholder="e.g., 25" />
                  </NumberInput>
                )}
              />
              <FormHelperText>Minimum monthly payment amount</FormHelperText>
              <FormErrorMessage>{errors.minimum_payment?.message}</FormErrorMessage>
            </FormControl>
          </>
        )}

        {/* Pension / Annuity Income Details */}
        {showIncomeFields && (
          <>
            <Divider />
            <Text fontWeight="semibold" fontSize="sm" color="text.secondary">
              {accountType === ACCOUNT_TYPES.PENSION ? 'Pension Income Details (Optional)' : 'Annuity Income Details (Optional)'}
            </Text>

            <FormControl isInvalid={!!errors.monthly_benefit}>
              <FormLabel>Monthly Benefit Amount</FormLabel>
              <Controller
                name="monthly_benefit"
                control={control}
                render={({ field: { onChange, value, ...field } }) => (
                  <NumberInput
                    {...field}
                    value={value ?? ''}
                    onChange={(valueString) => onChange(valueString ? parseFloat(valueString) : undefined)}
                    precision={2}
                    min={0}
                  >
                    <NumberInputField placeholder="e.g., 2500" />
                  </NumberInput>
                )}
              />
              <FormHelperText>
                {accountType === ACCOUNT_TYPES.PENSION
                  ? 'Monthly pension payment you receive (or expect to receive)'
                  : 'Monthly annuity income payment'}
              </FormHelperText>
              <FormErrorMessage>{errors.monthly_benefit?.message}</FormErrorMessage>
            </FormControl>

            <FormControl isInvalid={!!errors.benefit_start_date}>
              <FormLabel>Benefit Start Date (Optional)</FormLabel>
              <Input type="date" {...register('benefit_start_date')} />
              <FormHelperText>
                {accountType === ACCOUNT_TYPES.PENSION
                  ? 'When pension payments begin (leave blank if already receiving)'
                  : 'When annuity payments begin'}
              </FormHelperText>
              <FormErrorMessage>{errors.benefit_start_date?.message}</FormErrorMessage>
            </FormControl>
          </>
        )}

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
                  : accountType === ACCOUNT_TYPES.PENSION
                  ? 'Pensions are excluded from net worth by default since they represent future income, not a liquid asset. Enable this if your plan provides a lump-sum equivalent value.'
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
