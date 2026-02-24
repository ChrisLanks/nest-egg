/**
 * Form for adding vehicle accounts (cars, trucks, etc.)
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
  Link,
  Box,
  Switch,
  FormHelperText,
  Divider,
} from '@chakra-ui/react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { ArrowBackIcon, ExternalLinkIcon } from '@chakra-ui/icons';
import {
  vehicleAccountSchema,
  type VehicleAccountFormData,
} from '../../schemas/manualAccountSchemas';

interface VehicleAccountFormProps {
  onSubmit: (data: VehicleAccountFormData) => void;
  onBack: () => void;
  isLoading?: boolean;
}

export const VehicleAccountForm = ({
  onSubmit,
  onBack,
  isLoading,
}: VehicleAccountFormProps) => {
  const {
    register,
    handleSubmit,
    control,
    watch,
    formState: { errors },
  } = useForm<VehicleAccountFormData>({
    resolver: zodResolver(vehicleAccountSchema),
    defaultValues: {
      include_in_networth: false,
    },
  });

  const value = watch('value');
  const loanBalance = watch('loan_balance');
  const equity = (Number(value) || 0) - (Number(loanBalance) || 0);

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
          Add Vehicle
        </Text>

        <FormControl isInvalid={!!errors.name}>
          <FormLabel>Vehicle Name</FormLabel>
          <Input
            {...register('name')}
            placeholder="e.g., 2020 Honda Accord"
          />
          <FormErrorMessage>{errors.name?.message}</FormErrorMessage>
        </FormControl>

        <HStack spacing={4} align="start">
          <FormControl isInvalid={!!errors.make} flex={1}>
            <FormLabel>Make</FormLabel>
            <Input
              {...register('make')}
              placeholder="e.g., Honda"
            />
            <FormErrorMessage>{errors.make?.message}</FormErrorMessage>
          </FormControl>

          <FormControl isInvalid={!!errors.model} flex={1}>
            <FormLabel>Model</FormLabel>
            <Input
              {...register('model')}
              placeholder="e.g., Accord"
            />
            <FormErrorMessage>{errors.model?.message}</FormErrorMessage>
          </FormControl>
        </HStack>

        <HStack spacing={4} align="start">
          <FormControl isInvalid={!!errors.year} flex={1}>
            <FormLabel>Year</FormLabel>
            <Controller
              name="year"
              control={control}
              render={({ field: { onChange, value, ...field } }) => (
                <NumberInput
                  {...field}
                  value={value as number}
                  onChange={(valueString) => onChange(parseInt(valueString, 10) || 0)}
                  min={1900}
                  max={new Date().getFullYear() + 1}
                >
                  <NumberInputField placeholder="2020" />
                </NumberInput>
              )}
            />
            <FormErrorMessage>{errors.year?.message}</FormErrorMessage>
          </FormControl>

          <FormControl isInvalid={!!errors.mileage} flex={1}>
            <FormLabel>Mileage (Optional)</FormLabel>
            <Controller
              name="mileage"
              control={control}
              render={({ field: { onChange, value, ...field } }) => (
                <NumberInput
                  {...field}
                  value={value as number}
                  onChange={(valueString) => onChange(parseInt(valueString, 10) || 0)}
                  min={0}
                >
                  <NumberInputField placeholder="50000" />
                </NumberInput>
              )}
            />
            <FormErrorMessage>{errors.mileage?.message}</FormErrorMessage>
          </FormControl>
        </HStack>

        <FormControl>
          <FormLabel>VIN <Text as="span" fontSize="xs" color="text.muted">(optional — enables auto-valuation)</Text></FormLabel>
          <Input
            {...register('vin')}
            placeholder="e.g., 1HGBH41JXMN109186"
            maxLength={17}
            textTransform="uppercase"
          />
          <Text fontSize="xs" color="text.muted" mt={1}>
            17-character Vehicle Identification Number. Enables automatic market value updates.
          </Text>
        </FormControl>

        <Box p={4} bg="bg.info" borderRadius="md" borderWidth={1} borderColor="blue.200">
          <Text fontSize="sm" color="blue.800" mb={2}>
            💡 <strong>Need help estimating your vehicle's value?</strong>
          </Text>
          <Text fontSize="sm" color="blue.700">
            Check{' '}
            <Link
              href="https://www.kbb.com"
              isExternal
              color="blue.600"
              fontWeight="medium"
            >
              KBB.com <ExternalLinkIcon mx="2px" />
            </Link>
            {' '}or{' '}
            <Link
              href="https://www.edmunds.com"
              isExternal
              color="blue.600"
              fontWeight="medium"
            >
              Edmunds.com <ExternalLinkIcon mx="2px" />
            </Link>
            {' '}for estimates, then enter the value below.
          </Text>
        </Box>

        <FormControl isInvalid={!!errors.value}>
          <FormLabel>Current Value</FormLabel>
          <Controller
            name="value"
            control={control}
            render={({ field: { onChange, value, ...field } }) => (
              <NumberInput
                {...field}
                value={value as number}
                onChange={(valueString) => onChange(parseFloat(valueString) || 0)}
                precision={0}
                step={100}
              >
                <NumberInputField placeholder="25000" />
              </NumberInput>
            )}
          />
          <FormErrorMessage>{errors.value?.message}</FormErrorMessage>
        </FormControl>

        <FormControl isInvalid={!!errors.loan_balance}>
          <FormLabel>Loan Balance (Optional)</FormLabel>
          <Controller
            name="loan_balance"
            control={control}
            render={({ field: { onChange, value, ...field } }) => (
              <NumberInput
                {...field}
                value={value as number}
                onChange={(valueString) => onChange(parseFloat(valueString) || 0)}
                precision={0}
                step={100}
              >
                <NumberInputField placeholder="15000" />
              </NumberInput>
            )}
          />
          <FormErrorMessage>{errors.loan_balance?.message}</FormErrorMessage>
          <Text fontSize="xs" color="text.secondary" mt={1}>
            Leave blank if the vehicle is paid off
          </Text>
        </FormControl>

        {loanBalance && loanBalance > 0 && (
          <Box p={3} bg="bg.subtle" borderRadius="md">
            <HStack justify="space-between">
              <Text fontWeight="semibold">Vehicle Equity:</Text>
              <Text fontSize="lg" fontWeight="bold" color={equity >= 0 ? 'finance.positive' : 'finance.negative'}>
                ${equity.toLocaleString()}
              </Text>
            </HStack>
            <Text fontSize="xs" color="text.secondary" mt={1}>
              (Vehicle Value - Loan Balance)
            </Text>
            {equity < 0 && (
              <Text fontSize="xs" color="red.600" mt={1}>
                ⚠️ Negative equity (upside down on loan)
              </Text>
            )}
          </Box>
        )}

        <Divider />

        <FormControl>
          <HStack justify="space-between" align="center">
            <FormLabel htmlFor="vehicle-include-networth" mb="0">
              Count as Investment in Net Worth
            </FormLabel>
            <Controller
              name="include_in_networth"
              control={control}
              render={({ field }) => (
                <Switch
                  id="vehicle-include-networth"
                  isChecked={field.value ?? false}
                  onChange={field.onChange}
                  colorScheme="blue"
                />
              )}
            />
          </HStack>
          <FormHelperText>
            Vehicles typically depreciate and are excluded from net worth by default. Enable this for classic or collectible vehicles you consider an investment.
          </FormHelperText>
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
            Add Vehicle
          </Button>
        </HStack>
      </VStack>
    </form>
  );
};
