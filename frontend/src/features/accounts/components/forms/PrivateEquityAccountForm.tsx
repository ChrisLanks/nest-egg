/**
 * Form for adding private equity accounts (RSUs, stock options, company equity)
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
  IconButton,
  Switch,
  Divider,
} from '@chakra-ui/react';
import { useForm, Controller, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { ArrowBackIcon, AddIcon, DeleteIcon } from '@chakra-ui/icons';
import {
  privateEquityAccountSchema,
  type PrivateEquityAccountFormData,
  type VestingMilestone,
} from '../../schemas/manualAccountSchemas';

interface PrivateEquityAccountFormProps {
  onSubmit: (data: PrivateEquityAccountFormData) => void;
  onBack: () => void;
  isLoading?: boolean;
}

export const PrivateEquityAccountForm = ({
  onSubmit,
  onBack,
  isLoading,
}: PrivateEquityAccountFormProps) => {
  const {
    register,
    handleSubmit,
    control,
    watch,
    setValue,
    formState: { errors },
  } = useForm<PrivateEquityAccountFormData>({
    resolver: zodResolver(privateEquityAccountSchema),
    defaultValues: {
      account_type: 'private_equity' as any,
      company_status: 'private',
      vesting_schedule: [],
      include_in_networth: undefined, // Will be auto-determined based on company_status
    },
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'vesting_schedule',
  });

  const grantType = watch('grant_type');
  const quantity = watch('quantity');
  const sharePrice = watch('share_price');
  const companyStatus = watch('company_status');
  const includeInNetworth = watch('include_in_networth');

  // Calculate estimated value
  const estimatedValue = quantity && sharePrice ? Number(quantity) * Number(sharePrice) : 0;

  // Auto-set include_in_networth based on company status if not explicitly set
  const shouldIncludeInNetworth = includeInNetworth !== undefined
    ? includeInNetworth
    : companyStatus === 'public';

  const handleFormSubmit = (data: PrivateEquityAccountFormData) => {
    // Convert vesting_schedule array to JSON string for backend
    const vestingScheduleJson = data.vesting_schedule && data.vesting_schedule.length > 0
      ? JSON.stringify(data.vesting_schedule)
      : undefined;

    const submitData = {
      ...data,
      balance: estimatedValue || data.balance || 0,
      vesting_schedule: vestingScheduleJson as any,
      include_in_networth: data.include_in_networth !== undefined
        ? data.include_in_networth
        : (companyStatus === 'public'),
    };
    onSubmit(submitData);
  };

  const addVestingMilestone = () => {
    append({ date: '', quantity: 0, notes: '' });
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
          Add Private Equity Account
        </Text>

        {/* Company Name */}
        <FormControl isInvalid={!!errors.name}>
          <FormLabel>Company Name</FormLabel>
          <Input {...register('name')} placeholder="e.g., Acme Corp" />
          <FormErrorMessage>{errors.name?.message}</FormErrorMessage>
        </FormControl>

        {/* Institution/Fund (optional) */}
        <FormControl>
          <FormLabel>Institution/Fund (Optional)</FormLabel>
          <Input {...register('institution')} placeholder="e.g., Private fund name" />
        </FormControl>

        {/* Company Status */}
        <FormControl isInvalid={!!errors.company_status}>
          <FormLabel>Company Status</FormLabel>
          <Select {...register('company_status')}>
            <option value="private">Private</option>
            <option value="public">Public</option>
          </Select>
          <FormHelperText>
            {companyStatus === 'private'
              ? 'Private company equity (not publicly traded)'
              : 'Publicly traded company stock'}
          </FormHelperText>
          <FormErrorMessage>{errors.company_status?.message}</FormErrorMessage>
        </FormControl>

        {/* Grant Type */}
        <FormControl isInvalid={!!errors.grant_type}>
          <FormLabel>Grant Type</FormLabel>
          <Select {...register('grant_type')} placeholder="Select grant type">
            <option value="iso">ISO (Incentive Stock Option)</option>
            <option value="nso">NSO (Non-Qualified Stock Option)</option>
            <option value="rsu">RSU (Restricted Stock Unit)</option>
            <option value="rsa">RSA (Restricted Stock Award)</option>
          </Select>
          <FormErrorMessage>{errors.grant_type?.message}</FormErrorMessage>
        </FormControl>

        {/* Grant Date */}
        <FormControl isInvalid={!!errors.grant_date}>
          <FormLabel>Grant Date</FormLabel>
          <Input type="date" {...register('grant_date')} />
          <FormErrorMessage>{errors.grant_date?.message}</FormErrorMessage>
        </FormControl>

        {/* Quantity (Shares/Options) */}
        <FormControl isInvalid={!!errors.quantity}>
          <FormLabel>Quantity (Number of Shares/Options)</FormLabel>
          <Controller
            name="quantity"
            control={control}
            render={({ field }) => (
              <NumberInput {...field} onChange={(_, val) => field.onChange(val)} min={0} step={0.0001}>
                <NumberInputField placeholder="e.g., 10000" />
              </NumberInput>
            )}
          />
          <FormErrorMessage>{errors.quantity?.message}</FormErrorMessage>
        </FormControl>

        {/* Strike Price (for options) */}
        {(grantType === 'iso' || grantType === 'nso') && (
          <FormControl isInvalid={!!errors.strike_price}>
            <FormLabel>Strike Price (Exercise Price)</FormLabel>
            <Controller
              name="strike_price"
              control={control}
              render={({ field }) => (
                <NumberInput {...field} onChange={(_, val) => field.onChange(val)} min={0} precision={4}>
                  <NumberInputField placeholder="e.g., 10.50" />
                </NumberInput>
              )}
            />
            <FormHelperText>Price you must pay to exercise options</FormHelperText>
            <FormErrorMessage>{errors.strike_price?.message}</FormErrorMessage>
          </FormControl>
        )}

        {/* Share Price (Current Valuation) */}
        <FormControl isInvalid={!!errors.share_price}>
          <FormLabel>Current Share Price</FormLabel>
          <Controller
            name="share_price"
            control={control}
            render={({ field }) => (
              <NumberInput {...field} onChange={(_, val) => field.onChange(val)} min={0} precision={4}>
                <NumberInputField placeholder="e.g., 25.00" />
              </NumberInput>
            )}
          />
          <FormHelperText>Most recent valuation per share</FormHelperText>
          <FormErrorMessage>{errors.share_price?.message}</FormErrorMessage>
        </FormControl>

        {/* Valuation Method */}
        <FormControl isInvalid={!!errors.valuation_method}>
          <FormLabel>Valuation Method</FormLabel>
          <Select {...register('valuation_method')} placeholder="Select method">
            <option value="409a">409a (Fair Market Value)</option>
            <option value="preferred">Preferred Price (Last Round)</option>
            <option value="custom">Custom Price</option>
          </Select>
          <FormHelperText>How the share price is determined</FormHelperText>
          <FormErrorMessage>{errors.valuation_method?.message}</FormErrorMessage>
        </FormControl>

        <Divider />

        {/* Vesting Schedule */}
        <Box>
          <FormLabel>Vesting Schedule</FormLabel>
          <FormHelperText mb={3}>
            Define when your equity vests. Add milestones with dates and quantities.
          </FormHelperText>

          <VStack spacing={3} align="stretch">
            {fields.map((field, index) => (
              <Box key={field.id} p={4} borderWidth={1} borderRadius="md" bg="gray.50">
                <HStack spacing={3} align="start">
                  <FormControl flex={1} isInvalid={!!errors.vesting_schedule?.[index]?.date}>
                    <FormLabel fontSize="sm">Vest Date</FormLabel>
                    <Input
                      type="date"
                      size="sm"
                      {...register(`vesting_schedule.${index}.date` as const)}
                    />
                    <FormErrorMessage>
                      {errors.vesting_schedule?.[index]?.date?.message}
                    </FormErrorMessage>
                  </FormControl>

                  <FormControl flex={1} isInvalid={!!errors.vesting_schedule?.[index]?.quantity}>
                    <FormLabel fontSize="sm">Quantity</FormLabel>
                    <Controller
                      name={`vesting_schedule.${index}.quantity` as const}
                      control={control}
                      render={({ field }) => (
                        <NumberInput
                          {...field}
                          onChange={(_, val) => field.onChange(val)}
                          min={0}
                          size="sm"
                        >
                          <NumberInputField placeholder="e.g., 250" />
                        </NumberInput>
                      )}
                    />
                    <FormErrorMessage>
                      {errors.vesting_schedule?.[index]?.quantity?.message}
                    </FormErrorMessage>
                  </FormControl>

                  <FormControl flex={2}>
                    <FormLabel fontSize="sm">Notes (optional)</FormLabel>
                    <Input
                      size="sm"
                      {...register(`vesting_schedule.${index}.notes` as const)}
                      placeholder="e.g., 25% of grant"
                    />
                  </FormControl>

                  <IconButton
                    aria-label="Remove milestone"
                    icon={<DeleteIcon />}
                    size="sm"
                    colorScheme="red"
                    variant="ghost"
                    onClick={() => remove(index)}
                    mt={8}
                  />
                </HStack>
              </Box>
            ))}

            <Button
              leftIcon={<AddIcon />}
              onClick={addVestingMilestone}
              variant="outline"
              size="sm"
              w="fit-content"
            >
              Add Vesting Milestone
            </Button>
          </VStack>
        </Box>

        <Divider />

        {/* Include in Net Worth Toggle */}
        <FormControl display="flex" alignItems="center">
          <FormLabel htmlFor="include-in-networth" mb="0" flex={1}>
            Include in Net Worth & Cash Flow Calculations
          </FormLabel>
          <Controller
            name="include_in_networth"
            control={control}
            render={({ field: { value, onChange } }) => (
              <Switch
                id="include-in-networth"
                isChecked={value !== undefined ? value : (companyStatus === 'public')}
                onChange={(e) => onChange(e.target.checked)}
                colorScheme="blue"
              />
            )}
          />
        </FormControl>
        <FormHelperText mt={-4}>
          {companyStatus === 'private' ? (
            <>Private equity is excluded by default since it's not easily liquidated. Enable this if you want it included in your net worth and cash flow calculations.</>
          ) : (
            <>Public equity is included by default. Vested shares are automatically calculated in your net worth and cash flow.</>
          )}
        </FormHelperText>

        {/* Estimated Value (calculated) */}
        {estimatedValue > 0 && (
          <FormControl>
            <FormLabel>Estimated Value</FormLabel>
            <Input
              value={`$${estimatedValue.toFixed(2)}`}
              isReadOnly
              bg="gray.50"
            />
            <FormHelperText>Calculated from quantity × share price</FormHelperText>
          </FormControl>
        )}

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
