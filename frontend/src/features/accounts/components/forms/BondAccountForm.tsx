/**
 * Form for adding Bond accounts (corporate bonds, municipal bonds, treasury bonds, I-Bonds)
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
  Box,
  Alert,
  AlertIcon,
} from '@chakra-ui/react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { ArrowBackIcon } from '@chakra-ui/icons';
import { z } from 'zod';

// Bond Account schema
const bondAccountSchema = z.object({
  name: z.string().min(1, 'Bond name is required'),
  institution: z.string().optional(),
  account_number_last4: z.string().max(4).optional(),
  account_type: z.literal('bond'),
  bond_type: z.enum(['corporate', 'municipal', 'treasury', 'i_bond', 'other']),
  principal: z.number().or(z.string().transform((val) => parseFloat(val))).refine((val) => val > 0, 'Principal must be greater than 0'),
  interest_rate: z.number().or(z.string().transform((val) => parseFloat(val))).optional(),
  maturity_date: z.string().optional(),
  current_value: z.number().or(z.string().transform((val) => parseFloat(val))).optional(),
  notes: z.string().optional(),
});

type BondAccountFormData = z.infer<typeof bondAccountSchema>;

interface BondAccountFormProps {
  onSubmit: (data: any) => void;
  onBack: () => void;
  isLoading?: boolean;
}

export const BondAccountForm = ({ onSubmit, onBack, isLoading }: BondAccountFormProps) => {
  const {
    register,
    handleSubmit,
    control,
    watch,
    formState: { errors },
  } = useForm<BondAccountFormData>({
    resolver: zodResolver(bondAccountSchema),
    defaultValues: {
      account_type: 'bond',
      bond_type: 'corporate',
    },
  });

  const bondType = watch('bond_type');
  const principal = watch('principal');
  const currentValue = watch('current_value');

  const handleFormSubmit = (data: BondAccountFormData) => {
    const submitData: any = {
      name: data.name,
      institution: data.institution,
      account_number_last4: data.account_number_last4,
      account_type: 'bond',
      balance: data.current_value || data.principal || 0,
      original_amount: data.principal,
      interest_rate: data.interest_rate,
      maturity_date: data.maturity_date,
      notes: data.notes,
    };

    onSubmit(submitData);
  };

  // Calculate premium/discount
  const premiumDiscount = currentValue != null && principal != null && principal > 0 ? ((Number(currentValue) - Number(principal)) / Number(principal)) * 100 : 0;

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
          Add Bond
        </Text>

        {/* Bond Name */}
        <FormControl isInvalid={!!errors.name}>
          <FormLabel>Bond Name</FormLabel>
          <Input {...register('name')} placeholder="e.g., US Treasury 10-Year or Corporate Bond XYZ" />
          <FormErrorMessage>{errors.name?.message}</FormErrorMessage>
        </FormControl>

        {/* Bond Type */}
        <FormControl isInvalid={!!errors.bond_type}>
          <FormLabel>Bond Type</FormLabel>
          <Select {...register('bond_type')}>
            <option value="corporate">Corporate Bond</option>
            <option value="municipal">Municipal Bond</option>
            <option value="treasury">Treasury Bond</option>
            <option value="i_bond">I-Bond (Inflation-Protected)</option>
            <option value="other">Other</option>
          </Select>
          <FormErrorMessage>{errors.bond_type?.message}</FormErrorMessage>
        </FormControl>

        {/* I-Bond Warning */}
        {bondType === 'i_bond' && (
          <Alert status="info" borderRadius="md">
            <AlertIcon />
            <Box>
              <Text fontSize="sm" fontWeight="semibold">I-Bond Early Redemption</Text>
              <Text fontSize="xs">
                Redeeming before 5 years incurs a 3-month interest penalty. Enter redemption value as Current Value if applicable.
              </Text>
            </Box>
          </Alert>
        )}

        {/* Issuer/Institution */}
        <FormControl>
          <FormLabel>Issuer/Institution (Optional)</FormLabel>
          <Input {...register('institution')} placeholder="e.g., US Treasury, Apple Inc." />
          <FormHelperText>The entity that issued the bond</FormHelperText>
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

        {/* Principal (Face Value/Par Value) */}
        <FormControl isInvalid={!!errors.principal}>
          <FormLabel>Principal (Face Value)</FormLabel>
          <Controller
            name="principal"
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
          <FormHelperText>The face value (par value) of the bond at maturity</FormHelperText>
          <FormErrorMessage>{errors.principal?.message}</FormErrorMessage>
        </FormControl>

        {/* Current Market Value */}
        <FormControl isInvalid={!!errors.current_value}>
          <FormLabel>Current Market Value (Optional)</FormLabel>
          <Controller
            name="current_value"
            control={control}
            render={({ field: { onChange, value, ...field } }) => (
              <NumberInput
                {...field}
                value={value as number}
                onChange={(valueString) => onChange(parseFloat(valueString) || 0)}
                min={0}
                precision={2}
              >
                <NumberInputField placeholder="e.g., 10250.00" />
              </NumberInput>
            )}
          />
          <FormHelperText>
            Current market value if different from principal (e.g., if trading at premium/discount)
          </FormHelperText>
          <FormErrorMessage>{errors.current_value?.message}</FormErrorMessage>
        </FormControl>

        {/* Show Premium/Discount if different */}
        {premiumDiscount !== 0 && Math.abs(premiumDiscount) > 0.01 && (
          <Box p={3} bg={premiumDiscount > 0 ? 'green.50' : 'red.50'} borderRadius="md" borderWidth={1} borderColor={premiumDiscount > 0 ? 'green.200' : 'red.200'}>
            <Text fontSize="sm" color={premiumDiscount > 0 ? 'green.800' : 'red.800'}>
              {premiumDiscount > 0 ? '📈 Trading at Premium' : '📉 Trading at Discount'}:{' '}
              <Text as="span" fontWeight="bold">
                {premiumDiscount > 0 ? '+' : ''}{premiumDiscount.toFixed(2)}%
              </Text>
            </Text>
          </Box>
        )}

        {/* Interest Rate / Yield */}
        <FormControl isInvalid={!!errors.interest_rate}>
          <FormLabel>Interest Rate / Yield (%) (Optional)</FormLabel>
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
                precision={3}
              >
                <NumberInputField placeholder="e.g., 4.250" />
              </NumberInput>
            )}
          />
          <FormHelperText>Annual interest rate or yield to maturity (YTM) as a percentage</FormHelperText>
          <FormErrorMessage>{errors.interest_rate?.message}</FormErrorMessage>
        </FormControl>

        {/* Maturity Date */}
        <FormControl isInvalid={!!errors.maturity_date}>
          <FormLabel>Maturity Date (Optional)</FormLabel>
          <Input type="date" {...register('maturity_date')} />
          <FormHelperText>Date when the bond reaches maturity</FormHelperText>
          <FormErrorMessage>{errors.maturity_date?.message}</FormErrorMessage>
        </FormControl>

        {/* Notes */}
        <FormControl isInvalid={!!errors.notes}>
          <FormLabel>Notes (Optional)</FormLabel>
          <Input {...register('notes')} placeholder="e.g., Coupon payment dates, call features" />
          <FormHelperText>Additional details like coupon dates, call provisions, etc.</FormHelperText>
          <FormErrorMessage>{errors.notes?.message}</FormErrorMessage>
        </FormControl>

        <Button
          type="submit"
          colorScheme="blue"
          size="lg"
          w="full"
          isLoading={isLoading}
        >
          Add Bond
        </Button>
      </VStack>
    </form>
  );
};
