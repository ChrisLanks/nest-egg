/**
 * Source selection step for adding accounts
 */

import {
  VStack,
  Text,
  SimpleGrid,
  Box,
  Icon,
} from '@chakra-ui/react';
import { FiLink, FiEdit3 } from 'react-icons/fi';

export type AccountSource = 'plaid' | 'mx' | 'manual';

interface SourceSelectionStepProps {
  onSelectSource: (source: AccountSource) => void;
}

export const SourceSelectionStep = ({ onSelectSource }: SourceSelectionStepProps) => {
  return (
    <VStack spacing={6} align="stretch">
      <Text fontSize="md" color="gray.600">
        Choose how you'd like to add your account
      </Text>

      <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
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
            <Text fontWeight="bold">Connect Account</Text>
            <Text fontSize="sm" color="gray.600" textAlign="center">
              Securely link your financial accounts for automatic syncing
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
            <Text fontWeight="bold">Connect via MX</Text>
            <Text fontSize="sm" color="gray.600" textAlign="center">
              Alternative secure connection method
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
            <Text fontWeight="bold">Add Manually</Text>
            <Text fontSize="sm" color="gray.600" textAlign="center">
              Enter account details yourself
            </Text>
          </VStack>
        </Box>
      </SimpleGrid>
    </VStack>
  );
};
