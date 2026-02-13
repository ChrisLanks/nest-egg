/**
 * Manual account type selection step
 */

import {
  VStack,
  Text,
  SimpleGrid,
  Box,
  Icon,
  Button,
  HStack,
} from '@chakra-ui/react';
import {
  FiDollarSign,
  FiCreditCard,
  FiTrendingUp,
  FiHome,
  FiTruck,
  FiFileText,
} from 'react-icons/fi';
import { ArrowBackIcon } from '@chakra-ui/icons';
import { type AccountType, ACCOUNT_TYPES } from '../schemas/manualAccountSchemas';

interface AccountTypeOption {
  type: AccountType;
  label: string;
  description: string;
  icon: any;
  category: 'basic' | 'investment' | 'property';
}

const accountTypeOptions: AccountTypeOption[] = [
  // Basic accounts
  {
    type: ACCOUNT_TYPES.CHECKING,
    label: 'Checking',
    description: 'Day-to-day spending account',
    icon: FiDollarSign,
    category: 'basic',
  },
  {
    type: ACCOUNT_TYPES.SAVINGS,
    label: 'Savings',
    description: 'Savings and emergency funds',
    icon: FiDollarSign,
    category: 'basic',
  },
  {
    type: ACCOUNT_TYPES.CREDIT_CARD,
    label: 'Credit Card',
    description: 'Credit card balance',
    icon: FiCreditCard,
    category: 'basic',
  },
  {
    type: ACCOUNT_TYPES.LOAN,
    label: 'Loan',
    description: 'Personal or student loan',
    icon: FiFileText,
    category: 'basic',
  },
  {
    type: ACCOUNT_TYPES.MORTGAGE,
    label: 'Mortgage',
    description: 'Home mortgage loan',
    icon: FiHome,
    category: 'basic',
  },

  // Investment accounts
  {
    type: ACCOUNT_TYPES.BROKERAGE,
    label: 'Brokerage',
    description: 'Investment brokerage account',
    icon: FiTrendingUp,
    category: 'investment',
  },
  {
    type: ACCOUNT_TYPES.RETIREMENT_401K,
    label: '401(k)',
    description: 'Employer 401(k) retirement account',
    icon: FiTrendingUp,
    category: 'investment',
  },
  {
    type: ACCOUNT_TYPES.RETIREMENT_IRA,
    label: 'IRA',
    description: 'Traditional IRA retirement account',
    icon: FiTrendingUp,
    category: 'investment',
  },
  {
    type: ACCOUNT_TYPES.RETIREMENT_ROTH,
    label: 'Roth IRA',
    description: 'Roth IRA retirement account',
    icon: FiTrendingUp,
    category: 'investment',
  },
  {
    type: ACCOUNT_TYPES.HSA,
    label: 'HSA',
    description: 'Health savings account',
    icon: FiTrendingUp,
    category: 'investment',
  },

  // Property
  {
    type: ACCOUNT_TYPES.PROPERTY,
    label: 'Property',
    description: 'Home or real estate',
    icon: FiHome,
    category: 'property',
  },
  {
    type: ACCOUNT_TYPES.VEHICLE,
    label: 'Vehicle',
    description: 'Car, truck, or other vehicle',
    icon: FiTruck,
    category: 'property',
  },

  // Other
  {
    type: ACCOUNT_TYPES.MANUAL,
    label: 'Other',
    description: 'Any other account type',
    icon: FiFileText,
    category: 'basic',
  },
];

interface ManualAccountTypeStepProps {
  onSelectType: (type: AccountType, category: 'basic' | 'investment' | 'property') => void;
  onBack: () => void;
}

export const ManualAccountTypeStep = ({ onSelectType, onBack }: ManualAccountTypeStepProps) => {
  return (
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

      <Text fontSize="md" color="gray.600">
        Select the type of account you want to add
      </Text>

      {/* Basic Accounts */}
      <Box>
        <Text fontSize="sm" fontWeight="bold" color="gray.700" mb={3}>
          Basic Accounts
        </Text>
        <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={4}>
          {accountTypeOptions
            .filter((option) => option.category === 'basic')
            .map((option) => (
              <Box
                key={option.type}
                as="button"
                onClick={() => onSelectType(option.type, option.category)}
                p={4}
                borderWidth={2}
                borderRadius="md"
                borderColor="gray.200"
                _hover={{
                  borderColor: 'brand.500',
                  bg: 'brand.50',
                  transform: 'translateY(-2px)',
                  shadow: 'md',
                }}
                transition="all 0.2s"
                cursor="pointer"
                textAlign="left"
              >
                <HStack spacing={3} align="start">
                  <Icon as={option.icon} boxSize={5} color="brand.500" mt={1} />
                  <VStack align="start" spacing={1} flex={1}>
                    <Text fontWeight="bold" fontSize="sm">
                      {option.label}
                    </Text>
                    <Text fontSize="xs" color="gray.600">
                      {option.description}
                    </Text>
                  </VStack>
                </HStack>
              </Box>
            ))}
        </SimpleGrid>
      </Box>

      {/* Investment Accounts */}
      <Box>
        <Text fontSize="sm" fontWeight="bold" color="gray.700" mb={3}>
          Investment Accounts
        </Text>
        <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={4}>
          {accountTypeOptions
            .filter((option) => option.category === 'investment')
            .map((option) => (
              <Box
                key={option.type}
                as="button"
                onClick={() => onSelectType(option.type, option.category)}
                p={4}
                borderWidth={2}
                borderRadius="md"
                borderColor="gray.200"
                _hover={{
                  borderColor: 'brand.500',
                  bg: 'brand.50',
                  transform: 'translateY(-2px)',
                  shadow: 'md',
                }}
                transition="all 0.2s"
                cursor="pointer"
                textAlign="left"
              >
                <HStack spacing={3} align="start">
                  <Icon as={option.icon} boxSize={5} color="brand.500" mt={1} />
                  <VStack align="start" spacing={1} flex={1}>
                    <Text fontWeight="bold" fontSize="sm">
                      {option.label}
                    </Text>
                    <Text fontSize="xs" color="gray.600">
                      {option.description}
                    </Text>
                  </VStack>
                </HStack>
              </Box>
            ))}
        </SimpleGrid>
      </Box>

      {/* Property Accounts */}
      <Box>
        <Text fontSize="sm" fontWeight="bold" color="gray.700" mb={3}>
          Property & Vehicles
        </Text>
        <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={4}>
          {accountTypeOptions
            .filter((option) => option.category === 'property')
            .map((option) => (
              <Box
                key={option.type}
                as="button"
                onClick={() => onSelectType(option.type, option.category)}
                p={4}
                borderWidth={2}
                borderRadius="md"
                borderColor="gray.200"
                _hover={{
                  borderColor: 'brand.500',
                  bg: 'brand.50',
                  transform: 'translateY(-2px)',
                  shadow: 'md',
                }}
                transition="all 0.2s"
                cursor="pointer"
                textAlign="left"
              >
                <HStack spacing={3} align="start">
                  <Icon as={option.icon} boxSize={5} color="brand.500" mt={1} />
                  <VStack align="start" spacing={1} flex={1}>
                    <Text fontWeight="bold" fontSize="sm">
                      {option.label}
                    </Text>
                    <Text fontSize="xs" color="gray.600">
                      {option.description}
                    </Text>
                  </VStack>
                </HStack>
              </Box>
            ))}
        </SimpleGrid>
      </Box>
    </VStack>
  );
};
