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
  FiBriefcase,
  FiShield,
  FiAward,
  FiPackage,
} from 'react-icons/fi';
import { ArrowBackIcon } from '@chakra-ui/icons';
import { type AccountType, ACCOUNT_TYPES } from '../schemas/manualAccountSchemas';

interface AccountTypeOption {
  type: AccountType;
  label: string;
  description: string;
  icon: any;
  category: 'basic' | 'investment' | 'alternative' | 'insurance' | 'securities' | 'business' | 'property';
}

const accountTypeOptions: AccountTypeOption[] = [
  // Basic accounts - Cash & Checking
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
    type: ACCOUNT_TYPES.MONEY_MARKET,
    label: 'Money Market',
    description: 'Higher-yield savings account',
    icon: FiDollarSign,
    category: 'basic',
  },
  {
    type: ACCOUNT_TYPES.CD,
    label: 'CD',
    description: 'Certificate of deposit',
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
    description: 'Personal loan',
    icon: FiFileText,
    category: 'basic',
  },
  {
    type: ACCOUNT_TYPES.STUDENT_LOAN,
    label: 'Student Loan',
    description: 'Student loan debt',
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
    type: ACCOUNT_TYPES.RETIREMENT_529,
    label: '529 Plan',
    description: 'College savings plan',
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
  {
    type: ACCOUNT_TYPES.PENSION,
    label: 'Pension',
    description: 'Employer pension plan',
    icon: FiTrendingUp,
    category: 'investment',
  },

  // Alternative Investments
  {
    type: ACCOUNT_TYPES.CRYPTO,
    label: 'Cryptocurrency',
    description: 'Digital currency holdings',
    icon: FiTrendingUp,
    category: 'alternative',
  },
  {
    type: ACCOUNT_TYPES.PRIVATE_EQUITY,
    label: 'Private Equity',
    description: 'Company equity, RSUs, and stock options',
    icon: FiBriefcase,
    category: 'alternative',
  },
  {
    type: ACCOUNT_TYPES.PRIVATE_DEBT,
    label: 'Private Debt',
    description: 'Private credit funds and loans made',
    icon: FiFileText,
    category: 'alternative',
  },
  {
    type: ACCOUNT_TYPES.COLLECTIBLES,
    label: 'Collectibles',
    description: 'Art, antiques, and collectibles',
    icon: FiAward,
    category: 'alternative',
  },
  {
    type: ACCOUNT_TYPES.PRECIOUS_METALS,
    label: 'Precious Metals',
    description: 'Gold, silver, and other metals',
    icon: FiPackage,
    category: 'alternative',
  },

  // Securities
  {
    type: ACCOUNT_TYPES.BOND,
    label: 'Bonds',
    description: 'Corporate or government bonds',
    icon: FiFileText,
    category: 'securities',
  },
  {
    type: ACCOUNT_TYPES.STOCK_OPTIONS,
    label: 'Stock Options',
    description: 'Employee stock options',
    icon: FiTrendingUp,
    category: 'securities',
  },

  // Insurance & Annuities
  {
    type: ACCOUNT_TYPES.LIFE_INSURANCE_CASH_VALUE,
    label: 'Life Insurance',
    description: 'Cash value life insurance',
    icon: FiShield,
    category: 'insurance',
  },
  {
    type: ACCOUNT_TYPES.ANNUITY,
    label: 'Annuity',
    description: 'Annuity contracts',
    icon: FiShield,
    category: 'insurance',
  },

  // Business
  {
    type: ACCOUNT_TYPES.BUSINESS_EQUITY,
    label: 'Business Equity',
    description: 'Ownership in a business',
    icon: FiBriefcase,
    category: 'business',
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
  onSelectType: (type: AccountType, category: 'basic' | 'investment' | 'alternative' | 'insurance' | 'securities' | 'business' | 'property') => void;
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

      {/* Alternative Investments */}
      <Box>
        <Text fontSize="sm" fontWeight="bold" color="gray.700" mb={3}>
          Alternative Investments
        </Text>
        <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={4}>
          {accountTypeOptions
            .filter((option) => option.category === 'alternative')
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

      {/* Securities */}
      <Box>
        <Text fontSize="sm" fontWeight="bold" color="gray.700" mb={3}>
          Securities
        </Text>
        <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={4}>
          {accountTypeOptions
            .filter((option) => option.category === 'securities')
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

      {/* Insurance & Annuities */}
      <Box>
        <Text fontSize="sm" fontWeight="bold" color="gray.700" mb={3}>
          Insurance & Annuities
        </Text>
        <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={4}>
          {accountTypeOptions
            .filter((option) => option.category === 'insurance')
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

      {/* Business */}
      <Box>
        <Text fontSize="sm" fontWeight="bold" color="gray.700" mb={3}>
          Business
        </Text>
        <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={4}>
          {accountTypeOptions
            .filter((option) => option.category === 'business')
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
