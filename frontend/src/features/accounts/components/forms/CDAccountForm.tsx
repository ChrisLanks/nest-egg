/**
 * Form for adding Certificate of Deposit (CD) accounts
 * Supports both simple (balance only) and detailed (principal + APY + compounding) tracking
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

// CD Account schema
const cdAccountSchema = z.object({
  name: z.string().min(1, 'Account name is required'),
  institution: z.string().optional(),
  account_number_last4: z.string().max(4).optional(),
  account_type: z.literal('cd'),
  account_source: z.literal('manual'),
  tracking_mode: z.enum(['simple', 'detailed']),
  // Simple mode
  balance: z.number().optional(),
  // Detailed mode
  original_amount: z.number().optional(),
  interest_rate: z.number().optional(),
  compounding_frequency: z.enum(['daily', 'monthly', 'quarterly', 'at_maturity']).optional(),
  origination_date: z.string().optional(),
  maturity_date: z.string().optional(),
});

type CDAccountFormData = z.infer<typeof cdAccountSchema>;

interface CDAccountFormProps {
  onSubmit: (data: any) => void;
  onBack: () => void;
  isLoading?: boolean;
}

export const CDAccountForm = ({ onSubmit, onBack, isLoading }: CDAccountFormProps) => {
  const [trackingMode, setTrackingMode] = useState<'simple' | 'detailed'>('simple');

  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = useForm<CDAccountFormData>({
    resolver: zodResolver(cdAccountSchema),
    defaultValues: {
      account_type: 'cd' as any,
      account_source: 'manual' as any,
      tracking_mode: 'simple',
      compounding_frequency: 'monthly',
    },
  });


  const handleFormSubmit = (data: CDAccountFormData) => {
    const submitData: any = {
      name: data.name,
      institution: data.institution,
      account_number_last4: data.account_number_last4,
      account_type: 'cd',
      account_source: 'manual',
    };

    if (trackingMode === 'simple') {
      // Simple mode: just balance
      submitData.balance = data.balance || 0;
    } else {
      // Detailed mode: principal + APY + compounding
      submitData.balance = data.original_amount || 0; // Initial balance = principal
      submitData.original_amount = data.original_amount;
      submitData.interest_rate = data.interest_rate;
      submitData.compounding_frequency = data.compounding_frequency;
      submitData.origination_date = data.origination_date;
      submitData.maturity_date = data.maturity_date;
      submitData.interest_rate_type = 'FIXED'; // CDs are always fixed rate
    }

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
          Add Certificate of Deposit (CD)
        </Text>

        {/* CD Name */}
        <FormControl isInvalid={!!errors.name}>
          <FormLabel>CD Name</FormLabel>
          <Input {...register('name')} placeholder="e.g., 5-Year CD" />
          <FormErrorMessage>{errors.name?.message}</FormErrorMessage>
        </FormControl>

        {/* Bank/Institution */}
        <FormControl>
          <FormLabel>Bank/Institution (Optional)</FormLabel>
          <Input {...register('institution')} placeholder="e.g., Chase Bank" />
        </FormControl>

        {/* Account Number Last 4 */}
        <FormControl>
          <FormLabel>Account Number Last 4 (Optional)</FormLabel>
          <Input
            {...register('account_number_last4')}
            placeholder="1234"
            maxLength={4}
          />
        </FormControl>

        <Divider />

        {/* Tracking Mode Selection */}
        <FormControl>
          <FormLabel>Tracking Mode</FormLabel>
          <RadioGroup value={trackingMode} onChange={(value: any) => setTrackingMode(value)}>
            <Stack spacing={3}>
              <Box
                p={4}
                borderWidth={2}
                borderRadius="md"
                borderColor={trackingMode === 'simple' ? 'blue.500' : 'border.default'}
                bg={trackingMode === 'simple' ? 'bg.info' : 'bg.surface'}
                cursor="pointer"
                onClick={() => setTrackingMode('simple')}
              >
                <Radio value="simple" size="lg">
                  <VStack align="start" spacing={0} ml={2}>
                    <Text fontWeight="semibold">Simple (Balance Only)</Text>
                    <Text fontSize="sm" color="text.secondary">
                      Just track the current balance. You'll update it manually.
                    </Text>
                  </VStack>
                </Radio>
              </Box>

              <Box
                p={4}
                borderWidth={2}
                borderRadius="md"
                borderColor={trackingMode === 'detailed' ? 'blue.500' : 'border.default'}
                bg={trackingMode === 'detailed' ? 'bg.info' : 'bg.surface'}
                cursor="pointer"
                onClick={() => setTrackingMode('detailed')}
              >
                <Radio value="detailed" size="lg">
                  <VStack align="start" spacing={0} ml={2}>
                    <Text fontWeight="semibold">Detailed (Principal + APY)</Text>
                    <Text fontSize="sm" color="text.secondary">
                      Track principal, APY, and compounding. We'll calculate interest for you.
                    </Text>
                  </VStack>
                </Radio>
              </Box>
            </Stack>
          </RadioGroup>
        </FormControl>

        <Divider />

        {/* Simple Mode Fields */}
        {trackingMode === 'simple' && (
          <FormControl isInvalid={!!errors.balance}>
            <FormLabel>Current Balance</FormLabel>
            <Controller
              name="balance"
              control={control}
              render={({ field: { onChange, value, ...field } }) => (
                <NumberInput
                  {...field}
                  value={value as number}
                  onChange={(valueString) => onChange(parseFloat(valueString) || 0)}
                  min={0}
                  precision={2}
                >
                  <NumberInputField placeholder="e.g., 10500.00" />
                </NumberInput>
              )}
            />
            <FormHelperText>
              You'll update this balance manually based on your bank statements.
            </FormHelperText>
            <FormErrorMessage>{errors.balance?.message}</FormErrorMessage>
          </FormControl>
        )}

        {/* Detailed Mode Fields */}
        {trackingMode === 'detailed' && (
          <>
            {/* Principal Amount */}
            <FormControl isInvalid={!!errors.original_amount}>
              <FormLabel>Principal Amount (Original Deposit)</FormLabel>
              <Controller
                name="original_amount"
                control={control}
                render={({ field: { onChange, value, ...field } }) => (
                  <NumberInput
                    {...field}
                    value={value as number}
                    onChange={(valueString) => onChange(parseFloat(valueString) || 0)}
                    min={0}
                    precision={2}
                  >
                    <NumberInputField placeholder="e.g., 10000.00" />
                  </NumberInput>
                )}
              />
              <FormHelperText>The initial amount you deposited</FormHelperText>
              <FormErrorMessage>{errors.original_amount?.message}</FormErrorMessage>
            </FormControl>

            {/* APY (Annual Percentage Yield) */}
            <FormControl isInvalid={!!errors.interest_rate}>
              <FormLabel>APY (Annual Percentage Yield)</FormLabel>
              <Controller
                name="interest_rate"
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
                    <NumberInputField placeholder="e.g., 5.00" />
                  </NumberInput>
                )}
              />
              <FormHelperText>Annual interest rate as a percentage (e.g., 5.00%)</FormHelperText>
              <FormErrorMessage>{errors.interest_rate?.message}</FormErrorMessage>
            </FormControl>

            {/* Compounding Frequency */}
            <FormControl isInvalid={!!errors.compounding_frequency}>
              <FormLabel>Compounding Frequency</FormLabel>
              <Select {...register('compounding_frequency')}>
                <option value="daily">Daily</option>
                <option value="monthly">Monthly</option>
                <option value="quarterly">Quarterly</option>
                <option value="at_maturity">At Maturity (Simple Interest)</option>
              </Select>
              <FormHelperText>How often interest is compounded</FormHelperText>
              <FormErrorMessage>{errors.compounding_frequency?.message}</FormErrorMessage>
            </FormControl>

            {/* Origination Date */}
            <FormControl isInvalid={!!errors.origination_date}>
              <FormLabel>Opening Date</FormLabel>
              <Input type="date" {...register('origination_date')} />
              <FormHelperText>When you opened the CD</FormHelperText>
              <FormErrorMessage>{errors.origination_date?.message}</FormErrorMessage>
            </FormControl>

            {/* Maturity Date */}
            <FormControl isInvalid={!!errors.maturity_date}>
              <FormLabel>Maturity Date</FormLabel>
              <Input type="date" {...register('maturity_date')} />
              <FormHelperText>When the CD matures</FormHelperText>
              <FormErrorMessage>{errors.maturity_date?.message}</FormErrorMessage>
            </FormControl>
          </>
        )}

        <Button
          type="submit"
          colorScheme="blue"
          size="lg"
          w="full"
          isLoading={isLoading}
        >
          Add CD Account
        </Button>
      </VStack>
    </form>
  );
};
