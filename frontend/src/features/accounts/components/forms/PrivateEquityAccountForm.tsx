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
  Switch,
  Divider,
  Box,
  IconButton,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
} from '@chakra-ui/react';
import { AddIcon, DeleteIcon } from '@chakra-ui/icons';
import { useForm, Controller, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { ArrowBackIcon } from '@chakra-ui/icons';
import {
  privateEquityAccountSchema,
  type PrivateEquityAccountFormData,
} from '../../schemas/manualAccountSchemas';

interface PrivateEquityAccountFormProps {
  onSubmit: (data: PrivateEquityAccountFormData) => void;
  onBack: () => void;
  isLoading?: boolean;
  defaultAccountType?: 'private_equity' | 'stock_options';
}

/**
 * Controlled decimal input that allows the user to type a period without it
 * being stripped. We keep valueString as the displayed value and only parse
 * to a number when the field loses focus or the form is submitted.
 */
function DecimalInput({
  value,
  onChange,
  placeholder,
  min = 0,
  precision = 2,
}: {
  value: number | string | undefined;
  onChange: (v: number | undefined) => void;
  placeholder?: string;
  min?: number;
  precision?: number;
}) {
  return (
    <NumberInput
      value={value ?? ''}
      onChange={(valueString) => {
        // Pass through raw string so user can type "25." without it snapping to 25
        // The actual numeric value is parsed on change for downstream calcs,
        // but we store the string display value via the underlying input ref.
        const parsed = parseFloat(valueString);
        onChange(isNaN(parsed) ? undefined : parsed);
      }}
      min={min}
      precision={precision}
      // Allow typing a trailing period by using the string-based display
      format={(v) => (v === '' ? '' : String(v))}
      parse={(v) => v} // keep as-is so the field doesn't strip trailing "."
    >
      <NumberInputField placeholder={placeholder} />
    </NumberInput>
  );
}

export const PrivateEquityAccountForm = ({
  onSubmit,
  onBack,
  isLoading,
  defaultAccountType = 'private_equity',
}: PrivateEquityAccountFormProps) => {
  const {
    register,
    handleSubmit,
    control,
    watch,
    formState: { errors },
  } = useForm<PrivateEquityAccountFormData>({
    resolver: zodResolver(privateEquityAccountSchema),
    defaultValues: {
      account_type: defaultAccountType,
      name: '',
      company_status: 'private',
      balance: 0,
      vesting_schedule: [],
    },
  });

  // Dynamic vesting schedule rows
  const { fields: vestFields, append: appendVest, remove: removeVest } = useFieldArray({
    control,
    name: 'vesting_schedule',
  });

  const grantType = watch('grant_type');
  const quantity = watch('quantity');
  const sharePrice = watch('share_price');
  const companyStatus = watch('company_status');

  const isOptions = grantType === 'iso' || grantType === 'nso';
  const hasVesting = grantType === 'iso' || grantType === 'nso' || grantType === 'rsu' || grantType === 'rsa';

  // Calculate estimated value
  const estimatedValue =
    quantity != null && sharePrice != null ? Number(quantity) * Number(sharePrice) : 0;

  const handleFormSubmit = (data: PrivateEquityAccountFormData) => {
    const vestingScheduleJson =
      data.vesting_schedule && data.vesting_schedule.length > 0
        ? JSON.stringify(data.vesting_schedule)
        : undefined;

    const submitData = {
      ...data,
      balance: estimatedValue || data.balance || 0,
      vesting_schedule: vestingScheduleJson as any,
      include_in_networth:
        data.include_in_networth !== undefined
          ? data.include_in_networth
          : companyStatus === 'public',
    };

    onSubmit(submitData);
  };

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)}>
      <VStack spacing={6} align="stretch">
        <HStack>
          <Button variant="ghost" leftIcon={<ArrowBackIcon />} onClick={onBack} size="sm">
            Back
          </Button>
        </HStack>

        <Text fontSize="lg" fontWeight="bold">
          {defaultAccountType === 'stock_options' ? 'Add Stock Options' : 'Add Private Equity Account'}
        </Text>

        {/* Company Name */}
        <FormControl isInvalid={!!errors.name} isRequired>
          <FormLabel>Company Name</FormLabel>
          <Input {...register('name')} placeholder="e.g., Acme Corp" />
          <FormErrorMessage>{errors.name?.message}</FormErrorMessage>
        </FormControl>

        {/* Institution/Fund */}
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
          <FormLabel>Grant Type (Optional)</FormLabel>
          <Select {...register('grant_type')} placeholder="Select grant type">
            <option value="iso">ISO (Incentive Stock Option)</option>
            <option value="nso">NSO (Non-Qualified Stock Option)</option>
            <option value="rsu">RSU (Restricted Stock Unit)</option>
            <option value="rsa">RSA (Restricted Stock Award)</option>
            <option value="profit_interest">Profits Interest (LLC Units)</option>
          </Select>
          <FormErrorMessage>{errors.grant_type?.message}</FormErrorMessage>
        </FormControl>

        {/* Grant Date */}
        <FormControl isInvalid={!!errors.grant_date}>
          <FormLabel>Grant Date (Optional)</FormLabel>
          <Input type="date" {...register('grant_date')} />
          <FormErrorMessage>{errors.grant_date?.message}</FormErrorMessage>
        </FormControl>

        {/* Quantity */}
        <FormControl isInvalid={!!errors.quantity}>
          <FormLabel>Quantity (Number of Shares/Options)</FormLabel>
          <Controller
            name="quantity"
            control={control}
            render={({ field }) => (
              <DecimalInput
                value={field.value}
                onChange={field.onChange}
                placeholder="e.g., 10000"
                precision={4}
              />
            )}
          />
          <FormErrorMessage>{errors.quantity?.message}</FormErrorMessage>
        </FormControl>

        {/* Strike Price (for ISO/NSO) */}
        {isOptions && (
          <FormControl isInvalid={!!errors.strike_price}>
            <FormLabel>Strike Price (Exercise Price)</FormLabel>
            <Controller
              name="strike_price"
              control={control}
              render={({ field }) => (
                <DecimalInput
                  value={field.value}
                  onChange={field.onChange}
                  placeholder="e.g., 10.50"
                  precision={4}
                />
              )}
            />
            <FormHelperText>Price you must pay to exercise options</FormHelperText>
            <FormErrorMessage>{errors.strike_price?.message}</FormErrorMessage>
          </FormControl>
        )}

        {/* Share Price */}
        <FormControl isInvalid={!!errors.share_price}>
          <FormLabel>Current Share Price</FormLabel>
          <Controller
            name="share_price"
            control={control}
            render={({ field }) => (
              <DecimalInput
                value={field.value}
                onChange={field.onChange}
                placeholder="e.g., 25.00"
                precision={4}
              />
            )}
          />
          <FormHelperText>Most recent valuation per share</FormHelperText>
          <FormErrorMessage>{errors.share_price?.message}</FormErrorMessage>
        </FormControl>

        {/* Valuation Method */}
        <FormControl isInvalid={!!errors.valuation_method}>
          <FormLabel>Valuation Method (Optional)</FormLabel>
          <Select {...register('valuation_method')} placeholder="Select method">
            <option value="409a">409a (Fair Market Value)</option>
            <option value="preferred">Preferred Price (Last Round)</option>
            <option value="custom">Custom Price</option>
          </Select>
          <FormHelperText>How the share price is determined</FormHelperText>
          <FormErrorMessage>{errors.valuation_method?.message}</FormErrorMessage>
        </FormControl>

        {/* Vesting Schedule — shown for ISO, NSO, RSU, RSA */}
        {hasVesting && (
          <>
            <Divider />
            <Box>
              <HStack justify="space-between" mb={2}>
                <Box>
                  <Text fontWeight="semibold" fontSize="sm">Vesting Schedule</Text>
                  <Text fontSize="xs" color="text.secondary" mt={0.5}>
                    Add each vest event — date and number of shares that vest on that date.
                    {isOptions && ' For a standard 4-year / 1-year cliff, add the cliff date then quarterly milestones.'}
                  </Text>
                </Box>
                <Button
                  size="xs"
                  leftIcon={<AddIcon />}
                  variant="outline"
                  onClick={() => appendVest({ date: '', quantity: 0, notes: '' })}
                >
                  Add Event
                </Button>
              </HStack>

              {vestFields.length === 0 ? (
                <Text fontSize="xs" color="text.muted" py={2}>
                  No vest events added. Click "Add Event" to build your schedule.
                </Text>
              ) : (
                <Box overflowX="auto">
                  <Table size="sm" variant="simple">
                    <Thead>
                      <Tr>
                        <Th>Vest Date</Th>
                        <Th isNumeric>Shares</Th>
                        <Th>Notes (optional)</Th>
                        <Th />
                      </Tr>
                    </Thead>
                    <Tbody>
                      {vestFields.map((field, index) => (
                        <Tr key={field.id}>
                          <Td minW="150px">
                            <Input
                              type="date"
                              size="sm"
                              {...register(`vesting_schedule.${index}.date`)}
                            />
                          </Td>
                          <Td minW="120px">
                            <Controller
                              name={`vesting_schedule.${index}.quantity`}
                              control={control}
                              render={({ field: f }) => (
                                <DecimalInput
                                  value={f.value}
                                  onChange={f.onChange}
                                  placeholder="250"
                                  precision={4}
                                />
                              )}
                            />
                          </Td>
                          <Td minW="160px">
                            <Input
                              size="sm"
                              placeholder="e.g., Cliff"
                              {...register(`vesting_schedule.${index}.notes`)}
                            />
                          </Td>
                          <Td>
                            <IconButton
                              aria-label="Remove vest event"
                              icon={<DeleteIcon />}
                              size="xs"
                              variant="ghost"
                              colorScheme="red"
                              onClick={() => removeVest(index)}
                            />
                          </Td>
                        </Tr>
                      ))}
                    </Tbody>
                  </Table>
                </Box>
              )}
            </Box>
          </>
        )}

        <Divider />

        {/* Include in Net Worth Toggle */}
        <FormControl>
          <HStack justify="space-between" align="center">
            <FormLabel htmlFor="include-in-networth" mb="0">
              Include in Net Worth & Cash Flow Calculations
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
            {companyStatus === 'private'
              ? "Private equity is excluded by default since it's not easily liquidated. Enable if you want it counted in your net worth."
              : 'Public equity is included by default. Vested shares are automatically calculated in your net worth.'}
          </FormHelperText>
        </FormControl>

        {/* Estimated Value */}
        {estimatedValue > 0 && (
          <FormControl>
            <FormLabel>Estimated Value</FormLabel>
            <Input
              value={`$${estimatedValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
              isReadOnly
              bg="bg.subtle"
            />
            <FormHelperText>Calculated from quantity × share price</FormHelperText>
          </FormControl>
        )}

        <Button type="submit" colorScheme="blue" size="lg" w="full" isLoading={isLoading}>
          Add Account
        </Button>
      </VStack>
    </form>
  );
};
