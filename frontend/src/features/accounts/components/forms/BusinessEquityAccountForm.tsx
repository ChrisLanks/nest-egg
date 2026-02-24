/**
 * Form for adding Business Equity accounts
 * Supports two input methods: Company Valuation + Ownership % OR Direct Equity Value
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
  Radio,
  RadioGroup,
  Stack,
  Box,
  Divider,
} from '@chakra-ui/react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { ArrowBackIcon } from '@chakra-ui/icons';
import { useState } from 'react';
import { z } from 'zod';

// Business Equity Account schema
const businessEquityAccountSchema = z.object({
  name: z.string().min(1, 'Account name is required'),
  institution: z.string().optional(),
  account_number_last4: z.string().max(4).optional(),
  account_type: z.literal('business_equity'),
  account_source: z.literal('manual'),
  input_method: z.enum(['valuation_percentage', 'direct_value']),
  // Valuation + Percentage method
  company_valuation: z.number().optional(),
  ownership_percentage: z.number().optional(),
  // Direct value method
  equity_value: z.number().optional(),
});

type BusinessEquityAccountFormData = z.infer<typeof businessEquityAccountSchema>;

interface BusinessEquityAccountFormProps {
  onSubmit: (data: any) => void;
  onBack: () => void;
  isLoading?: boolean;
}

export const BusinessEquityAccountForm = ({
  onSubmit,
  onBack,
  isLoading,
}: BusinessEquityAccountFormProps) => {
  const [inputMethod, setInputMethod] = useState<'valuation_percentage' | 'direct_value'>('direct_value');

  const {
    register,
    handleSubmit,
    control,
    watch,
    formState: { errors },
  } = useForm<BusinessEquityAccountFormData>({
    resolver: zodResolver(businessEquityAccountSchema),
    defaultValues: {
      account_type: 'business_equity' as any,
      account_source: 'manual' as any,
      input_method: 'direct_value',
    },
  });

  const companyValuation = watch('company_valuation');
  const ownershipPercentage = watch('ownership_percentage');
  const equityValue = watch('equity_value');

  // Calculate current balance based on input method
  const calculateBalance = (data: BusinessEquityAccountFormData): number => {
    if (data.input_method === 'direct_value') {
      return data.equity_value || 0;
    } else {
      // Calculate from valuation and percentage
      const valuation = data.company_valuation || 0;
      const percentage = data.ownership_percentage || 0;
      return (valuation * percentage) / 100;
    }
  };

  const handleFormSubmit = (data: BusinessEquityAccountFormData) => {
    const submitData: any = {
      name: data.name,
      institution: data.institution,
      account_number_last4: data.account_number_last4,
      account_type: 'business_equity',
      account_source: 'manual',
      balance: calculateBalance(data),
    };

    if (inputMethod === 'valuation_percentage') {
      submitData.company_valuation = data.company_valuation;
      submitData.ownership_percentage = data.ownership_percentage;
    } else {
      submitData.equity_value = data.equity_value;
    }

    onSubmit(submitData);
  };

  // Calculate estimated value for valuation method
  const estimatedValue = companyValuation && ownershipPercentage
    ? (companyValuation * ownershipPercentage) / 100
    : 0;

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
          Add Business Equity
        </Text>

        {/* Business Name */}
        <FormControl isInvalid={!!errors.name}>
          <FormLabel>Business Name</FormLabel>
          <Input {...register('name')} placeholder="e.g., My Company LLC" />
          <FormErrorMessage>{errors.name?.message}</FormErrorMessage>
        </FormControl>

        {/* Institution (Optional) */}
        <FormControl>
          <FormLabel>Business Type (Optional)</FormLabel>
          <Input {...register('institution')} placeholder="e.g., LLC, S-Corp, Partnership" />
          <FormHelperText>Type of business entity</FormHelperText>
        </FormControl>

        {/* Account Number Last 4 (Optional) */}
        <FormControl>
          <FormLabel>Account/EIN Last 4 (Optional)</FormLabel>
          <Input
            {...register('account_number_last4')}
            placeholder="1234"
            maxLength={4}
          />
        </FormControl>

        <Divider />

        {/* Input Method Selection */}
        <FormControl>
          <FormLabel>How do you want to track your equity?</FormLabel>
          <RadioGroup value={inputMethod} onChange={(value: any) => setInputMethod(value)}>
            <Stack spacing={3}>
              <Box
                p={4}
                borderWidth={2}
                borderRadius="md"
                borderColor={inputMethod === 'direct_value' ? 'blue.500' : 'border.default'}
                bg={inputMethod === 'direct_value' ? 'bg.info' : 'bg.surface'}
                cursor="pointer"
                onClick={() => setInputMethod('direct_value')}
              >
                <Radio value="direct_value" size="lg">
                  <VStack align="start" spacing={0} ml={2}>
                    <Text fontWeight="semibold">Direct Equity Value</Text>
                    <Text fontSize="sm" color="text.secondary">
                      Enter the total dollar value of your ownership stake
                    </Text>
                  </VStack>
                </Radio>
              </Box>

              <Box
                p={4}
                borderWidth={2}
                borderRadius="md"
                borderColor={inputMethod === 'valuation_percentage' ? 'blue.500' : 'border.default'}
                bg={inputMethod === 'valuation_percentage' ? 'bg.info' : 'bg.surface'}
                cursor="pointer"
                onClick={() => setInputMethod('valuation_percentage')}
              >
                <Radio value="valuation_percentage" size="lg">
                  <VStack align="start" spacing={0} ml={2}>
                    <Text fontWeight="semibold">Company Valuation + Ownership %</Text>
                    <Text fontSize="sm" color="text.secondary">
                      Enter company valuation and your ownership percentage
                    </Text>
                  </VStack>
                </Radio>
              </Box>
            </Stack>
          </RadioGroup>
        </FormControl>

        <Divider />

        {/* Direct Value Method */}
        {inputMethod === 'direct_value' && (
          <FormControl isInvalid={!!errors.equity_value}>
            <FormLabel>Your Equity Value</FormLabel>
            <Controller
              name="equity_value"
              control={control}
              render={({ field: { onChange, value, ...field } }) => (
                <NumberInput
                  {...field}
                  value={value as number}
                  onChange={(valueString) => onChange(parseFloat(valueString) || 0)}
                  min={0}
                  precision={2}
                >
                  <NumberInputField placeholder="e.g., 250000.00" />
                </NumberInput>
              )}
            />
            <FormHelperText>
              The total dollar value of your ownership in the business
            </FormHelperText>
            <FormErrorMessage>{errors.equity_value?.message}</FormErrorMessage>
          </FormControl>
        )}

        {/* Valuation + Percentage Method */}
        {inputMethod === 'valuation_percentage' && (
          <>
            <FormControl isInvalid={!!errors.company_valuation}>
              <FormLabel>Company Valuation</FormLabel>
              <Controller
                name="company_valuation"
                control={control}
                render={({ field: { onChange, value, ...field } }) => (
                  <NumberInput
                    {...field}
                    value={value as number}
                    onChange={(valueString) => onChange(parseFloat(valueString) || 0)}
                    min={0}
                    precision={2}
                  >
                    <NumberInputField placeholder="e.g., 1000000.00" />
                  </NumberInput>
                )}
              />
              <FormHelperText>Total company valuation</FormHelperText>
              <FormErrorMessage>{errors.company_valuation?.message}</FormErrorMessage>
            </FormControl>

            <FormControl isInvalid={!!errors.ownership_percentage}>
              <FormLabel>Your Ownership Percentage</FormLabel>
              <Controller
                name="ownership_percentage"
                control={control}
                render={({ field: { onChange, value, ...field } }) => (
                  <NumberInput
                    {...field}
                    value={value as number}
                    onChange={(valueString) => onChange(parseFloat(valueString) || 0)}
                    min={0}
                    max={100}
                    precision={2}
                  >
                    <NumberInputField placeholder="e.g., 25.00" />
                  </NumberInput>
                )}
              />
              <FormHelperText>Your percentage of ownership (0-100%)</FormHelperText>
              <FormErrorMessage>{errors.ownership_percentage?.message}</FormErrorMessage>
            </FormControl>

            {/* Calculated Value Display */}
            {estimatedValue > 0 && (
              <Box p={4} bg="bg.info" borderRadius="md" borderWidth={1} borderColor="blue.200">
                <Text fontSize="sm" color="blue.800" fontWeight="medium">
                  Estimated Equity Value:{' '}
                  <Text as="span" fontSize="lg" fontWeight="bold">
                    ${estimatedValue.toLocaleString(undefined, {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}
                  </Text>
                </Text>
                <Text fontSize="xs" color="blue.600" mt={1}>
                  {ownershipPercentage}% of ${companyValuation?.toLocaleString()}
                </Text>
              </Box>
            )}
          </>
        )}

        <Button
          type="submit"
          colorScheme="blue"
          size="lg"
          w="full"
          isLoading={isLoading}
        >
          Add Business Equity
        </Button>
      </VStack>
    </form>
  );
};
