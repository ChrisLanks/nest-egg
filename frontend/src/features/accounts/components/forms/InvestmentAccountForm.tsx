/**
 * Form for adding investment accounts (brokerage, 401k, IRA, etc.)
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
  Box,
  IconButton,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Divider,
  Switch,
  FormHelperText,
} from '@chakra-ui/react';
import { useState } from 'react';
import { useForm, Controller, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { ArrowBackIcon, AddIcon, DeleteIcon } from '@chakra-ui/icons';
import {
  investmentAccountSchema,
  type InvestmentAccountFormData,
  ACCOUNT_TYPES,
  type AccountType,
} from '../../schemas/manualAccountSchemas';
import { formatAccountType } from '../../../../utils/formatAccountType';

interface InvestmentAccountFormProps {
  defaultAccountType: AccountType;
  onSubmit: (data: InvestmentAccountFormData) => void;
  onBack: () => void;
  isLoading?: boolean;
}

export const InvestmentAccountForm = ({
  defaultAccountType,
  onSubmit,
  onBack,
  isLoading,
}: InvestmentAccountFormProps) => {
  // Track individual holdings or just balance
  const [trackHoldings, setTrackHoldings] = useState(true);

  const {
    register,
    handleSubmit,
    control,
    watch,
    setValue,
    formState: { errors },
  } = useForm<InvestmentAccountFormData>({
    resolver: zodResolver(investmentAccountSchema),
    defaultValues: {
      account_type: defaultAccountType as any,
      holdings: [{ ticker: '', shares: 0, price_per_share: 0 }],
    },
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'holdings',
  });

  const holdings = watch('holdings');

  // Calculate total value from holdings
  const totalValue = holdings?.reduce((sum, holding) => {
    const shares = Number(holding.shares) || 0;
    const price = Number(holding.price_per_share) || 0;
    return sum + shares * price;
  }, 0) || 0;

  // Toggle between holdings and balance mode
  const handleTrackHoldingsToggle = (checked: boolean) => {
    setTrackHoldings(checked);
    if (!checked) {
      // Clear holdings when switching to balance mode
      setValue('holdings', []);
    } else {
      // Initialize with one empty holding when switching to holdings mode
      setValue('holdings', [{ ticker: '', shares: 0, price_per_share: 0 }]);
      setValue('balance', undefined);
    }
  };

  const handleFormSubmit = (data: InvestmentAccountFormData) => {
    // Clean up data based on mode
    if (trackHoldings) {
      // Remove balance field if tracking holdings
      const { balance, ...holdingsData } = data;
      onSubmit(holdingsData);
    } else {
      // Remove holdings field if using balance mode
      const { holdings, ...balanceData } = data;
      onSubmit(balanceData);
    }
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
            placeholder="e.g., Vanguard Brokerage"
          />
          <FormErrorMessage>{errors.name?.message}</FormErrorMessage>
        </FormControl>

        <FormControl isInvalid={!!errors.institution}>
          <FormLabel>Institution (Optional)</FormLabel>
          <Input
            {...register('institution')}
            placeholder="e.g., Vanguard"
          />
          <FormErrorMessage>{errors.institution?.message}</FormErrorMessage>
        </FormControl>

        <FormControl isInvalid={!!errors.account_type}>
          <FormLabel>Account Type</FormLabel>
          <Select {...register('account_type')}>
            <option value={ACCOUNT_TYPES.BROKERAGE}>Brokerage</option>
            <option value={ACCOUNT_TYPES.RETIREMENT_401K}>401(k)</option>
            <option value={ACCOUNT_TYPES.RETIREMENT_IRA}>IRA</option>
            <option value={ACCOUNT_TYPES.RETIREMENT_ROTH}>Roth IRA</option>
            <option value={ACCOUNT_TYPES.RETIREMENT_529}>529 Plan</option>
            <option value={ACCOUNT_TYPES.HSA}>HSA</option>
          </Select>
          <FormErrorMessage>{errors.account_type?.message}</FormErrorMessage>
        </FormControl>

        <Divider />

        {/* Toggle between holdings and balance mode */}
        <FormControl display="flex" alignItems="center">
          <FormLabel htmlFor="track-holdings" mb="0">
            Track individual holdings
          </FormLabel>
          <Switch
            id="track-holdings"
            isChecked={trackHoldings}
            onChange={(e) => handleTrackHoldingsToggle(e.target.checked)}
            colorScheme="brand"
          />
          <FormHelperText ml={3} mb="0">
            {trackHoldings
              ? 'You can add individual stocks, funds, etc.'
              : 'Just track the total account balance'}
          </FormHelperText>
        </FormControl>

        {trackHoldings ? (
          // Holdings Mode
          <Box>
            <HStack justify="space-between" mb={3}>
              <Text fontSize="md" fontWeight="semibold">
                Holdings
              </Text>
              <Button
                size="sm"
                leftIcon={<AddIcon />}
                onClick={() => append({ ticker: '', shares: 0, price_per_share: 0 })}
                variant="outline"
                colorScheme="brand"
              >
                Add Holding
              </Button>
            </HStack>

          <Box overflowX="auto">
            <Table size="sm" variant="simple">
              <Thead>
                <Tr>
                  <Th>{defaultAccountType === ACCOUNT_TYPES.CRYPTO ? 'Symbol' : 'Ticker'}</Th>
                  <Th>{defaultAccountType === ACCOUNT_TYPES.CRYPTO ? 'Quantity' : 'Shares'}</Th>
                  <Th>{defaultAccountType === ACCOUNT_TYPES.CRYPTO ? 'Price' : 'Price/Share'}</Th>
                  <Th isNumeric>Total Value</Th>
                  <Th></Th>
                </Tr>
              </Thead>
              <Tbody>
                {fields.map((field, index) => {
                  const shares = Number(holdings?.[index]?.shares) || 0;
                  const price = Number(holdings?.[index]?.price_per_share) || 0;
                  const value = shares * price;

                  return (
                    <Tr key={field.id}>
                      <Td>
                        <FormControl isInvalid={!!errors.holdings?.[index]?.ticker} size="sm">
                          <Input
                            {...register(`holdings.${index}.ticker` as const)}
                            placeholder={defaultAccountType === ACCOUNT_TYPES.CRYPTO ? "BTC" : "AAPL"}
                            size="sm"
                            textTransform="uppercase"
                          />
                        </FormControl>
                      </Td>
                      <Td>
                        <FormControl isInvalid={!!errors.holdings?.[index]?.shares}>
                          <Controller
                            name={`holdings.${index}.shares` as const}
                            control={control}
                            render={({ field: { onChange, value, ...field } }) => (
                              <NumberInput
                                {...field}
                                value={value as number}
                                onChange={(valueString) => onChange(parseFloat(valueString) || 0)}
                                precision={4}
                                step={0.01}
                                size="sm"
                              >
                                <NumberInputField placeholder={defaultAccountType === ACCOUNT_TYPES.CRYPTO ? "0.5" : "100"} />
                              </NumberInput>
                            )}
                          />
                        </FormControl>
                      </Td>
                      <Td>
                        <FormControl isInvalid={!!errors.holdings?.[index]?.price_per_share}>
                          <Controller
                            name={`holdings.${index}.price_per_share` as const}
                            control={control}
                            render={({ field: { onChange, value, ...field } }) => (
                              <NumberInput
                                {...field}
                                value={value as number}
                                onChange={(valueString) => onChange(parseFloat(valueString) || 0)}
                                precision={2}
                                step={0.01}
                                size="sm"
                              >
                                <NumberInputField placeholder={defaultAccountType === ACCOUNT_TYPES.CRYPTO ? "65000.00" : "185.50"} />
                              </NumberInput>
                            )}
                          />
                        </FormControl>
                      </Td>
                      <Td isNumeric>
                        <Text fontSize="sm" fontWeight="medium">
                          ${value.toFixed(2)}
                        </Text>
                      </Td>
                      <Td>
                        {fields.length > 1 && (
                          <IconButton
                            aria-label="Remove holding"
                            icon={<DeleteIcon />}
                            size="sm"
                            variant="ghost"
                            colorScheme="red"
                            onClick={() => remove(index)}
                          />
                        )}
                      </Td>
                    </Tr>
                  );
                })}
              </Tbody>
            </Table>
          </Box>

            {errors.holdings && (
              <Text color="red.500" fontSize="sm" mt={2}>
                {errors.holdings.message}
              </Text>
            )}

            <Box mt={4} p={3} bg="bg.subtle" borderRadius="md">
              <HStack justify="space-between">
                <Text fontWeight="semibold">Total Portfolio Value:</Text>
                <Text fontSize="lg" fontWeight="bold" color="brand.accent">
                  ${totalValue.toFixed(2)}
                </Text>
              </HStack>
            </Box>

            <Text fontSize="xs" color="text.secondary" mt={2}>
              💡 Tip: You can manually enter stock prices or look them up on Yahoo Finance or Google
            </Text>
          </Box>
        ) : (
          // Balance Only Mode
          <FormControl isInvalid={!!errors.balance}>
            <FormLabel>Account Balance</FormLabel>
            <Controller
              name="balance"
              control={control}
              render={({ field: { onChange, value, ...field } }) => (
                <NumberInput
                  {...field}
                  value={value as number}
                  onChange={(valueString) => onChange(parseFloat(valueString) || 0)}
                  precision={2}
                  step={100}
                >
                  <NumberInputField placeholder="e.g., 25000.00" />
                </NumberInput>
              )}
            />
            <FormHelperText>
              Enter the total current balance of your account
            </FormHelperText>
            <FormErrorMessage>{errors.balance?.message}</FormErrorMessage>
          </FormControl>
        )}

        <FormControl isInvalid={!!errors.account_number_last4}>
          <FormLabel>Account Number Last 4 Digits (Optional)</FormLabel>
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
