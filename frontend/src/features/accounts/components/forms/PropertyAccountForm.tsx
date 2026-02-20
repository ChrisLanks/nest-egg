/**
 * Form for adding property accounts (homes, real estate)
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
  Link,
  Box,
} from '@chakra-ui/react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { ArrowBackIcon, ExternalLinkIcon } from '@chakra-ui/icons';
import {
  propertyAccountSchema,
  type PropertyAccountFormData,
} from '../../schemas/manualAccountSchemas';

interface PropertyAccountFormProps {
  onSubmit: (data: PropertyAccountFormData) => void;
  onBack: () => void;
  isLoading?: boolean;
}

export const PropertyAccountForm = ({
  onSubmit,
  onBack,
  isLoading,
}: PropertyAccountFormProps) => {
  const {
    register,
    handleSubmit,
    control,
    watch,
    formState: { errors },
  } = useForm<PropertyAccountFormData>({
    resolver: zodResolver(propertyAccountSchema),
    defaultValues: {
      property_classification: 'personal_residence',
      property_type: 'single_family',
    },
  });

  const value = watch('value');
  const mortgageBalance = watch('mortgage_balance');
  const equity = (Number(value) || 0) - (Number(mortgageBalance) || 0);

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
          Add Property
        </Text>

        <FormControl isInvalid={!!errors.name}>
          <FormLabel>Property Name</FormLabel>
          <Input
            {...register('name')}
            placeholder="e.g., Primary Residence"
          />
          <FormErrorMessage>{errors.name?.message}</FormErrorMessage>
        </FormControl>

        <HStack spacing={4} align="start">
          <FormControl isInvalid={!!errors.address} flex={2}>
            <FormLabel>Street Address</FormLabel>
            <Input
              {...register('address')}
              placeholder="e.g., 123 Main St"
            />
            <FormErrorMessage>{errors.address?.message}</FormErrorMessage>
          </FormControl>

          <FormControl isInvalid={!!errors.zip_code} flex={1}>
            <FormLabel>ZIP Code <Text as="span" fontSize="xs" color="gray.500">(optional)</Text></FormLabel>
            <Input
              {...register('zip_code')}
              placeholder="e.g., 94102"
              maxLength={10}
            />
            <FormErrorMessage>{errors.zip_code?.message}</FormErrorMessage>
          </FormControl>
        </HStack>

        <FormControl isInvalid={!!errors.property_classification}>
          <FormLabel>Property Classification</FormLabel>
          <Select {...register('property_classification')}>
            <option value="personal_residence">Personal Residence</option>
            <option value="investment">Investment Property</option>
            <option value="vacation_home">Vacation Home</option>
          </Select>
          <FormErrorMessage>{errors.property_classification?.message}</FormErrorMessage>
          <Text fontSize="xs" color="gray.600" mt={1}>
            This classification affects tax implications and rental income tracking
          </Text>
        </FormControl>

        <FormControl isInvalid={!!errors.property_type}>
          <FormLabel>Property Type</FormLabel>
          <Select {...register('property_type')}>
            <option value="single_family">Single Family Home</option>
            <option value="condo">Condo</option>
            <option value="townhouse">Townhouse</option>
            <option value="multi_family">Multi-Family</option>
            <option value="other">Other</option>
          </Select>
          <FormErrorMessage>{errors.property_type?.message}</FormErrorMessage>
        </FormControl>

        <Box p={4} bg="blue.50" borderRadius="md" borderWidth={1} borderColor="blue.200">
          <Text fontSize="sm" color="blue.800" mb={2}>
            💡 <strong>Need help estimating your home's value?</strong>
          </Text>
          <Text fontSize="sm" color="blue.700">
            Check{' '}
            <Link
              href="https://www.zillow.com"
              isExternal
              color="blue.600"
              fontWeight="medium"
            >
              Zillow.com <ExternalLinkIcon mx="2px" />
            </Link>
            {' '}or{' '}
            <Link
              href="https://www.redfin.com"
              isExternal
              color="blue.600"
              fontWeight="medium"
            >
              Redfin.com <ExternalLinkIcon mx="2px" />
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
                step={1000}
              >
                <NumberInputField placeholder="500000" />
              </NumberInput>
            )}
          />
          <FormErrorMessage>{errors.value?.message}</FormErrorMessage>
        </FormControl>

        <FormControl isInvalid={!!errors.mortgage_balance}>
          <FormLabel>Mortgage Balance (Optional)</FormLabel>
          <Controller
            name="mortgage_balance"
            control={control}
            render={({ field: { onChange, value, ...field } }) => (
              <NumberInput
                {...field}
                value={value as number}
                onChange={(valueString) => onChange(parseFloat(valueString) || 0)}
                precision={0}
                step={1000}
              >
                <NumberInputField placeholder="350000" />
              </NumberInput>
            )}
          />
          <FormErrorMessage>{errors.mortgage_balance?.message}</FormErrorMessage>
          <Text fontSize="xs" color="gray.600" mt={1}>
            Leave blank if you own the property outright
          </Text>
        </FormControl>

        {mortgageBalance && mortgageBalance > 0 && (
          <Box p={3} bg="gray.50" borderRadius="md">
            <HStack justify="space-between">
              <Text fontWeight="semibold">Home Equity:</Text>
              <Text fontSize="lg" fontWeight="bold" color={equity >= 0 ? 'green.600' : 'red.600'}>
                ${equity.toLocaleString()}
              </Text>
            </HStack>
            <Text fontSize="xs" color="gray.600" mt={1}>
              (Property Value - Mortgage Balance)
            </Text>
          </Box>
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
            Add Property
          </Button>
        </HStack>
      </VStack>
    </form>
  );
};
