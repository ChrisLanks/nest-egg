/**
 * Source selection step for adding accounts
 */

import {
  VStack,
  Text,
  SimpleGrid,
  Box,
  Icon,
  Badge,
} from '@chakra-ui/react';
import { FiLink, FiEdit3, FiDollarSign } from 'react-icons/fi';

export type AccountSource = 'plaid' | 'teller' | 'mx' | 'manual';

interface SourceSelectionStepProps {
  onSelectSource: (source: AccountSource) => void;
}

export const SourceSelectionStep = ({ onSelectSource }: SourceSelectionStepProps) => {
  return (
    <VStack spacing={6} align="stretch">
      <Text fontSize="md" color="gray.600">
        Choose how you'd like to add your account
      </Text>

      <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={4}>
        {/* Plaid */}
        <Box
          as="button"
          onClick={() => onSelectSource('plaid')}
          p={6}
          borderWidth={2}
          borderRadius="lg"
          borderColor="gray.200"
          _hover={{
            borderColor: 'brand.500',
            bg: 'brand.50',
            transform: 'translateY(-2px)',
            shadow: 'md',
          }}
          transition="all 0.2s"
          cursor="pointer"
        >
          <VStack spacing={3}>
            <Icon as={FiLink} boxSize={8} color="brand.500" />
            <Text fontWeight="bold">Plaid</Text>
            <Text fontSize="sm" color="gray.600" textAlign="center">
              11,000+ institutions. Comprehensive support.
            </Text>
          </VStack>
        </Box>

        {/* Teller */}
        <Box
          as="button"
          onClick={() => onSelectSource('teller')}
          p={6}
          borderWidth={2}
          borderRadius="lg"
          borderColor="gray.200"
          _hover={{
            borderColor: 'green.500',
            bg: 'green.50',
            transform: 'translateY(-2px)',
            shadow: 'md',
          }}
          transition="all 0.2s"
          cursor="pointer"
          position="relative"
        >
          <Badge
            position="absolute"
            top={2}
            right={2}
            colorScheme="green"
            fontSize="xs"
          >
            100 FREE
          </Badge>
          <VStack spacing={3}>
            <Icon as={FiDollarSign} boxSize={8} color="green.500" />
            <Text fontWeight="bold">Teller</Text>
            <Text fontSize="sm" color="gray.600" textAlign="center">
              100 free accounts/month. Simple & affordable.
            </Text>
          </VStack>
        </Box>

        {/* MX (Optional - can be enabled later) */}
        <Box
          as="button"
          onClick={(e: React.MouseEvent) => e.preventDefault()}
          p={6}
          borderWidth={2}
          borderRadius="lg"
          borderColor="gray.200"
          transition="all 0.2s"
          cursor="not-allowed"
          opacity={0.6}
        >
          <VStack spacing={3}>
            <Icon as={FiLink} boxSize={8} color="brand.500" />
            <Text fontWeight="bold">MX</Text>
            <Text fontSize="sm" color="gray.600" textAlign="center">
              Alternative provider
            </Text>
            <Text fontSize="xs" color="gray.500">
              Coming soon
            </Text>
          </VStack>
        </Box>

        {/* Manual */}
        <Box
          as="button"
          onClick={() => onSelectSource('manual')}
          p={6}
          borderWidth={2}
          borderRadius="lg"
          borderColor="gray.200"
          _hover={{
            borderColor: 'brand.500',
            bg: 'brand.50',
            transform: 'translateY(-2px)',
            shadow: 'md',
          }}
          transition="all 0.2s"
          cursor="pointer"
        >
          <VStack spacing={3}>
            <Icon as={FiEdit3} boxSize={8} color="brand.500" />
            <Text fontWeight="bold">Manual</Text>
            <Text fontSize="sm" color="gray.600" textAlign="center">
              Enter account details yourself
            </Text>
          </VStack>
        </Box>
      </SimpleGrid>
    </VStack>
  );
};
